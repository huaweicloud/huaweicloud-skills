#!/usr/bin/env python3
"""create_page.py —— 全新模式「生成 markdown → 创建在线 page 文档」的一发脚本（clouddocs-cli）。

为什么有这个脚本：
  用户给内容 → 模型生成 markdown（落 <项目工作目录>/drafts/page.md）→ 本脚本读 markdown，经
  clouddocs-cli page +create 一次创建在线 page 文档。organization_id / wiki_id 由 CLI 自动解析
  （个人空间 + 默认文档库），脚本只需 title + content；可选 parent_document_id（如 AI创作文档）
  显式传。服务地址由 CLI 配置（~/.clouddocs/config.json）决定，认证由 CLI 自管。

草稿目录约定：
  drafts（page.md / created_doc.json / page.kpge）一律建在**当前项目工作目录**（会话 cwd）下的
  drafts/，禁止写入技能安装目录或技能源码目录。脚本默认 --drafts-dir ./drafts，在项目工作目录
  运行即解析到 <项目工作目录>/drafts/。

幂等（关键）：
  建文档成功后**第一时间**落 created_doc.json（doc_id / doc_url）当锚点；重跑本脚本若锚点已在 →
  跳过 page +create、绝不重复建文档，只复用锚点回吐交付信息。

用法（cwd = 项目工作目录）：
  python3 <技能基目录>/scripts/create_page.py --title '<按主题命名的文档标题>'    # 读 ./drafts/page.md
  python3 <技能基目录>/scripts/create_page.py --title '...' --content '<markdown 文本>'     # 不走文件
  python3 <技能基目录>/scripts/create_page.py --title '...' --parent-document-id '<父文档ID>' # 建到指定父文档
  python3 <技能基目录>/scripts/create_page.py --title '...' --drafts-dir '<自定义目录>'       # 指定草稿目录
  python3 <技能基目录>/scripts/create_page.py --title '...' --dry-run                        # 不发网络、不写盘
  python3 <技能基目录>/scripts/create_page.py --probe-auth                                   # 只看 base/鉴权，不发网络、不写盘

退出码：0 成功 / 1 参数或前置缺失（未建文档）/ 2 鉴权或网络失败（未建文档）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _hws_cli as hws

def _fail(code: int, msg: str, extra: dict) -> int:
    print(json.dumps({"ok": False, "code": code, "msg": msg, **extra}, ensure_ascii=False, indent=2),
          file=sys.stderr)
    return code


def _unwrap(obj):
    return obj["data"] if isinstance(obj, dict) and isinstance(obj.get("data"), (dict, list)) else obj


def _find_str(obj, keys):
    o = _unwrap(obj)
    if isinstance(o, dict):
        for k in keys:
            v = o.get(k)
            if isinstance(v, str) and v:
                return v
    return None


def _walk_first_id(obj, keys):
    """深度优先找第一个非空字符串值，key 命中 keys 任一候选。

    CLI 信封 data 的字段名是运行时未知项；page +create 返回的文档 id 可能叫
    id / document_id / documentId / doc_id / node_id，这里递归兜底，找不到返回 None。
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and v:
                return v
        for v in obj.values():
            found = _walk_first_id(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _walk_first_id(item, keys)
            if found:
                return found
    return None


def _status_kind(status):
    if status in (401, 403):
        return "鉴权失败"
    if status is None:
        return "网络失败"
    return "后端拒绝（业务错误）"


def _read_markdown(drafts: Path, explicit_content: str) -> tuple[int, str]:
    """取 markdown 内容：--content 优先，否则读 drafts/page.md。"""
    if explicit_content.strip():
        return 0, explicit_content
    path = drafts / "page.md"
    if not path.exists():
        return 1, f"缺少内容：既没有 --content 参数，也没有 {path}"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return 1, f"读取 {path} 失败：{exc}"
    if not content.strip():
        return 1, f"{path} 内容为空"
    return 0, content


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title", help="文档标题（按主题命名）；建文档必填，created_doc.json 已在时可省")
    ap.add_argument("--content", default="", help="markdown 内容文本；缺省读 drafts/page.md")
    ap.add_argument("--format", type=int, default=1, dest="format_", help="page +create 的 --format（默认 1）")
    ap.add_argument("--parent-document-id", default="", dest="parent_document_id",
                    help="父文档 ID（如 AI创作文档）；缺省建在 CLI 默认位置")
    ap.add_argument("--drafts-dir", default="drafts",
                    help="drafts 目录（默认 ./drafts，即项目工作目录下的 drafts；禁止指向技能安装目录）")
    ap.add_argument("--probe-auth", action="store_true", help="只看 base/鉴权，不发网络、不写盘")
    ap.add_argument("--dry-run", action="store_true", help="不发网络、不写盘，仅预览将发的请求")
    args = ap.parse_args()

    drafts = Path(args.drafts_dir).resolve()
    if not drafts.is_dir():
        return _fail(1, f"drafts 目录不存在：{drafts}", {})

    base = hws.base_url()

    if args.probe_auth:
        h = hws.auth_headers()
        if h.get("error"):
            return _fail(2, h["error"], {"base": base})
        print(json.dumps({
            "ok": True, "base": base,
            "auth_present": {k: bool(v) for k, v in h.items()},
        }, ensure_ascii=False, indent=2))
        return 0

    created_path = drafts / "created_doc.json"

    # 幂等锚点：已建过 → 直接回吐交付信息，不再调 CLI
    if created_path.exists():
        try:
            created = json.loads(created_path.read_text(encoding="utf-8"))
            doc_id, doc_url = created["doc_id"], created["doc_url"]
        except (OSError, json.JSONDecodeError, KeyError):
            return _fail(1, "created_doc.json 损坏；删除它后重跑本脚本", {"path": str(created_path)})
        print(json.dumps({"ok": True, "doc_id": doc_id, "doc_url": doc_url,
                          "reused": True}, ensure_ascii=False, indent=2))
        return 0

    if not args.title:
        return _fail(1, "缺少 --title（建文档必填）", {})
    rc, content = _read_markdown(drafts, args.content)
    if rc != 0:
        return _fail(1, content, {})

    if args.dry_run:
        host = base.rstrip("/") if base else "<cloud-doc-base-url>"
        print(json.dumps({
            "ok": True, "dry_run": True, "base": base, "host": host,
            "title": args.title,
            "content_preview": content.strip()[:200],
            "content_chars": len(content),
            "format": args.format_,
            "parent_document_id": args.parent_document_id or "<default>",
            "create_body": {
                "title": args.title,
                "content": "<markdown 文本>",
                "format": args.format_,
                "parent_document_id": args.parent_document_id or "<resolved-by-cli>",
            },
            "doc_url_template": f"{host}/wapp/doc/<docId>",
        }, ensure_ascii=False, indent=2))
        return 0

    status, raw = hws.page_create(
        args.title, content,
        format_=args.format_,
        parent_document_id=args.parent_document_id,
    )
    if status not in (200, 201):
        return _fail(2, f"page +create {_status_kind(status)} status={status}",
                     {"body": (raw or "")[:500]})
    try:
        dobj = json.loads(raw)
    except json.JSONDecodeError:
        return _fail(2, "page +create 返回非 JSON", {"body": raw[:500]})
    doc_id = _find_str(dobj, ["id", "document_id", "documentId", "doc_id"]) \
        or _walk_first_id(dobj, ("id", "document_id", "documentId", "doc_id", "node_id"))
    if not doc_id:
        return _fail(2, "page +create 响应缺文档 id", {"body": raw[:500]})
    doc_url = f"{base.rstrip('/')}/wapp/doc/{doc_id}"
    # 建文档成功后第一时间落锚点——重跑不再重复建文档
    try:
        created_path.write_text(json.dumps({"doc_id": doc_id, "doc_url": doc_url},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        return _fail(1, f"建文档已成但 created_doc.json 落盘失败：{exc}（doc_id={doc_id}）", {})

    # 交付链接落盘（用户可见产物用 /outputs，运行态放 drafts）
    try:
        (drafts / "page.kpge").write_text(doc_url, encoding="utf-8")
    except OSError:
        pass

    print(json.dumps({
        "ok": True, "doc_id": doc_id, "doc_url": doc_url,
        "title": args.title,
    }, ensure_ascii=False, indent=2))
    print()
    print("==================================================================")
    print(f"✅ 在线 page 文档已创建：{doc_url}")
    print("➡️ 交付：把该链接交给用户即可（不主动打开文档，由用户自行决定是否打开）。")
    print("🚨 严禁: 重复运行本脚本再次建文档（created_doc.json 已是锚点，重跑只回吐、不新建）。")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
