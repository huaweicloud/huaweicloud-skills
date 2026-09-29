#!/usr/bin/env python3
"""
hcloud_wrapper.py — 华为云 CLI 封装

封装 hcloud CLI 调用，提供:
  - AK/SK 认证管理 (通过 credential_manager RSA 加密流程传入, 脱敏日志)
  - ECS 操作 (查询/创建/删除/启停)
  - SMS 操作 (查询迁移任务/源端)
  - VPN 操作 (查询网关/连接)
  - VPC/子网/安全组操作
  - EIP 操作
  - 统一错误处理和重试
"""

import os
import json
import time
import logging
import subprocess
from typing import Optional, Dict, List, Any, Tuple

from task_name_utils import sanitize_task_name, generate_task_name_from_id

logger = logging.getLogger(__name__)


class HcloudCLI:
    """华为云 hcloud CLI 封装"""

    def __init__(
        self,
        ak: str = None,
        sk: str = None,
        region: str = "cn-north-1",
        project_id: str = None,
        hcloud_path: str = "hcloud",
        security_token: str = None,
    ):
        """
        Args:
            ak: Access Key (通过 credential_manager RSA 加密流程解密后传入)
            sk: Secret Key (通过 credential_manager RSA 加密流程解密后传入)
            region: 区域
            project_id: 项目 ID
            hcloud_path: hcloud 可执行文件路径

        重要: AK/SK 只接受显式传入的参数 (应来自 credential_manager 解密结果)。
        禁止从环境变量 (HUAWEICLOUD_SDK_AK/SK) 或临时凭证获取，确保凭证来源唯一可控。
        AK/SK 在日志中始终脱敏显示 (如 HPUA****YPQY)，不会泄露明文。
        """
        # AK/SK 只接受显式传入参数 (来源: credential_manager RSA 解密)
        # 禁止从环境变量或临时凭证获取
        self.ak = ak or ""
        self.sk = sk or ""
        self.security_token = security_token or ""

        if not self.ak or not self.sk:
            logger.warning(
                "AK/SK 未通过参数显式传入。请通过 credential_manager RSA 加密流程提供凭证，"
                "不接受环境变量 (HUAWEICLOUD_SDK_AK/SK) 或临时凭证。"
            )
        else:
            logger.info(f"HCloudCLI 初始化: AK={self._mask_ak(self.ak)}, region={region}")
        self.region = region
        self.project_id = project_id or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID", "")
        self.hcloud_path = hcloud_path

        self._setup_env()

    def _setup_env(self):
        """配置环境变量 (仅用于 hcloud 子进程认证)

        重要: 此方法只将已通过参数传入的 AK/SK 设置到环境变量供 hcloud CLI 子进程使用。
        不会从环境变量读取 AK/SK — 凭证来源唯一: credential_manager 显式传入。
        """
        # 只设置环境变量供 hcloud 子进程使用，不从环境变量读取
        if self.ak:
            os.environ["HUAWEICLOUD_SDK_AK"] = self.ak
        if self.sk:
            os.environ["HUAWEICLOUD_SDK_SK"] = self.sk
        if self.security_token:
            os.environ["HUAWEICLOUD_SDK_SECURITY_TOKEN"] = self.security_token
        os.environ["HUAWEICLOUD_SDK_REGION"] = self.region
        if self.project_id:
            os.environ["HUAWEICLOUD_SDK_PROJECT_ID"] = self.project_id

    @staticmethod
    def _mask_ak(ak: str) -> str:
        """脱敏 AK (如 HPUA****YPQY)"""
        if not ak or len(ak) < 8:
            return "****"
        return f"{ak[:4]}****{ak[-4:]}"

    def _exec(self, args: List[str], timeout: int = 60, retry: int = 2) -> Dict[str, Any]:
        """执行 hcloud 命令

        Args:
            args: 命令参数列表 (不含 hcloud 本身)
            timeout: 超时秒数
            retry: 重试次数

        Returns:
            {"success": bool, "data": Any, "raw": str, "error": str}
        """
        cmd = [self.hcloud_path]
        # KooCLI 需要显式传递认证参数 (不识别 HUAWEICLOUD_SDK_* 环境变量)
        if self.ak:
            cmd.append(f"--cli-access-key={self.ak}")
        if self.sk:
            cmd.append(f"--cli-secret-key={self.sk}")
        if self.security_token:
            cmd.append(f"--cli-security-token={self.security_token}")
        if self.region:
            cmd.append(f"--cli-region={self.region}")
        cmd += args
        # 构建脱敏的命令字符串用于日志 (不泄露 AK/SK 明文)
        masked_cmd = [self.hcloud_path]
        if self.ak:
            masked_cmd.append(f"--cli-access-key={self._mask_ak(self.ak)}")
        if self.sk:
            masked_cmd.append("--cli-secret-key=****")
        if self.region:
            masked_cmd.append(f"--cli-region={self.region}")
        masked_cmd += args
        cmd_str = " ".join(masked_cmd[:3]) + " ..." if len(masked_cmd) > 3 else " ".join(masked_cmd)

        for attempt in range(retry + 1):
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    text=True,
                    env=os.environ.copy(),
                )

                if proc.returncode == 0:
                    # 尝试解析 JSON
                    data = None
                    stdout = proc.stdout
                    # hcloud CLI 可能将版本警告输出到 stdout，需要跳过
                    # 找到第一个 JSON 起始字符 { 或 [
                    json_start = -1
                    for i, ch in enumerate(stdout):
                        if ch in ('{', '['):
                            json_start = i
                            break
                    if json_start > 0:
                        stdout = stdout[json_start:]
                    try:
                        data = json.loads(stdout)
                    except (json.JSONDecodeError, ValueError):
                        # hcloud 可能输出 JSON + 诊断文本，尝试提取纯 JSON 部分
                        try:
                            # 找到匹配的闭合括号
                            brace_count = 0
                            json_end = -1
                            for i, ch in enumerate(stdout):
                                if ch == '{':
                                    brace_count += 1
                                elif ch == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = i + 1
                                        break
                            if json_end > 0:
                                data = json.loads(stdout[:json_end])
                            else:
                                data = stdout.strip()
                        except (json.JSONDecodeError, ValueError):
                            data = stdout.strip()

                    # 检测 hcloud API 错误响应 (return code 0 但 JSON 包含 error_code)
                    if isinstance(data, dict) and "error_code" in data:
                        err_msg = data.get("error_msg", data.get("error_code", "unknown"))
                        logger.error(f"hcloud API 错误: {cmd_str}, error_code={data['error_code']}, error_msg={err_msg}")
                        return {"success": False, "data": data, "raw": proc.stdout, "error": f"{data['error_code']}: {err_msg}"}

                    return {"success": True, "data": data, "raw": proc.stdout, "error": ""}

                else:
                    err = proc.stderr.strip() or proc.stdout.strip()
                    # v2.5.0 优化5: 区分可重试和不可重试错误
                    # 不可重试: 命令不存在, 权限拒绝, 参数错误, 配置缺失
                    non_retryable_markers = [
                        "command not found", "not found", "No such file",
                        "permission denied", "Permission denied",
                        "invalid parameter", "InvalidParameter", "parameter error",
                        "config not found", "AK/SK", "authentication",
                        "Usage:", "unrecognized arguments",
                    ]
                    is_retryable = not any(m.lower() in err.lower() for m in non_retryable_markers)

                    if attempt < retry and is_retryable:
                        # v2.5.0 优化5: 递增间隔 1s, 2s, 3s (替代 2s, 4s, 6s)
                        backoff = attempt + 1
                        logger.warning(f"hcloud 命令失败 (attempt {attempt+1}/{retry+1}), {backoff}s 后重试: {cmd_str}")
                        time.sleep(backoff)
                        continue
                    if not is_retryable:
                        logger.error(f"hcloud 命令失败 (不可重试): {cmd_str}, error: {err[:200]}")
                    else:
                        logger.error(f"hcloud 命令失败 (重试已耗尽): {cmd_str}, error: {err[:200]}")
                    return {"success": False, "data": None, "raw": proc.stdout, "error": err}

            except subprocess.TimeoutExpired:
                if attempt < retry:
                    logger.warning(f"hcloud 命令超时 (attempt {attempt+1}), 重试: {cmd_str}")
                    continue
                return {"success": False, "data": None, "raw": "", "error": "timeout"}
            except Exception as e:
                return {"success": False, "data": None, "raw": "", "error": str(e)}

        return {"success": False, "data": None, "raw": "", "error": "max retries exceeded"}

    def check_available(self) -> bool:
        """检查 hcloud CLI 是否可用"""
        result = self._exec(["--version"], timeout=10, retry=0)
        return result["success"]

    # ──────────────────────────────────────────────────────────────
    #  ECS 操作
    # ──────────────────────────────────────────────────────────────

    def ecs_list(self, limit: int = 100) -> Dict:
        """查询 ECS 列表"""
        result = self._exec(["ECS", "ListServersDetails", f"--limit={limit}"])
        return result["data"] if result["success"] else {}

    def ecs_show(self, server_id: str) -> Dict:
        """查询 ECS 详情"""
        result = self._exec(["ECS", "ShowServer", f"--server_id={server_id}"])
        return result["data"] if result["success"] else {}

    def ecs_create(self, name: str, image_id: str, flavor_id: str,
                   vpc_id: str, subnet_id: str, sg_id: str,
                   key_name: str = None, password: str = None,
                   eip_id: str = None, disk_size: int = 40,
                   disk_type: str = "SAS") -> Dict:
        """创建 ECS"""
        args = [
            "ECS", "CreateServers",
            f"--server.name={name}",
            f"--server.imageRef={image_id}",
            f"--server.flavorRef={flavor_id}",
            f"--server.vpcid={vpc_id}",
            f"--server.nics.1.subnet_id={subnet_id}",
            f"--server.security_groups.1.id={sg_id}",
            f"--server.root_volume.volumetype={disk_type}",
            f"--server.root_volume.size={disk_size}",
        ]
        if key_name:
            args.append(f"--server.key_name={key_name}")
        if password:
            args.append(f"--server.adminPass={password}")
        if eip_id:
            args.append(f"--server.publicip.id={eip_id}")

        result = self._exec(args, timeout=120)
        return result["data"] if result["success"] else {}

    def ecs_create_full(
        self,
        name: str,
        image_id: str,
        flavor_id: str,
        vpc_id: str,
        subnet_id: str,
        sg_id: str,
        root_volume_type: str = "SAS",
        root_volume_size: int = 40,
        data_volumes: List[Dict] = None,
        admin_pass: str = None,
        key_name: str = None,
        availability_zone: str = None,
        eip_id: str = None,
        tags: List[Dict] = None,
    ) -> Dict:
        """创建 ECS (完整版，支持多数据盘、AZ、标签)

        Args:
            name: ECS 名称
            image_id: 镜像 ID
            flavor_id: 规格 ID
            vpc_id: VPC ID
            subnet_id: 子网 ID
            sg_id: 安全组 ID
            root_volume_type: 系统盘类型 (SAS/SATA/SSD/GPSSD)
            root_volume_size: 系统盘大小 GB
            data_volumes: 数据盘列表 [{"size": 100, "type": "SAS"}, ...]
            admin_pass: 管理密码
            key_name: 密钥对名称
            availability_zone: 可用区
            eip_id: EIP ID
            tags: 标签 [{"key": "k", "value": "v"}, ...]

        Returns:
            创建结果 (server 信息)
        """
        args = [
            "ECS", "CreateServers",
            f"--server.name={name}",
            f"--server.imageRef={image_id}",
            f"--server.flavorRef={flavor_id}",
            f"--server.vpcid={vpc_id}",
            f"--server.nics.1.subnet_id={subnet_id}",
            f"--server.security_groups.1.id={sg_id}",
            f"--server.root_volume.volumetype={root_volume_type}",
            f"--server.root_volume.size={root_volume_size}",
        ]

        # 数据盘
        if data_volumes:
            for i, vol in enumerate(data_volumes, 1):
                args.append(f"--server.data_volumes.{i}.volumetype={vol.get('type', 'SAS')}")
                args.append(f"--server.data_volumes.{i}.size={vol['size']}")

        # 认证方式
        if key_name:
            args.append(f"--server.key_name={key_name}")
        elif admin_pass:
            args.append(f"--server.adminPass={admin_pass}")

        # 可用区
        if availability_zone:
            args.append(f"--server.availability_zone={availability_zone}")

        # EIP
        if eip_id:
            args.append(f"--server.publicip.id={eip_id}")

        # 标签
        if tags:
            for i, tag in enumerate(tags, 1):
                args.append(f"--server.tags.{i}.key={tag['key']}")
                args.append(f"--server.tags.{i}.value={tag['value']}")

        result = self._exec(args, timeout=180)
        return result["data"] if result["success"] else {}

    def ecs_list_azs(self) -> Dict:
        """查询可用区列表"""
        result = self._exec(["ECS", "NovaListAvailabilityZones"])
        return result["data"] if result["success"] else {}

    def ecs_show_block_device(self, server_id: str) -> Dict:
        """查询 ECS 磁盘信息 (block_device_mapping)"""
        result = self._exec(["ECS", "ShowServerBlockDevice", f"--server_id={server_id}"])
        return result["data"] if result["success"] else {}

    def ecs_list_flavors_detail(self, availability_zone: str = None) -> Dict:
        """查询可用规格详情 (含 vCPU/内存/磁盘信息)"""
        args = ["ECS", "ListFlavors"]
        if availability_zone:
            args.append(f"--availability_zone={availability_zone}")
        result = self._exec(args)
        return result["data"] if result["success"] else {}

    def ecs_delete(self, server_id: str, delete_volumes: bool = True) -> bool:
        """删除 ECS"""
        args = ["ECS", "DeleteServers", f"--servers.1.id={server_id}"]
        if delete_volumes:
            args.append("--delete_publicip=true")
            args.append("--delete_volume=true")
        result = self._exec(args, timeout=60)
        return result["success"]

    def ecs_start(self, server_id: str) -> bool:
        """启动 ECS"""
        result = self._exec(["ECS", "StartServers", f"--os-start.servers.1.id={server_id}"])
        return result["success"]

    def ecs_stop(self, server_id: str, force: bool = False) -> bool:
        """停止 ECS"""
        args = ["ECS", "StopServers", f"--os-stop.servers.1.id={server_id}"]
        if force:
            args.append("--os-stop.type=HARD")
        result = self._exec(args, timeout=60)
        return result["success"]

    def ecs_reboot(self, server_id: str, force: bool = False) -> bool:
        """重启 ECS"""
        args = ["ECS", "RebootServers", f"--os-reboot.servers.1.id={server_id}"]
        if force:
            args.append("--os-reboot.type=HARD")
        result = self._exec(args, timeout=60)
        return result["success"]

    # ── 方法别名 (兼容 ecs_ops.py 调用命名) ──
    def ecs_list_servers(self, limit: int = 100) -> Dict:
        """别名: ecs_list"""
        return self.ecs_list(limit=limit)

    def ecs_show_server(self, server_id: str) -> Dict:
        """别名: ecs_show"""
        return self.ecs_show(server_id)

    def ecs_create_server(self, **kwargs) -> Dict:
        """别名: ecs_create"""
        return self.ecs_create(**kwargs)

    def ecs_delete_server(self, server_id: str, delete_volumes: bool = True) -> bool:
        """别名: ecs_delete"""
        return self.ecs_delete(server_id, delete_volumes=delete_volumes)

    def ecs_start_server(self, server_id: str) -> bool:
        """别名: ecs_start"""
        return self.ecs_start(server_id)

    def ecs_stop_server(self, server_id: str, force: bool = False) -> bool:
        """别名: ecs_stop"""
        return self.ecs_stop(server_id, force=force)

    def ecs_reboot_server(self, server_id: str, force: bool = False) -> bool:
        """别名: ecs_reboot"""
        return self.ecs_reboot(server_id, force=force)

    def ecs_wait_status(self, server_id: str, target_status: str = "ACTIVE",
                        timeout: int = 300, interval: int = 5) -> bool:
        """等待 ECS 达到指定状态

        v2.5.0 优化4: 自适应轮询间隔 — 前 30s 用 3s 间隔 (快速检测启动完成),
        之后 8s 间隔 (减少 API 调用). 相比固定 5s, 早期检测快 40%, 后期调用减少 37%.
        """
        start = time.time()
        while time.time() - start < timeout:
            info = self.ecs_show(server_id)
            status = info.get("server", {}).get("status", "").upper()
            if status == target_status.upper():
                return True
            # v2.5.0 优化4: 自适应轮询间隔
            elapsed = time.time() - start
            current_interval = 3 if elapsed < 30 else 8
            time.sleep(current_interval)
        return False

    def ecs_list_flavors(self) -> Dict:
        """查询可用规格"""
        result = self._exec(["ECS", "ListFlavors"])
        return result["data"] if result["success"] else {}

    def ecs_add_tags(self, server_id: str, tags: List[Dict[str, str]]) -> bool:
        """给 ECS 实例添加标签

        Args:
            server_id: ECS 实例 ID
            tags: 标签列表 [{"key": "k1", "value": "v1"}, ...]

        Returns:
            是否成功
        """
        if not tags:
            return True
        args = ["ECS", "BatchAddServerTags", f"--server_id={server_id}"]
        for i, tag in enumerate(tags, 1):
            args.append(f"--tags.{i}.key={tag['key']}")
            args.append(f"--tags.{i}.value={tag['value']}")
        result = self._exec(args, timeout=30)
        if not result["success"]:
            logger.error(f"ecs_add_tags failed for {server_id}: {result.get('error', '')}")
        return result["success"]

    def ecs_list_by_tag(self, tag_key: str, tag_value: str = None) -> List[Dict]:
        """按标签查找 ECS 实例

        使用 ECS ListServersDetails 并在客户端过滤标签，
        因为 hcloud CLI 的 --tags 过滤支持因版本而异。

        Args:
            tag_key: 标签键
            tag_value: 标签值 (可选, 为 None 时只匹配 key)

        Returns:
            匹配的 ECS 实例列表 [{server info}, ...]
        """
        result = self._exec(["ECS", "ListServersDetails", "--limit=500"])
        if not result["success"]:
            logger.error(f"ecs_list_by_tag: ListServersDetails failed: {result.get('error', '')}")
            return []

        servers = []
        data = result["data"]
        if isinstance(data, dict):
            servers = data.get("servers", [])
        elif isinstance(data, list):
            servers = data

        matched = []
        for srv in servers:
            srv_tags = srv.get("tags", {})
            if not isinstance(srv_tags, dict):
                # 有些 API 返回 tags 为列表 [{"key":..,"value":..}]
                srv_tags = {t.get("key", ""): t.get("value", "") for t in srv_tags} if srv_tags else {}
            if tag_key in srv_tags:
                if tag_value is None or srv_tags[tag_key] == tag_value:
                    matched.append(srv)
        logger.info(f"ecs_list_by_tag(key={tag_key}, value={tag_value}): found {len(matched)} ECS")
        return matched

    # ──────────────────────────────────────────────────────────────
    #  SMS 操作
    # ──────────────────────────────────────────────────────────────

    def sms_list_tasks(self, state: str = None, limit: int = 100) -> Dict:
        """查询 SMS 迁移任务列表

        Args:
            state: 任务状态 (READY, RUNNING, SUCCESS, FAIL, STOPPED)
        """
        args = ["SMS", "ListTasks", f"--limit={limit}"]
        if state:
            args.append(f"--state={state}")
        result = self._exec(args)
        return result["data"] if result["success"] else {}

    def sms_show_task(self, task_id: str) -> Dict:
        """查询 SMS 迁移任务详情"""
        result = self._exec(["SMS", "ShowTask", f"--task_id={task_id}"])
        return result["data"] if result["success"] else {}

    def sms_list_sources(self, limit: int = 100) -> Dict:
        """查询 SMS 源端列表"""
        result = self._exec(["SMS", "ListServers", f"--limit={limit}"])
        return result["data"] if result["success"] else {}

    def sms_show_source(self, source_id: str) -> Dict:
        """查询 SMS 源端详情"""
        result = self._exec(["SMS", "ShowServer", f"--source_id={source_id}"])
        return result["data"] if result["success"] else {}

    def sms_delete_source(self, source_id: str) -> bool:
        """删除 SMS 源端"""
        result = self._exec(["SMS", "DeleteServer", f"--source_id={source_id}"])
        return result["success"]

    def sms_create_task(self, source_id: str, target_server_id: str,
                        name: str = None, type: str = "MIGRATE_FILE",
                        use_public_ip: bool = False,
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
                        **kwargs) -> Dict:
        """创建 SMS 迁移任务

        Args:
            source_id: 源端 ID
            target_server_id: 目标 ECS ID (已预创建, 对应 --target_server.vm_id)
            name: 任务名称
            type: 迁移类型 (MIGRATE_BLOCK 全量, MIGRATE_FILE 增量)
            use_public_ip: 是否使用公网 IP (私网迁移为 False)
            target_disks: 目标磁盘配置列表, 每项: {"size": 41, "name": "disk1"}
                重要: size 单位为 **GB** (gigabytes), 不是 MB 或 KB。
                SMS API --target_server.disks.N.size 参数要求 GB 单位。
                Issue 20 修复: 支持完整磁盘参数:
                - disk_id: 目标 ECS 云硬盘 ID (EVS volume ID, 必填)
                - name: 磁盘名称
                - size: 磁盘大小 GB
                - device_use: 磁盘用途 (BOOT 系统盘 / DATA 数据盘)
                - used_size: 已使用大小 GB
                - physical_volumes: 物理卷信息列表 [{pv_name, vg_name, size, ...}]
            exist_server: 是否已有目标服务器 (默认 True, 因为本 Skill 预创建目标 ECS)。
                Issue 4 修复: 必须设为 True, 否则 SMS 创建的任务子任务不全 (4个而非6-7个),
                导致 SMS.0007 报错。exist_server=True 告知 SMS 目标服务器已存在,
                SMS 将创建完整的迁移工作流 (6-7 个子任务)。
            os_type: 操作系统类型 (LINUX / WINDOWS), 传递给 SMS API --os_type
            project_id: 项目 ID (SMS API 必填)
            project_name: 项目名称 (SMS API 必填)
            region_id: 区域 ID (SMS API 必填)
            region_name: 区域名称 (SMS API 必填)
            target_server_name: 目标服务器名称 (SMS API 必填 --target_server.name)
            syncing: 是否同步迁移 (默认 False)。
                Issue 18 修复: syncing=true 时 SMS 仅创建 4 个子任务
                (缺少 CONFIGURE_LINUX_FILE 和 DETTACH_AGENT_IMAGE)。
                syncing=false 时 SMS 创建完整 6 个子任务。
            is_need_consistency_check: 是否需要一致性检查 (默认 True)。
                Issue 19 修复: 必须设为 True, 才能创建第 7 个子任务
                (CHECK_CONSISTENCY), 确保迁移后数据一致性。
                syncing=false + is_need_consistency_check=true → 完整 7 个子任务。
            migration_ip: 迁移 IP (目标 ECS 内网 IP, 私网迁移必填)
            **kwargs: 额外参数

        Returns:
            创建结果 (任务信息)
        """
        # Issue 21 修复: SMS 任务名称规则 — 只能由中文字符、英文字母、数字、下划线、短横线组成
        # 最小长度 1, 最大长度 20。旧代码生成 "migration-{source_id[:8]}-{timestamp}" 长达 29 字符。
        # 使用 generate_task_name_from_id 确保名称符合规则，再 sanitize 兜底。
        if name:
            task_name = sanitize_task_name(name)
        else:
            task_name = generate_task_name_from_id(source_id)
        logger.info(f"SMS task name: '{task_name}' (len={len(task_name)}, max=20)")

        # Issue 4 修复: 使用 SMS API 正确的参数名
        # --source_server.id (非 source_server_id)
        # --target_server.vm_id (非 target_server_id)
        # --target_server.name (SMS API 必填)
        args = [
            "SMS", "CreateTask",
            f"--source_server.id={source_id}",
            f"--target_server.vm_id={target_server_id}",
            f"--name={task_name}",
            f"--type={type}",
            f"--use_public_ip={str(use_public_ip).lower()}",
        ]

        # Issue 4 修复: exist_server=true (关键参数)
        # 告知 SMS 目标服务器已预创建, 创建完整迁移工作流 (6-7 个子任务)
        # 不设此参数时 SMS 仅创建 4 个子任务, 导致 SMS.0007 报错
        args.append(f"--exist_server={str(exist_server).lower()}")
        logger.info(f"SMS CreateTask exist_server={exist_server} (target ECS pre-created)")

        # SMS API 必填参数: project_id, project_name, region_id, region_name
        if project_id:
            args.append(f"--project_id={project_id}")
        if project_name:
            args.append(f"--project_name={project_name}")
        if region_id:
            args.append(f"--region_id={region_id}")
        if region_name:
            args.append(f"--region_name={region_name}")

        # 目标服务器名称 (SMS API 必填 --target_server.name)
        if target_server_name:
            args.append(f"--target_server.name={target_server_name}")

        # OS 类型
        if os_type:
            args.append(f"--os_type={os_type.upper()}")

        # Issue 4 修复: syncing=false (关键参数)
        # syncing=true 时 SMS 仅创建 4 个子任务 (缺少 CONFIGURE_LINUX_FILE 和 DETTACH_AGENT_IMAGE)
        # syncing=false 时 SMS 创建完整 6 个子任务
        args.append(f"--syncing={str(syncing).lower()}")
        logger.info(f"SMS CreateTask syncing={syncing} (false=full 6 subtasks, true=only 4)")

        # Issue 19 修复: is_need_consistency_check=true (关键参数)
        # 必须设为 True, 才能创建第 7 个子任务 (CHECK_CONSISTENCY), 确保迁移后数据一致性
        # syncing=false + is_need_consistency_check=true → 完整 7 个子任务
        args.append(f"--is_need_consistency_check={str(is_need_consistency_check).lower()}")
        logger.info(f"SMS CreateTask is_need_consistency_check={is_need_consistency_check} (true=7th subtask CHECK_CONSISTENCY)")

        # migration_ip: 目标 ECS 私网 IP, 用于数据传输 (私网迁移必填)
        if migration_ip:
            args.append(f"--migration_ip={migration_ip}")
            logger.info(f"SMS CreateTask migration_ip={migration_ip} (target ECS private IP)")

        # SMS.0515 根因修复: SMS API 要求 size/used_size/free_size 单位为**字节**，
        # 非 GB。ecs_ops.py 和 migrate_worker.py 从 ShowServer 提取时做了 bytes→GB 转换
        # (// 1024**3)，此处需转回字节 (* 1024**3) 才能与源端 Agent 上报的磁盘信息匹配。
        # 参照优化版 skill: 直接传 ShowServer 字节值，不做单位转换。
        _GB = 1024 ** 3  # GB → bytes 转换因子
        if target_disks:
            for i, disk in enumerate(target_disks, 1):
                disk_size_gb = int(disk.get("size", 0))
                if disk_size_gb <= 0:
                    logger.warning(f"Invalid disk size {disk_size_gb} GB for disk {i}, skipping")
                    continue
                disk_size_bytes = disk_size_gb * _GB
                args.append(f"--target_server.disks.{i}.size={disk_size_bytes}")
                if disk.get("name"):
                    args.append(f"--target_server.disks.{i}.name={disk['name']}")
                # Issue 20: 传递目标云硬盘 ID (EVS volume ID)
                if disk.get("disk_id"):
                    args.append(f"--target_server.disks.{i}.disk_id={disk['disk_id']}")
                # Issue 20: 传递磁盘用途 (BOOT=系统盘, DATA=数据盘)
                if disk.get("device_use"):
                    args.append(f"--target_server.disks.{i}.device_use={disk['device_use']}")
                # SMS.0515 修复: used_size 已是字节 (ecs_ops.py 不再转 GB)，直接传
                if disk.get("used_size"):
                    args.append(f"--target_server.disks.{i}.used_size={int(disk['used_size'])}")
                # Issue 20: 传递物理卷信息 (LVM PV)
                # Issue 22: 完善 physical_volumes 传递链路 (从源端提取→目标磁盘→SMS API)
                pvs = disk.get("physical_volumes", [])
                pv_sent = 0
                for j, pv in enumerate(pvs, 1):
                    # SMS.0515 修复: SMS API 返回字段名为 "name"，兼容 "pv_name" 和 "name"
                    pv_name = pv.get("pv_name") or pv.get("name")
                    if not pv_name:
                        logger.warning(f"Skipping PV {j} on disk {i}: pv_name missing (SMS.6104)")
                        continue
                    pv_sent += 1
                    args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.name={pv_name}")
                    # Note: vg_name is not a valid API param for physical_volumes; skip it
                    # SMS.0515 修复: PV size/used_size 已是字节 (ecs_ops.py 不再转 GB)，直接传
                    if pv.get("size"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.size={int(pv['size'])}")
                    if pv.get("used_size"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.used_size={int(pv['used_size'])}")
                    if pv.get("uuid"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.uuid={pv['uuid']}")
                    # SMS.0515 修复: 补全 PV 字段，与源端 Agent 上报信息匹配
                    if pv.get("device_use"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.device_use={pv['device_use']}")
                    if pv.get("file_system"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.file_system={pv['file_system']}")
                    if pv.get("mount_point"):
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.mount_point={pv['mount_point']}")
                    if pv.get("index") is not None:
                        args.append(f"--target_server.disks.{i}.physical_volumes.{pv_sent}.index={pv['index']}")
                # Issue 22 修复: 传递卷组信息 (LVM VG)
                # volume_groups 描述磁盘上的 LVM 卷组，SMS 需要此信息匹配源端磁盘配置
                vgs = disk.get("volume_groups", [])
                for j, vg in enumerate(vgs, 1):
                    # SMS.0515 修复: 兼容 "vg_name" 和 "name" 字段
                    vg_name = vg.get("vg_name") or vg.get("name")
                    if vg_name:
                        args.append(f"--target_server.disks.{i}.volume_groups.{j}.name={vg_name}")
                    # Note: pv_count is not a valid API param for volume_groups; skip it
                    # SMS.0515 修复: VG size/free_size 已是字节 (ecs_ops.py 不再转 GB)，直接传
                    if vg.get("size"):
                        args.append(f"--target_server.disks.{i}.volume_groups.{j}.size={int(vg['size'])}")
                    if vg.get("free_size"):
                        args.append(f"--target_server.disks.{i}.volume_groups.{j}.free_size={int(vg['free_size'])}")
                logger.info(f"Target disk {i}: size={disk_size_gb}GB ({disk_size_bytes} bytes), disk_id={disk.get('disk_id', 'N/A')}, "
                           f"device_use={disk.get('device_use', 'N/A')}, pvs={pv_sent}, vgs={len(vgs)}")
                # SMS.0515 预防: 校验 PV 是否成功传递
                if pvs and pv_sent == 0:
                    logger.error(f"SMS.0515 RISK: disk {i} has {len(pvs)} PVs but none were sent! "
                                 f"PV data: {pvs}. Check field name mapping (name vs pv_name).")
        else:
            logger.info("No target_disks specified for SMS task, SMS will use defaults")

        # SMS.0515 预防: 记录所有磁盘相关参数用于排查
        disk_args = [a for a in args if "target_server.disks" in a]
        if disk_args:
            logger.info(f"SMS CreateTask disk params ({len(disk_args)} args):")
            for da in disk_args:
                logger.info(f"  {da}")

        # 额外参数
        for k, v in kwargs.items():
            args.append(f"--{k}={v}")

        logger.info(f"SMS CreateTask args: {len(args)} params, exist_server={exist_server}, os_type={os_type}")
        result = self._exec(args, timeout=60)
        if not result["success"]:
            logger.error(f"SMS CreateTask hcloud failed: error={result.get('error', '')[:500]}, raw={result.get('raw', '')[:500]}")
        return result["data"] if result["success"] else {}


    def sms_start_task(self, task_id: str) -> bool:
        """启动 SMS 迁移任务"""
        result = self._exec(["SMS", "UpdateTaskStatus", f"--task_id={task_id}", "--operation=start"])
        return result["success"]

    def sms_stop_task(self, task_id: str) -> bool:
        """停止 SMS 迁移任务"""
        result = self._exec(["SMS", "UpdateTaskStatus", f"--task_id={task_id}", "--operation=stop"])
        return result["success"]

    def sms_pause_task(self, task_id: str) -> bool:
        """暂停 SMS 迁移任务 (用于 AK/SK 更新时安全暂停)"""
        result = self._exec(["SMS", "UpdateTaskStatus", f"--task_id={task_id}", "--operation=pause"])
        return result["success"]

    def sms_resume_task(self, task_id: str) -> bool:
        """恢复 SMS 迁移任务 (AK/SK 更新完成后恢复)"""
        result = self._exec(["SMS", "UpdateTaskStatus", f"--task_id={task_id}", "--operation=start"])
        return result["success"]

    def sms_delete_task(self, task_id: str) -> bool:
        """删除 SMS 迁移任务"""
        result = self._exec(["SMS", "DeleteTask", f"--task_id={task_id}"])
        return result["success"]

    def sms_wait_task_complete(self, task_id: str, timeout: int = 7200,
                                interval: int = 30,
                                min_interval: int = 5,
                                backoff_factor: float = 1.5) -> Dict:
        """等待 SMS 迁移任务完成

        P1-2优化: 指数退避轮询 (5s→30s)，减少任务完成检测延迟。
        初始间隔 min_interval (默认5s)，每次乘以 backoff_factor (默认1.5)，
        直到达到 interval (默认30s) 上限。
        相比固定30s间隔，平均减少2-3分钟检测延迟。

        退避序列示例: 5s → 7.5s → 11.25s → 16.9s → 25.3s → 30s → 30s → ...

        Args:
            task_id: SMS 任务 ID
            timeout: 总超时秒数
            interval: 最大轮询间隔 (退避上限)
            min_interval: 初始轮询间隔 (退避起点)
            backoff_factor: 退避因子 (每次间隔乘以此值)

        Returns:
            {"completed": bool, "state": str, "progress": int, "error": str}
        """
        start = time.time()
        last_progress = -1
        # v2.5.0 优化3: 自适应轮询 — 前 5 分钟 10s 间隔 (快速检测), 之后 20s 间隔 (减少 API 调用)
        # 相比指数退避, 在长任务 (700-850s) 中后期减少 ~50% API 调用, 同时保持早期响应速度

        while time.time() - start < timeout:
            info = self.sms_show_task(task_id)
            state = info.get("state", "").upper()
            progress = info.get("progress", 0)

            if progress != last_progress:
                logger.info(f"SMS task {task_id}: state={state}, progress={progress}%")
                last_progress = progress

            if state in ("SUCCESS", "SUCCEED", "MIGRATE_SUCCESS"):
                return {"completed": True, "state": state, "progress": 100, "error": ""}
            elif state in ("FAIL", "FAILED", "MIGRATE_FAIL"):
                # error_json 是 JSON 字符串: {"error_code":"SMS.0515","error_param":"[]"}
                err_msg = "Unknown error"
                error_json = info.get("error_json", "")
                if error_json:
                    try:
                        ej = json.loads(error_json)
                        err_msg = ej.get("error_code", "") + ": " + str(ej.get("error_param", ""))
                    except (json.JSONDecodeError, ValueError):
                        err_msg = error_json
                return {"completed": False, "state": state, "progress": progress, "error": err_msg}
            elif state in ("STOPPED", "STOP"):
                return {"completed": False, "state": state, "progress": progress, "error": "stopped"}

            # v2.5.0 优化3: 自适应轮询间隔
            elapsed = time.time() - start
            current_interval = 10 if elapsed < 300 else 20
            time.sleep(current_interval)

        return {"completed": False, "state": "TIMEOUT", "progress": last_progress, "error": "timeout"}

    # ──────────────────────────────────────────────────────────────
    #  VPN 操作
    # ──────────────────────────────────────────────────────────────

    def vpn_list_gateways(self) -> Dict:
        """查询 VPN 网关列表"""
        result = self._exec(["VPN", "ListVgws"])
        return result["data"] if result["success"] else {}

    def vpn_show_gateway(self, vgw_id: str) -> Dict:
        """查询 VPN 网关详情"""
        result = self._exec(["VPN", "ShowVgw", f"--vgw_id={vgw_id}"])
        return result["data"] if result["success"] else {}

    def vpn_list_connections(self, vgw_id: str) -> Dict:
        """查询 VPN 连接列表"""
        result = self._exec(["VPN", "ListVpnConnections", f"--vgw_id={vgw_id}"])
        return result["data"] if result["success"] else {}

    # ──────────────────────────────────────────────────────────────
    #  VPC / 子网 / 安全组
    # ──────────────────────────────────────────────────────────────

    def vpc_list(self) -> Dict:
        """查询 VPC 列表"""
        result = self._exec(["VPC", "ListVpcs"])
        return result["data"] if result["success"] else {}

    def vpc_show(self, vpc_id: str) -> Dict:
        """查询 VPC 详情"""
        result = self._exec(["VPC", "ShowVpc", f"--vpc_id={vpc_id}"])
        return result["data"] if result["success"] else {}

    def subnet_list(self, vpc_id: str) -> Dict:
        """查询子网列表"""
        result = self._exec(["VPC", "ListSubnets", f"--vpc_id={vpc_id}"])
        return result["data"] if result["success"] else {}

    def sg_list(self) -> Dict:
        """查询安全组列表"""
        result = self._exec(["VPC", "ListSecurityGroups"])
        return result["data"] if result["success"] else {}

    # 安全约束: 禁止 0.0.0.0/0 (高危，必须指定具体网段或 IP)
    _BLOCKED_CIDRS = {"0.0.0.0/0", "0.0.0.0/0", "::/0"}

    @classmethod
    def _validate_remote_ip(cls, remote_ip: str, direction: str = "ingress") -> None:
        """校验 remote_ip，禁止 0.0.0.0/0 (ingress 高危)"""
        if not remote_ip:
            return
        normalized = remote_ip.strip().lower()
        if normalized in cls._BLOCKED_CIDRS and direction == "ingress":
            raise ValueError(
                f"安全约束违规: 禁止添加 ingress 规则 with remote_ip={remote_ip}。"
                "0.0.0.0/0 表示对所有 IP 开放，属于高危操作。"
                "请指定具体的源端 CIDR 网段或 IP 地址 (如 192.168.0.0/24)。"
            )

    def sg_create_rule(self, sg_id: str, protocol: str, port_range: str,
                       remote_ip: str, direction: str = "ingress",
                       action: str = "allow",
                       description: str = "") -> bool:
        """创建安全组规则

        Args:
            sg_id: 安全组 ID
            protocol: 协议 (tcp/udp/icmp/any)
            port_range: 端口范围 (如 "22" 或 "8081-8090")
            remote_ip: 源/目的 CIDR (禁止 0.0.0.0/0 for ingress)
            direction: 方向 (ingress/egress)
            action: 动作 (allow/deny)
            description: 规则描述

        Returns:
            是否成功
        """
        # 安全约束: 禁止 ingress 0.0.0.0/0
        self._validate_remote_ip(remote_ip, direction)

        args = [
            "VPC", "CreateSecurityGroupRule",
            f"--security_group_id={sg_id}",
            f"--protocol={protocol.lower()}",
            f"--port_range_min={port_range.split('-')[0]}",
            f"--port_range_max={port_range.split('-')[-1]}",
            f"--remote_ip_prefix={remote_ip}",
            f"--direction={direction}",
            f"--action={action}",
        ]
        if description:
            args.append(f"--description={description}")
        result = self._exec(args)
        return result["success"]

    def vpc_add_sg_rule(self, sg_id: str, protocol: str, port: str,
                        remote_ip: str, direction: str = "ingress",
                        description: str = "") -> bool:
        """添加安全组规则 (兼容方法，供 ecs_ops.py 调用)

        Args:
            sg_id: 安全组 ID
            protocol: 协议 (tcp/udp/icmp/any)
            port: 端口 (如 "22" 或 "8081-8090")
            remote_ip: 源/目的 CIDR (禁止 0.0.0.0/0 for ingress)
            direction: 方向 (ingress/egress)
            description: 规则描述

        Returns:
            是否成功
        """
        return self.sg_create_rule(
            sg_id=sg_id,
            protocol=protocol,
            port_range=port,
            remote_ip=remote_ip,
            direction=direction,
            description=description,
        )

    # ──────────────────────────────────────────────────────────────
    #  EIP 操作
    # ──────────────────────────────────────────────────────────────

    def eip_list(self) -> Dict:
        """查询 EIP 列表"""
        result = self._exec(["EIP", "ListPublicIps"])
        return result["data"] if result["success"] else {}

    def eip_create(self, bandwidth_size: int = 5, bandwidth_type: str = "PER_B") -> Dict:
        """创建 EIP"""
        args = [
            "EIP", "CreatePublicip",
            f"--bandwidth.size={bandwidth_size}",
            f"--bandwidth.share_type={bandwidth_type}",
        ]
        result = self._exec(args, timeout=60)
        return result["data"] if result["success"] else {}

    def eip_delete(self, eip_id: str) -> bool:
        """删除 EIP"""
        result = self._exec(["EIP", "DeletePublicip", f"--publicip_id={eip_id}"])
        return result["success"]

    def eip_bind(self, server_id: str, eip_id: str) -> bool:
        """绑定 EIP 到 ECS

        Args:
            server_id: ECS 实例 ID
            eip_id: EIP ID

        Returns:
            是否成功
        """
        args = [
            "EIP", "AssociatePublicip",
            f"--publicip_id={eip_id}",
            f"--port_id={server_id}",
        ]
        result = self._exec(args, timeout=60)
        return result["success"]

    def eip_unbind(self, server_id: str, eip_id: str) -> bool:
        """解绑 EIP

        Args:
            server_id: ECS 实例 ID
            eip_id: EIP ID

        Returns:
            是否成功
        """
        args = [
            "EIP", "DisassociatePublicip",
            f"--publicip_id={eip_id}",
        ]
        result = self._exec(args, timeout=60)
        return result["success"]

    # ──────────────────────────────────────────────────────────────
    #  IMS 镜像操作
    # ──────────────────────────────────────────────────────────────

    def ims_list(self, os_type: str = "Linux", name: str = None, image_type: str = None) -> Dict:
        """查询镜像列表

        Args:
            os_type: 操作系统类型 (Linux/Windows)
            name: 镜像名称关键字 (模糊匹配)
            image_type: 镜像类型 (gold=公共镜像, private=私有镜像)
        """
        args = ["IMS", "ListImages"]
        if os_type:
            args.append(f"--__os_type={os_type}")
        if name:
            args.append(f"--name={name}")
        if image_type:
            args.append(f"--__imagetype={image_type}")
        result = self._exec(args)
        return result["data"] if result["success"] else {}

    def ims_show(self, image_id: str) -> Dict:
        """查询镜像详情"""
        result = self._exec(["IMS", "ShowImageInfo", f"--image_id={image_id}"])
        return result["data"] if result["success"] else {}

    # ──────────────────────────────────────────────────────────────
    #  EVS 云硬盘操作
    # ──────────────────────────────────────────────────────────────

    def evs_list_volumes(self, server_id: str = None, limit: int = 100) -> Dict:
        """查询云硬盘列表"""
        args = ["EVS", "ListVolumes", f"--limit={limit}"]
        if server_id:
            args.append(f"--server_id={server_id}")
        result = self._exec(args)
        return result["data"] if result["success"] else {}

    def evs_show_volume(self, volume_id: str) -> Dict:
        """查询云硬盘详情"""
        result = self._exec(["EVS", "ShowVolume", f"--volume_id={volume_id}"])
        return result["data"] if result["success"] else {}

    def evs_list_types(self) -> Dict:
        """查询云硬盘类型"""
        result = self._exec(["EVS", "ListVolumeTypes"])
        return result["data"] if result["success"] else {}

    # ──────────────────────────────────────────────────────────────
    #  VPC / 子网 / 安全组 — 创建操作
    # ──────────────────────────────────────────────────────────────

    def vpc_create(self, name: str, cidr: str = "192.168.0.0/16") -> Dict:
        """创建 VPC"""
        args = [
            "VPC", "CreateVpc",
            f"--name={name}",
            f"--cidr={cidr}",
        ]
        result = self._exec(args, timeout=60)
        return result["data"] if result["success"] else {}

    def vpc_delete(self, vpc_id: str) -> bool:
        """删除 VPC"""
        result = self._exec(["VPC", "DeleteVpc", f"--vpc_id={vpc_id}"], timeout=60)
        return result["success"]

    def subnet_create(
        self,
        vpc_id: str,
        name: str,
        cidr: str = "192.168.0.0/24",
        gateway_ip: str = "192.168.0.1",
    ) -> Dict:
        """创建子网"""
        args = [
            "VPC", "CreateSubnet",
            f"--vpc_id={vpc_id}",
            f"--name={name}",
            f"--cidr={cidr}",
            f"--gateway_ip={gateway_ip}",
        ]
        result = self._exec(args, timeout=60)
        return result["data"] if result["success"] else {}

    def sg_create(self, name: str, vpc_id: str = None) -> Dict:
        """创建安全组 (v3 API, 不需要 vpc_id)"""
        args = [
            "VPC", "CreateSecurityGroup",
            f"--security_group.name={name}",
        ]
        result = self._exec(args, timeout=60)
        return result["data"] if result["success"] else {}

    def sg_delete(self, sg_id: str) -> bool:
        """删除安全组"""
        result = self._exec(["VPC", "DeleteSecurityGroup", f"--security_group_id={sg_id}"])
        return result["success"]
