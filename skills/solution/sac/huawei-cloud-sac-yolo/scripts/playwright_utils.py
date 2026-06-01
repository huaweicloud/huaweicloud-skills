#!/usr/bin/env python
"""Shared playwright-cli helpers for SAC scripts."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def resolve_command(command: str) -> str | None:
    return shutil.which(command)


def build_pw_command() -> list[str]:
    pw = resolve_command("playwright-cli")
    if pw:
        return [pw]
    npx = resolve_command("npx")
    if npx:
        return [npx, "playwright-cli"]
    raise RuntimeError(
        "playwright-cli is not installed. Install with: npm install -g @playwright/cli@latest"
    )


def run_pw(
    base_cmd: list[str],
    session: str,
    args: list[str],
    allow_failure: bool = False,
) -> subprocess.CompletedProcess:
    full_cmd = [*base_cmd, f"-s={session}", *args]
    proc = subprocess.run(
        full_cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )

    if not allow_failure and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"playwright-cli {' '.join(args)} failed (exit {proc.returncode}): {detail}")

    return proc


def cleanup_output(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"^#\s?", "", text, flags=re.MULTILINE)
    return text.strip()


def run_pw_code(base_cmd: list[str], session: str, script: str) -> subprocess.CompletedProcess:
    script_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as handle:
            handle.write(script)
            script_path = handle.name

        proc = run_pw(base_cmd, session, ["run-code", f"--filename={script_path}"], allow_failure=True)
        if proc.returncode == 0:
            return proc

        detail = cleanup_output(f"{proc.stdout}\n{proc.stderr}")
        # Backward compatibility for older playwright-cli versions without --filename.
        if re.search(r"(unknown|unexpected).*(--filename|filename)", detail, flags=re.IGNORECASE):
            return run_pw(base_cmd, session, ["run-code", script])

        raise RuntimeError(
            f"playwright-cli run-code failed (exit {proc.returncode}): {detail or 'unknown error'}"
        )
    finally:
        if script_path:
            try:
                Path(script_path).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass


def extract_last_json_structure(text: str):
    decoder = json.JSONDecoder()
    best = None
    best_len = -1
    for idx, ch in enumerate(text):
        if ch not in '[{"':
            continue
        try:
            parsed, consumed = decoder.raw_decode(text[idx:])
        except Exception:  # noqa: BLE001
            continue
        if isinstance(parsed, str):
            try:
                reparsed = json.loads(parsed)
            except Exception:  # noqa: BLE001
                reparsed = None
            if isinstance(reparsed, (list, dict)):
                if consumed > best_len:
                    best = reparsed
                    best_len = consumed
                continue
        if isinstance(parsed, (list, dict)):
            if consumed > best_len:
                best = parsed
                best_len = consumed
    return best


def extract_marked_json(output: str, marker: str):
    cleaned = cleanup_output(output)
    quoted_chunks = re.findall(r'"(?:[^"\\]|\\.)*"', cleaned, flags=re.DOTALL)
    for chunk in reversed(quoted_chunks):
        try:
            decoded = json.loads(chunk)
        except Exception:  # noqa: BLE001
            continue
        if marker in decoded:
            payload = decoded.split(marker, 1)[1]
            try:
                return json.loads(payload)
            except Exception:  # noqa: BLE001
                continue

    idx = cleaned.rfind(marker)
    if idx < 0:
        parsed = extract_last_json_structure(cleaned)
        if parsed is not None:
            return parsed

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        for line in reversed(lines):
            candidate = line
            if (
                (candidate.startswith('"') and candidate.endswith('"'))
                or (candidate.startswith("'") and candidate.endswith("'"))
            ):
                candidate = candidate[1:-1]
            try:
                decoded = json.loads(candidate)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(decoded, str):
                try:
                    decoded = json.loads(decoded)
                except Exception:  # noqa: BLE001
                    pass
            if isinstance(decoded, (list, dict)):
                return decoded

        tail = "\n".join(lines[-8:])
        raise RuntimeError(
            f"Unable to find marker {marker} in playwright-cli output. Last output lines:\n{tail}"
        )

    after = cleaned[idx + len(marker) :].strip()
    first_line = after.splitlines()[0].strip() if after else ""

    if (first_line.startswith('"') and first_line.endswith('"')) or (
        first_line.startswith("'") and first_line.endswith("'")
    ):
        first_line = first_line[1:-1]

    return json.loads(first_line)
