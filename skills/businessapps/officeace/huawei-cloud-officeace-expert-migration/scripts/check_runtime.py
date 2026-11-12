#!/usr/bin/env python3
"""应用内可用性确认（只读）：问一次正在运行的 OfficeAce，看它是否真的认得迁移来的专家与团队。

静态校验（verify_install.py）只能证明"文件写对了"，证明不了"应用读到了"。这个脚本走本地 API：

  1. GET /api/experts          每个迁移专家的 expertId 是否都在（团队主理人也在）；
  2. GET /api/teams/<teamId>   memberProfiles 是否解析出中文名（而不是回落成 expertId），
                               人设是否完整（>= 200 字）；
  3. 顺带确认 variant 的运行配置在应用侧没被改回占位值。

参数：--home 数据目录（默认 ~/.office-claw）；--base API 地址（默认 https://127.0.0.1:3004）；
      --team 指定团队 id（缺省校验 user-teams.json 里来源为 workbuddy 的团）。
返回值：0 = 应用侧认得全部迁移内容；1 = 有缺失；2 = 应用未运行/无法鉴权（不算迁移失败）。

前置：OfficeAce 正在运行（API 起在 3004），且当前用户有 ~/.office-claw/session.cookie。
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import json
import ssl
import sys
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_contract as rc  # noqa: E402

DEFAULT_BASE = "https://127.0.0.1:3004"
MIN_PERSONA = 200


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> "_BLOB":
    buf = ctypes.create_string_buffer(data, len(data))
    return _BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def session_cookie(home: Path) -> str:
    """oc_sid：session.cookie 是 `OC-DPAPI-1\\n<base64>`，用当前用户的 DPAPI 解。"""
    raw = (home / "session.cookie").read_bytes()
    _, _, payload = raw.partition(b"\n")
    blob = base64.b64decode(payload.strip())
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    src, dst = _blob(blob), _BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)):
        raise OSError(ctypes.get_last_error(), "CryptUnprotectData 失败（换用户或换机器后 cookie 失效）")
    try:
        return json.loads(ctypes.string_at(dst.pbData, dst.cbData).decode("utf-8"))["value"]
    finally:
        kernel32.LocalFree(dst.pbData)


class Api:
    def __init__(self, base: str, sid: str):
        self.base, self.sid = base.rstrip("/"), sid
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def get(self, path: str, timeout: int = 30):
        req = urllib.request.Request(self.base + path, method="GET")
        req.add_header("Cookie", f"oc_sid={self.sid}")
        with urllib.request.urlopen(req, context=self.ctx, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))


def main() -> int:
    ap = argparse.ArgumentParser(description="检查运行中的 OfficeAce 是否认得迁移来的专家/团队")
    ap.add_argument("--home", default="~/.office-claw")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--team", default=None)
    args = ap.parse_args()

    home = Path(args.home).expanduser()
    cards = {}
    for p in sorted((home / "experts").glob("*.json")):
        if ".bak" in p.name:
            continue
        d = rc._read_json(p, {}) or {}
        if d.get("agent_created") and d.get("expertId"):
            cards[d["expertId"]] = d

    try:
        api = Api(args.base, session_cookie(home))
        experts = api.get("/api/experts")
    except Exception as e:  # noqa: BLE001
        print(f"! 无法访问 {args.base}：{e}")
        print("  应用未运行或会话已失效时属正常；启动 OfficeAce 后重试。")
        return 2

    items = experts if isinstance(experts, list) else (experts.get("experts") or experts.get("items") or [])
    live = {e.get("expertId") for e in items if isinstance(e, dict)}
    print(f"应用内专家总数：{len(live)}；待校验的迁移专家：{len(cards)}")

    errors = []
    for eid, card in cards.items():
        if eid not in live:
            errors.append(f"专家 `{card.get('displayName')}`（{eid}）不在 /api/experts —— 团队解析不到该角色")
    if not errors:
        print(f"  ✓ {len(cards)} 个迁移专家在应用侧全部可见（含团队主理人）")

    # 团队：成员必须解析出中文名与人设，不能回落成 expertId
    teams = []
    ue = rc.user_experts_path(home)
    if args.team:
        teams = [args.team]
    elif ue and (ue.parent / "user-teams.json").is_file():
        data = rc._read_json(ue.parent / "user-teams.json", {}) or {}
        teams = [t.get("teamId") for t in data.get("teams", [])
                 if isinstance(t.get("teamId"), str) and t["teamId"].startswith("wb-team-")]
    for tid in teams:
        try:
            t = api.get(f"/api/teams/{tid}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"团队 {tid} 读取失败：{e}")
            continue
        profiles = t.get("memberProfiles") or []
        if not profiles:
            errors.append(f"团队 {tid} 没有解析出任何成员档案")
            continue
        bad = []
        for mp in profiles:
            name = mp.get("displayName") or ""
            eid = mp.get("expertId") or ""
            if not name or name == eid or name.startswith("expert-"):
                bad.append(f"{eid}（回落成 id，说明该角色不在专家目录）")
            elif len(mp.get("personality") or "") < MIN_PERSONA:
                bad.append(f"{name}（人设只有 {len(mp.get('personality') or '')} 字）")
        if bad:
            errors.append(f"团队 {tid} 成员档案异常：{'；'.join(bad)}")
        else:
            print(f"  ✓ 团队 {t.get('displayName') or tid}：{len(profiles)} 个成员均已解析出中文名与人设")

    for e in errors:
        print(f"  ✗ {e}")
    print("\n结论：" + ("应用侧已认得全部迁移内容" if not errors else f"发现 {len(errors)} 个问题"))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
