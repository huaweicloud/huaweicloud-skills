#!/usr/bin/env python3
"""ov_redact.py — PII / secret redaction before sending text to OpenViking.

This module strips personally identifiable information and secrets from text
before it is persisted to the OpenViking long-term memory store.  It is
designed to be called as a CLI helper by the agent-integration shell scripts::

    python3 ov_redact.py redact <input_file>
    python3 ov_redact.py redact-string "<text>"
    python3 ov_redact.py redact-stdin          # read from stdin

Configuration:
    OV_REDACT_SECRETS  env var — set to "false"/"0"/"no"/"off"/"disable" to
                       disable redaction (default: enabled).
    --no-redact        CLI flag — bypasses redaction regardless of env var.

Only the standard-library ``re`` module is used — no external dependencies.
"""
from __future__ import annotations

import os
import re
import sys

# ── Redaction patterns ────────────────────────────────────────
# Order matters: most specific patterns are applied first so that generic
# patterns (e.g. high-entropy strings) do not clobber more precise matches.

# API keys — most specific, applied first.
_API_KEY_PATTERNS: list[tuple[str, str]] = [
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"ghp_[A-Za-z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
    (r"sk-ant-[A-Za-z0-9]{20,}", "[REDACTED_ANTHROPIC_KEY]"),
    (r"sk-[A-Za-z0-9]{20,}", "[REDACTED_OPENAI_KEY]"),
]

# Bearer tokens.
_BEARER_RE = re.compile(r"Bearer [A-Za-z0-9._-]+")
_BEARER_REPLACEMENT = "Bearer [REDACTED]"

# Password / secret assignments — capture the keyword for the replacement.
_PASSWORD_RE = re.compile(
    r"(password|passwd|pwd|secret|token|api_key|apikey)\s*[=:]\s*\S+"
)

# Email addresses.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_EMAIL_REPLACEMENT = "[REDACTED_EMAIL]"

# Phone numbers — international (with + prefix) checked before Chinese mobile.
_PHONE_INTL_RE = re.compile(r"\+\d{1,3}[\s-]?\d{3,}[\s-]?\d{3,}[\s-]?\d{3,}")
_PHONE_CN_RE = re.compile(r"\b1[3-9]\d{9}\b")
_PHONE_REPLACEMENT = "[REDACTED_PHONE]"

# IP addresses — non-loopback / non-private (negative lookaheads).
_IP_RE = re.compile(
    r"\b(?!127\.)(?!10\.)(?!192\.168\.)(?!172\.)(?!0\.)"
    r"([0-9]{1,3}\.){3}[0-9]{1,3}\b"
)
_IP_REPLACEMENT = "[REDACTED_IP]"

# High-entropy strings — generic, applied last.
_HIGH_ENTROPY_RE = re.compile(r"[A-Za-z0-9]{40,}")
_HIGH_ENTROPY_REPLACEMENT = "[REDACTED_TOKEN]"

# ISSUE-015: 32-char hex runs were not covered by the 40+ rule and leaked
# (session tokens / md5-style secrets in text). Skipped in hash contexts
# (checksum/sha/commit/...) like the generic high-entropy rule.
_HEX32_RE = re.compile(r"\b[0-9a-fA-F]{32}\b")
_HEX32_REPLACEMENT = "[REDACTED_HEX32]"

# Keywords that indicate a SHA-hash context (skip high-entropy redaction).
_HASH_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "sha", "commit", "hash", "digest", "checksum", "git", "blob", "tree",
)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# Pre-compile API-key regexes for reuse.
_API_KEY_RES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p), r) for p, r in _API_KEY_PATTERNS
]


# ── Helpers ───────────────────────────────────────────────────
def _is_hash_context(text: str, pos: int) -> bool:
    """Return True if *pos* in *text* is preceded by a hash-context keyword.

    Looks at the 30 characters immediately before *pos* for any keyword
    in :data:`_HASH_CONTEXT_KEYWORDS` (case-insensitive).
    """
    window = text[max(0, pos - 30):pos].lower()
    return any(kw in window for kw in _HASH_CONTEXT_KEYWORDS)


def _redact_high_entropy(text: str) -> str:
    """Redact high-entropy strings, skipping SHA hashes in known contexts.

    A 40+ character alphanumeric run is considered a SHA hash (and skipped)
    only when it is entirely hexadecimal **and** preceded by a hash-context
    keyword such as *commit*, *sha*, *digest*, etc.
    """
    def _replace(m: re.Match[str]) -> str:
        token = m.group(0)
        if _HEX_RE.match(token) and _is_hash_context(text, m.start()):
            return token  # looks like a SHA hash in context — keep it
        return _HIGH_ENTROPY_REPLACEMENT

    return _HIGH_ENTROPY_RE.sub(_replace, text)


def _redact_hex32(text: str) -> str:
    """Redact 32-char hex runs (ISSUE-015), keeping hash-context occurrences."""
    def _replace(m: re.Match[str]) -> str:
        if _is_hash_context(text, m.start()):
            return m.group(0)  # checksum/sha context — looks like a digest
        return _HEX32_REPLACEMENT

    return _HEX32_RE.sub(_replace, text)


# ── Public API ────────────────────────────────────────────────
def redact(text: str) -> str:
    """Apply all redaction patterns to *text* and return the result.

    Patterns are applied in order from most specific (API keys, bearer tokens)
    to most generic (high-entropy strings) so that precise matches are not
    overwritten by broad ones.
    """
    # 1. API keys (most specific).
    for regex, replacement in _API_KEY_RES:
        text = regex.sub(replacement, text)

    # 2. Bearer tokens.
    text = _BEARER_RE.sub(_BEARER_REPLACEMENT, text)

    # 3. Password / secret assignments.
    text = _PASSWORD_RE.sub(lambda m: m.group(1) + "=[REDACTED]", text)

    # 4. Email addresses.
    text = _EMAIL_RE.sub(_EMAIL_REPLACEMENT, text)

    # 5. Phone numbers (international first, then Chinese mobile).
    text = _PHONE_INTL_RE.sub(_PHONE_REPLACEMENT, text)
    text = _PHONE_CN_RE.sub(_PHONE_REPLACEMENT, text)

    # 6. IP addresses (non-loopback / non-private).
    text = _IP_RE.sub(_IP_REPLACEMENT, text)

    # 7. High-entropy strings (generic, last — with SHA-hash context skip).
    text = _redact_high_entropy(text)

    # 8. 32-char hex runs (ISSUE-015 — hash-context aware).
    text = _redact_hex32(text)

    return text


def is_redaction_enabled(no_redact_flag: bool) -> bool:
    """Return True if redaction should run given the flag and env var.

    Redaction is disabled when *no_redact_flag* is ``True`` or when the
    ``OV_REDACT_SECRETS`` environment variable is set to a falsy value
    (``false``, ``0``, ``no``, ``off``, ``disable``, ``disabled``).
    """
    if no_redact_flag:
        return False
    env_val = os.environ.get("OV_REDACT_SECRETS", "true").strip().lower()
    return env_val not in ("false", "0", "no", "off", "disable", "disabled")


def process(text: str, no_redact: bool = False) -> str:
    """Process *text*: redact if enabled, otherwise return unchanged."""
    if is_redaction_enabled(no_redact):
        return redact(text)
    return text


# ── CLI ───────────────────────────────────────────────────────
def _split_flag(args: list[str]) -> tuple[list[str], bool]:
    """Separate ``--no-redact`` from positional arguments."""
    no_redact = "--no-redact" in args
    positional = [a for a in args if a != "--no-redact"]
    return positional, no_redact


def _read_input(path: str) -> str:
    """Read text from *path* (``-`` or empty string means stdin)."""
    if path in ("-", ""):
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"Error reading {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_redact(args: list[str]) -> None:
    """Read text from a file, redact, and write to stdout."""
    positional, no_redact = _split_flag(args)
    if not positional:
        print("Usage: redact <input_file> [--no-redact]", file=sys.stderr)
        sys.exit(2)
    text = _read_input(positional[0])
    sys.stdout.write(process(text, no_redact))


def cmd_redact_string(args: list[str]) -> None:
    """Redact a string given as a command-line argument."""
    positional, no_redact = _split_flag(args)
    if not positional:
        print("Usage: redact-string <text> [--no-redact]", file=sys.stderr)
        sys.exit(2)
    # Use print() for string args — adds trailing newline for shell ergonomics.
    print(process(positional[0], no_redact))


def cmd_redact_stdin(args: list[str]) -> None:
    """Read text from stdin, redact, and write to stdout."""
    _, no_redact = _split_flag(args)
    text = sys.stdin.read()
    sys.stdout.write(process(text, no_redact))


def main() -> None:
    """CLI entry point — dispatch to a subcommand."""
    if len(sys.argv) < 2:
        print(
            "Usage: ov_redact.py <subcommand> [args]\n"
            "\n"
            "Subcommands:\n"
            "  redact <file>          Redact text from a file\n"
            "  redact-string <text>   Redact text from a command-line arg\n"
            "  redact-stdin            Redact text from stdin\n"
            "\n"
            "Options:\n"
            "  --no-redact             Bypass redaction\n"
            "\n"
            "Environment:\n"
            "  OV_REDACT_SECRETS       Set to false/0/no/off to disable\n",
            file=sys.stderr,
        )
        sys.exit(2)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "redact": cmd_redact,
        "redact-string": cmd_redact_string,
        "redact-stdin": cmd_redact_stdin,
    }
    fn = dispatch.get(cmd)
    if fn is None:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
