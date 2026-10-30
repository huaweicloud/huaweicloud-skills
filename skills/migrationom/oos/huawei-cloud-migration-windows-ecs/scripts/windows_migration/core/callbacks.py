"""
回调机制 — 执行过程中异步通知上层。

回调类型:
    PhaseCallback   — 单台模式，每个阶段完成时触发
    HostCallback    — 批量模式，每台主机完成时触发
    EventCallback   — 通用事件回调（场景开始/结束、阶段开始等）

线程安全:
    - 单台模式: 回调在主线程同步调用
    - 批量模式: 回调在线程池工作线程中调用（天然异步）
    - 多个回调按注册顺序依次调用
    - 单个回调抛异常不影响后续回调和主流程（仅记录日志）

使用示例:
    from core.callbacks import Callbacks

    cbs = Callbacks()
    cbs.on_phase_complete = lambda r: print(f"阶段 {r.name} → {r.status.value}")
    cbs.on_host_complete = lambda s: print(f"主机 {s.host} → {s.status}")

    # 单台
    scenario = PublicScenario(config)
    scenario.callbacks = cbs
    result = scenario.run()

    # 批量
    orchestrator = BatchOrchestrator(config, ..., callbacks=cbs)
    result = orchestrator.run()
"""
from __future__ import annotations

import logging
from typing import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# 回调签名
PhaseCallback = Callable[[object], None]      # PhaseResult → None
HostCallback = Callable[[object], None]       # HostState → None
EventCallback = Callable[[str, dict], None]   # event_name, payload → None
ProgressCallback = Callable[[dict], None]        # progress info dict → None


@dataclass
class Callbacks:
    """回调注册中心 — 收集并安全调用上层回调。"""

    # 单台模式回调
    on_phase_start: list[PhaseCallback] = field(default_factory=list)
    on_phase_complete: list[PhaseCallback] = field(default_factory=list)
    on_phase_progress: list[ProgressCallback] = field(default_factory=list)
    on_scenario_start: list[EventCallback] = field(default_factory=list)
    on_scenario_complete: list[EventCallback] = field(default_factory=list)

    # 批量模式回调
    on_host_start: list[HostCallback] = field(default_factory=list)
    on_host_complete: list[HostCallback] = field(default_factory=list)
    on_batch_complete: list[EventCallback] = field(default_factory=list)

    # ---- 注册方法（链式） ----

    def phase_start(self, cb: PhaseCallback) -> "Callbacks":
        self.on_phase_start.append(cb)
        return self

    def phase_complete(self, cb: PhaseCallback) -> "Callbacks":
        self.on_phase_complete.append(cb)
        return self

    def phase_progress(self, cb: ProgressCallback) -> "Callbacks":
        self.on_phase_progress.append(cb)
        return self

    def scenario_start(self, cb: EventCallback) -> "Callbacks":
        self.on_scenario_start.append(cb)
        return self

    def scenario_complete(self, cb: EventCallback) -> "Callbacks":
        self.on_scenario_complete.append(cb)
        return self

    def host_start(self, cb: HostCallback) -> "Callbacks":
        self.on_host_start.append(cb)
        return self

    def host_complete(self, cb: HostCallback) -> "Callbacks":
        self.on_host_complete.append(cb)
        return self

    def batch_complete(self, cb: EventCallback) -> "Callbacks":
        self.on_batch_complete.append(cb)
        return self

    # ---- 触发方法（安全调用，异常不外泄） ----

    def fire_phase_start(self, phase_result) -> None:
        self._fire(self.on_phase_start, phase_result, "on_phase_start")

    def fire_phase_complete(self, phase_result) -> None:
        self._fire(self.on_phase_complete, phase_result, "on_phase_complete")

    def fire_phase_progress(self, payload: dict) -> None:
        self._fire(self.on_phase_progress, payload, "on_phase_progress")

    def fire_scenario_start(self, payload: dict) -> None:
        self._fire_event(self.on_scenario_start, payload, "on_scenario_start")

    def fire_scenario_complete(self, payload: dict) -> None:
        self._fire_event(self.on_scenario_complete, payload, "on_scenario_complete")

    def fire_host_start(self, host_state) -> None:
        self._fire(self.on_host_start, host_state, "on_host_start")

    def fire_host_complete(self, host_state) -> None:
        self._fire(self.on_host_complete, host_state, "on_host_complete")

    def fire_batch_complete(self, payload: dict) -> None:
        self._fire_event(self.on_batch_complete, payload, "on_batch_complete")

    # ---- 内部 ----

    def _fire(self, callbacks: list, arg, label: str) -> None:
        for cb in callbacks:
            try:
                cb(arg)
            except Exception as e:
                logger.warning("回调 %s 异常: %s", label, e)

    def _fire_event(self, callbacks: list, payload: dict, label: str) -> None:
        for cb in callbacks:
            try:
                cb(label, payload)
            except Exception as e:
                logger.warning("回调 %s 异常: %s", label, e)
