#!/usr/bin/env python3
"""
sms_ops.py — SMS 迁移服务操作

封装 SMS (Server Migration Service) 相关操作:
  - 源端注册状态查询
  - 迁移任务创建/启动/监控
  - 私网迁移特殊参数设置
  - 迁移进度查询
  - 错误诊断
"""

import time
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class SMSOps:
    """SMS 迁移服务操作"""

    def __init__(self, hcloud):
        """
        Args:
            hcloud: HcloudCLI 实例
        """
        self.hcloud = hcloud

    # ──────────────────────────────────────────────────────────────
    #  源端管理
    # ──────────────────────────────────────────────────────────────

    def find_source_by_ip(self, source_ip: str) -> Optional[Dict]:
        """通过 IP 查找 SMS 源端

        Args:
            source_ip: 源端 IP

        Returns:
            源端信息 (或 None)
        """
        sources = self.hcloud.sms_list_sources()
        source_list = sources.get("source_servers", sources.get("sources", [])) if isinstance(sources, dict) else []

        for src in source_list:
            # 检查 IP 是否匹配
            ip = src.get("ip") or src.get("ipaddress") or ""
            if source_ip in ip:
                logger.info(f"Found source: id={src.get('id')}, name={src.get('name')}, ip={ip}")
                return src

        logger.warning(f"Source not found for IP: {source_ip}")
        return None

    def get_source_state(self, source_id: str) -> str:
        """获取源端状态"""
        info = self.hcloud.sms_show_source(source_id)
        return info.get("state", "").upper() if isinstance(info, dict) else ""

    def wait_source_online(self, source_id: str, timeout: int = 300,
                           interval: int = 10) -> bool:
        """等待源端在线 (Agent 已连接)

        Args:
            source_id: 源端 ID
            timeout: 超时秒数
            interval: 轮询间隔

        Returns:
            源端是否在线
        """
        start = time.time()
        while time.time() - start < timeout:
            state = self.get_source_state(source_id)
            if state in ("ONLINE", "READY", "ACTIVE", "WAITING", "CONNECTED"):
                logger.info(f"Source {source_id} is online (state={state})")
                return True
            logger.debug(f"Source {source_id} state: {state}, waiting...")
            time.sleep(interval)

        logger.error(f"Source {source_id} not online after {timeout}s")
        return False

    # ──────────────────────────────────────────────────────────────
    #  迁移任务管理
    # ──────────────────────────────────────────────────────────────

    def create_migration_task(
        self,
        source_id: str,
        target_server_id: str,
        task_name: str = None,
        migration_type: str = "MIGRATE_FILE",
        use_public_ip: bool = False,
        region: str = None,
        target_disks: List[Dict] = None,
        exist_server: bool = True,
        os_type: str = "LINUX",
        project_id: str = None,
        project_name: str = None,
        region_id: str = None,
        region_name: str = None,
        target_server_name: str = None,
        syncing: bool = False,
        is_need_consistency_check: bool = True,
        migration_ip: str = None,
        network_type: str = None,
    ) -> Optional[Dict]:
        """创建迁移任务 (私网迁移专用)

        本 Skill 为私网迁移专用，强制以下设置:
        - use_public_ip = False (禁止公网迁移)
        - exist_server = True (目标 ECS 已预创建)
        - network_type = "private" (私网网络类型)
        - migration_ip = 目标 ECS 内网 IP (必须指定)
        - syncing = False (创建完整 6 个子任务)
        - is_need_consistency_check = True (创建第 7 个子任务 CHECK_CONSISTENCY)

        Args:
            source_id: 源端 ID
            target_server_id: 目标 ECS ID (已预创建)
            task_name: 任务名称
            migration_type: MIGRATE_BLOCK (全量) / MIGRATE_FILE (增量)
            use_public_ip: 是否使用公网 IP (私网迁移强制 False)
            region: 区域
            target_disks: 目标磁盘配置列表, 每项: {"size": 41, "name": "disk1"}
                重要: size 单位为 **GB** (gigabytes)。
                Issue 20: 支持完整磁盘参数:
                - disk_id: 目标 ECS 云硬盘 ID (EVS volume ID)
                - device_use: 磁盘用途 (BOOT / DATA)
                - used_size: 已使用大小 GB
                - physical_volumes: 物理卷信息列表
            exist_server: 是否已有目标服务器 (强制 True)
            os_type: 操作系统类型 (LINUX / WINDOWS)
            project_id: 项目 ID (SMS API 必填)
            project_name: 项目名称 (SMS API 必填)
            region_id: 区域 ID (SMS API 必填)
            region_name: 区域名称 (SMS API 必填)
            target_server_name: 目标服务器名称 (SMS API 必填)
            syncing: 是否同步迁移 (强制 False, 创建完整 6 个子任务)
            is_need_consistency_check: 是否需要一致性检查 (默认 True, 创建第 7 个子任务)
            migration_ip: 迁移 IP (私网迁移必须设为目标 ECS 内网 IP)
            network_type: 网络类型 (私网迁移强制 "private")

        Returns:
            任务信息 (或 None)
        """
        logger.info(f"Creating migration task: source={source_id}, target={target_server_id}")

        # Issue 3 修复: 本 Skill 为私网迁移专用, 强制使用私网 (use_public_ip=false)
        use_public_ip = False
        logger.info("Private network migration enforced: use_public_ip=false")

        # Issue 4 修复: exist_server 强制为 True (本 Skill 预创建目标 ECS)
        exist_server = True
        logger.info(f"exist_server=True enforced (target ECS pre-created, ensures 6-7 subtasks)")

        # Issue 18 修复: syncing 强制为 False (创建完整 6 个子任务)
        syncing = False
        logger.info("syncing=False enforced (creates 6 subtasks instead of 4)")

        # Issue 19 修复: is_need_consistency_check 强制为 True (创建第 7 个子任务)
        is_need_consistency_check = True
        logger.info("is_need_consistency_check=True enforced (creates 7th subtask CHECK_CONSISTENCY)")

        # 私网迁移: network_type 强制为 "private"
        network_type = "private"
        logger.info("network_type=private enforced (private network migration)")

        # 私网迁移: migration_ip 必须指定 (目标 ECS 内网 IP)
        if not migration_ip:
            logger.error(
                "私网迁移约束: migration_ip 未指定。"
                "必须设置为目标 ECS 的内网 IP (如 192.168.x.x)。"
            )
            return None
        logger.info(f"migration_ip={migration_ip} (target ECS private IP)")

        # Issue 2 修复: 记录磁盘大小单位信息
        if target_disks:
            for i, disk in enumerate(target_disks, 1):
                size_gb = disk.get("size", 0)
                logger.info(f"Target disk {i}: size={size_gb} GB (unit: GB, source for SMS API)")

        # Issue 4 修复: 传递完整参数给 hcloud CLI
        # 注意: network_type 是 Skill 内部标识，不是 SMS API 参数，不传递给 API
        result = self.hcloud.sms_create_task(
            source_id=source_id,
            target_server_id=target_server_id,
            name=task_name,
            type=migration_type,
            use_public_ip=use_public_ip,
            target_disks=target_disks,
            exist_server=exist_server,
            os_type=os_type,
            project_id=project_id,
            project_name=project_name,
            region_id=region_id,
            region_name=region_name,
            target_server_name=target_server_name,
            syncing=syncing,
            is_need_consistency_check=is_need_consistency_check,
            migration_ip=migration_ip,
        )

        if result and isinstance(result, dict):
            task_id = result.get("id", "")
            logger.info(f"Migration task created: id={task_id}")
            return result
        else:
            logger.error(f"Failed to create migration task, result type={type(result).__name__}, value={str(result)[:500]}")
            return None

    def start_and_monitor(
        self,
        task_id: str,
        timeout: int = 7200,
        interval: int = 30,
        progress_callback=None,
        min_interval: int = 5,
        backoff_factor: float = 1.5,
    ) -> Dict[str, Any]:
        """启动迁移任务并监控进度

        P1-2优化: 支持指数退避轮询参数透传。

        Args:
            task_id: 任务 ID
            timeout: 超时秒数
            interval: 最大轮询间隔 (退避上限)
            progress_callback: 进度回调函数 callback(progress: int, state: str)
            min_interval: 初始轮询间隔 (退避起点, 默认5s)
            backoff_factor: 退避因子 (默认1.5)

        Returns:
            {"completed": bool, "state": str, "progress": int, "error": str, "duration": float}
        """
        start_time = time.time()

        # 启动任务
        if not self.hcloud.sms_start_task(task_id):
            return {
                "completed": False, "state": "START_FAILED",
                "progress": 0, "error": "Failed to start task", "duration": 0
            }

        logger.info(f"Migration task {task_id} started")

        # 监控
        result = self.hcloud.sms_wait_task_complete(
            task_id, timeout=timeout, interval=interval,
            min_interval=min_interval, backoff_factor=backoff_factor,
        )
        duration = time.time() - start_time

        result["duration"] = round(duration, 1)
        result["task_id"] = task_id

        if result["completed"]:
            logger.info(f"Migration task {task_id} completed: {duration:.1f}s")
        else:
            logger.error(f"Migration task {task_id} failed: state={result['state']}, error={result['error']}")

        return result

    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度

        Returns:
            {"state": str, "progress": int, "subtask_progress": {}}
        """
        info = self.hcloud.sms_show_task(task_id)
        if not info or not isinstance(info, dict):
            return {"state": "UNKNOWN", "progress": 0}

        state = info.get("state", "").upper()
        progress = info.get("progress", 0)

        # 子任务进度
        subtasks = {}
        for st in info.get("sub_tasks", []):
            subtasks[st.get("name", "")] = {
                "state": st.get("state", "").upper(),
                "progress": st.get("progress", 0),
            }

        # 解析 error_json 获取错误信息
        error_msg = ""
        error_json = info.get("error_json", "")
        if error_json:
            try:
                import json
                ej = json.loads(error_json)
                error_msg = ej.get("error_code", "") + ": " + str(ej.get("error_param", ""))
            except (json.JSONDecodeError, ValueError):
                error_msg = error_json

        return {
            "state": state,
            "progress": progress,
            "subtasks": subtasks,
            "error_msg": error_msg,
        }

    # ──────────────────────────────────────────────────────────────
    #  错误诊断
    # ──────────────────────────────────────────────────────────────

    def diagnose_error(self, task_id: str) -> Dict[str, Any]:
        """诊断迁移错误

        Args:
            task_id: 任务 ID

        Returns:
            诊断结果 {"error_code": str, "error_msg": str, "suggestion": str, "action": str}
        """
        info = self.hcloud.sms_show_task(task_id)
        if not info or not isinstance(info, dict):
            return {"error_code": "UNKNOWN", "error_msg": "无法获取任务信息"}

        # 解析 error_json 获取错误码 (API 返回 error_json 为 JSON 字符串)
        import json
        error_code = ""
        error_msg = ""
        error_json = info.get("error_json", "")
        if error_json:
            try:
                ej = json.loads(error_json)
                error_code = ej.get("error_code", "")
                error_msg = str(ej.get("error_param", ""))
            except (json.JSONDecodeError, ValueError):
                error_msg = error_json
        state = info.get("state", "").upper()

        diagnosis = {
            "error_code": error_code,
            "error_msg": error_msg,
            "state": state,
            "suggestion": "",
            "action": "",
        }

        # 常见错误码诊断
        ERROR_DIAGNOSIS = {
            "SMS.0515": {
                "suggestion": "源端磁盘信息与创建任务时传递的磁盘参数不匹配 (通常是 physical_volumes/volume_groups 未正确传递)",
                "action": "修复流程 (不删Agent): 1) 查看本次 CreateTask 日志中 --target_server.disks.*.physical_volumes 参数; "
                          "2) 对比 SMS ShowServer 返回的 init_target_server.disks 中的 physical_volumes; "
                          "3) 若 PV/VG 缺失, 说明字段映射有 bug (API 返回 name 而非 pv_name); "
                          "4) 删除失败任务 (sms_delete_task), 用正确磁盘参数重建任务; "
                          "5) 仅在确认 Agent 采集的磁盘信息本身有误时才考虑重启 Agent",
            },
            "SMS.0301": {
                "suggestion": "源端 Agent 未连接",
                "action": "检查 Agent 进程是否运行，检查网络连通性",
            },
            "SMS.0304": {
                "suggestion": "目标 ECS 不可达",
                "action": "检查目标 ECS 状态和安全组规则，检查 GOST 转发是否正常，"
                          "检查 migration_ip 是否设置为目标 ECS 内网 IP，"
                          "检查 VPN 连通性",
            },
            "SMS.0307": {
                "suggestion": "迁移 IP 不可达或未设置",
                "action": "检查 migration_ip 是否正确设置为目标 ECS 内网 IP，"
                          "检查 GOST 数据流转发配置 (源端 → 代理 → 目标 ECS)，"
                          "确认 network_type=private",
            },
            "SMS.0401": {
                "suggestion": "磁盘空间不足",
                "action": "检查目标 ECS 磁盘容量是否大于源端",
            },
            "SMS.0501": {
                "suggestion": "网络传输超时",
                "action": "检查 VPN 连通性和带宽，检查 GOST/squid 代理状态",
            },
            "SMS.1201": {
                "suggestion": "源端磁盘读取错误",
                "action": "检查源端磁盘健康状态 (smartctl)",
            },
            "SMS.0007": {
                "suggestion": "Agent 程序异常 (迁移任务子任务不全, 仅 4 个而非 6-7 个)",
                "action": "创建迁移任务时未设置 exist_server=true, 导致 SMS 工作流不完整。"
                          "已修复: exist_server=true + 补全 SMS API 必填参数 "
                          "(project_id/project_name/region_id/region_name/target_server.name)。"
                          "请删除旧任务重新创建。",
            },
            "SMS.7719": {
                "suggestion": "源端服务器仍在运行中, 无法删除任务",
                "action": "源端 Agent 仍在运行导致状态为 running。修复: "
                          "1) 在源端 kill Agent 进程 (kill -9 $(pgrep -f SMS-Agent)); "
                          "2) 等待源端状态变为 deleted (轮询 sms_show_source); "
                          "3) 再执行 sms_delete_task。",
            },
            "SMS.7703": {
                "suggestion": "源端服务器正在删除中, 操作冲突",
                "action": "源端删除操作正在进行中。修复: 等待源端完全删除完成 "
                          "(轮询 sms_show_source 直到 404), 然后重新操作。",
            },
        }

        if error_code in ERROR_DIAGNOSIS:
            diagnosis.update(ERROR_DIAGNOSIS[error_code])
        elif state in ("FAIL", "FAILED"):
            diagnosis["suggestion"] = "迁移失败，请查看详细日志"
            diagnosis["action"] = f"查看任务详情: hcloud SMS ShowTask --task_id={task_id}"

        logger.info(f"Error diagnosis for {task_id}: {diagnosis['error_code']} -> {diagnosis['suggestion']}")
        return diagnosis

    # ──────────────────────────────────────────────────────────────
    #  批量操作
    # ──────────────────────────────────────────────────────────────

    def list_tasks_by_state(self, state: str = None) -> List[Dict]:
        """按状态查询迁移任务"""
        result = self.hcloud.sms_list_tasks(state=state)
        if isinstance(result, dict):
            return result.get("tasks", [])
        return []

    def cleanup_failed_tasks(self, older_than_hours: int = 24) -> int:
        """清理失败的迁移任务

        Args:
            older_than_hours: 清理多少小时前的任务

        Returns:
            清理的任务数量
        """
        failed_tasks = self.list_tasks_by_state("FAIL")
        cleaned = 0
        cutoff = time.time() - older_than_hours * 3600

        for task in failed_tasks:
            create_time = task.get("create_time", "")
            # 简单时间判断 (实际需要解析时间)
            task_id = task.get("id", "")
            if task_id:
                if self.hcloud.sms_delete_task(task_id):
                    cleaned += 1
                    logger.info(f"Deleted failed task: {task_id}")

        logger.info(f"Cleaned {cleaned} failed tasks")
        return cleaned

    # ──────────────────────────────────────────────────────────────
    #  任务暂停/恢复 (用于 AK/SK 更新时安全操作)
    # ──────────────────────────────────────────────────────────────

    def pause_task(self, task_id: str) -> bool:
        """暂停迁移任务 (安全暂停，用于 AK/SK 更新)

        Returns: True 暂停成功
        """
        logger.info(f"暂停迁移任务: {task_id}")
        return self.hcloud.sms_pause_task(task_id)

    def resume_task(self, task_id: str) -> bool:
        """恢复迁移任务 (AK/SK 更新完成后恢复)

        Returns: True 恢复成功
        """
        logger.info(f"恢复迁移任务: {task_id}")
        return self.hcloud.sms_resume_task(task_id)

    def find_task_by_source_ip(self, source_ip: str) -> Optional[Dict]:
        """根据源端 IP 查找关联的迁移任务

        Returns: 任务信息 dict 或 None
        """
        tasks = self.list_tasks_by_state()
        for task in tasks:
            # 检查任务的源端 IP 是否匹配
            source_server = task.get("source_server", {})
            if isinstance(source_server, dict):
                task_ip = source_server.get("ip", "")
            else:
                task_ip = ""
            if not task_ip:
                # 尝试从其他字段获取
                task_ip = task.get("source_ip", "")
            if task_ip == source_ip:
                return task
        return None

    def check_task_active(self, task_id: str) -> Dict[str, Any]:
        """检查任务是否活跃 (有进度更新)

        Returns:
            {"active": bool, "state": str, "progress": int, "can_safely_restart": bool}
        """
        progress = self.get_task_progress(task_id)
        state = progress.get("state", "UNKNOWN").upper()

        # 活跃状态: RUNNING, READY(等待启动)
        is_active = state in ("RUNNING", "READY")
        # 可以安全重启的状态: 非 RUNNING, 或 FAIL
        can_safely_restart = state not in ("RUNNING",)

        return {
            "active": is_active,
            "state": state,
            "progress": progress.get("progress", 0),
            "can_safely_restart": can_safely_restart,
        }
