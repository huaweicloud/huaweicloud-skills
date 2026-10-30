#!/usr/bin/env python3
"""Query the public SAC catalog JSON (always fetched fresh) with concept-aware search.

Single data source: the public OBS catalog (49+ solutions with solution_describe,
count grows over time). Never falls back to stale local data; reports generated_at
so the agent can announce catalog freshness to the user."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

PUBLIC_CATALOG_URL = "https://documentation-samples-5.obs.ap-southeast-1.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/sac_intl.json"

# Concept expansion: business term -> aliases matched against solution name / solution_url.
# Keep aliases >= 3 chars to avoid false hits (e.g. "bi" inside "building").
CONCEPTS: dict[str, list[str]] = {
    "网关": ["网关", "gateway", "litellm", "new api", "newapi"],
    "模型网关": ["网关", "gateway", "litellm", "new api", "newapi"],
    "agent": ["agent", "智能体", "openclaw", "hermes", "jiuwen", "swarm", "dify", "n8n"],
    "agents": ["agent", "智能体", "openclaw", "hermes", "jiuwen", "swarm", "dify", "n8n"],
    "智能体": ["agent", "智能体", "openclaw", "hermes", "jiuwen", "swarm", "dify", "n8n"],
    "知识库": ["知识库", "knowledge", "ragflow"],
    "问数": ["问数", "sqlbot", "智能问数"],
    "客服": ["客服", "chatbot"],
    "训练": ["训练", "yolo"],
    "视觉": ["视觉", "yolo"],
    "记忆": ["记忆", "memory"],
    "erp": ["erp", "odoo"],
    "工作流": ["n8n", "workflow"],
    "workflow": ["n8n", "workflow"],
    "推理": ["deepseek", "推理"],
    "embedding": ["embedding", "reranker"],
    "mcp": ["mcp"],
    "模板": ["模板", "template"],
    "微服务": ["微服务", "nacos", "服务发现"],
    "服务发现": ["nacos", "服务发现"],
    "语音": ["语音", "vibevoice", "转写"],
    "编程": ["编程", "opencode", "agent"],
    "备份": ["备份", "backup"],
    "加速": ["加速", "cdn", "wsa"],
    "cdn": ["cdn", "加速"],
    "安全": ["安全", "waf", "modsecurity"],
    "waf": ["waf", "modsecurity"],
    "电商": ["电商", "magento", "wordpress"],
    "网站": ["网站", "wordpress", "建站"],
    "运维": ["运维", "jumpserver", "堡垒"],
    "消息队列": ["rabbitmq", "pulsar", "消息"],
    "数据库": ["数据库", "supabase", "mysql", "mongodb"],
    "评测": ["评测", "evalscape", "evalscope"],
    "数据集": ["数据集", "dataset"],
    "sap": ["sap", "erp", "odoo"],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Search prebuilt public SAC catalog JSON (always fetched fresh).")
    p.add_argument("--keyword", default="", help="Business term or name, e.g. 模型网关 / agent方案 / Dify")
    p.add_argument(
        "--catalog",
        default="",
        help="Optional local catalog JSON path override (explicit offline/debug only). When set, takes precedence over --catalog-url.",
    )
    p.add_argument("--catalog-url", default=PUBLIC_CATALOG_URL, help="Public catalog URL (default: OBS-hosted sac_intl.json).")
    p.add_argument("--insecure", action="store_true", help="Skip TLS verification (only for broken local CA / MITM proxy envs).")
    p.add_argument("--ca-bundle", default="", help="Optional custom CA bundle path (sets SSL_CERT_FILE equivalent).")
    p.add_argument("--region-filter", default="", help="Optional region substring (stage B only), e.g. sa-brazil-1")
    p.add_argument("--group", action="store_true", help="Stage A: list distinct solution+variant rows with region counts (no region expansion)")
    p.add_argument("--solution", default="", help="Stage B: exact solution name filter; lists ALL regions for it")
    p.add_argument("--variant", default="", help="Stage B: variant filter, e.g. 单机版部署")
    p.add_argument("--limit", type=int, default=500, help="Max region rows in stage B (default 500; catalog never exceeds this)")
    p.add_argument("--out", default="", help="Optional output JSON path")
    return p.parse_args()


def fetch_catalog(args: argparse.Namespace) -> dict:
    if args.catalog:
        print("WARNING: using LOCAL catalog override (--catalog, offline/debug only).", file=sys.stderr)
        return json.loads(Path(args.catalog).expanduser().read_text(encoding="utf-8"))

    ctx = None
    if args.insecure:
        ctx = ssl._create_unverified_context()
        print("WARNING: TLS verification disabled (--insecure).", file=sys.stderr)
    elif args.ca_bundle:
        ctx = ssl.create_default_context(cafile=args.ca_bundle)

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(args.catalog_url, headers={"User-Agent": "sac-catalog-deploy/2.0"})
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = resp.read()
            ts = time.strftime("%Y-%m-%d %H:%M:%S %z")
            catalog = json.loads(data.decode("utf-8"))
            generated_at = str(catalog.get("generated_at", "")) if isinstance(catalog, dict) else ""
            print(f"catalog fetched fresh from OBS at {ts}", file=sys.stderr)
            if generated_at:
                print(f"catalog data as of: {generated_at}", file=sys.stderr)
            return catalog
        except Exception as exc:
            last_exc = exc
            print(f"fetch attempt {attempt}/3 failed: {exc}", file=sys.stderr)
            if attempt < 3:
                time.sleep(attempt)
    raise RuntimeError(
        f"cannot fetch fresh catalog after 3 attempts: {last_exc}. "
        "Refusing to proceed with stale data — inform the user and retry later or fix the network."
    )


def _alias_ok(e: str) -> bool:
    """English aliases need >=3 chars to avoid substring noise (e.g. "bi" in "building");
    CJK aliases are fine at 2 chars (网关, 知识库, 训练...)."""
    is_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in e)
    return (is_cjk and len(e) >= 2) or (not is_cjk and len(e) >= 3)


def expand_keyword(keyword: str) -> set[str]:
    kw = (keyword or "").lower().strip()
    out: set[str] = set()
    if not kw:
        return out
    for concept, aliases in CONCEPTS.items():
        c = concept.lower()
        if c in kw or kw in c:
            out.update(a.lower() for a in aliases)
            continue
        # Reverse mapping: an English keyword that equals/contains one of the concept's
        # aliases expands to the full alias set (e.g. "gateway" -> 网关 aliases),
        # so English business terms still hit Chinese describe text.
        if any(al.lower() == kw or (al.lower() in kw and _alias_ok(al)) for al in aliases):
            out.update(a.lower() for a in aliases)
    return out


def describe_of(s: dict) -> str:
    short = (s.get("solution_describe", "") or "").strip()
    long = (s.get("solution_describe_long", "") or "").strip()
    if long and short and (long.startswith(short) or short in long):
        return long
    return f"{short} {long}".strip()


def score_solution(name: str, url: str, describe: str, keyword: str, extras: set[str]) -> int:
    text = (name or "").lower()
    url_l = (url or "").lower()
    desc = (describe or "").lower()
    kw = (keyword or "").lower().strip()
    best = 0
    if kw:
        if kw == text:
            best = 100
        elif kw in text:
            best = 50
        elif kw in desc:
            best = 30
        else:
            parts = re.findall(r"[a-z0-9]+|[一-鿿]+", kw)
            if parts:
                t = text.replace(" ", "")
                d = desc.replace(" ", "")
                if all(p in t for p in parts):
                    best = 20
                elif all(p in d for p in parts):
                    best = 12
    for e in extras:
        if _alias_ok(e) and (e in text or e in url_l or e in desc):
            best = max(best, 40)
    return best


def main() -> int:
    args = parse_args()
    if not args.keyword and not args.solution:
        print("Need --keyword (stage A search) or --solution (stage B region listing).", file=sys.stderr)
        return 1
    try:
        catalog = fetch_catalog(args)
    except Exception as exc:
        print(f"Load catalog failed: {exc}", file=sys.stderr)
        return 1

    solutions = catalog.get("solutions", []) if isinstance(catalog, dict) else []
    catalog_generated_at = str(catalog.get("generated_at", "")) if isinstance(catalog, dict) else ""
    extras = expand_keyword(args.keyword)
    sol_f = args.solution.lower().strip()
    var_f = args.variant.lower().strip()
    region_f = args.region_filter.lower().strip()
    no_match = False

    if sol_f:
        # Stage B: filter by solution/variant, expand ALL regions.
        matched = [
            s
            for s in solutions
            if sol_f in str(s.get("solution_name", "")).lower()
            and (not var_f or var_f in " ".join(str(v.get("variant", "")) for v in s.get("variants", []) or []).lower())
        ]
        if not matched:
            print(f'No solution matches --solution="{args.solution}" --variant="{args.variant}"')
            return 2
    else:
        # Stage A: concept-aware scoring; zero hit -> full catalog fallback.
        scored = []
        for s in solutions:
            sc = score_solution(str(s.get("solution_name", "")), str(s.get("solution_url", "")), describe_of(s), args.keyword, extras)
            if sc > 0:
                scored.append((sc, s))
        if not scored:
            no_match = True
            print(f'No direct match for "{args.keyword}" — showing FULL catalog so you can pick one:')
            scored = [(0, s) for s in solutions]
        matched = [s for _, s in scored]

    score_by_id = {}
    if not sol_f:
        for s in solutions:
            score_by_id[id(s)] = score_solution(str(s.get("solution_name", "")), str(s.get("solution_url", "")), describe_of(s), args.keyword, extras)

    if args.group:
        # Stage A output: distinct solution+variant rows with region counts.
        rows: list[dict] = []
        for s in matched:
            desc = describe_of(s)
            for v in s.get("variants", []) or []:
                rows.append(
                    {
                        "score": score_by_id.get(id(s), 0),
                        "solution_name": s.get("solution_name", ""),
                        "solution_describe": desc[:200],
                        "solution_url": s.get("solution_url", ""),
                        "variant": str(v.get("variant", "")),
                        "region_count": len(v.get("regions", []) or []),
                    }
                )
        if not rows:
            print("No variants found for matched solutions (some solutions have 0 variants).")
            return 2
        rows.sort(key=lambda x: (-x["score"], x["solution_name"], x["variant"]))
        for i, r in enumerate(rows, 1):
            line = f'{i}) {r["solution_name"]} | {r["variant"]} | {r["region_count"]} regions'
            if r["solution_describe"]:
                line += f' — {r["solution_describe"][:72]}'
            print(line)
        print("Next: re-run with --solution \"<solution_name>\" --variant \"<variant>\" to list ALL regions.")
        if args.out:
            Path(args.out).expanduser().write_text(
                json.dumps({"keyword": args.keyword, "mode": "group", "no_match": no_match, "count": len(rows), "total_solutions": len(solutions), "catalog_generated_at": catalog_generated_at, "candidates": rows}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote candidates: {args.out}")
        return 0

    # Region-expanded rows (stage B, or stage A compat mode).
    rows = []
    for s in matched:
        for v in s.get("variants", []) or []:
            variant = str(v.get("variant", ""))
            if var_f and var_f not in variant.lower():
                continue
            for r in v.get("regions", []) or []:
                label = str(r.get("region_label", ""))
                console = str(r.get("console_region", ""))
                if region_f and region_f not in f"{label} {console}".lower():
                    continue
                rows.append(
                    {
                        "score": score_by_id.get(id(s), 0),
                        "solution_name": s.get("solution_name", ""),
                        "solution_url": s.get("solution_url", ""),
                        "variant": variant,
                        "region_label": label,
                        "console_region": console,
                        "template_url": r.get("template_url", ""),
                        "deploy_link": r.get("deploy_link", ""),
                    }
                )

    rows.sort(key=lambda x: (-x["score"], x["solution_name"], x["variant"], x["region_label"]))
    rows = rows[: args.limit]

    if not rows:
        print(f'No rows for keyword="{args.keyword}" solution="{args.solution}" variant="{args.variant}" region_filter="{args.region_filter}"')
        return 2

    for i, r in enumerate(rows, 1):
        print(f'{i}) {r["solution_name"]} | {r["variant"]} | {r["region_label"]} ({r["console_region"]})')
        print(f'   template: {r["template_url"]}')
        print(f'   deploy: {r["deploy_link"]}')

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps({"keyword": args.keyword, "mode": "regions", "no_match": no_match, "count": len(rows), "total_solutions": len(solutions), "catalog_generated_at": catalog_generated_at, "candidates": rows}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote candidates: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
