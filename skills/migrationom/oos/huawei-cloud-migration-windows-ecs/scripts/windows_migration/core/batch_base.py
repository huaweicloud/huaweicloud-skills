"""
批量编排器基类 — 公网/私网共用逻辑。

公共能力:
  - 主机列表加载 (CSV)
  - 状态持久化 (JSON, 线程安全)
  - ThreadPool 并发执行
  - 阶段级重试 (按 retry_policy 配置)
  - 回调通知 (host_start/complete, phase_start/complete, batch_complete)
  - 幂等: 已成功主机/阶段自动跳过

子类需实现:
  - _build_phases(): 返回阶段列表 [(name, phase_or_callable)]
  - _build_executor(host, state): 返回该主机的 WinRMExecutor
  - _pre_run(): 运行前准备（如 gost 端口转发）
  - _post_run(): 运行后清理
"""
from __future__ import annotations

import csv
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from core.config import MigrateConfig
from core.executor.winrm_executor import WinRMExecutor
from phases.base_phase import BasePhase, MigrationContext, PhaseResult, PhaseStatus
from core.callbacks import Callbacks

logger = logging.getLogger(__name__)


@dataclass
class HostState:
    """单台主机的迁移状态。"""
    host: str = ""
    username: str = ""
    password: str = ""
    winrm_port: int = 5985
    hostname: str = ""
    public_ip: str = ""
    private_ip: str = ""
    region_id: str = ""
    region_name: str = ""
    project_id: str = ""
    project_name: str = ""
    os_type: str = ""
    use_public_ip: str = ""
    gost_port: int = 0
    status: str = "pending"
    current_phase: str = ""
    phase_results: dict = field(default_factory=dict)
    markers: int = 0
    error: str = ""
    retry_count: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "host": self.host, "username": self.username,
            "hostname": self.hostname, "public_ip": self.public_ip, "private_ip": self.private_ip,
            "region_id": self.region_id, "project_id": self.project_id,
            "os_type": self.os_type, "use_public_ip": self.use_public_ip,
            "status": self.status, "current_phase": self.current_phase,
            "phase_results": self.phase_results, "markers": self.markers,
            "error": self.error, "retry_count": self.retry_count,
            "gost_port": self.gost_port,
            "duration": round(self.end_time - self.start_time, 1) if self.end_time else 0,
        }


@dataclass
class BatchResult:
    """批量迁移结构化结果。"""
    total: int = 0
    success: int = 0
    failed: int = 0
    pending: int = 0
    hosts: list = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.failed == 0 and self.pending == 0

    def to_dict(self) -> dict:
        return {
            "total": self.total, "success": self.success,
            "failed": self.failed, "pending": self.pending,
            "is_success": self.is_success, "hosts": self.hosts,
        }

    def summary(self, title: str = "批量迁移汇总") -> str:
        lines = [
            f"\n{'=' * 60}",
            f"{title}",
            f"{'=' * 60}",
            f"总计: {self.total} | 成功: {self.success} | 失败: {self.failed} | 待处理: {self.pending}",
            "-" * 60,
        ]
        for h in self.hosts:
            status = h.get("status", "?")
            icon = {"success": "✅", "failed": "❌", "pending": "⏳", "running": "🔄"}.get(status, "?")
            dur = f" ({h['duration']:.0f}s)" if h.get("duration") else ""
            markers = h.get("markers", 0)
            err = f" — {h.get('error', '')[:60]}" if h.get("error") else ""
            gost = f" [gost:{h.get('gost_port',0)}]" if h.get("gost_port") else ""
            lines.append(f"  {icon} {h['host']}{gost} [{h.get('current_phase', '')}] markers={markers}/5{dur}{err}")
        lines.append("=" * 60)
        return "\n".join(lines)


class BaseBatchOrchestrator:
    """批量编排器基类 — 公网/私网共用。"""

    def __init__(
        self,
        config: MigrateConfig,
        hosts_csv: str,
        max_workers: int = 10,
        state_file: str = "batch_state.json",
        callbacks: Callbacks | None = None,
        hosts_info: list | None = None,
    ):
        self._config = config
        self._hosts_csv = hosts_csv
        self._hosts_info = hosts_info
        self._max_workers = max_workers
        self._state_file = Path(state_file)
        self._states: dict[str, HostState] = {}
        self._lock = threading.Lock()
        self._callbacks = callbacks or Callbacks()

    # ---- 子类实现 ----

    def _build_phases(self) -> list[tuple[str, BasePhase]]:
        """返回阶段列表 [(phase_name, phase_instance)]。"""
        raise NotImplementedError

    def _build_executor(self, host: str, state: HostState) -> WinRMExecutor:
        """为单台主机构建 WinRM 执行器。"""
        raise NotImplementedError

    def _pre_run(self) -> None:
        """运行前准备（如 gost 端口转发），默认无操作。"""
        pass

    def _post_run(self) -> None:
        """运行后清理，默认无操作。"""
        pass

    def _result_title(self) -> str:
        return "批量迁移汇总"

    # ---- 公共逻辑 ----

    def run(self) -> BatchResult:
        self._load_hosts()
        self._load_state()
        self._pre_run()

        pending = {h: s for h, s in self._states.items() if s.status != "success"}
        if not pending:
            logger.info("所有主机已成功迁移，无需重跑")
            return self._build_result()

        logger.info("=" * 60)
        logger.info("批量迁移开始: %d 台主机, 并发 %d", len(pending), self._max_workers)
        logger.info("=" * 60)

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self._migrate_host, host, state): host
                for host, state in pending.items()
            }
            for future in as_completed(futures):
                host = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("主机 %s 异常: %s", host, e)
                    with self._lock:
                        self._states[host].status = "failed"
                        self._states[host].error = str(e)
                    self._save_state()

        self._post_run()

        result = self._build_result()
        self._callbacks.fire_batch_complete(result.to_dict())
        return result

    def _migrate_host(self, host: str, state: HostState) -> None:
        """单台主机迁移全流程。"""
        state.status = "running"
        state.start_time = time.time()
        state.retry_count += 1
        self._save_state()

        logger.info("[%s] 开始迁移 (retry=%d)", host, state.retry_count)
        self._callbacks.fire_host_start(state)

        # 构建 WinRM 执行器
        try:
            exe = self._build_executor(host, state)
        except Exception as e:
            state.status = "failed"
            state.error = f"WinRM 连接失败: {e}"
            state.end_time = time.time()
            self._save_state()
            self._callbacks.fire_host_complete(state)
            return

        # 构建上下文
        ctx = MigrationContext(
            config=self._config,
            winrm_executor=exe,
            source_download_dir=self._config.source_download_dir,
        )

        # 执行阶段链
        phases = self._build_phases()
        for phase_name, phase in phases:
            if state.phase_results.get(phase_name) == "ok":
                logger.info("[%s] %s 已完成，跳过", host, phase_name)
                self._fire_phase(host, phase_name, PhaseStatus.SKIPPED, 0, "", 0)
                continue

            state.current_phase = phase_name
            self._save_state()

            ok = self._run_phase_with_retry(phase_name, phase, ctx, state, host)
            self._save_state()

            if not ok:
                state.status = "failed"
                state.end_time = time.time()
                self._save_state()
                logger.error("[%s] 迁移失败于 %s", host, phase_name)
                self._callbacks.fire_host_complete(state)
                return

        state.status = "success"
        state.current_phase = "done"
        state.end_time = time.time()
        self._save_state()
        logger.info("[%s] ✓ 迁移成功 (markers=%d/5)", host, state.markers)
        self._callbacks.fire_host_complete(state)

    def _run_phase_with_retry(
        self, phase_name: str, phase: BasePhase,
        ctx: MigrationContext, state: HostState, host: str,
    ) -> bool:
        """执行单个阶段，失败时按 retry_policy 重试。"""
        policy = self._config.retry_policy.get(phase_name)
        max_attempts = policy.max_retries + 1

        for attempt in range(max_attempts):
            attempt_start = time.time()
            error_msg = ""

            try:
                result = phase.run(ctx)
                if result.status == PhaseStatus.SUCCESS:
                    state.phase_results[phase_name] = "ok"
                    duration = time.time() - attempt_start
                    self._fire_phase(host, phase_name, PhaseStatus.SUCCESS, duration, "", attempt)
                    return True
                else:
                    error_msg = result.error or f"{phase_name} failed"
            except Exception as e:
                error_msg = str(e)
                logger.error("[%s] %s 异常 (attempt=%d): %s", host, phase_name, attempt + 1, e)

            # 阶段失败
            duration = time.time() - attempt_start
            state.phase_results[phase_name] = "fail"
            state.error = f"{phase_name}: {error_msg}"

            self._fire_phase(host, phase_name, PhaseStatus.FAILED, duration, error_msg, attempt)

            remaining = max_attempts - attempt - 1
            if remaining > 0 and policy.is_retryable(error_msg):
                wait = policy.backoff_time(attempt)
                logger.warning(
                    "[%s] %s 失败 (attempt=%d/%d), 瞬时错误, %.1fs 后重试: %s",
                    host, phase_name, attempt + 1, max_attempts, wait, error_msg[:80],
                )
                time.sleep(wait)
            else:
                if remaining > 0 and not policy.is_retryable(error_msg):
                    logger.error(
                        "[%s] %s 失败: 永久错误, 不重试: %s",
                        host, phase_name, error_msg[:80],
                    )
                else:
                    logger.error(
                        "[%s] %s 失败: 重试已耗尽 (attempt=%d/%d)",
                        host, phase_name, attempt + 1, max_attempts,
                    )
                return False

        return False

    def _fire_phase(
        self, host: str, phase_name: str, status: PhaseStatus,
        duration: float, error: str, attempt: int = 0,
    ) -> None:
        """触发阶段级回调。"""
        result = PhaseResult(
            name=f"{host}:{phase_name}",
            status=status,
            duration=duration,
            detail=f"host={host}, attempt={attempt}",
            error=error,
        )
        self._callbacks.fire_phase_complete(result)

    # ---- 状态管理 ----

    def _load_hosts(self) -> None:
        # 优先使用结构化主机信息（环境变量 Host_Information 解析结果）
        if self._hosts_info:
            for item in self._hosts_info:
                host = str(item.get("host") or "").strip()
                if not host:
                    continue
                self._states[host] = HostState(
                    host=host,
                    hostname=str(item.get("hostname") or "").strip(),
                    public_ip=str(item.get("public_ip") or "").strip(),
                    private_ip=str(item.get("private_ip") or "").strip(),
                    username=item.get("username", "Administrator"),
                    password=item.get("password", ""),
                    winrm_port=int(item.get("winrm_port", 5985) or 5985),
                    region_id=str(item.get("region_id") or "").strip(),
                    region_name=str(item.get("region_name") or "").strip(),
                    project_id=str(item.get("project_id") or "").strip(),
                    project_name=str(item.get("project_name") or "").strip(),
                    os_type=str(item.get("os_type") or "").strip(),
                    use_public_ip=str(item.get("use_public_ip") or "").strip(),
                )
            logger.info("加载 %d 台主机（来源: 环境变量 Host_Information）", len(self._states))
            return

        # 兼容回退：CSV 主机列表
        path = Path(self._hosts_csv)
        if not path.exists():
            raise FileNotFoundError(f"主机列表不存在: {path}（也可通过环境变量 Host_Information 提供 JSON 主机信息）")
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                host = row.get("host", "").strip()
                if not host or host.startswith("#"):
                    continue
                self._states[host] = HostState(
                    host=host,
                    username=row.get("username", "Administrator").strip(),
                    password=row.get("password", "").strip(),
                    winrm_port=int(row.get("winrm_port", 5985)),
                )
        logger.info("加载 %d 台主机（来源: %s）", len(self._states), self._hosts_csv)

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for host, data in saved.items():
                if host in self._states:
                    s = self._states[host]
                    s.status = data.get("status", "pending")
                    s.current_phase = data.get("current_phase", "")
                    s.phase_results = data.get("phase_results", {})
                    s.markers = data.get("markers", 0)
                    s.error = data.get("error", "")
                    s.retry_count = data.get("retry_count", 0)
                    s.gost_port = data.get("gost_port", 0)
            logger.info("加载状态: %d 台", len(saved))
        except (json.JSONDecodeError, IOError):
            pass

    def _save_state(self) -> None:
        with self._lock:
            data = {h: s.to_dict() for h, s in self._states.items()}
            tmp = self._state_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(self._state_file)

    def _build_result(self) -> BatchResult:
        with self._lock:
            total = len(self._states)
            success = sum(1 for s in self._states.values() if s.status == "success")
            failed = sum(1 for s in self._states.values() if s.status == "failed")
            pending = sum(1 for s in self._states.values() if s.status in ("pending", "running"))
            hosts = [s.to_dict() for s in self._states.values()]
        return BatchResult(total, success, failed, pending, hosts)
