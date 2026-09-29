#!/usr/bin/env python3
"""
batch_migrate.py — 批量迁移编排器

管理多台源端到目标 ECS 的批量迁移:
  - 从 Excel 读取迁移参数
  - 并发控制 (信号量限制)
  - 进度汇总和实时报告
  - 失败重试
  - 迁移结果汇总
  - 锁机制防止重复迁移
"""

import os
import time
import json
import signal
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from migrate_worker import MigrateWorker
from step_tracker import StepTracker
from excel_reader import ExcelReader
from safety_checker import SafetyChecker
from skill_logger import MigrationLogger as SkillLogger
from network_ops import CloudNetworkOps
from task_name_utils import sanitize_task_name, generate_task_name_from_ip
from credential_manager import CredentialManager


def _ensure_paramiko():
    """启动时自动检测并安装 paramiko 依赖 (pip3 install paramiko)。

    paramiko 是 SSH 远程操作的核心依赖，缺失时所有 SSH 操作将失败。
    本方法在 main() 入口最先调用，确保后续流程不受影响。
    """
    try:
        import paramiko  # noqa: F401
        return True
    except ImportError:
        import subprocess as _sp
        import sys as _sys
        print("[batch_migrate] paramiko 未安装，正在自动安装 (pip3 install paramiko)...")
        try:
            _r = _sp.run(
                [_sys.executable, "-m", "pip", "install", "paramiko", "--quiet"],
                capture_output=True, text=True, timeout=120,
            )
            if _r.returncode == 0:
                print("[batch_migrate] paramiko 安装成功")
                return True
            else:
                print(f"[batch_migrate] paramiko 安装失败 (code={_r.returncode}): {_r.stderr[:300]}")
                return False
        except Exception as e:
            print(f"[batch_migrate] paramiko 自动安装异常: {e}")
            return False

try:
    from ecs_ops import validate_ecs_name
    _HAS_NAME_VALIDATE = True
except ImportError:
    _HAS_NAME_VALIDATE = False

logger = logging.getLogger(__name__)


class BatchMigrate:
    """批量迁移编排器"""

    def __init__(
        self,
        migrate_worker: MigrateWorker,
        excel_reader: ExcelReader,
        safety_checker: SafetyChecker,
        config: Dict[str, Any],
        cloud_network_ops: CloudNetworkOps = None,
        proxy_ecs_ops: Any = None,
    ):
        """
        Args:
            migrate_worker: 单机迁移执行器
            excel_reader: Excel 读取器
            safety_checker: 安全检查器
            config: 全局配置
            cloud_network_ops: 云网络操作实例 (用于自动创建网络资源)
            proxy_ecs_ops: 代理 ECS 操作实例 (用于代理部署和 GOST 转发更新)
        """
        self.worker = migrate_worker
        self.excel = excel_reader
        self.safety = safety_checker
        self.config = config
        self.cloud_network = cloud_network_ops
        self.proxy_ops = proxy_ecs_ops

        # 优雅关闭标志 (用于信号处理)
        self._shutdown_requested = threading.Event()

        # 锁文件路径
        self.lock_dir = config.get("lock_dir", "/tmp/migration-locks")
        os.makedirs(self.lock_dir, exist_ok=True)

        # 结果存储
        self.results: List[Dict[str, Any]] = []
        self.results_lock = threading.Lock()

        # 统计
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "in_progress": 0,
        }

    # ──────────────────────────────────────────────────────
    #  锁机制
    # ──────────────────────────────────────────────────────

    def _lock_path(self, source_ip: str) -> str:
        """获取锁文件路径"""
        safe_ip = source_ip.replace(".", "_")
        return os.path.join(self.lock_dir, f"{safe_ip}.lock")

    def acquire_lock(self, source_ip: str) -> bool:
        """获取迁移锁 (防止重复迁移)

        Args:
            source_ip: 源端 IP

        Returns:
            是否获取成功
        """
        lock_file = self._lock_path(source_ip)
        if os.path.exists(lock_file):
            # 检查锁是否过期 (超过 24 小时)
            age = time.time() - os.path.getmtime(lock_file)
            if age < 86400:
                logger.warning(f"Lock exists for {source_ip} (age={age:.0f}s), skipping")
                return False
            else:
                logger.info(f"Stale lock for {source_ip} (age={age:.0f}s), removing")
                os.remove(lock_file)

        try:
            with open(lock_file, "w") as f:
                f.write(json.dumps({
                    "source_ip": source_ip,
                    "pid": os.getpid(),
                    "time": time.time(),
                }))
            return True
        except Exception as e:
            logger.error(f"Failed to acquire lock for {source_ip}: {e}")
            return False

    def release_lock(self, source_ip: str):
        """释放迁移锁"""
        lock_file = self._lock_path(source_ip)
        if os.path.exists(lock_file):
            os.remove(lock_file)

    # ──────────────────────────────────────────────────────
    #  任务读取和过滤
    # ──────────────────────────────────────────────────────

    def load_tasks(self, excel_path: str, sheet_name: str = None,
                   ak: str = "", sk: str = "") -> List[Dict[str, Any]]:
        """从 Excel 加载迁移任务 (支持2个Sheet页)

        Excel 结构:
            Sheet1 '主机信息': 源主机信息 (含 target_image_id, target_AZ)
            Sheet2 '代理主机信息': 代理/跳板机信息

        AK/SK 通过 credential_manager 从环境变量读取, 不再从 Excel 读取。

        Args:
            excel_path: Excel 文件路径
            sheet_name: 工作表名 (可选, 默认读取全部)
            ak: Access Key Id (来自环境变量 migration_Access_Key)
            sk: Secret Access Key (来自环境变量 migration_Secret_Access_Key)

        Returns:
            迁移任务列表
        """
        # 读取全部2个Sheet
        all_data = self.excel.read_all_sheets(excel_path)

        # 主机信息 → 迁移任务
        tasks = all_data.get("hosts", [])
        # 代理主机信息
        proxy_hosts = all_data.get("proxy_hosts", [])

        # 验证 AK/SK 已通过环境变量提供
        if not ak or not sk:
            logger.error(
                "AK/SK 未提供。请设置环境变量 migration_Access_Key 和 migration_Secret_Access_Key, "
                "禁止使用命令行明文参数或临时凭证。"
            )
            raise ValueError("AK/SK missing — environment variables required")

        logger.info(f"Loaded {len(tasks)} migration tasks from Excel")
        logger.info(f"Loaded {len(proxy_hosts)} proxy hosts")
        logger.info(f"AK/SK 来源: 环境变量 (credential_manager v2.9.0)")

        # 将代理主机和AK/SK信息注入到每个任务中
        for task in tasks:
            # 注入 AK/SK (来自 credential_manager, 已解密)
            task["ak"] = ak
            task["sk"] = sk
            # 注入代理主机信息 (取第一个代理主机)
            if proxy_hosts:
                proxy = proxy_hosts[0]
                task["proxy_ip"] = proxy.get("public_ip", "")
                task["proxy_private_ip"] = proxy.get("private_ip", "")
                task["proxy_port"] = proxy.get("port", 22)
                task["proxy_username"] = proxy.get("username", "root")
                task["proxy_password"] = proxy.get("password", "")

            # 注入本地 SMS Agent 路径 (通过环境变量 SMS_AGENT_PATH)
            agent_path = os.environ.get("SMS_AGENT_PATH", "")
            if agent_path and os.path.exists(agent_path):
                task["local_agent_path"] = agent_path
                logger.info(f"Using local SMS Agent: {agent_path}")

            # 注入 per-task GOST SSH 端口 (动态分配，每台源主机独立端口)
            # 起始端口 10022，按源端 IP 顺序递增
            # 不再硬编码端口映射表，而是在 run() 中统一动态分配
            pass

        # 生成并校验 target_name (目标端 ECS 主机名)
        # 命名规则: target_name = f"migrated-{source_name}"
        # 校验: 只能由中文字符、英文字母、数字及 _ - . 组成，长度 [1-128] 英文 / [1-64] 中文
        for task in tasks:
            if not task.get("target_name"):
                source_name = task.get("source_name", "")
                if source_name:
                    task["target_name"] = f"migrated-{source_name}"
                else:
                    # 回退: 使用 source_ip 生成
                    sip = task.get("source_ip", "unknown")
                    task["target_name"] = f"migrated-{sip.replace('.', '-')}"

            # 校验命名规则
            if _HAS_NAME_VALIDATE:
                tn = task.get("target_name", "")
                if tn:
                    try:
                        validate_ecs_name(tn)
                    except (ValueError, Exception) as e:
                        logger.error(
                            f"target_name '{tn}' 不符合命名规则: {e}。"
                            f"task source_ip={task.get('source_ip', '?')}"
                        )
                        # 自动修正: 替换非法字符
                        import re
                        fixed = re.sub(r'[^a-zA-Z0-9_\-.]', '-', tn)
                        if not fixed:
                            fixed = f"migrated-{task.get('source_ip', 'unknown').replace('.', '-')}"
                        task["target_name"] = fixed[:128]
                        logger.warning(f"target_name auto-corrected to '{task['target_name']}'")

        logger.info(f"target_name generated and validated for {len(tasks)} tasks")

        # 过滤: 只处理 use_public_ip=false 的任务 (私网迁移)
        private_tasks = [t for t in tasks if not t.get("use_public_ip", False)]
        public_tasks = [t for t in tasks if t.get("use_public_ip", False)]

        if public_tasks:
            logger.info(f"Skipping {len(public_tasks)} public-network tasks (use_public_ip=true)")

        logger.info(f"Private-network tasks to migrate: {len(private_tasks)}")

        return private_tasks

    def filter_ready_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤出可以立即执行的任务

        - 跳过已锁定的任务
        - 跳过安全检查不通过的任务
        """
        ready = []
        for task in tasks:
            source_ip = task.get("source_ip", "")

            # 检查锁
            if not self.acquire_lock(source_ip):
                self.stats["skipped"] += 1
                continue

            # 安全检查
            safety_result = self.safety.check_task_safety(task)
            if not safety_result["passed"]:
                logger.warning(f"Safety check failed for {source_ip}: {safety_result['errors']}")
                self.release_lock(source_ip)
                self.stats["skipped"] += 1
                # 记录跳过原因
                with self.results_lock:
                    self.results.append({
                        "source_ip": source_ip,
                        "success": False,
                        "skipped": True,
                        "error": f"Safety check: {'; '.join(safety_result['errors'])}",
                    })
                continue

            ready.append(task)

        return ready

    # ──────────────────────────────────────────────────────
    #  预部署阶段 (pre-deploy)
    # ──────────────────────────────────────────────────────

    def _pre_deploy_phase(self, ready_tasks: List[Dict[str, Any]]) -> bool:
        """预部署阶段: 在并发迁移前一次性完成代理 ECS 准备。

        解决 100 台并发时每个 task 独立安装 GOST/squid/rsync 导致的:
        - 重复安装 (100 次 GOST 安装竞态)
        - rsync 编译竞态 (多个线程同时编译)
        - squid 配置竞态

        本方法在 ThreadPoolExecutor 之前调用, 仅执行一次:
        1. 安装 GOST + squid (如尚未安装)
        2. 预编译 rsync (如尚未编译)
        3. 调优 sshd (支持高并发连接)

        Args:
            ready_tasks: 就绪任务列表

        Returns:
            是否成功
        """
        if not self.proxy_ops:
            logger.warning("proxy_ops not configured, skipping pre-deploy phase")
            return True

        if not ready_tasks:
            return True

        logger.info("=== Pre-deployment phase started ===")
        pre_deploy_start = time.time()

        try:
            # Step 1: 安装依赖 (GOST + squid)
            logger.info("[pre-deploy] Step 1: Installing dependencies (GOST + squid)")
            if hasattr(self.proxy_ops, 'install_dependencies'):
                if not self.proxy_ops.install_dependencies():
                    logger.warning("[pre-deploy] Dependency installation failed, "
                                   "individual tasks may retry")
                else:
                    logger.info("[pre-deploy] Dependencies installed successfully")

            # Step 2: 调优 sshd (支持 100 并发连接)
            logger.info("[pre-deploy] Step 2: Tuning sshd for high concurrency")
            if hasattr(self.proxy_ops, 'tune_sshd_for_concurrency'):
                try:
                    self.proxy_ops.tune_sshd_for_concurrency(max_concurrent=100)
                    logger.info("[pre-deploy] sshd tuned for 100 concurrent connections")
                except Exception as e:
                    logger.warning(f"[pre-deploy] sshd tuning failed: {e}")

            # Step 3: 预部署 rsync (二进制包优先，源码编译兜底)
            rsync_bin = os.environ.get("RSYNC_BINARY_PATH", "")
            if rsync_bin:
                logger.info(f"[pre-deploy] Step 3: Deploying rsync binary package: {rsync_bin}")
            else:
                logger.info("[pre-deploy] Step 3: Pre-compiling rsync on proxy ECS (no binary package found)")
            try:
                from gost_ops import GostOps
                gost = GostOps(self.proxy_ops.ssh)
                # 检查 rsync 是否已编译
                out, _, _ = gost._exec(
                    "test -x /opt/rsync-bin/rsync && /opt/rsync-bin/rsync --version | head -1"
                )
                if out and ("rsync  version" in out.lower() or "rsync version" in out.lower()):
                    logger.info(f"[pre-deploy] rsync already compiled: {out}")
                else:
                    logger.info("[pre-deploy] Compiling rsync on proxy ECS...")
                    # 使用 SMSAgentPush 的编译方法 (带锁保护)
                    from sms_agent_push import SMSAgentPush
                    # 创建临时实例用于编译
                    proxy_ip = self.config.get("proxy_public_ip", "")
                    proxy_user = self.config.get("proxy_username", "root")
                    proxy_pass = self.config.get("proxy_password", "")
                    proxy_ssh = self.proxy_ops.ssh
                    sms_push = SMSAgentPush(
                        ssh_utils=proxy_ssh,
                        proxy_ip=proxy_ip,
                        proxy_username=proxy_user,
                        proxy_password=proxy_pass,
                    )
                    # 直接在代理 ECS 上编译
                    if hasattr(proxy_ssh, 'client') and proxy_ssh.client:
                        sms_push._compile_rsync_on_proxy(proxy_ssh.client)
                        logger.info("[pre-deploy] rsync compiled successfully")
                    else:
                        # 尝试连接
                        try:
                            conn = proxy_ssh.connect()
                            sms_push._compile_rsync_on_proxy(conn.client)
                            proxy_ssh.disconnect(conn)
                            logger.info("[pre-deploy] rsync compiled successfully")
                        except Exception as e:
                            logger.warning(f"[pre-deploy] rsync compilation failed: {e}")
            except ImportError:
                logger.warning("[pre-deploy] sms_agent_push module not available, "
                               "rsync will be compiled per-task")
            except Exception as e:
                logger.warning(f"[pre-deploy] rsync pre-compilation failed: {e}")

            # Step 4: 配置 squid (收集所有源端 IP)
            logger.info("[pre-deploy] Step 4: Configuring squid for all source IPs")
            try:
                source_ips = [t.get("source_ip", "") for t in ready_tasks if t.get("source_ip")]
                if source_ips and hasattr(self.proxy_ops, 'configure_squid'):
                    self.proxy_ops.configure_squid(source_ips)
                    logger.info(f"[pre-deploy] squid configured for {len(source_ips)} source IPs")
            except Exception as e:
                logger.warning(f"[pre-deploy] squid configuration failed: {e}")

            elapsed = round(time.time() - pre_deploy_start, 1)
            logger.info(f"=== Pre-deployment phase completed ({elapsed}s) ===")
            return True

        except Exception as e:
            logger.error(f"Pre-deployment phase failed: {e}")
            return False

    # ──────────────────────────────────────────────────────
    #  单任务执行 (线程池调用)
    # ──────────────────────────────────────────────────────

    def _execute_single(self, task: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """执行单个迁移任务 (带重试 + 完整异常隔离)

        异常隔离保证:
          - 任何异常 (包括未预期的) 都被捕获，不会传播到线程池
          - 单任务失败不影响其他任务
          - 每个任务有独立的结果记录
          - 锁始终被释放 (finally)

        Args:
            task: 迁移任务
            retry_count: 当前重试次数

        Returns:
            迁移结果 (始终返回 dict，永不抛出异常)
        """
        source_ip = task.get("source_ip", "")
        # Issue 21 修复: SMS 任务名称规则 — 只能由中文字符、英文字母、数字、下划线、短横线组成
        # 最小长度 1, 最大长度 20。使用 generate_task_name_from_ip 确保符合规则。
        if task.get("task_name"):
            task_name = sanitize_task_name(task.get("task_name"))
        else:
            task_name = generate_task_name_from_ip(source_ip)
        max_retries = self.config.get("max_retries", 2)
        retry_delay = self.config.get("retry_delay", 10)

        # 默认结果 (异常时返回)
        default_result = {
            "source_ip": source_ip,
            "task_name": task_name,
            "success": False,
            "phase": "init",
            "error": "",
            "duration": 0,
            "task_id": "",
            "source_id": "",
            "retry_count": retry_count,
        }

        try:
            with self.results_lock:
                self.stats["in_progress"] += 1

            logger.info(f"[TASK] {source_ip} starting (attempt {retry_count + 1}/{max_retries + 1})")

            # 执行迁移 — 核心调用，所有异常被外层 try 捕获
            result = self.worker.execute_migration(task)

            # 确保 result 是 dict (防御性编程)
            if not isinstance(result, dict):
                result = dict(default_result)
                result["error"] = f"Worker returned non-dict: {type(result)}"
            else:
                result.setdefault("retry_count", retry_count)

            # 失败重试 (仅在异常隔离内)
            if not result.get("success", False) and retry_count < max_retries:
                # P3-8优化: 指数退避替代固定延迟
                actual_delay = retry_delay * (1.5 ** retry_count)
                actual_delay = min(actual_delay, retry_delay * 4)  # 上限为初始延迟的4倍
                logger.warning(
                    f"[TASK] {source_ip} failed (phase={result.get('phase', '?')}), "
                    f"retrying {retry_count + 1}/{max_retries} after {actual_delay:.1f}s..."
                )
                time.sleep(actual_delay)
                # 递归重试 (异常隔离保证不会栈溢出)
                result = self._execute_single(task, retry_count + 1)
                return result

            # 记录结果
            with self.results_lock:
                self.stats["in_progress"] -= 1
                if result.get("success", False):
                    self.stats["success"] += 1
                    logger.info(f"[TASK] {source_ip} ✅ SUCCESS (phase={result.get('phase', 'completed')})")
                else:
                    self.stats["failed"] += 1
                    logger.error(
                        f"[TASK] {source_ip} ❌ FAILED (phase={result.get('phase', '?')}, "
                        f"error={result.get('error', 'unknown')[:200]})"
                    )
                self.results.append(result)

        except Exception as e:
            # 🛡️ 异常隔离: 捕获所有异常，确保不影响其他任务
            logger.exception(f"[TASK] {source_ip} 💥 UNEXPECTED EXCEPTION: {e}")
            default_result["error"] = f"Isolated exception: {str(e)[:500]}"
            default_result["phase"] = "exception"

            with self.results_lock:
                self.stats["in_progress"] = max(0, self.stats["in_progress"] - 1)
                self.stats["failed"] += 1
                self.results.append(default_result)

            result = default_result

        finally:
            # 🔒 锁始终释放 (即使异常)
            self.release_lock(source_ip)

        return result

    # ──────────────────────────────────────────────────────
    #  两阶段执行 (prepare → batch GOST → migrate)
    # ──────────────────────────────────────────────────────

    def _execute_prepare_phase(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行准备阶段: ensure_agent → ensure_target_ecs

        异常完全隔离, 单任务失败不影响其他。
        返回 prepare_result + task (已更新 source_server_id, target_server_id 等)
        """
        source_ip = task.get("source_ip", "")
        if task.get("task_name"):
            task_name = sanitize_task_name(task.get("task_name"))
        else:
            task_name = generate_task_name_from_ip(source_ip)
        task["task_name"] = task_name

        # 创建每任务独立日志
        safe_ip = source_ip.replace(".", "_") if source_ip else "unknown"
        task_log_id = f"{safe_ip}_prepare_{int(time.time())}"
        task_logger = SkillLogger(
            log_dir=self.worker.log_dir,
            task_id=task_log_id,
            level=logging.INFO,
        )
        tlog = task_logger.get_logger()

        result = {
            "source_ip": source_ip,
            "task_name": task_name,
            "success": False,
            "phase": "prepare",
            "error": "",
            "log_file": task_logger.get_log_path(),
        }

        step_tracker = StepTracker()

        try:
            tlog.info(f"=== Prepare phase: {source_ip} ===")
            prepare_result = self.worker._prepare_phase(task, task_logger, tlog, step_tracker)
            if not prepare_result["success"]:
                result["error"] = prepare_result.get("error", "Prepare phase failed")
                result["step_tracking"] = step_tracker.get_summary()
                return result
            result["success"] = True
            result["target_server_id"] = prepare_result["target_server_id"]
            result["target_private_ip"] = prepare_result.get("target_private_ip", "")
            result["created"] = prepare_result.get("created", False)
            result["source_id"] = prepare_result.get("source_id", "")
            result["step_tracking"] = step_tracker.get_summary()
            tlog.info(f"Prepare phase completed: source_id={result['source_id']}, "
                      f"target={result['target_server_id']}")
        except Exception as e:
            tlog.exception(f"Prepare phase exception for {source_ip}")
            result["error"] = f"Isolated exception: {str(e)[:500]}"
            result["phase"] = "prepare_exception"
            result["step_tracking"] = step_tracker.get_summary()

        return result

    def _execute_migrate_phase(self, task: Dict[str, Any], prepare_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行迁移阶段: pre_check → create_task → migrating → verify

        异常完全隔离, 单任务失败不影响其他。
        """
        source_ip = task.get("source_ip", "")
        task_name = task.get("task_name", "")

        # 复用 prepare 阶段的日志
        safe_ip = source_ip.replace(".", "_") if source_ip else "unknown"
        task_log_id = f"{safe_ip}_migrate_{int(time.time())}"
        task_logger = SkillLogger(
            log_dir=self.worker.log_dir,
            task_id=task_log_id,
            level=logging.INFO,
        )
        tlog = task_logger.get_logger()

        result = {
            "source_ip": source_ip,
            "task_name": task_name,
            "success": False,
            "phase": "migrate",
            "error": "",
            "duration": 0,
            "task_id": "",
            "source_id": prepare_result.get("source_id", ""),
            "target_server_id": task.get("target_server_id", ""),
            "log_file": task_logger.get_log_path(),
        }

        step_tracker = StepTracker()

        start_time = time.time()

        try:
            tlog.info(f"=== Migrate phase: {source_ip} -> {task.get('target_server_id', '')} ===")
            # 标记非单任务模式 (GOST 数据转发已由批量处理)
            task["_single_task_mode"] = False
            migrate_result = self.worker._migrate_phase(task, prepare_result, task_logger, tlog, step_tracker)
            result.update(migrate_result)
            result["source_ip"] = source_ip
            result["task_name"] = task_name
            result["log_file"] = task_logger.get_log_path()
        except Exception as e:
            tlog.exception(f"Migrate phase exception for {source_ip}")
            result["error"] = f"Isolated exception: {str(e)[:500]}"
            result["phase"] = "migrate_exception"

        result["duration"] = round(time.time() - start_time, 1)
        result["step_tracking"] = step_tracker.get_summary()
        return result

    def _batch_gost_data_forwards(self, prepared_tasks: List[Dict[str, Any]]) -> bool:
        """批量为所有新创建的目标 ECS 添加 GOST 数据流转发 (单次热重载)

        Args:
            prepared_tasks: 已完成 prepare 阶段的 task 列表

        Returns:
            是否成功
        """
        targets_to_forward = []
        for task in prepared_tasks:
            # 仅对新创建的目标 ECS 添加数据转发
            if not task.get("_target_created", False):
                continue
            target_private_ip = task.get("target_private_ip", "")
            if not target_private_ip:
                logger.warning(f"Task {task.get('source_ip', '?')}: no target_private_ip, skipping GOST forward")
                continue
            gost_data_ports = task.get("gost_data_ports", [8899, 8900])
            gost_data_local_ports = task.get("gost_data_local_ports", gost_data_ports)
            targets_to_forward.append((target_private_ip, gost_data_ports, gost_data_local_ports))

        if not targets_to_forward:
            logger.info("No new target ECS needs GOST data forward")
            return True

        logger.info(f"Batch adding GOST data forwards for {len(targets_to_forward)} new targets")
        if not self.proxy_ops:
            logger.error("proxy_ops not available, cannot batch update GOST forwards")
            return False

        return self.proxy_ops.batch_update_target_forwards(targets_to_forward)

    # ──────────────────────────────────────────────────────
    #  批量执行
    # ──────────────────────────────────────────────────────

    def run(
        self,
        excel_path: str,
        sheet_name: str = None,
        max_workers: int = 20,
        dry_run: bool = False,
        max_workers_prepare: int = None,
        max_workers_migrate: int = None,
        ak: str = "",
        sk: str = "",
    ) -> Dict[str, Any]:
        """执行批量迁移

        P1-3优化: 分阶段独立并发控制。
        Phase A (准备) 和 Phase B (迁移) 可使用不同的并发数，
        优化资源利用: 准备阶段轻量可高并发，迁移阶段重负载可低并发。

        Args:
            excel_path: Excel 文件路径
            sheet_name: 工作表名
            max_workers: 最大并发数 (默认 20, 支持 100 台源端并发)
            dry_run: 干跑模式 (仅检查不执行)
            max_workers_prepare: Phase A 准备阶段并发数 (None 则用 max_workers)
            max_workers_migrate: Phase B 迁移阶段并发数 (None 则用 max_workers)

        Returns:
            汇总结果
        """
        logger.info(f"=== Batch migration started ===")
        logger.info(f"Excel: {excel_path}, max_workers={max_workers}, dry_run={dry_run}")

        # P1-3优化: 分阶段并发数，未指定时回退到 max_workers
        workers_prepare = max_workers_prepare or max_workers
        workers_migrate = max_workers_migrate or max_workers
        logger.info(f"Phase concurrency: prepare={workers_prepare}, migrate={workers_migrate}")

        # 重置统计
        self.stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0, "in_progress": 0}
        self.results = []

        start_time = time.time()

        # 1. 加载任务
        tasks = self.load_tasks(excel_path, sheet_name, ak=ak, sk=sk)
        self.stats["total"] = len(tasks)

        if not tasks:
            logger.warning("No tasks to migrate")
            return self._summary(0)

        # 2. 过滤就绪任务
        ready_tasks = self.filter_ready_tasks(tasks)
        logger.info(f"Ready tasks: {len(ready_tasks)}/{len(tasks)}")

        if dry_run:
            logger.info("Dry run mode - no migration executed")
            for task in ready_tasks:
                self.release_lock(task.get("source_ip", ""))
            return self._summary(time.time() - start_time)

        # 3. 准备网络资源 (VPC/子网/安全组)
        # 如果配置中没有指定网络资源, 且有 cloud_network_ops, 则自动创建
        vpc_id = self.config.get("vpc_id", "")
        subnet_id = self.config.get("subnet_id", "")
        sg_id = self.config.get("sg_id", "")

        # ── 优先从代理 ECS 获取网络资源, 直接复用 ──
        if not vpc_id or not subnet_id or not sg_id:
            proxy_private_ip = ""
            proxy_server_id = ""
            if ready_tasks:
                proxy_private_ip = ready_tasks[0].get("proxy_private_ip", "")
                proxy_server_id = ready_tasks[0].get("proxy_server_id", "")
            if not proxy_private_ip:
                proxy_private_ip = self.config.get("proxy_private_ip", "")
            if not proxy_server_id:
                proxy_server_id = self.config.get("proxy_server_id", "")

            if proxy_private_ip or proxy_server_id:
                logger.info("Discovering network from proxy ECS...")
                try:
                    proxy_net = self.worker.ecs.get_proxy_network_info(
                        server_id=proxy_server_id,
                        private_ip=proxy_private_ip,
                    )
                    if proxy_net:
                        if not vpc_id:
                            vpc_id = proxy_net.get("vpc_id", "")
                        if not subnet_id:
                            subnet_id = proxy_net.get("subnet_id", "")
                        if not sg_id and proxy_net.get("sg_ids"):
                            sg_id = proxy_net["sg_ids"][0]
                        logger.info(
                            f"Reusing proxy ECS network: VPC={vpc_id}, "
                            f"subnet={subnet_id}, SG={sg_id}"
                        )
                        # 确保代理 SG 包含目标 ECS 所需端口 (22/8899/8900)
                        if sg_id:
                            source_cidr = self.config.get("source_cidr", "")
                            if not source_cidr and proxy_net.get("private_ip"):
                                source_cidr = CloudNetworkOps.compute_source_cidr(
                                    [proxy_net["private_ip"]]
                                )
                            if (
                                source_cidr
                                and source_cidr.strip().lower()
                                not in ("0.0.0.0/0", "::/0")
                            ):
                                self.worker.ecs.ensure_sg_rules_for_migration(
                                    sg_id, source_cidr=source_cidr
                                )
                                logger.info(
                                    f"Ensured target ECS ports (22/8899/8900) "
                                    f"open in proxy SG {sg_id} for {source_cidr}"
                                )
                except Exception as e:
                    logger.warning(f"Failed to discover proxy ECS network: {e}")

        if not vpc_id and self.cloud_network:
            # 安全约束: source_cidr 禁止 0.0.0.0/0
            source_cidr = self.config.get("source_cidr", "")
            if not source_cidr or source_cidr.strip().lower() in ("0.0.0.0/0", "::/0"):
                # 尝试从所有源端 IP 推导汇总 CIDR
                all_source_ips = [t.get("source_ip", "") for t in ready_tasks if t.get("source_ip")]
                if all_source_ips:
                    source_cidr = CloudNetworkOps.compute_source_cidr(all_source_ips)
                if not source_cidr:
                    logger.error(
                        "安全约束: source_cidr 未指定且无法从源端 IP 推导。"
                        "禁止使用 0.0.0.0/0。请在 config 或 Excel 中指定具体源端 CIDR。"
                    )
                    for task in ready_tasks:
                        self.release_lock(task.get("source_ip", ""))
                    return self._summary(time.time() - start_time)
                logger.info(f"Auto-computed source_cidr={source_cidr} from source IPs")

            logger.info("Auto-creating network resources (VPC/subnet/SG)...")
            net_result = self.cloud_network.ensure_migration_network(
                vpc_name=self.config.get("vpc_name", "migration-vpc"),
                subnet_name=self.config.get("subnet_name", "migration-subnet"),
                sg_name=self.config.get("sg_name", "migration-sg"),
                source_cidr=source_cidr,
            )
            if net_result:
                vpc_id = net_result["vpc_id"]
                subnet_id = net_result["subnet_id"]
                sg_id = net_result["sg_id"]
                logger.info(f"Network ready: VPC={vpc_id}, subnet={subnet_id}, SG={sg_id}")
            else:
                logger.error("Failed to create network resources, aborting")
                for task in ready_tasks:
                    self.release_lock(task.get("source_ip", ""))
                return self._summary(time.time() - start_time)

        # 将网络资源注入到每个任务
        for task in ready_tasks:
            if vpc_id:
                task.setdefault("vpc_id", vpc_id)
            if subnet_id:
                task.setdefault("subnet_id", subnet_id)
            if sg_id:
                task.setdefault("sg_id", sg_id)
            # 注入单任务超时 (从全局配置)
            task.setdefault("task_timeout", self.config.get("task_timeout", 10800))
            # 注入深度校验标志
            if self.config.get("deep_verify"):
                task["deep_verify"] = True

        # 3b. 动态分配 GOST SSH 端口 + 数据流端口 (每台源端机独立端口)
        GOST_SSH_PORT_START = 10022
        DATA_PORT_BASE = 8899  # 数据流起始端口, 每台目标 ECS 占 2 个端口 (8899+idx*2, 8900+idx*2)
        for idx, task in enumerate(ready_tasks):
            sip = task.get("source_ip", "")
            if sip and not task.get("gost_ssh_port"):
                task["gost_ssh_port"] = GOST_SSH_PORT_START + idx
                logger.info(f"Task {sip} assigned GOST SSH port {task['gost_ssh_port']}")

            # 每台目标 ECS 独立数据流端口 (避免多台目标 ECS 争抢同一端口)
            if not task.get("gost_data_local_ports"):
                local_port_1 = DATA_PORT_BASE + idx * 2       # 8899, 8901, 8903, ...
                local_port_2 = local_port_1 + 1               # 8900, 8902, 8904, ...
                task["gost_data_local_ports"] = [local_port_1, local_port_2]
                task["gost_data_ports"] = [8899, 8900]  # 目标 ECS 侧始终是 8899/8900
                logger.info(
                    f"Task {sip} assigned data stream ports: "
                    f"local=[{local_port_1},{local_port_2}] -> target=[8899,8900]"
                )

        # 3b-2. 批量创建 GOST SSH 管理通道转发 (所有源端一次性部署, 仅一次 GOST 重启)
        if self.proxy_ops and ready_tasks:
            source_hosts_for_gost = []
            for task in ready_tasks:
                sip = task.get("source_ip", "")
                gost_port = task.get("gost_ssh_port")
                if sip and gost_port:
                    source_ssh_port = task.get("source_port", 22)
                    source_hosts_for_gost.append((sip, source_ssh_port, gost_port))

            if source_hosts_for_gost:
                logger.info(
                    f"Batch creating GOST SSH forwards for {len(source_hosts_for_gost)} source hosts"
                )
                try:
                    if self.proxy_ops.batch_create_ssh_forwards(source_hosts_for_gost):
                        logger.info("All GOST SSH forwards created successfully")
                    else:
                        logger.warning(
                            "Batch GOST SSH forward creation failed; "
                            "individual tasks may fail at pre_check"
                        )
                except Exception as e:
                    logger.warning(f"Batch GOST SSH forward exception: {e}")
        else:
            if not self.proxy_ops:
                logger.warning(
                    "proxy_ecs_ops not configured; GOST SSH forwards must be pre-created. "
                    "100-host concurrency requires batch_create_ssh_forwards."
                )

        # 3c. 计算并注入 source_cidr 到每个任务 (如果尚未指定)
        if not self.config.get("source_cidr"):
            all_source_ips = [t.get("source_ip", "") for t in ready_tasks if t.get("source_ip")]
            if all_source_ips:
                computed_cidr = CloudNetworkOps.compute_source_cidr(all_source_ips)
                if computed_cidr:
                    for task in ready_tasks:
                        task.setdefault("source_cidr", computed_cidr)
                    logger.info(f"Injected source_cidr={computed_cidr} into all tasks")

        # 3d. 预部署阶段 (pre-deploy): 在并发迁移前一次性完成代理 ECS 准备
        # 解决 100 台并发时每个 task 独立安装 GOST/squid/rsync 导致的竞态和重复
        self._pre_deploy_phase(ready_tasks)

        # 4. 两阶段并发执行 (prepare → batch GOST → migrate)
        # P1-3优化: 各阶段独立并发数，不超过任务数
        workers_prepare = max(1, min(workers_prepare, len(ready_tasks)))
        workers_migrate = max(1, min(workers_migrate, len(ready_tasks)))
        logger.info(f"Starting two-phase migration: {len(ready_tasks)} tasks, "
                    f"workers_prepare={workers_prepare}, workers_migrate={workers_migrate}")

        # 并发建议: 任务数 > 50 且 max_workers < 20 时提示
        if len(ready_tasks) > 50 and max(workers_prepare, workers_migrate) < 20:
            logger.warning(
                f"⚠ {len(ready_tasks)} 台源端但 max_workers={max_workers}, "
                f"建议设置 --max-workers 20~30 以提高并发效率"
            )

        # v2.5.0 优化2: Phase A→B 流水线化 (消除同步屏障)
        # 每个 task 完成 prepare 后立即添加 GOST 转发并进入 migrate, 无需等待其他 task
        logger.info(f"=== Pipeline: Prepare → GOST → Migrate ({len(ready_tasks)} tasks) ===")
        pipeline_start = time.time()
        prepared_count = 0
        failed_prepare_count = 0

        # 使用两个线程池: prepare 和 migrate 并行流水线
        migrate_executor = ThreadPoolExecutor(max_workers=workers_migrate, thread_name_prefix="migrate")
        migrate_futures = {}  # future -> (task, prep_result)

        with ThreadPoolExecutor(max_workers=workers_prepare, thread_name_prefix="prepare") as prep_executor:
            prep_future_to_task = {
                prep_executor.submit(self._execute_prepare_phase, task): task
                for task in ready_tasks
            }

            for future in as_completed(prep_future_to_task):
                task = prep_future_to_task[future]
                source_ip = task.get("source_ip", "")
                try:
                    prep_result = future.result(timeout=600)  # prepare 超时 10min
                    if prep_result.get("success"):
                        # 标记目标是否新创建
                        task["_target_created"] = prep_result.get("created", False)
                        prepared_count += 1
                        logger.info(f"[Pipeline] {source_ip}: ✅ prepared "
                                    f"(target={prep_result.get('target_server_id', '?')})")

                        # 立即为该 task 添加 GOST 数据流转发 (线程安全, _config_lock 保护)
                        if task.get("_target_created", False):
                            target_private_ip = task.get("target_private_ip", "")
                            if target_private_ip and self.proxy_ops:
                                gost_data_ports = task.get("gost_data_ports", [8899, 8900])
                                gost_data_local_ports = task.get("gost_data_local_ports", gost_data_ports)
                                try:
                                    self.proxy_ops.batch_update_target_forwards(
                                        [(target_private_ip, gost_data_ports, gost_data_local_ports)]
                                    )
                                    logger.info(f"[Pipeline] {source_ip}: GOST forward added")
                                except Exception as ge:
                                    logger.warning(f"[Pipeline] {source_ip}: GOST forward failed: {ge}")

                        # 立即提交到 migrate 线程池 (无需等待其他 prepare 完成)
                        mig_future = migrate_executor.submit(
                            self._execute_migrate_phase, task, prep_result
                        )
                        migrate_futures[mig_future] = (task, prep_result)
                    else:
                        failed_prepare_count += 1
                        logger.error(f"[Pipeline] {source_ip}: ❌ prepare failed: "
                                     f"{prep_result.get('error', '?')[:200]}")
                        # 记录 prepare 失败
                        with self.results_lock:
                            self.stats["failed"] += 1
                            self.results.append({
                                "source_ip": source_ip,
                                "task_name": task.get("task_name", ""),
                                "success": False,
                                "phase": "prepare",
                                "error": prep_result.get("error", "prepare failed"),
                                "duration": 0,
                            })
                        self.release_lock(source_ip)
                except Exception as e:
                    logger.error(f"[Pipeline] {source_ip}: prepare pool error: {e}")
                    failed_prepare_count += 1
                    with self.results_lock:
                        self.stats["failed"] += 1
                        self.results.append({
                            "source_ip": source_ip,
                            "task_name": task.get("task_name", ""),
                            "success": False,
                            "phase": "prepare",
                            "error": f"Pool exception: {str(e)[:500]}",
                            "duration": 0,
                        })
                    self.release_lock(source_ip)

        # 所有 prepare 已完成, migrate 任务已在流水线中提交
        phase_a_duration = time.time() - pipeline_start
        logger.info(f"Phase A completed in {phase_a_duration:.1f}s: "
                    f"{prepared_count} prepared, {failed_prepare_count} failed")

        if not migrate_futures:
            logger.error("No tasks prepared successfully, aborting migration")
            migrate_executor.shutdown(wait=False)
            duration = time.time() - start_time
            summary = self._summary(duration)
            return summary

        # 等待所有 migrate 任务完成
        logger.info(f"=== Phase B: Waiting for {len(migrate_futures)} migrate tasks ===")
        phase_b_start = time.time()

        for future in as_completed(migrate_futures):
            # 检查是否收到关闭信号 (Ctrl+C / SIGTERM)
            if self._shutdown_requested.is_set():
                logger.warning("Shutdown requested, cancelling remaining tasks...")
                for f in migrate_futures:
                    f.cancel()
                break

            task, prep_result = migrate_futures[future]
            source_ip = task.get("source_ip", "")
            try:
                result = future.result(timeout=task.get("task_timeout", 10800))  # 单任务超时 3h
                with self.results_lock:
                    if result.get("success"):
                        self.stats["success"] += 1
                        logger.info(f"[Phase B] {source_ip}: ✅ SUCCESS")
                    else:
                        self.stats["failed"] += 1
                        logger.error(f"[Phase B] {source_ip}: ❌ FAILED "
                                     f"(phase={result.get('phase', '?')}, "
                                     f"error={result.get('error', '?')[:200]})")
                    self.results.append(result)
            except Exception as e:
                logger.error(f"[Phase B] {source_ip}: pool error: {e}")
                with self.results_lock:
                    self.stats["failed"] += 1
                    self.results.append({
                        "source_ip": source_ip,
                        "task_name": task.get("task_name", ""),
                        "success": False,
                        "phase": "migrate_pool_exception",
                        "error": f"Pool exception: {str(e)[:500]}",
                        "duration": 0,
                    })
            finally:
                self.release_lock(source_ip)

        migrate_executor.shutdown(wait=True)

        phase_b_duration = time.time() - phase_b_start
        logger.info(f"Phase B completed in {phase_b_duration:.1f}s")

        duration = time.time() - start_time
        summary = self._summary(duration)

        logger.info(f"=== Batch migration completed in {duration:.1f}s ===")
        logger.info(f"Stats: {self.stats}")

        return summary

    # ──────────────────────────────────────────────────────
    #  汇总
    # ──────────────────────────────────────────────────────

    def deploy_proxy(self, proxy_config: Dict[str, Any]) -> Dict[str, Any]:
        """部署代理 ECS (squid + GOST + rsync)。

        在批量迁移前调用，部署代理 ECS 并配置:
        - squid: SMS Agent 控制流代理 (→ 云API:443)
        - GOST: 数据流转发 (源端 → 目标 ECS)
        - rsync: 文件同步

        Args:
            proxy_config: 代理配置, 包含:
                - proxy_ip: 代理 ECS 公网 IP
                - proxy_private_ip: 代理 ECS 内网 IP
                - proxy_username: SSH 用户名
                - proxy_password: SSH 密码
                - source_ips: 源端 IP 列表 (用于 GOST 端口映射)
                - target_api_endpoint: 云 API 端点
                - squid_port: squid 代理端口 (默认 3128)

        Returns:
            部署结果
        """
        if not self.proxy_ops:
            logger.error("proxy_ecs_ops not provided, cannot deploy proxy")
            return {"success": False, "error": "proxy_ecs_ops not configured"}

        logger.info("=== Proxy ECS deployment ===")
        logger.info(f"Proxy IP: {proxy_config.get('proxy_ip', 'N/A')}")

        try:
            result = self.proxy_ops.deploy_all(proxy_config)
            if result.get("success"):
                logger.info("Proxy ECS deployed successfully (squid + GOST + rsync)")
            else:
                logger.error(f"Proxy deployment failed: {result.get('error', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Proxy deployment exception: {e}")
            return {"success": False, "error": str(e)}

    def _summary(self, duration: float) -> Dict[str, Any]:
        """生成汇总报告 (含每任务日志路径)"""
        return {
            "stats": dict(self.stats),
            "duration": round(duration, 1),
            "results": list(self.results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "log_dir": self.config.get("log_dir", "/var/log/migration-private"),
        }

    def save_results(self, output_path: str):
        """保存迁移结果到 JSON"""
        summary = self._summary(0)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {output_path}")

    # ──────────────────────────────────────────────────────
    #  进度查询
    # ──────────────────────────────────────────────────────

    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        with self.results_lock:
            return {
                "stats": dict(self.stats),
                "completed": len(self.results),
                "remaining": self.stats["total"] - len(self.results),
            }


# ──────────────────────────────────────────────────────
#  CLI 入口
# ──────────────────────────────────────────────────────

def main():
    """命令行入口"""
    import argparse
    import sys

    # ── 启动时自动检测并安装 paramiko 依赖 ──
    _ensure_paramiko()

    parser = argparse.ArgumentParser(
        description="私网迁移批量编排器 — 支持目标ECS自动创建、VPC/安全组自动创建"
    )
    parser.add_argument("excel", help="Excel 文件路径 (2 Sheet 页: 主机信息 + 代理信息)")
    # AK/SK 从环境变量读取 (migration_Access_Key / migration_Secret_Access_Key)
    # 禁止通过命令行明文或临时凭证提供 AK/SK
    parser.add_argument("--security-token", help="临时凭证安全令牌 (HST 前缀 AK 必须提供)", default=None)
    parser.add_argument("--cred-cache", action="store_true",
                        help="使用本地加密缓存中的凭证 (首次配置后可用)")
    parser.add_argument("--region", default="cn-north-4", help="华为云 region")
    parser.add_argument("--project-id", help="华为云 project ID")
    parser.add_argument("--proxy-ip", help="代理主机公网 IP (覆盖 Excel Sheet2)")
    parser.add_argument("--proxy-port", type=int, default=22, help="代理主机 SSH 端口")
    parser.add_argument("--proxy-user", default="root", help="代理主机用户名")
    parser.add_argument("--proxy-pass", help="代理主机密码")
    parser.add_argument("--vpc-id", help="已有 VPC ID (不传则自动创建)")
    parser.add_argument("--subnet-id", help="已有子网 ID (不传则自动创建)")
    parser.add_argument("--sg-id", help="已有安全组 ID (不传则自动创建)")
    parser.add_argument("--max-workers", type=int, default=20, help="最大并发数 (默认20, 支持100台源端并发)")
    parser.add_argument("--max-workers-prepare", type=int, default=None, help="Phase A 准备阶段并发数 (默认同 max-workers)")
    parser.add_argument("--max-workers-migrate", type=int, default=None, help="Phase B 迁移阶段并发数 (默认同 max-workers)")
    parser.add_argument("--max-retries", type=int, default=2, help="最大重试次数")
    parser.add_argument("--retry-delay", type=int, default=10, help="重试间隔秒数")
    parser.add_argument("--task-timeout", type=int, default=10800, help="单任务超时秒数 (默认3小时)")
    parser.add_argument("--dry-run", action="store_true", help="干跑模式 (仅检查不执行)")
    parser.add_argument("--deep-verify", action="store_true",
                        help="迁移后执行深度数据完整性校验 (hostname/OS/disks/users/services/fstab)")
    parser.add_argument("--force-update", action="store_true",
                        help="强制更新 AK/SK 到所有依赖工具 (hcloud/obsutil/SMS)，跳过变更检测")
    parser.add_argument("--output", default="migration-results.json", help="结果输出路径")
    parser.add_argument("--log-dir", default="/var/log/migration-private", help="日志目录 (每任务独立日志)")
    parser.add_argument("--rsync-binary", default=None,
                        help="预编译 rsync 二进制包路径 (tar.gz), 跳过源码编译, 部署从2-5分钟降至5-10秒")
    parser.add_argument("--background", "-b", action="store_true",
                        help="后台运行 (nohup), 防止进程被终端关闭杀死; 日志输出到 --log-file")
    parser.add_argument("--log-file", default="migration.log",
                        help="后台运行时的日志输出文件 (默认 migration.log)")
    parser.add_argument("--pid-file", default="migration.pid",
                        help="后台运行时的 PID 文件 (默认 migration.pid)")
    args = parser.parse_args()

    # ── 后台运行: nohup 重新启动自身, 防止进程被杀 ──
    if args.background:
        import subprocess as _sp
        log_path = os.path.abspath(args.log_file)
        pid_path = os.path.abspath(args.pid_file)
        # 重建命令行, 去掉 --background/-b, 保留其余参数
        relaunch_args = [sys.executable, os.path.abspath(__file__)]
        for i, a in enumerate(sys.argv[1:]):
            if a in ("--background", "-b"):
                continue
            if a.startswith("--log-file="):
                continue
            if a.startswith("--pid-file="):
                continue
            relaunch_args.append(a)
        # 确保非 background 模式运行
        relaunch_args.append(f"--log-file={log_path}")
        relaunch_cmd = "nohup " + " ".join(relaunch_args) + f" > {log_path} 2>&1 &"
        logger.info(f"Launching background process: {relaunch_cmd}")
        proc = _sp.Popen(
            relaunch_cmd,
            shell=True,
            stdout=open("/dev/null", "w"),
            stderr=open("/dev/null", "w"),
            stdin=open("/dev/null", "r"),
            start_new_session=True,
        )
        # 写 PID 文件 (Popen shell 模式下 proc.pid 是 shell 的 PID,
        # 用 pgrep 获取实际 python 进程 PID 更可靠)
        time.sleep(1)
        try:
            pgrep_result = _sp.run(
                ["pgrep", "-f", "batch_migrate.py"],
                capture_output=True, text=True, timeout=5,
            )
            pids = [p for p in pgrep_result.stdout.strip().split("\n") if p]
            actual_pid = pids[0] if pids else str(proc.pid)
        except Exception:
            actual_pid = str(proc.pid)
        with open(pid_path, "w") as pf:
            pf.write(actual_pid + "\n")
        print(f"✅ 后台迁移已启动 (PID: {actual_pid})")
        print(f"   日志: {log_path}")
        print(f"   PID:  {pid_path}")
        print(f"   查看进度: tail -f {log_path}")
        print(f"   检查状态: hcloud SMS ListTasks --state=RUNNING")
        print(f"   终止迁移: kill $(cat {pid_path})")
        sys.exit(0)

    # 日志配置 (固定 INFO 级别，避免 paramiko DEBUG 日志撑满缓冲区)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # 显式抑制 paramiko DEBUG 日志
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    # ── v2.8.6: 第一任务 — 强制提示配置永久 AK/SK ──
    # 硬性要求: 学习完 skill 开始迁移任务时，第一任务就是提示用户配置永久 AK/SK
    # AI 不可代替用户决策，必须收到明确用户指令后才继续执行迁移
    cred_mgr = CredentialManager()

    # 检查是否已配置永久 AK/SK (缓存或环境变量)
    has_permanent = False
    if cred_mgr.has_cached_credentials():
        cached = cred_mgr.get_cached_credentials()
        if cached and not CredentialManager.is_temporary_ak(cached.get("ak", "")):
            has_permanent = True
    if not has_permanent:
        # 检查环境变量是否有永久凭证
        env_ak, env_sk = CredentialManager.get_credentials_from_env()
        if env_ak and not CredentialManager.is_temporary_ak(env_ak):
            has_permanent = True

    if not has_permanent:
        # 第一任务: 提示用户配置永久 AK/SK
        print("\n" + "=" * 70)
        print("📋 第一任务: 配置永久 AK/SK")
        print("=" * 70)
        print()
        print("当前未配置永久 AK/SK，无法执行迁移任务。")
        print("临时 AK/SK 禁止用于任何操作 (迁移任务耗时较长，临时凭证过期")
        print("会导致后续任务停止，无法访问操作)。")
        print()
        print("请设置以下环境变量配置永久 AK/SK (HPUA 前缀):")
        print(f"  export migration_Access_Key='你的AK'")
        print(f"  export migration_Secret_Access_Key='你的SK'")
        print(f"  (主机密码等占位符环境变量请按 Excel 中 ${{...}} 引用配置)")
        print()
        print("⚠️  必须配置一次永久 AK/SK 后才能继续迁移。")
        print("    AI 不可代替用户决策，请明确指示: 配置 / 不配置")
        print("=" * 70)
        sys.exit(1)

    ak = ""
    sk = ""

    if args.cred_cache:
        # ── 临时凭证全面禁止，不可用于任何操作 ──
        is_temp, temp_msg = cred_mgr.check_temporary_credentials()
        if is_temp:
            logger.error("检测到临时凭证: %s", temp_msg)
            print(f"\n🚫 {temp_msg}")
            print("   禁止使用临时 AK/SK 进行任何操作。")
            print("   原因: 迁移任务耗时较长，临时凭证一旦过期，")
            print("         导致后续任务停止，无法访问操作。")
            print("   请通过环境变量配置永久 AK/SK (HPUA前缀):")
            print(f"   export migration_Access_Key='你的AK'")
            print(f"   export migration_Secret_Access_Key='你的SK'")
            sys.exit(1)

        # 使用本地加密缓存 (已确认非临时凭证)
        creds = cred_mgr.get_cached_credentials()
        if creds:
            ak = creds.get("ak", "")
            sk = creds.get("sk", "")
            logger.info("AK/SK 来源: 本地加密缓存 (credential_manager)")
            # 验证缓存中的凭证是否仍然有效
            region_for_verify = args.region or "cn-north-1"
            ok, err = CredentialManager.verify_credentials(ak, sk, region_for_verify)
            if not ok:
                logger.warning("缓存凭证验证失败: %s", err)
                print(f"\n⚠️  缓存凭证已失效: {err}")
                print("请重新设置环境变量后运行 (不带 --cred-cache)。")
                sys.exit(1)
            logger.info("缓存凭证验证通过 (永久凭证)")
        else:
            logger.error("本地凭证缓存为空, 请先通过环境变量配置凭证")
            sys.exit(1)
    else:
        # 从环境变量读取 AK/SK 并验证
        env_ak, env_sk = CredentialManager.get_credentials_from_env()
        if not env_ak or not env_sk:
            logger.error(
                "环境变量未设置。请先设置:\n"
                "  export migration_Access_Key='你的AK'\n"
                "  export migration_Secret_Access_Key='你的SK'\n"
                "  (主机密码等占位符环境变量请按 Excel 中 ${...} 引用配置)"
            )
            sys.exit(1)

        region_for_verify = args.region or "cn-north-1"
        try:
            ak, sk = cred_mgr.verify_and_retry(
                region=region_for_verify,
                max_retries=3,
            )
        except ValueError as e:
            logger.error("凭证验证+重试失败: %s", e)
            sys.exit(1)

        # ── 拒绝临时凭证: 只接受永久 AK/SK (HPUA前缀) ──
        if CredentialManager.is_temporary_ak(ak):
            masked_ak = cred_mgr.mask_ak(ak)
            logger.error("拒绝临时凭证: AK=%s (HST前缀)", masked_ak)
            print(f"\n🚫 拒绝临时凭证 (AK: {masked_ak})")
            print("   临时凭证 (HST前缀) 不被接受，请使用永久 AK/SK。")
            print("   永久 AK 通常以 HPUA 开头，可在 IAM 控制台创建。")
            sys.exit(1)
        logger.info("凭证类型确认: 永久凭证 (非HST前缀)")

        # ── AK/SK 变更检测 ──
        if not args.force_update:
            if cred_mgr.has_cached_credentials():
                cached = cred_mgr.get_cached_credentials()
                if cached and cached.get("ak") != ak:
                    logger.warning("检测到 AK/SK 已变更!")
                    old_masked = cred_mgr.mask_ak(cached.get("ak", ""))
                    new_masked = cred_mgr.mask_ak(ak)
                    confirm = CredentialManager.confirm_change(old_masked, new_masked)
                    if confirm:
                        logger.info("用户确认变更，将重新配置使用 AK/SK 的进程、权限等")
                        CredentialManager.clear_temporary_env_vars()
                    else:
                        logger.info("用户取消凭证更新, 使用缓存中的旧凭证")
                        ak = cached.get("ak", "")
                        sk = cached.get("sk", "")
        else:
            logger.info("--force-update: 跳过变更检测，强制使用新 AK/SK")
            CredentialManager.clear_temporary_env_vars()

        # 缓存凭证 (AES-256-GCM 加密)
        cred_mgr.cache_credentials(ak, sk)
        logger.info("AK/SK 来源: 环境变量 → 已缓存 (credential_manager)")

        # ── 永久凭证已确认并缓存，现在作废临时凭证 ──
        cred_mgr.invalidate_temporary_after_permanent(ak)
        logger.info("临时凭证已作废，后续操作仅使用永久凭证")

    # 脱敏显示
    logger.info(f"AK (脱敏): {cred_mgr.mask_ak(ak)}")

    # ── v2.8.5: GOST obsutil 修复 + Agent AK/SK 自适应更新 ──
    # 无论 hcloud 当前配置如何，强制用最新 AK/SK 更新所有依赖工具
    region_for_config = args.region or "cn-north-1"
    cred_mgr.configure_hcloud(ak, sk, region_for_config, security_token=args.security_token)
    cred_mgr.configure_obsutil(ak, sk, region_for_config)
    cred_mgr.configure_sms_agent(ak, sk, region_for_config)
    logger.info("hcloud + obsutil + SMS Agent 凭证已联动更新")

    # ── v2.8.3: 凭证验证通过后，读取 Excel 获取代理信息 ──
    excel_reader = ExcelReader(args.excel)
    try:
        excel_reader.read()
    except Exception as e:
        logger.error(f"Failed to read Excel: {e}")
        sys.exit(1)

    # ── v2.9.1: 校验 Excel 中所有占位符对应的环境变量已配置 ──
    required_env_vars = excel_reader.get_required_env_vars()
    unresolved = excel_reader.get_unresolved_placeholders()
    if required_env_vars:
        logger.info(f"Excel 占位符环境变量: {sorted(required_env_vars)}")
        if unresolved:
            print("\n" + "=" * 70)
            print("📋 环境变量校验: Excel 中存在未解析的占位符")
            print("=" * 70)
            print()
            print("以下占位符在 Excel 中使用，但对应环境变量未设置:")
            for env_name, field_name in sorted(unresolved.items()):
                print(f"  ${{{env_name}}}  (字段: {field_name})")
            print()
            print("请在运行迁移前配置以下环境变量:")
            for env_name in sorted(unresolved.keys()):
                print(f"  export {env_name}='对应值'")
            print()
            print("⚠️  所有占位符环境变量必须配置后才能继续迁移。")
            print("=" * 70)
            sys.exit(1)
        else:
            logger.info(f"全部 {len(required_env_vars)} 个占位符环境变量校验通过 ✅")

    # 提前读取代理信息 (供 config 和 SMSAgentPush 使用)
    all_sheets = excel_reader.read_all_sheets(args.excel)
    proxy_list = all_sheets.get("proxy_hosts", [])
    proxy_info = proxy_list[0] if proxy_list else {}

    # 构建配置
    # 如果命令行未指定 project_id，从 Excel Sheet1 自动读取
    auto_project_id = args.project_id or ""
    if not auto_project_id:
        hosts_data = all_sheets.get("hosts", [])
        if hosts_data:
            auto_project_id = hosts_data[0].get("project_id", "")
            if auto_project_id:
                logger.info(f"Auto-detected project_id from Excel: {auto_project_id}")

    config = {
        "region": args.region,
        "project_id": auto_project_id,
        "max_retries": args.max_retries,
        "retry_delay": args.retry_delay,
        "task_timeout": args.task_timeout,
        "lock_dir": "/tmp/migration-locks",
        "log_dir": args.log_dir,
    }
    if args.vpc_id:
        config["vpc_id"] = args.vpc_id
    if args.subnet_id:
        config["subnet_id"] = args.subnet_id
    if args.sg_id:
        config["sg_id"] = args.sg_id
    if args.deep_verify:
        config["deep_verify"] = True
    # 代理 ECS 信息 (供深度校验使用)
    config["proxy"] = {
        "ip": args.proxy_ip or proxy_info.get("public_ip", ""),
        "port": args.proxy_port,
        "user": args.proxy_user,
        "password": args.proxy_pass or proxy_info.get("password", ""),
    }
    # 注入代理 ECS 私网 IP (供 run() 从代理 ECS 发现 VPC/子网)
    if proxy_info.get("private_ip"):
        config["proxy_private_ip"] = proxy_info["private_ip"]
    # 注入代理 ECS 公网 IP/用户名/密码 (供 pre-deploy rsync 编译使用)
    config["proxy_public_ip"] = args.proxy_ip or proxy_info.get("public_ip", "")
    config["proxy_username"] = args.proxy_user or proxy_info.get("username", "root")
    config["proxy_password"] = args.proxy_pass or proxy_info.get("password", "")

    # 初始化各组件
    from hcloud_wrapper import HcloudCLI as HCloudWrapper
    from sms_ops import SMSOps
    from ecs_ops import ECSOps
    from sms_agent_push import SMSAgentPush
    from safety_checker import SafetyChecker

    hcloud = HCloudWrapper(ak=ak, sk=sk, region=args.region, project_id=config["project_id"], security_token=args.security_token)

    sms_ops = SMSOps(hcloud=hcloud)
    ecs_ops = ECSOps(hcloud=hcloud)
    # proxy_info 已在上方提前读取
    from ssh_utils import SSHClient
    ssh_utils_inst = SSHClient(host="localhost")
    agent_pusher = SMSAgentPush(
        ssh_utils=ssh_utils_inst,
        proxy_ip=args.proxy_ip or proxy_info.get("public_ip", ""),
        gost_ssh_port=10022,  # default, overridden per-task in load_tasks
        squid_proxy=f"{args.proxy_ip or proxy_info.get('public_ip', '')}:3128",
        proxy_username=args.proxy_user or proxy_info.get("username", "root"),
        proxy_password=args.proxy_pass or proxy_info.get("password", ""),
        proxy_private_ip=proxy_info.get("private_ip", ""),
    )
    safety_checker = SafetyChecker(hcloud=hcloud)

    # 云网络操作 (用于自动创建 VPC/子网/安全组)
    cloud_network = CloudNetworkOps(hcloud=hcloud)

    # 初始化代理 ECS 操作 (用于部署 squid+GOST+rsync 和动态更新 GOST 转发)
    from proxy_ecs_ops import ProxyEcsOps
    proxy_ecs_ops = None
    proxy_public_ip = args.proxy_ip or proxy_info.get("public_ip", "")
    proxy_private_ip = proxy_info.get("private_ip", "")
    proxy_ssh_port = proxy_info.get("port", args.proxy_port)
    proxy_username = args.proxy_user or proxy_info.get("username", "root")
    proxy_password = args.proxy_pass or proxy_info.get("password", "")
    if proxy_public_ip:
        try:
            proxy_ssh_client = SSHClient(
                host=proxy_public_ip,
                port=proxy_ssh_port,
                username=proxy_username,
                password=proxy_password,
            )
            proxy_ssh_client.connect(timeout=30)
            proxy_ecs_ops = ProxyEcsOps(ssh_client=proxy_ssh_client)
            logger.info(f"ProxyEcsOps initialized: proxy={proxy_public_ip}, private={proxy_private_ip}")
        except Exception as e:
            logger.warning(f"Failed to init ProxyEcsOps: {e}; proxy deployment will be skipped")

    # 设置 SMS Agent 本地包路径 (供 load_tasks 注入 local_agent_path)
    agent_local_path = os.environ.get("SMS_AGENT_PATH", "")
    if not agent_local_path:
        for candidate in ["/root/migration-work/SMS-Agent.tar.gz", "/tmp/SMS-Agent.tar.gz"]:
            if os.path.exists(candidate):
                os.environ["SMS_AGENT_PATH"] = candidate
                logger.info(f"SMS_AGENT_PATH set to {candidate}")
                break

    # v2.6.0: 设置预编译 rsync 二进制包路径 (跳过源码编译, 部署从2-5分钟降至5-10秒)
    if args.rsync_binary:
        if os.path.exists(args.rsync_binary):
            os.environ["RSYNC_BINARY_PATH"] = args.rsync_binary
            logger.info(f"RSYNC_BINARY_PATH set to {args.rsync_binary} (from --rsync-binary)")
        else:
            logger.warning(f"--rsync-binary path not found: {args.rsync_binary}, will compile from source")
    elif not os.environ.get("RSYNC_BINARY_PATH"):
        for candidate in [
            "/root/migration-work/rsync-3.5.0-x86_64.tar.gz",
            "/tmp/rsync-3.5.0-x86_64.tar.gz",
        ]:
            if os.path.exists(candidate):
                os.environ["RSYNC_BINARY_PATH"] = candidate
                logger.info(f"RSYNC_BINARY_PATH auto-detected: {candidate}")
                break

    # 迁移执行器
    worker = MigrateWorker(
        sms_ops=sms_ops,
        ecs_ops=ecs_ops,
        agent_pusher=agent_pusher,
        config=config,
        cloud_network_ops=cloud_network,
        proxy_ecs_ops=proxy_ecs_ops,
    )

    # 批量编排器
    batch = BatchMigrate(
        migrate_worker=worker,
        excel_reader=excel_reader,
        safety_checker=safety_checker,
        config=config,
        cloud_network_ops=cloud_network,
        proxy_ecs_ops=proxy_ecs_ops,
    )

    # 信号处理: Ctrl+C / SIGTERM 时优雅关闭, 保存部分结果
    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.warning(f"Received {sig_name}, requesting graceful shutdown...")
        batch._shutdown_requested.set()

    original_sigint = signal.signal(signal.SIGINT, _signal_handler)
    original_sigterm = signal.signal(signal.SIGTERM, _signal_handler)

    # 执行
    try:
        summary = batch.run(
            excel_path=args.excel,
            max_workers=args.max_workers,
            dry_run=args.dry_run,
            max_workers_prepare=args.max_workers_prepare,
            max_workers_migrate=args.max_workers_migrate,
            ak=ak,
            sk=sk,
        )
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught, saving partial results...")
        summary = {
            "stats": batch.stats,
            "duration": 0,
            "interrupted": True,
        }
    finally:
        # 恢复原始信号处理器
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    # 保存结果
    batch.save_results(args.output)

    # 打印汇总
    print(f"\n{'='*60}")
    print(f"迁移汇总:")
    print(f"  总数: {summary['stats']['total']}")
    print(f"  成功: {summary['stats']['success']}")
    print(f"  失败: {summary['stats']['failed']}")
    print(f"  跳过: {summary['stats']['skipped']}")
    print(f"  耗时: {summary['duration']}s")
    print(f"  结果: {args.output}")
    print(f"{'='*60}")

    # 退出码
    sys.exit(0 if summary["stats"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
