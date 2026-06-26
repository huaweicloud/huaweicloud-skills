from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path


_STACK_PATTERNS = [
    re.compile(r"(Traceback \(most recent call last\):.*?)(?=\n\S|\Z)", re.DOTALL),
    re.compile(r"((?:Error|Exception|Fault|Failure):[^\n]*(?:\n\s+at[^\n]*)*)", re.MULTILINE),
    re.compile(r"((?:Caused by:)[^\n]*(?:\n\s+at[^\n]*)*)", re.MULTILINE),
]


def extract_error_stack(text: str, max_length: int = 4096) -> str:
    for pattern in _STACK_PATTERNS:
        match = pattern.search(text)
        if match:
            stack = match.group(1).strip()
            if len(stack) > max_length:
                stack = stack[:max_length] + f"\n... [截断，原长度{len(stack)}]"
            return stack
    return ""


def extract_agent_action(dialog_context: dict, anchor_turn: int) -> str:
    turns = dialog_context.get("turns", [])
    for turn in turns:
        if turn.get("turn_index") == anchor_turn and turn.get("role") == "assistant":
            parts = []
            if turn.get("tool_calls"):
                for tc in turn["tool_calls"]:
                    parts.append(f"调用工具: {tc.get('name', 'unknown')}")
                    if tc.get("args"):
                        args_summary = str(tc["args"])[:200]
                        parts.append(f"  参数摘要: {args_summary}")
            content = turn.get("content", "")
            if content:
                parts.append(f"生成内容摘要: {content[:300]}")
            return "\n".join(parts) if parts else ""
    return ""


def collect_environment() -> dict[str, str]:
    env_info: dict[str, str] = {}
    env_info["platform_type"] = detect_platform()
    env_info["platform_version"] = os.environ.get("AGENT_PLATFORM_VERSION", "未知")
    env_info["session_id"] = os.environ.get("SESSION_ID", "未知")
    env_info["os_info"] = f"{platform.system()} {platform.release()} ({platform.machine()})"
    env_info["python_version"] = platform.python_version()
    return env_info


def extract_dialog_context(
    dialog_file: Path, session_id: str, anchor_turn: int, depth: int
) -> list[dict]:
    if not dialog_file.exists():
        return []
    try:
        data = json.loads(dialog_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

    all_turns = [t for t in data.get("turns", []) if t.get("session_id") == session_id]
    if not all_turns:
        return []

    anchor_indices = [i for i, t in enumerate(all_turns) if t.get("turn_index") == anchor_turn]
    if not anchor_indices:
        return all_turns[-depth * 2:] if len(all_turns) > depth * 2 else all_turns

    anchor_idx = anchor_indices[0]
    start = max(0, anchor_idx - depth)
    end = min(len(all_turns), anchor_idx + depth + 1)
    result = all_turns[start:end]

    if start > 0 or end < len(all_turns):
        for t in result:
            t.setdefault("annotations", [])
            t["annotations"].append("上下文已截断")

    return result


def detect_platform() -> str:
    platform_env = os.environ.get("AGENT_PLATFORM", "")
    if platform_env:
        return platform_env.lower()

    cwd = Path.cwd()
    if (cwd / ".openclaw" / "config").exists():
        return "openclaw"
    if (cwd / ".hermes" / "config").exists():
        return "hermes"

    try:
        import psutil
        parent = psutil.Process().parent()
        if parent:
            pname = parent.name().lower()
            if "openclaw" in pname:
                return "openclaw"
            if "hermes" in pname:
                return "hermes"
    except (ImportError, Exception):
        pass

    return "generic"


def main() -> None:
    parser = argparse.ArgumentParser(description="上下文提取辅助工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stack_p = subparsers.add_parser("extract-stack", help="提取错误堆栈")
    stack_p.add_argument("--text", required=True, help="包含错误信息的文本")
    stack_p.add_argument("--max-length", type=int, default=4096, help="堆栈最大长度")

    action_p = subparsers.add_parser("extract-agent-action", help="提取Agent行为")
    action_p.add_argument("--dialog", required=True, type=Path, help="对话上下文JSON文件")
    action_p.add_argument("--anchor-turn", required=True, type=int, help="锚定轮次")

    env_p = subparsers.add_parser("collect-env", help="采集运行环境信息")

    dialog_p = subparsers.add_parser("extract-dialog", help="提取对话上下文")
    dialog_p.add_argument("--dialog", required=True, type=Path, help="对话文件路径")
    dialog_p.add_argument("--session-id", required=True, help="会话ID")
    dialog_p.add_argument("--anchor-turn", required=True, type=int, help="锚定轮次")
    dialog_p.add_argument("--depth", type=int, default=3, help="提取深度（前后各N轮）")

    platform_p = subparsers.add_parser("detect-platform", help="检测当前Agent平台")

    args = parser.parse_args()

    if args.command == "extract-stack":
        result = extract_error_stack(args.text, args.max_length)
        print(json.dumps({"error_stack": result}, ensure_ascii=False))
    elif args.command == "extract-agent-action":
        try:
            data = json.loads(args.dialog.read_text(encoding="utf-8"))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        result = extract_agent_action(data, args.anchor_turn)
        print(json.dumps({"agent_action": result}, ensure_ascii=False))
    elif args.command == "collect-env":
        result = collect_environment()
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "extract-dialog":
        result = extract_dialog_context(args.dialog, args.session_id, args.anchor_turn, args.depth)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "detect-platform":
        result = detect_platform()
        print(result)


if __name__ == "__main__":
    main()