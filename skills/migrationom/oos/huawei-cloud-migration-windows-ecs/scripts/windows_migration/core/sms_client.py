#!/usr/bin/env python3
"""
SMS 控制面客户端 — 基于 KooCLI (hcloud) 封装，与 OBSSigner(obsutil) 同一模式。

设计原则（遵循仓库零硬编码架构）：
  - 凭据不落盘：AK/SK 每次调用经环境变量注入 hcloud，不写 hcloud 配置文件
  - 环境数据运行时发现：project_id / domain_id 通过 IAM 自动获取，不硬编码
  - 区域、任务参数全部来自 config/migrate.yaml（sms_agent + sms_task 段）
  - 统一异常：任何非零退出 / JSON 解析失败 / USE_ERROR 均抛 SmsApiError

调用示例:
  client = SmsClient(ak=cfg.sms_agent.ak, sk=cfg.sms_agent.sk, region=cfg.sms_task.region)
  servers = client.list_servers({"ip": "x.x.x.x"})
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field

from core.exceptions import SmsApiError

logger = logging.getLogger(__name__)

# KooCLI 7.2.x 实测：UpdateTaskStatus 的 operation 枚举仅支持以下值（不含 syncing/cutover）：
#   start | stop | test | clone_test | restart | network_check | clear | skip | migration_test
# 说明：
#   - 创建任务时传 syncing=false（config sms_task.syncing），全量复制完成即 MIGRATE_SUCCESS，
#     控制台/旧 SDK 的持续同步 + cutover 语义在 KooCLI 7.2.x 下不可用，无需也不应再执行 sync/cutover。
#   - “等效割接”（退出持续同步并启动目的端）→ 直接调用 ecs_start() 启动目的端 ECS。
#   - “清理快照资源”对应 clear（cmd_cleanup 已使用）。
UPDATE_TASK_STATUS_OPS = ("start", "stop", "test", "clone_test", "restart",
                          "network_check", "clear", "skip", "migration_test")


@dataclass
class SmsClient:
    """SMS / IAM / ECS 控制面客户端（hcloud CLI 包装，线程安全=每次独立子进程）。"""
    ak: str
    sk: str
    region: str
    _project_id: str = field(default="", repr=False)
    _domain_id: str = field(default="", repr=False)

    # ---- 基础调用 ----

    def _call(self, operation: str, params: dict | None = None,
              service: str = "SMS", timeout: int = 120) -> dict:
        """执行 hcloud <service> <operation>。None/空值参数自动跳过。"""
        cmd = ["hcloud", service, operation, f"--cli-region={self.region}",
              f"--cli-access-key={self.ak}", f"--cli-secret-key={self.sk}"]
        for k, v in (params or {}).items():
            if v is None or v == "":
                continue
            if isinstance(v, (list, tuple)):
                # KooCLI 列表参数格式: --k.1=value1 --k.2=value2 ...
                for i, item in enumerate(v, start=1):
                    if item is None or item == "":
                        continue
                    cmd.append(f"--{k}.{i}={item}")
            else:
                cmd.append(f"--{k}={v}")

        env = dict(os.environ)
        env["HWCLOUD_ACCESS_KEY"] = self.ak
        env["HWCLOUD_SECRET_KEY"] = self.sk

        # 安全: debug 日志禁止打印完整 AK/SK（仅输出 service/operation/region）
        logger.debug("hcloud 调用: %s %s (region=%s, 凭据已打码)", service, operation, self.region)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            raise SmsApiError(f"hcloud {service} {operation} 超时({timeout}s)")

        out = (r.stdout or "").strip()
        # KooCLI 的 USE_ERROR 信息输出到 stdout 且退出码可能为 0，需显式识别
        if "USE_ERROR" in out or "is not supported" in out:
            raise SmsApiError(f"hcloud 参数错误: {out[:300]}")

        if r.returncode != 0:
            raise SmsApiError(
                f"hcloud {service} {operation} 失败: {(r.stderr or r.stdout or '')[:300]}",
                detail={"returncode": r.returncode},
            )

        if not out:
            return {}
        try:
            # KooCLI 对多版本 API 会在 stdout 打印提示行后再输出 JSON，需定位首个 '{'
            start = out.find("{")
            blob = out[start:] if start >= 0 else out
            return json.loads(blob)
        except json.JSONDecodeError:
            # 识别业务错误（SMS.xxxx/Ecs.xxxx）→ 抛 SmsApiError，杜绝静默吞错
            for tag in ("error_code", "error_msg", "error"):
                import re as _re
                m = _re.search(rf'"{tag}"\s*:\s*"([^"]+)"', out)
                if m:
                    raise SmsApiError(f"hcloud {service} {operation} 业务错误: {m.group(1)}",
                                      detail={"raw": out[:500]})
            # 个别操作输出非 JSON（如日志类），原样返回
            return {"_raw": out}

    # ---- 账号 / 项目（运行时自动发现，零硬编码）----

    def project(self) -> tuple[str, str]:
        """发现项目 ID 与账号 ID（当前区域系统项目），结果缓存。"""
        if self._project_id and self._domain_id:
            return self._project_id, self._domain_id
        data = self._call("KeystoneListProjects", {"name": self.region}, service="IAM")
        for pj in data.get("projects") or []:
            if pj.get("name") == self.region:
                self._project_id = pj.get("id", "")
                self._domain_id = pj.get("domain_id", "")
                break
        if not self._project_id:
            raise SmsApiError(f"未发现区域 {self.region} 的项目 ID（检查 AK/SK 权限）")
        logger.info("项目/账号发现: project=%s domain=%s", self._project_id, self._domain_id[-6:])
        return self._project_id, self._domain_id

    # ---- SMS 查询 ----

    def list_servers(self, filters: dict | None = None) -> dict:
        return self._call("ListServers", filters or {})

    def find_source_server(self, ip: str = "") -> dict:
        """
        定位已注册的源端服务器。
        优先按 IP 精确匹配；未命中则列出全部 connected 的源端，
        唯一候选直接返回，多个则报错引导配置 source_server_id。
        """
        if ip:
            data = self.list_servers({"ip": ip, "limit": 200})
            hits = data.get("source_servers") or []
            if len(hits) == 1:
                logger.info("源端按 IP 命中: %s (%s)", hits[0].get("id"), ip)
                return hits[0]
            if len(hits) > 1:
                raise SmsApiError(
                    f"IP {ip} 匹配到 {len(hits)} 台源端，请配置 sms_task.source_server_id",
                    detail={"candidates": [s.get("id") for s in hits]},
                )
        # 兜底：全量列出已连接源端
        data = self.list_servers({"limit": 200})
        servers = [s for s in (data.get("source_servers") or []) if s.get("connected")]
        if len(servers) == 1:
            s = servers[0]
            logger.info("源端唯一候选 (connected): %s (%s / %s)", s.get("id"), s.get("name"), s.get("ip"))
            return s
        if servers:
            raise SmsApiError(
                f"SMS 中有 {len(servers)} 台 connected 源端，请配置 sms_task.source_server_id",
                detail={"candidates": [{"id": s.get("id"), "name": s.get("name"), "ip": s.get("ip")} for s in servers]},
            )
        raise SmsApiError("SMS 未发现已注册且 connected 的源端服务器（请确认 Agent 已启动注册）")

    def list_migprojects(self) -> dict:
        return self._call("ListMigprojects")

    def list_templates(self) -> dict:
        return self._call("ListTemplates")

    def list_tasks(self, filters: dict | None = None) -> dict:
        return self._call("ListTasks", filters or {})

    def find_task(self, source_server_id: str) -> dict | None:
        """查询某源端已有的迁移任务（幂等用：避免重复创建）。"""
        data = self.list_tasks({"source_server_id": source_server_id, "limit": 100})
        tasks = data.get("tasks") or data.get("items") or []
        return tasks[0] if tasks else None

    def show_task(self, task_id: str) -> dict:
        return self._call("ShowTask", {"task_id": task_id})

    # ---- SMS 变更（需上层显式确认后调用）----

    def create_task(self, params: dict) -> dict:
        return self._call("CreateTask", params, timeout=180)

    def update_task_status(self, task_id: str, operation: str, extra: dict | None = None) -> dict:
        """更新迁移任务状态（operation 见 UPDATE_TASK_STATUS_OPS）。

        KooCLI 7.2.x 仅支持 UPDATE_TASK_STATUS_OPS 枚举；
        上层若需 syncing/cutover 语义请先探测兼容性，再回退到“启动目的端 ECS”（ecs_start）。
        """
        params = {"task_id": task_id, "operation": operation}
        if extra:
            params.update(extra)
        return self._call("UpdateTaskStatus", params, timeout=180)

    def delete_task(self, task_id: str) -> dict:
        return self._call("DeleteTask", {"task_id": task_id})

    # ---- ECS（已有服务器模式选型）----

    def list_ecs(self, name: str = "", limit: int = 200) -> dict:
        params: dict = {"limit": limit}
        if name:
            params["name"] = name
        return self._call("ListServersDetails", params, service="ECS", timeout=180)

    def ecs_start(self, server_id: str) -> dict:
        """启动目的端 ECS（等效割接）。

        KooCLI 7.2.x 无 StartServer operation，需用 BatchStartServers；
        嵌套 body 参数格式: --os-start.servers.1.id=<server_id>
        """
        params = {"os-start.servers.1.id": server_id}
        data = self._call("BatchStartServers", params, service="ECS", timeout=180)
        return {"job_id": data.get("job_id", "")}

    def ecs_stop(self, server_id: str) -> dict:
        """停止目的端 ECS（回滚/排查用；BatchStopServers 同款嵌套参数格式）。"""
        params = {"os-stop.servers.1.id": server_id,
                  "os-stop.type": "HARD"}
        data = self._call("BatchStopServers", params, service="ECS", timeout=180)
        return {"job_id": data.get("job_id", "")}

    # ---- 磁盘映射（步骤二创建任务前核对）----

    def show_server(self, source_id: str) -> dict:
        """查询源端服务器详情（含磁盘/分区拓扑）。"""
        return self._call("ShowServer", {"source_id": source_id})

    def ecs_volumes(self, server_id: str) -> list:
        """查询目的端 ECS 挂载的 EVS 卷（用于磁盘映射 disk_id）。

        实测：新版 hcloud 的 ListServerVolumeAttachments 响应可能为空，
        此时回退到 EVS ListVolumes --server_id 过滤（返回 volumes[]，归一为同构字段）。
        """
        data = self._call("ListServerVolumeAttachments", {"server_id": server_id},
                          service="ECS", timeout=180)
        vols = data.get("volumeAttachments") or data.get("attachments") or []
        if vols:
            return vols
        vdata = self._call("ListVolumes", {"server_id": server_id}, service="EVS", timeout=180)
        return [{
            "volumeId": v.get("id"),
            "device": (v.get("attachments") or [{}])[0].get("device") or "",
        } for v in (vdata.get("volumes") or [])]

    def call(self, service: str, operation: str, params: dict,
             with_project: bool = False, timeout: int = 120) -> dict:
        """通用 hcloud 调用（目标端基础设施编排 VPC/ECS/EIP/IMS 共用）。

        - with_project=True 时自动注入 project_id（VPC/EIP/ECS 创建类接口要求）
        - 其余行为与 _call 一致：USE_ERROR 识别、JSON 解析、SmsApiError
        """
        params = dict(params or {})
        if with_project and "project_id" not in params:
            pid, _ = self.project()
            params["project_id"] = pid
        return self._call(operation, params, service=service, timeout=timeout)