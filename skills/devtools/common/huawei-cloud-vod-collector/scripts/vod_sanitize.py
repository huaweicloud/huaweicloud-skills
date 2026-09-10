from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PATTERNS: dict[str, tuple[str, str]] = {
    "api_key": (
        r"(api[_\-]?key|apikey|access[_\-]?key)\s*[:=]\s*[\"']?(\S{8,})[\"']?",
        r"\1=***REDACTED***",
    ),
    "token": (
        r"(token|bearer)\s*[:=]\s*[\"']?(\S{8,})[\"']?",
        r"\1=***REDACTED***",
    ),
    "password": (
        r"(password|passwd|pwd)\s*[:=]\s*[\"']?(\S+)[\"']?",
        r"\1=***REDACTED***",
    ),
    "secret": (
        r"(secret|secret[_\-]?key|secret[_\-]?access[_\-]?key)\s*[:=]\s*[\"']?(\S{8,})[\"']?",
        r"\1=***REDACTED***",
    ),
    "huawei_ak": (
        r"\b(AK|HW_ACCESS_KEY|AccessKeyId)\s*[:=]\s*[\"']?(\S{8,})[\"']?",
        r"\1=***REDACTED***",
    ),
    "huawei_sk": (
        r"\b(SK|HW_SECRET_KEY|SecretAccessKey)\s*[:=]\s*[\"']?(\S{8,})[\"']?",
        r"\1=***REDACTED***",
    ),
    # 裸密钥字符串（无 key= 前缀）: 复用 skill_quality_sdk.py 的同款掩码逻辑,
    # 覆盖常见 AK/SK 前缀: sk- (OpenAI 类), AKIA (AWS), LTAI (阿里云), mul_ (Multica)
    "bare_secret": (
        r"\b(sk-[A-Za-z0-9-]{8,}|AKIA[A-Z0-9]{16}|LTAI[A-Za-z0-9]{12,}|mul_[A-Za-z0-9]{20,})\b",
        r"***REDACTED***",
    ),
}


def sanitize(text: str, custom_patterns: list[str] | None = None) -> str:
    result = text
    for _, (pattern, replacement) in PATTERNS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    if custom_patterns:
        for cp in custom_patterns:
            try:
                result = re.sub(cp, "***REDACTED***", result)
            except re.error:
                continue
    return result


def sanitize_file(file_path: Path, output_path: Path | None = None, custom_patterns: list[str] | None = None) -> Path:
    content = file_path.read_text(encoding="utf-8")
    sanitized = sanitize(content, custom_patterns=custom_patterns)
    target = output_path or file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(sanitized, encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="敏感信息脱敏工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    text_parser = subparsers.add_parser("text", help="对文本进行脱敏")
    text_parser.add_argument("--value", required=True, dest="text_value", help="待脱敏的文本")

    file_parser = subparsers.add_parser("file", help="对文件进行脱敏")
    file_parser.add_argument("--path", required=True, dest="file_path", type=Path, help="待脱敏的文件路径")
    file_parser.add_argument("--output", type=Path, default=None, help="输出文件路径（默认原地修改）")

    args = parser.parse_args()

    if args.command == "text":
        result = sanitize(args.text_value)
        print(result)
    elif args.command == "file":
        result_path = sanitize_file(args.file_path, args.output)
        print(str(result_path))


if __name__ == "__main__":
    main()