#!/usr/bin/env python3
"""Generate a reviewable LeRobot manifest draft from a local ROS bag."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bag2manifest.manifest import (
    build_manifest,
    default_choices,
    manifest_to_yaml,
    validate_manifest,
)
from bag2manifest.profiler import ProfileOptions, profile_bag
from summarize_profile import make_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="+", help="Bag directory, .mcap, .db3, .zip, or split bag files")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--msg-dir", action="append", default=[], help="Custom .msg/.idl definitions for db3")
    parser.add_argument("--max-seconds", type=float, default=0, help="Quick inspection of the first N seconds")
    parser.add_argument("--choices", type=Path, help="JSON object overriding default mapping choices")
    parser.add_argument("--confirm-action", action="store_true",
                        help="Confirm the suggested action topic after reviewing other candidates")
    parser.add_argument("--repo-id", help="LeRobot repository ID")
    parser.add_argument("--bag-glob", help="Batch input file pattern for source.bag_glob")
    parser.add_argument("--task-text", help="Constant episode task description")
    args = parser.parse_args()

    profile = profile_bag(
        args.input[0] if len(args.input) == 1 else args.input,
        ProfileOptions(max_seconds=args.max_seconds, msg_dirs=args.msg_dir),
    )
    defaults = default_choices(profile)
    choices = dict(defaults)
    overrides = {}
    if args.choices:
        overrides = json.loads(args.choices.read_text(encoding="utf-8"))
        if not isinstance(overrides, dict):
            parser.error("--choices must contain a JSON object")
        choices.update(overrides)
    if args.repo_id is not None:
        choices["repo_id"] = args.repo_id
    if args.bag_glob is not None:
        choices["bag_glob"] = args.bag_glob
    if args.task_text is not None:
        choices.update(task_mode="const", task_text=args.task_text)

    plan = build_manifest(profile, choices)
    validation = validate_manifest(plan, profile)
    source_issues = profile.get("issues", [])
    unresolved = []
    for issue in source_issues:
        if issue.get("level") != "error":
            continue
        code = issue.get("code")
        if code == "E021" and (args.confirm_action or choices["action"] != defaults["action"]
                               or choices["action_strategy"] != defaults["action_strategy"]):
            continue
        if code == "E022" and choices["state"] and choices["state"] != defaults["state"]:
            continue
        if code in ("E013", "E014", "E015"):
            # validate_manifest checks selected cameras and required message definitions.
            continue
        unresolved.append(issue)
    errors = unresolved + [i for i in validation if i.get("level") == "error"]

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "choices.json").write_text(
        json.dumps(choices, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "manifest.yaml").write_text(manifest_to_yaml(plan), encoding="utf-8")
    report = {"source": source_issues, "validation": validation, "unresolved_errors": errors}
    (args.output / "issues.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "summary.md").write_text(
        make_summary(profile, choices, report), encoding="utf-8")
    print(f"Wrote profile.json, choices.json, manifest.yaml, issues.json, summary.md to {args.output}")
    if errors:
        print("Draft needs review: " + ", ".join(str(i.get("code")) for i in errors))
        return 2
    print("Validation passed; review warnings and sampled data before conversion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
