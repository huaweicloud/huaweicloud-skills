#!/usr/bin/env python3
"""跨机器确认闸门（1.6.0）：所有迁移器的 --install 都必须先经过用户确认。

用途：供 migrate.py / migrate_workbuddy.py / migrate_suite.py 在 --install 前调用；
返回值（退出码）：0=确认通过放行，4=拦截（须先向用户提问并回传票据）。

为什么存在：跨机器迁移要求先把专家包传到本机，Agent 曾 7 次绕过「先问用户」的
提示词约定（自我确认、伪造答复）。提示词管不住的，用脚本管——这是机械强制，
不依赖模型自觉。

机制（1.6.0 起下沉为公共模块，migrate.py / migrate_workbuddy.py / migrate_suite.py
三个入口共用，直接调用子迁移器也无法绕过）：

  1. `--install` 未带 `--confirm-local` → 发放一次性票据（nonce）并退出码 4。
     调用方（Agent）必须停止执行、把跨机器问题输出给用户、结束本轮。
  2. `--confirm-local <nonce>` 回传票据：票据必须匹配最近一次发放的 nonce，
     且距发放时刻 ≥ 冷却秒数（默认 90，可用 `--gate-cooldown` 或环境变量
     `ESM_GATE_COOLDOWN` 调整）——冷却保证用户有真实时间答复，防自我确认。
  3. 校验通过后在票据文件写入 confirmed 标记（10 分钟窗口）：入口脚本
     migrate.py 确认后转调子迁移器时，子迁移器凭该标记放行，不重复提问；
     窗口过期后再次拦截，不会留下永久通行证。
  4. 票据携带会话标识 sid（pid + 毫秒时间戳），nonce 由 sid + 日期派生——
     多会话并发时各自覆盖票据文件也不会误用对方的确认结果。

退出码：4 = 被闸门拦截（需向用户提问或等冷却）；None = 放行。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_COOLDOWN = 90
# 入口脚本确认后，子迁移器的放行窗口（秒）。过期重新拦截，不留永久通行证。
CONFIRMED_WINDOW = 600
GATE_TAG = "[GATE-CROSS-MACHINE]"


def gate_path(home: Path | str) -> Path:
    return Path(home) / ".migration-gate.json"


def cooldown_from_env(default: int = DEFAULT_COOLDOWN) -> int:
    raw = os.environ.get("ESM_GATE_COOLDOWN", "")
    try:
        return max(0, int(raw)) if raw.strip() else default
    except ValueError:
        return default


def _read_gate(home: Path | str) -> dict:
    try:
        data = json.loads(gate_path(home).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def issue(home: Path | str, source: str = "") -> tuple[str, str]:
    """发放一次性票据。返回 (nonce, sid)。"""
    sid = f"{os.getpid()}-{int(time.time() * 1000)}"
    nonce = hashlib.sha256(
        f"{sid}:{source}:{time.time_ns()}:{time.strftime('%Y%m%d')}".encode()
    ).hexdigest()[:12]
    p = gate_path(home)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"sid": sid, "nonce": nonce, "ts": time.time(), "source": source},
        ensure_ascii=False), encoding="utf-8")
    return nonce, sid


def message(nonce: str, entry: str = "migrate.py") -> str:
    return (
        f"{GATE_TAG} 迁移被闸门拦截（确认票据 nonce={nonce}，入口 {entry}）。"
        "你现在必须做的是【停止执行、结束本轮回复】：\n"
        "1) 本轮回复只输出这一个问题，不要调用任何工具、不要继续任何迁移步骤：\n"
        "   「这次迁移是跨机器的吗？——即专家源包不在本机，需要先从别的机器把专家文件包传到这台电脑。」\n"
        "2) 【禁止】用你自己对源包位置的判断代替用户确认；哪怕你已定位到源包就在本机，也必须等用户亲口答复。\n"
        "3) 用户答复「不跨机器/就在本机」→ 重新执行本命令并加上 --confirm-local <nonce>（用上面括号里的票据值）。"
        "若返回「确认时间过短」，说明用户还没来得及答复，等待冷却时间后重试。\n"
        "4) 用户答复「跨机器」→ 指导用户把整个专家套件文件夹（含 agents/、skills/、清单文件）传输到本机"
        "（推荐 ~/.office-claw/.staging/），等用户给出本地路径后：--source <本地路径> --install --confirm-local <nonce>。\n"
        "未经用户在本对话中明确答复，不得以任何方式绕过本闸门。"
    )


def enforce(home: Path | str, install: bool, confirm_local: str | None = None,
            cooldown: int | None = None, source: str = "", entry: str = "",
            json_mode: bool = False) -> int | None:
    """闸门主入口。返回 None 表示放行，返回 4 表示拦截（调用方应立即 return 4）。

    - `install=False`：非安装动作（dry-run / --list），直接放行。
    - `confirm_local=None` 且票据文件带有新鲜 confirmed 标记：入口脚本已替本次
      调用完成确认（migrate.py → 子迁移器），放行；标记过期则重新拦截。
    - 其余情况按「发票据 → 校验票据 + 冷却」执行。
    """
    if not install:
        return None
    if cooldown is None:
        cooldown = cooldown_from_env()
    g = _read_gate(home)

    # 入口脚本已确认（子迁移器透传放行）；窗口过期重新拦截
    if confirm_local is None:
        confirmed_at = float(g.get("confirmedAt") or 0)
        if g.get("confirmed") and (time.time() - confirmed_at) <= CONFIRMED_WINDOW:
            return None
        nonce, _ = issue(home, source)
        msg = message(nonce, entry or "migrate.py")
        if json_mode:
            print(json.dumps({"gate": "cross-machine-confirm-required",
                              "nonce": nonce, "message": msg}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        return 4

    # 校验票据：必须是最近一次发放的那枚
    if g.get("nonce") != confirm_local:
        print(f"{GATE_TAG} 确认票据无效：请先不带 --confirm-local 执行一次以获取票据，"
              "并向用户提问（见闸门输出）。", file=sys.stderr)
        return 4
    age = time.time() - float(g.get("ts") or 0)
    if age < cooldown:
        print(f"{GATE_TAG} 确认时间过短（距拦截仅 {int(age)} 秒，需 ≥{cooldown} 秒）："
              "用户尚未真正答复。请先把跨机器问题输出给用户并结束本轮，等待答复后重试。",
              file=sys.stderr)
        return 4

    # 确认成立：写标记供子迁移器透传（窗口内），票据即告消费
    gate_path(home).write_text(json.dumps(
        {**g, "confirmed": True, "confirmedAt": time.time(),
         "confirmedBy": os.getpid(), "confirmedSource": source},
        ensure_ascii=False), encoding="utf-8")
    return None
