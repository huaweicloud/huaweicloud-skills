#!/usr/bin/env python
"""Extract SAC detail page price and deploy links via playwright-cli."""

import argparse
import json
import re
import sys
import time
from pathlib import Path

# Ensure sibling modules are importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright_utils import build_pw_command, extract_marked_json, run_pw, run_pw_code

MARKER = "__SAC_JSON__"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "extract_sac_deploy_info.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract deploy links and estimated price from SAC detail page."
    )
    parser.add_argument("--url", required=True, help="SAC detail page URL")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    parser.add_argument("--timeout-ms", type=int, default=60000)
    parser.add_argument("--session", default=f"sac-detail-{int(time.time() * 1000)}")
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def score_link(text: str, url: str) -> int:
    """Score a link by how likely it is a Terraform deploy/template download link.

    Chinese keywords (部署/模板/下载) match Huawei Cloud solution page UI text,
    which is primarily in Simplified Chinese.
    """
    signal = f"{text} {url}".lower()
    score = 0
    if "部署" in signal:  # Chinese: "deploy"
        score += 3
    if "terraform" in signal:
        score += 4
    if "template" in signal or "模板" in signal:  # Chinese: "template"
        score += 3
    if "download" in signal or "下载" in signal:  # Chinese: "download"
        score += 3
    if re.search(r"\.tf(\.json)?($|[?#])", url, re.IGNORECASE):
        score += 6
    if "aos" in signal or "stack" in signal:
        score += 1
    return score


def score_price_text(text: str) -> int:
    """Score a text candidate by how likely it contains pricing information.

    Chinese keywords (元/人民币/费用/成本规划 etc.) match Huawei Cloud
    solution page pricing text, which uses Simplified Chinese currency terms.
    """
    value = text or ""
    score = 0
    # Chinese: 元=CNY, 人民币=RMB, 至/到=range "to"
    if re.search(r"[0-9][0-9,.]*(?:\s*(?:~|-|至|到)\s*[0-9][0-9,.]*)?\s*(?:元|人民币|USD|美元)", value, re.IGNORECASE):
        score += 10
    if re.search(r"[0-9][0-9,.]*\s*\+\s*[^ ]*费用", value):  # 费用=cost/fee
        score += 4
    # Chinese: 资源和成本规划="resource and cost planning", 成本规划="cost planning"
    if "资源和成本规划" in value or "成本规划" in value:
        score += 1
    if re.search(r"表\d+", value):
        score += 1
    return score


def filter_out_reserved_price_lines(price_candidates: list[str]) -> list[str]:
    """Remove reserved/subscription pricing lines (包年包月=annual/monthly subscription)."""
    filtered = []
    for item in price_candidates:
        value = item or ""
        if re.search(r"包年包月|年付|月付|包月", value):  # Chinese: subscription terms
            continue
        filtered.append(value)
    return filtered


def filter_doc_fallback_on_demand_candidates(price_candidates: list[str]) -> list[str]:
    """When falling back to a cost documentation page, keep only on-demand pricing.

    Chinese: 按需计费/按需=on-demand/pay-as-you-go, 包年包月=subscription.
    """
    if not price_candidates:
        return []

    amount_re = re.compile(r"[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:元|人民币|USD|美元)", re.IGNORECASE)
    state = "unknown"  # unknown | on_demand | reserved
    kept: list[str] = []

    for item in price_candidates:
        value = item or ""
        if re.search(r"按需计费|按需", value):
            state = "on_demand"
            kept.append(value)
            continue
        if re.search(r"包年包月|年付|月付|包月", value):
            state = "reserved"
            continue

        if amount_re.search(value):
            if state == "reserved":
                continue
            kept.append(value)
            continue

        # Keep non-amount metadata lines only before entering reserved section.
        if state != "reserved":
            kept.append(value)

    return filter_out_reserved_price_lines(kept)


def derive_hourly_price_text(
    estimated_price_text: str,
    price_candidates: list[str],
    hours_per_month: int = 730,
) -> str:
    """Convert monthly price to hourly estimate (÷730 hours/month).

    Only applies when on-demand pricing context (按需) is detected.
    """
    if not estimated_price_text or hours_per_month <= 0:
        return ""

    text = estimated_price_text.strip()
    if re.search(r"/\s*小时|每小时", text):
        return text

    on_demand_context = any("按需" in (item or "") for item in price_candidates)
    if not on_demand_context:
        return ""

    amount_match = re.search(
        r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:~|-|至|到)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)?\s*(元|人民币|USD|美元)",
        text,
        re.IGNORECASE,
    )
    if not amount_match:
        return ""

    def _to_num(s: str) -> float:
        return float(s.replace(",", ""))

    lower = _to_num(amount_match.group(1))
    upper = _to_num(amount_match.group(2)) if amount_match.group(2) else None

    unit = "元/小时"
    if (amount_match.group(3) or "").lower() in ("usd", "美元"):
        unit = "USD/小时"

    suffix = text[amount_match.end() :].strip()
    if suffix.startswith("+"):
        suffix = suffix[1:].strip()
    suffix_text = f" + {suffix}（未折算）" if suffix else ""

    if upper is not None:
        hourly = f"{lower / hours_per_month:.4f}~{upper / hours_per_month:.4f}{unit}"
    else:
        hourly = f"{lower / hours_per_month:.4f}{unit}"

    return f"{hourly}{suffix_text}（按{hours_per_month}小时/月估算）"


def build_extract_script(timeout_ms: int) -> str:
    if not TEMPLATE_PATH.exists():
        raise RuntimeError(f"Missing JS template: {TEMPLATE_PATH}")
    script = TEMPLATE_PATH.read_text(encoding="utf-8")
    script = script.replace("__TIMEOUT__", str(timeout_ms))
    script = script.replace("__MARKER__", MARKER)
    return script


def main() -> int:
    args = parse_args()
    if args.timeout_ms <= 0:
        args.timeout_ms = 60000

    base_cmd = build_pw_command()

    open_args = ["open", args.url]
    if args.headed:
        open_args.append("--headed")
    run_pw(base_cmd, args.session, open_args)

    try:
        script = build_extract_script(args.timeout_ms)
        scrape = run_pw_code(base_cmd, args.session, script)
        extracted = extract_marked_json(f"{scrape.stdout}\n{scrape.stderr}", MARKER)
        price_candidates = extracted.get("price_text_candidates", [])
        price_source_url = extracted.get("price_source_url", extracted.get("page_url", ""))
        is_doc_fallback_price = bool(price_source_url and price_source_url != args.url)
        if is_doc_fallback_price:
            price_candidates = filter_doc_fallback_on_demand_candidates(price_candidates)
        best_price_text = ""
        if price_candidates:
            ranked_prices = sorted(price_candidates, key=score_price_text, reverse=True)
            best_price_text = ranked_prices[0]
        hourly_price_text = derive_hourly_price_text(best_price_text, price_candidates, 730)
        if is_doc_fallback_price and hourly_price_text:
            # For doc-page fallback, default to on-demand hourly display and hide monthly list prices.
            best_price_text = hourly_price_text

        deploy_links = extracted.get("deploy_links", [])
        deploy_links_ranked = sorted(
            [{**item, "score": score_link(item.get("text", ""), item.get("url", ""))} for item in deploy_links],
            key=lambda x: x.get("score", 0),
            reverse=True,
        )

        template_candidates = [
            item
            for item in deploy_links_ranked
            if re.search(r"terraform|template|模板|download|下载|\.tf(\.json)?($|[?#])", f"{item.get('text', '')} {item.get('url', '')}", re.IGNORECASE)
        ]
        tf_file_candidates = [
            item for item in deploy_links_ranked if re.search(r"\.tf(\.json)?($|[?#])", item.get("url", ""), re.IGNORECASE)
        ]

        result = {
            "selected_url": args.url,
            "session": args.session,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "title": extracted.get("title", ""),
            "estimated_price_text": best_price_text,
            "price_text_candidates": price_candidates,
            "price_source_url": price_source_url,
            "deploy_links": deploy_links_ranked,
            "template_download_candidates": template_candidates,
            "tf_template_file_candidates": tf_file_candidates,
            "primary_tf_template_url": (tf_file_candidates[0]["url"] if tf_file_candidates else ""),
        }

        if args.out:
            out_path = Path(args.out).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(f"Title: {result.get('title', '')}")
        if result.get("estimated_price_text"):
            print(f"Estimated Price: {result['estimated_price_text']}")
        else:
            print("Estimated Price: (not found)")
        print(f"Deploy links: {len(result.get('deploy_links', []))}")
        print(f"TF template files: {len(result.get('tf_template_file_candidates', []))}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        run_pw(base_cmd, args.session, ["close"], allow_failure=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"extract_sac_deploy_info failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
