#!/usr/bin/env python3
"""Append and summarize JSONL run journals for hcloud skill tasks."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import hcloud_common


def read_json(path: Path) -> Any:
    """Return parsed JSON content from a file."""
    return json.loads(path.read_text(encoding="utf-8"))


def append_event(path: Path, event: dict[str, Any], secrets: set[str] | None = None) -> dict[str, Any]:
    """Append one redacted event to a JSONL journal."""
    path.parent.mkdir(parents=True, exist_ok=True)
    known_secrets = set(secrets or set())
    known_secrets.update(hcloud_common.collect_json_secrets(event))
    entry = hcloud_common.redact_json(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "redaction_version": 1,
            **event,
        },
        known_secrets,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_events(path: Path) -> list[dict[str, Any]]:
    """Read all valid JSONL events from a journal path."""
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact summary of journal events."""
    commands = [event for event in events if event.get("type") == "command"]
    verifications = [event for event in events if event.get("type") == "verification"]
    return {
        "event_count": len(events),
        "first_timestamp": events[0].get("timestamp") if events else None,
        "last_timestamp": events[-1].get("timestamp") if events else None,
        "command_count": len(commands),
        "verification_count": len(verifications),
        "last_event": events[-1] if events else None,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, help="Path to a JSONL journal file.")
    parser.add_argument("--append-json", help="Inline JSON event to append.")
    parser.add_argument("--append-json-file", help="Path to a JSON event file to append.")
    parser.add_argument("--summary", action="store_true", help="Print a journal summary.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if bool(args.append_json) + bool(args.append_json_file) + bool(args.summary) != 1:
        parser.error("Choose exactly one of --append-json, --append-json-file, or --summary.")
    return args


def main() -> int:
    """Append to or summarize a run journal."""
    args = parse_args()
    path = Path(args.journal)
    if args.append_json:
        result = {"success": True, "event": append_event(path, json.loads(args.append_json))}
    elif args.append_json_file:
        result = {"success": True, "event": append_event(path, read_json(Path(args.append_json_file)))}
    else:
        result = {"success": True, "summary": summarize_events(read_events(path))}

    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
