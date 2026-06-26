from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "错误: 缺少 pyyaml 依赖，请执行: pip install pyyaml"
        " 或: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from .md_io import read_feedback_md, read_all_feedbacks
    from .models import FeedbackStatus, DeliveryStatus
    from .config_loader import load_config as _load_config_strict
except ImportError:
    from md_io import read_feedback_md, read_all_feedbacks
    from models import FeedbackStatus, DeliveryStatus
    try:
        from config_loader import load_config as _load_config_strict
    except ImportError:
        _load_config_strict = None


def _load_config(config_path: Path) -> dict:
    if _load_config_strict is not None:
        try:
            return _load_config_strict(config_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"[vod_deliver] 配置加载失败: {e}", file=sys.stderr)
            return {}

    if not config_path.exists():
        print(f"[vod_deliver] 配置文件不存在: {config_path}", file=sys.stderr)
        return {}

    try:
        text = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(text)
        if config is None:
            print(f"[vod_deliver] 配置文件为空或格式错误: {config_path}", file=sys.stderr)
            return {}
        return config
    except yaml.YAMLError as e:
        print(f"[vod_deliver] YAML解析失败: {e}", file=sys.stderr)
        return {}


def _extract_section_text(text: str, section_header: str) -> str:
    result_lines = []
    in_section = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == section_header:
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## "):
                break
            result_lines.append(line)
    content = "\n".join(result_lines).strip()
    return content


def _infer_product_name(feedback) -> str:
    if feedback.product_name:
        return feedback.product_name
    for ann in feedback.annotations:
        if ann.startswith("skill:"):
            return ann.split("skill:", 1)[1].strip()
    if feedback.agent_action:
        import re as _re
        m = _re.search(r"(?:调用|call|invoke)\s+(\S+?)(?:\s+技能|\s+skill|\s+的|\s+脚本|$)", feedback.agent_action)
        if m:
            return m.group(1).strip()
    if feedback.error_message:
        import re as _re
        m = _re.search(r"(\w+-\w+(?:-\w+)+)", feedback.error_message)
        if m:
            return m.group(1)
    return ""


def _build_issue_title(feedback, feedback_file: Path | None = None, product_name: str = "") -> str:
    desc = feedback.problem_description or feedback.error_message or feedback.user_intent or ""
    if not desc:
        desc = feedback.error_type or "VoD反馈"
    desc = desc[:60]
    name = product_name or _infer_product_name(feedback)
    if name:
        return f"【{name}】{desc}"
    return desc


def _build_issue_body(feedback, feedback_file: Path) -> str:
    description = (
        feedback.problem_description
        or feedback.error_message
        or feedback.user_intent
        or ""
    )

    occurrence_scenario = feedback.occurrence_scenario or ""

    expected_behavior = feedback.expected_behavior or ""

    actual_behavior = feedback.actual_behavior or ""

    if not occurrence_scenario and not expected_behavior and not actual_behavior:
        occurrence_scenario = feedback.agent_action or ""

    lines = [
        "### 描述问题 (Description)",
        description or "(待补充)",
        "",
    ]

    lines.append("### 复现步骤 (To Reproduce)")
    if occurrence_scenario:
        lines.append(occurrence_scenario)
    else:
        steps = []
        if feedback.user_intent:
            steps.append(f"1. 用户意图: {feedback.user_intent}")
        if feedback.agent_action:
            steps.append(f"2. Agent执行: {feedback.agent_action}")
        if feedback.error_type:
            steps.append(f"3. 触发错误: {feedback.error_type} - {feedback.error_message or ''}")
        lines.extend(steps if steps else ["(待补充)"])
    lines.append("")

    lines.extend([
        "### 预期行为 (Expected behavior)",
        expected_behavior or "(待补充)",
        "",
    ])

    if actual_behavior:
        lines.extend([
            "### 实际行为 (Actual behavior)",
            actual_behavior,
            "",
        ])

    if feedback.error_stack:
        lines.extend([
            "### 错误堆栈 (Stack Trace)",
            "```",
            feedback.error_stack,
            "```",
            "",
        ])

    if feedback.environment:
        lines.extend([
            "### 环境信息 (Environment)",
        ])
        for k, v in feedback.environment.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    return "\n".join(lines)


def _extract_repo_info(repo_url: str) -> tuple[str, str]:
    patterns = [
        r"https?://[^/]+/([^/]+)/([^/.]+?)(?:\.git)?$",
        r"git@[^:]+:([^/]+)/([^/.]+?)(?:\.git)?$",
    ]
    for p in patterns:
        m = re.match(p, repo_url.strip())
        if m:
            return m.group(1), m.group(2)
    raise ValueError(f"无法解析仓库地址: {repo_url}")


def _get_gitcode_api_base(repo_url: str) -> str:
    parsed = urllib.parse.urlparse(repo_url)
    return f"https://{parsed.hostname}/api/v5"


def _create_gitcode_issue(
    repo_url: str,
    token: str,
    title: str,
    body: str,
) -> dict:
    owner, repo = _extract_repo_info(repo_url)
    api_base = _get_gitcode_api_base(repo_url)
    url = f"{api_base}/repos/{owner}/{repo}/issues"

    data = {
        "access_token": token,
        "title": title,
        "body": body,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "issue_iid": result.get("iid", result.get("number", "")),
                "issue_url": result.get("html_url", result.get("web_url", "")),
                "issue_id": result.get("id", ""),
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        error_body = re.sub(r"access_token=[^&\s]+", "access_token=***", error_body)
        return {
            "success": False,
            "error": f"HTTP {e.code}: {error_body[:200]}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200],
        }


def _update_feedback_delivery_status(
    feedback_file: Path,
    issue_url: str,
    issue_iid: str,
) -> None:
    if not feedback_file.exists():
        return
    content = feedback_file.read_text(encoding="utf-8")
    delivery_section = (
        "\n## Delivery\n"
        f"- **delivery_status**: delivered\n"
        f"- **delivered_at**: {datetime.now().isoformat()}\n"
        f"- **delivery_channel**: gitcode_issue\n"
        f"- **issue_url**: {issue_url}\n"
        f"- **issue_iid**: {issue_iid}\n"
    )
    if "## Delivery" in content:
        lines = content.split("\n")
        new_lines = []
        skip = False
        for line in lines:
            if line.strip() == "## Delivery":
                skip = True
                continue
            if skip and line.strip().startswith("## "):
                skip = False
            if not skip:
                new_lines.append(line)
        content = "\n".join(new_lines)

    content = content.rstrip("\n") + "\n" + delivery_section
    feedback_file.write_text(content, encoding="utf-8")


def deliver_feedback(
    feedback_id: str,
    feedbacks_dir: Path,
    config_path: Path,
    token_override: str = "",
) -> dict:
    config = _load_config(config_path)
    gitcode_cfg = config.get("delivery", {}).get("channels", {}).get("gitcode", {})

    if not gitcode_cfg.get("enabled", False):
        return {"success": False, "error": "GitCode交付未启用"}

    repo_url = gitcode_cfg.get("repo_url", "")
    token = token_override or gitcode_cfg.get("token", "")

    if not repo_url or not token:
        return {"success": False, "error": "GitCode仓库地址或Token未配置"}

    feedback_file = feedbacks_dir / f"{feedback_id}.md"
    if not feedback_file.exists():
        return {"success": False, "error": f"反馈文件不存在: {feedback_file}"}

    try:
        feedback = read_feedback_md(feedback_file)
    except Exception as e:
        return {"success": False, "error": f"读取反馈记录失败: {e}"}

    if feedback.status == FeedbackStatus.DISCARDED:
        return {"success": False, "error": "已废弃的反馈不交付"}

    title = _build_issue_title(feedback, feedback_file, feedback.product_name or "")
    body = _build_issue_body(feedback, feedback_file)

    result = _create_gitcode_issue(repo_url, token, title, body)

    if result.get("success"):
        _update_feedback_delivery_status(
            feedback_file,
            result.get("issue_url", ""),
            str(result.get("issue_iid", "")),
        )

    return result


def _build_merged_issue_title(feedbacks: list, feedbacks_dir: Path, product_name: str = "") -> str:
    if len(feedbacks) == 1:
        fb_file = feedbacks_dir / f"{feedbacks[0].feedback_id}.md"
        return _build_issue_title(feedbacks[0], fb_file, product_name)
    first_desc = (
        feedbacks[0].problem_description
        or feedbacks[0].error_message
        or feedbacks[0].user_intent
        or ""
    )
    summary = first_desc[:30] if first_desc else "批量反馈"
    prefix = f"【{product_name}】" if product_name else ""
    return f"{prefix}VoD批量反馈（{len(feedbacks)}条）: {summary}等"


def _build_merged_issue_body(feedbacks: list, feedbacks_dir: Path) -> str:
    if len(feedbacks) == 1:
        fb_file = feedbacks_dir / f"{feedbacks[0].feedback_id}.md"
        return _build_issue_body(feedbacks[0], fb_file)

    parts = [f"共 {len(feedbacks)} 条反馈，合并提交：", ""]
    for i, fb in enumerate(feedbacks, 1):
        desc = fb.problem_description or fb.error_message or fb.user_intent or ""
        scenario = fb.occurrence_scenario or ""
        expected = fb.expected_behavior or ""
        actual = fb.actual_behavior or ""

        parts.append(f"### {i}. {desc or fb.feedback_id}")
        parts.append("")
        if scenario:
            parts.extend(["**复现步骤**", scenario, ""])
        if expected:
            parts.extend(["**预期行为**", expected, ""])
        if actual:
            parts.extend(["**实际行为**", actual, ""])
        if fb.error_stack:
            parts.extend(["```", fb.error_stack, "```", ""])
        parts.append("---")
        parts.append("")

    return "\n".join(parts)


def notify(feedbacks_dir: Path, config_path: Path, token_override: str = "") -> list[dict]:
    config = _load_config(config_path)
    gitcode_cfg = config.get("delivery", {}).get("channels", {}).get("gitcode", {})

    if not gitcode_cfg.get("enabled", False):
        return []

    repo_url = gitcode_cfg.get("repo_url", "")
    token = token_override or gitcode_cfg.get("token", "")

    if not repo_url or not token:
        return [{"success": False, "error": "GitCode仓库地址或Token未配置"}]

    all_feedbacks = read_all_feedbacks(feedbacks_dir)
    pending = []
    for fb in all_feedbacks:
        fb_file = feedbacks_dir / f"{fb.feedback_id}.md"
        content = fb_file.read_text(encoding="utf-8") if fb_file.exists() else ""
        if "delivery_status: delivered" in content:
            continue
        if fb.status == FeedbackStatus.DISCARDED:
            continue
        pending.append(fb)

    if not pending:
        return []

    product_name = pending[0].product_name or "" if pending else ""
    title = _build_merged_issue_title(pending, feedbacks_dir, product_name)
    body = _build_merged_issue_body(pending, feedbacks_dir)
    result = _create_gitcode_issue(repo_url, token, title, body)

    results = []
    if result.get("success"):
        for fb in pending:
            fb_file = feedbacks_dir / f"{fb.feedback_id}.md"
            _update_feedback_delivery_status(
                fb_file,
                result.get("issue_url", ""),
                str(result.get("issue_iid", "")),
            )
            results.append({
                "feedback_id": fb.feedback_id,
                "success": True,
                "issue_url": result.get("issue_url", ""),
                "issue_iid": result.get("issue_iid", ""),
            })
    else:
        for fb in pending:
            results.append({
                "feedback_id": fb.feedback_id,
                "success": False,
                "error": result.get("error", "unknown"),
            })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="VoD 反馈交付工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    notify_p = subparsers.add_parser("notify", help="推送未交付的反馈")
    notify_p.add_argument("--feedbacks-dir", required=True, type=Path, help="反馈目录")
    notify_p.add_argument("--config", required=True, type=Path, help="配置文件路径")
    notify_p.add_argument("--token", default="", help="GitCode Personal Access Token（优先于config中的token）")

    deliver_p = subparsers.add_parser("deliver", help="交付单条反馈")
    deliver_p.add_argument("--feedback-id", required=True, help="反馈ID")
    deliver_p.add_argument("--feedbacks-dir", required=True, type=Path, help="反馈目录")
    deliver_p.add_argument("--config", required=True, type=Path, help="配置文件路径")
    deliver_p.add_argument("--token", default="", help="GitCode Personal Access Token（优先于config中的token）")

    update_p = subparsers.add_parser("update-status", help="更新反馈交付状态")
    update_p.add_argument("--feedback-id", required=True, help="反馈ID")
    update_p.add_argument("--status", required=True, help="交付状态")
    update_p.add_argument("--feedbacks-dir", required=True, type=Path, help="反馈目录")

    args = parser.parse_args()

    if args.command == "notify":
        results = notify(args.feedbacks_dir, args.config, getattr(args, "token", ""))
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "deliver":
        result = deliver_feedback(args.feedback_id, args.feedbacks_dir, args.config, getattr(args, "token", ""))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "update-status":
        fb_file = args.feedbacks_dir / f"{args.feedback_id}.md"
        if not fb_file.exists():
            print(json.dumps({"error": "反馈文件不存在"}, ensure_ascii=False))
            sys.exit(1)
        content = fb_file.read_text(encoding="utf-8")
        if "## Delivery" not in content:
            content = content.rstrip("\n") + (
                "\n## Delivery\n"
                f"- **delivery_status**: {args.status}\n"
                f"- **delivered_at**: {datetime.now().isoformat()}\n"
            )
        else:
            content = re.sub(
                r"- \*\*delivery_status\*\*:.*",
                f"- **delivery_status**: {args.status}",
                content,
            )
        fb_file.write_text(content, encoding="utf-8")
        print(json.dumps({"feedback_id": args.feedback_id, "status": args.status}, ensure_ascii=False))


if __name__ == "__main__":
    main()
