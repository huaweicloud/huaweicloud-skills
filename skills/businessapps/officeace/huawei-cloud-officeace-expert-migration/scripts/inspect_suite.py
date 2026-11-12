#!/usr/bin/env python3
"""识别一个专家套件包属于哪个平台，并打印结构清单（只读，不改任何文件）。

用途：识别专家套件包所属平台（qwenwork/dumate/workbuddy/officeace）并输出结构清单。
参数：位置参数 <套件目录>；--json 以 JSON 格式输出。
返回值：退出码 0=识别成功，1=无法识别或目录不存在。

用法：
    python inspect_suite.py <套件目录>
    python inspect_suite.py <套件目录> --json

识别依据（按优先级）：
    .qwenwork-plugin/plugin.json  → qwenwork（千问办公，新格式）
    .qoder-plugin/plugin.json     → qwenwork（千问办公，旧格式，仍被支持）
    .claude-plugin/plugin.json    → dumate（百度搭子）
    .codebuddy-plugin/plugin.json → workbuddy（WorkBuddy 专家包/专家团，建议用 migrate_workbuddy.py）
    ~/.office-claw 结构            → officeace（已是目标格式）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MANIFESTS = {
    ".qwenwork-plugin/plugin.json": "qwenwork",
    ".qoder-plugin/plugin.json": "qwenwork",
    ".claude-plugin/plugin.json": "dumate",
    ".codebuddy-plugin/plugin.json": "workbuddy",
}


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"警告：{p} 解析失败 - {e}", file=sys.stderr)
        return None


def detect(root: Path) -> tuple[str, Path | None]:
    for rel, plat in MANIFESTS.items():
        p = root / rel
        if p.exists():
            return plat, p
    # OfficeAce：专家 json + skills
    if (root / "experts").is_dir() and (root / "skills").is_dir():
        return "officeace", None
    return "unknown", None


def parse_frontmatter(md: Path) -> dict:
    txt = md.read_text(encoding="utf-8", errors="replace")
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in txt[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip('"').strip("'")
        out[k.strip()] = v
    return out


def enumerate_skills(root: Path, manifest: dict) -> list[Path]:
    declared = manifest.get("skills")
    dirs: list[Path] = []
    if isinstance(declared, list) and declared:
        for s in declared:
            p = (root / s).resolve() if not str(s).startswith("skills") else (root / s)
            p = root / s if not Path(s).is_absolute() else Path(s)
            if p.exists():
                dirs.append(p)
    if not dirs:
        base = root / "skills"
        if base.is_dir():
            dirs = [d for d in sorted(base.iterdir()) if d.is_dir() and (d / "SKILL.md").exists()]
    # 去重保序
    seen, out = set(), []
    for d in dirs:
        r = d.resolve()
        if r in seen:
            continue
        seen.add(r)
        out.append(d)
    return out


def _zh(node, fallback: str = "") -> str:
    if isinstance(node, dict):
        return node.get("zh") or node.get("en") or fallback
    return node or fallback


def inspect(root: Path) -> dict:
    plat, mf_path = detect(root)
    info: dict = {"root": str(root), "platform": plat, "manifest": str(mf_path) if mf_path else None}
    manifest = read_json(mf_path) if mf_path else {}
    info["manifest_data"] = manifest or {}
    skills = enumerate_skills(root, manifest or {})
    info["skills"] = []
    for d in skills:
        fm = parse_frontmatter(d / "SKILL.md")
        assets = [x.name for x in d.iterdir() if x.is_dir()] if d.is_dir() else []
        info["skills"].append(
            {
                "dir": str(d),
                "slug": d.name,
                "fm_name": fm.get("name", ""),
                "description": fm.get("description_zh") or fm.get("description", ""),
                "subdirs": assets,
                "files": sum(1 for _ in d.rglob("*") if _.is_file()),
            }
        )
    info["counts"] = {
        "skills": len(info["skills"]),
        "with_scripts": sum(1 for s in info["skills"] if "scripts" in s["subdirs"]),
        "with_references": sum(1 for s in info["skills"] if "references" in s["subdirs"]),
        "with_templates": sum(1 for s in info["skills"] if "templates" in s["subdirs"]),
    }
    return info


def to_text(info: dict) -> str:
    m = info["manifest_data"]
    lines = [
        f"套件目录 : {info['root']}",
        f"识别平台 : {info['platform']}",
        f"清单文件 : {info['manifest'] or '（无，已是 OfficeAce 结构或非套件）'}",
    ]
    if m:
        lines += [
            f"名称     : {m.get('name', '')}",
            f"显示名   : {m.get('displayNameCn') or _zh(m.get('displayName'), '')}",
            f"版本     : {m.get('version', '')}",
            # P1（2026-11 评审）：description 允许是多语言 dict，直接 [:120] 切片会 TypeError；
            # 复用 _zh() 兜底取字符串再截断
            f"描述     : {str(m.get('descriptionZh') or _zh(m.get('displayDescription'), '') or _zh(m.get('description'), ''))[:120]}",
        ]
        agents = m.get("agents") or []
        if m.get("expertType"):
            lines.append(f"包类型   : {m['expertType']}"
                         + ("（专家团，建议 migrate_workbuddy.py）" if m["expertType"] == "team" else ""))
        if agents:
            if isinstance(agents[0], dict):
                a = agents[0]
                lines.append(f"入口agent: {a.get('name')}（prompt={a.get('prompt')}，skills={len(a.get('skills') or [])}）")
            else:
                lines.append(f"角色数   : {len(agents)} → {', '.join(Path(str(a)).stem for a in agents)}")
        if m.get("teamInfo"):
            ti = m["teamInfo"]
            lines.append(f"团队     : 主理人 {ti.get('leadAgent')} / 成员 {len(ti.get('memberAgents') or [])}")
    lines.append("")
    lines.append(f"技能数   : {info['counts']['skills']}（含 scripts {info['counts']['with_scripts']} / references {info['counts']['with_references']} / templates {info['counts']['with_templates']}）")
    for s in info["skills"]:
        lines.append(f"  - {s['slug']:<28} {s['files']:>4} 文件  {','.join(s['subdirs']) or '-'}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="识别专家套件平台并列出结构")
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = Path(args.path)
    if not root.exists():
        print(f"错误：目录不存在 {root}", file=sys.stderr)
        return 2
    info = inspect(root)
    print(json.dumps(info, ensure_ascii=False, indent=2) if args.json else to_text(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
