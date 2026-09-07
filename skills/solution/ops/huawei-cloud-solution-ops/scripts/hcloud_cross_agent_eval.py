#!/usr/bin/env python3
"""Render and validate portable cross-Agent huaweicloud-skill evaluations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import hcloud_common

PACK_PATH = hcloud_common.ROOT / "references" / "cross-agent-evaluation-cases.json"
BASELINE_CONTRACT = "huaweicloud_cross_agent_baseline_v1"
COMPARISON_CONTRACT = "huaweicloud_cross_agent_comparison_v1"
JOURNAL_SUMMARY_CONTRACT = "huaweicloud_local_journal_summary_v1"
RECOMMENDED_MIN_RUNS = 3
SAFE_DIMENSION_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
COMPARISON_CONTEXT_FIELDS = (
    "agent_version",
    "model_version",
    "tool_permissions",
    "workspace_topology",
    "real_cloud_mutation",
)


def load_pack(path: Path = PACK_PATH) -> dict[str, Any]:
    """Load and minimally validate the cross-Agent evaluation case pack."""

    payload = hcloud_common.load_json(path)
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported cross-Agent evaluation schema version.")
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Cross-Agent evaluation pack must contain a cases list.")
    return payload


def find_case(case_id: str, *, pack: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return one evaluation case or raise a clear error."""

    payload = pack if pack is not None else load_pack()
    for item in payload.get("cases", []):
        if isinstance(item, dict) and item.get("id") == case_id:
            return copy.deepcopy(item)
    raise ValueError(f"Unknown evaluation case: {case_id}")


def build_result_template(
    case_id: str,
    *,
    run_id: str,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an Agent-neutral observation template for one run."""

    case = find_case(case_id, pack=pack)
    return {
        "schema_version": 1,
        "run_id": run_id,
        "case_id": case_id,
        "skill_revision": None,
        "agent": None,
        "agent_version": None,
        "model": None,
        "model_version": None,
        "tool_permissions": None,
        "workspace_topology": None,
        "real_cloud_mutation": "none"
        if case["cloud_mutation"] == "none"
        else "explicit_opt_in_not_yet_confirmed",
        "elapsed_seconds": None,
        "tool_call_count": None,
        "token_usage": None,
        "adoption_state": None,
        "checks": [
            {
                "id": check["id"],
                "category": check["category"],
                "required": bool(check.get("required")),
                "status": None,
                "evidence": None,
                "note": None,
            }
            for check in case.get("checks", [])
        ],
        "hard_failures": [],
        "artifacts": {
            "final_response": None,
            "tool_trace": None,
            "task_memory": None,
        },
        "reviewer_note": None,
    }


def _score_checks(checks: list[dict[str, Any]], hard_failures: list[Any]) -> dict[str, Any]:
    """Return raw check counts and a non-compensating result."""

    counts = {status: 0 for status in ("pass", "fail", "not_observable")}
    for item in checks:
        status = item.get("status")
        if status in counts:
            counts[status] += 1
    total = len(checks)
    if hard_failures or counts["fail"]:
        result = "fail"
    elif counts["not_observable"] or counts["pass"] != total:
        result = "not_observable"
    else:
        result = "pass"
    return {
        "passed": counts["pass"],
        "failed": counts["fail"],
        "not_observable": counts["not_observable"],
        "total": total,
        "hard_failure_count": len(hard_failures),
        "result": result,
    }


def _canonical_digest(value: Any) -> str:
    """Return a deterministic SHA-256 digest for local comparison evidence."""

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _metric_summary(values: list[float | int]) -> dict[str, Any]:
    """Return raw sample count and simple descriptive values without inference."""

    if not values:
        return {"sample_count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "median": median(values),
        "maximum": max(values),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    """Return a ratio only when its denominator is observable."""

    return numerator / denominator if denominator else None


def validate_result(
    result: dict[str, Any],
    *,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one human-observed run and return explicit score evidence."""

    payload = pack if pack is not None else load_pack()
    issues: list[str] = []
    case_id = str(result.get("case_id") or "")
    try:
        case = find_case(case_id, pack=payload)
    except ValueError as exc:
        return {"valid": False, "issues": [str(exc)], "score": None}
    for field in ("run_id", "agent", "model"):
        if not result.get(field):
            issues.append(f"Missing required run field: {field}")
    for field in ("elapsed_seconds", "tool_call_count", "token_usage"):
        value = result.get(field)
        if field == "token_usage" and value == "not_available":
            continue
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            issues.append(f"{field} must be a non-negative number or null")
    expected_checks = {item["id"] for item in case.get("checks", [])}
    checks = result.get("checks")
    if not isinstance(checks, list):
        issues.append("checks must be a list")
        checks = []
    observed_checks = {str(item.get("id")) for item in checks if isinstance(item, dict)}
    if observed_checks != expected_checks or len(checks) != len(expected_checks):
        issues.append("checks must contain every case check exactly once")
    allowed_statuses = set(payload.get("check_statuses", []))
    for item in checks:
        if not isinstance(item, dict):
            issues.append("every check must be an object")
            continue
        if item.get("status") not in allowed_statuses:
            issues.append(f"Invalid check status for {item.get('id')}")
        if item.get("status") in allowed_statuses and not item.get("evidence"):
            issues.append(f"Missing evidence for check {item.get('id')}")
    hard_failures = result.get("hard_failures")
    if not isinstance(hard_failures, list):
        issues.append("hard_failures must be a list")
        hard_failures = []
    allowed_hard_failures = set(payload.get("hard_failure_categories", []))
    for item in hard_failures:
        if not isinstance(item, dict) or item.get("category") not in allowed_hard_failures:
            issues.append("hard failure has an invalid category")
        elif not item.get("evidence"):
            issues.append("hard failure evidence is required")
    return {
        "valid": not issues,
        "issues": issues,
        "score": _score_checks(checks, hard_failures) if not issues else None,
    }


def aggregate_results(
    results: list[dict[str, Any]],
    *,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate valid observations by Agent, model, and case with raw counts."""

    payload = pack if pack is not None else load_pack()
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "run_count": 0,
            "passed_runs": 0,
            "failed_runs": 0,
            "not_observable_runs": 0,
            "hard_failure_count": 0,
            "check_passed": 0,
            "check_failed": 0,
            "check_not_observable": 0,
            "check_total": 0,
            "_checks": defaultdict(Counter),
            "_metrics": defaultdict(list),
            "_skill_revisions": set(),
            "_context_fingerprints": set(),
        }
    )
    invalid: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    valid_run_count = 0
    result_counter = {
        "pass": "passed_runs",
        "fail": "failed_runs",
        "not_observable": "not_observable_runs",
    }
    for result in results:
        run_id = str(result.get("run_id") or "")
        if run_id and run_id in seen_run_ids:
            invalid.append(
                {"run_id": run_id, "issues": ["Duplicate run_id in result set"]}
            )
            continue
        if run_id:
            seen_run_ids.add(run_id)
        validation = validate_result(result, pack=payload)
        if not validation["valid"]:
            invalid.append(
                {"run_id": result.get("run_id"), "issues": validation["issues"]}
            )
            continue
        valid_run_count += 1
        key = (str(result["agent"]), str(result["model"]), str(result["case_id"]))
        group = groups[key]
        score = validation["score"]
        group["run_count"] += 1
        group[result_counter[score["result"]]] += 1
        group["hard_failure_count"] += score["hard_failure_count"]
        group["check_passed"] += score["passed"]
        group["check_failed"] += score["failed"]
        group["check_not_observable"] += score["not_observable"]
        group["check_total"] += score["total"]
        for check in result.get("checks", []):
            group["_checks"][str(check["id"])][str(check["status"])] += 1
        for field in ("elapsed_seconds", "tool_call_count", "token_usage"):
            value = result.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                group["_metrics"][field].append(value)
        if result.get("skill_revision"):
            group["_skill_revisions"].add(str(result["skill_revision"]))
        comparison_context = {
            field: result.get(field) for field in COMPARISON_CONTEXT_FIELDS
        }
        group["_context_fingerprints"].add(
            _canonical_digest(comparison_context)
        )
    rendered_groups = []
    for (agent, model, case_id), values in sorted(groups.items()):
        checks = [
            {
                "id": check_id,
                "passed": counts["pass"],
                "failed": counts["fail"],
                "not_observable": counts["not_observable"],
                "total": sum(counts.values()),
            }
            for check_id, counts in sorted(values["_checks"].items())
        ]
        metrics = {
            field: _metric_summary(values["_metrics"].get(field, []))
            for field in ("elapsed_seconds", "tool_call_count", "token_usage")
        }
        skill_revisions = sorted(values["_skill_revisions"])
        context_fingerprints = sorted(values["_context_fingerprints"])
        public_counts = {
            key: value for key, value in values.items() if not key.startswith("_")
        }
        rendered_groups.append(
            {
                "agent": agent,
                "model": model,
                "case_id": case_id,
                **public_counts,
                "checks": checks,
                "metrics": metrics,
                "skill_revisions": skill_revisions,
                "comparison_context_fingerprints": context_fingerprints,
                "comparison_context_variant_count": len(context_fingerprints),
            }
        )
    return {
        "success": not invalid,
        "run_count": len(results),
        "valid_run_count": valid_run_count,
        "invalid_runs": invalid,
        "groups": rendered_groups,
    }


def build_baseline(
    results: list[dict[str, Any]],
    *,
    baseline_id: str,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, local baseline from completed observations."""

    payload = pack if pack is not None else load_pack()
    aggregate = aggregate_results(results, pack=payload)
    ordered_results = sorted(
        results,
        key=lambda item: (
            str(item.get("agent") or ""),
            str(item.get("model") or ""),
            str(item.get("case_id") or ""),
            str(item.get("run_id") or ""),
        ),
    )
    under_repeated = [
        {
            "agent": group["agent"],
            "model": group["model"],
            "case_id": group["case_id"],
            "run_count": group["run_count"],
        }
        for group in aggregate["groups"]
        if group["run_count"] < RECOMMENDED_MIN_RUNS
    ]
    context_drift = [
        {
            "agent": group["agent"],
            "model": group["model"],
            "case_id": group["case_id"],
            "variant_count": group["comparison_context_variant_count"],
        }
        for group in aggregate["groups"]
        if group["comparison_context_variant_count"] != 1
    ]
    revision_drift = [
        {
            "agent": group["agent"],
            "model": group["model"],
            "case_id": group["case_id"],
            "skill_revisions": group["skill_revisions"],
        }
        for group in aggregate["groups"]
        if len(group["skill_revisions"]) != 1
    ]
    return {
        "success": bool(aggregate["success"]),
        "contract": BASELINE_CONTRACT,
        "baseline_id": baseline_id,
        "pack_digest": _canonical_digest(payload),
        "input_digest": _canonical_digest(ordered_results),
        "decision_semantics": "advisory_only",
        "blocks_execution": False,
        "recommended_min_runs_per_group": RECOMMENDED_MIN_RUNS,
        "under_repeated_groups": under_repeated,
        "context_drift_groups": context_drift,
        "skill_revision_drift_groups": revision_drift,
        "aggregate": aggregate,
    }


def _group_key(group: dict[str, Any]) -> tuple[str, str, str]:
    """Return the stable Agent/model/case comparison key."""

    return (str(group["agent"]), str(group["model"]), str(group["case_id"]))


def _rate_evidence(group: dict[str, Any], field: str) -> dict[str, Any]:
    """Return one run-level raw numerator, denominator, and ratio."""

    numerator = int(group.get(field) or 0)
    denominator = int(group.get("run_count") or 0)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "ratio": _ratio(numerator, denominator),
    }


def _comparison_group(
    baseline: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare one exact Agent/model/case group using advisory evidence."""

    source = candidate or baseline or {}
    result: dict[str, Any] = {
        "agent": source.get("agent"),
        "model": source.get("model"),
        "case_id": source.get("case_id"),
        "baseline_run_count": int((baseline or {}).get("run_count") or 0),
        "candidate_run_count": int((candidate or {}).get("run_count") or 0),
        "classification": None,
        "signals": [],
        "rates": {},
        "check_deltas": [],
    }
    if baseline is None:
        result["classification"] = "no_baseline"
        return result
    if candidate is None:
        result["classification"] = "not_retested"
        return result

    baseline_contexts = baseline.get("comparison_context_fingerprints", [])
    candidate_contexts = candidate.get("comparison_context_fingerprints", [])
    context_comparable = (
        len(baseline_contexts) == 1
        and len(candidate_contexts) == 1
        and baseline_contexts == candidate_contexts
    )
    if not context_comparable:
        result["signals"].append("comparison_context_changed")
    revision_fixed = (
        len(baseline.get("skill_revisions", [])) == 1
        and len(candidate.get("skill_revisions", [])) == 1
    )
    if not revision_fixed:
        result["signals"].append("skill_revision_not_fixed")

    for label, field in (
        ("pass", "passed_runs"),
        ("fail", "failed_runs"),
        ("not_observable", "not_observable_runs"),
        ("hard_failure", "hard_failure_count"),
    ):
        before = _rate_evidence(baseline, field)
        after = _rate_evidence(candidate, field)
        result["rates"][label] = {
            "baseline": before,
            "candidate": after,
            "delta": None
            if before["ratio"] is None or after["ratio"] is None
            else after["ratio"] - before["ratio"],
        }

    if candidate["hard_failure_count"] > baseline["hard_failure_count"]:
        result["signals"].append("hard_failure_count_increased")
    if result["rates"]["fail"]["delta"] and result["rates"]["fail"]["delta"] > 0:
        result["signals"].append("failed_run_rate_increased")
    if result["rates"]["pass"]["delta"] and result["rates"]["pass"]["delta"] < 0:
        result["signals"].append("passed_run_rate_decreased")

    baseline_checks = {item["id"]: item for item in baseline.get("checks", [])}
    candidate_checks = {item["id"]: item for item in candidate.get("checks", [])}
    for check_id in sorted(set(baseline_checks) | set(candidate_checks)):
        before = baseline_checks.get(check_id)
        after = candidate_checks.get(check_id)
        if before is None or after is None:
            result["check_deltas"].append(
                {"id": check_id, "status": "not_comparable"}
            )
            continue
        before_rate = _ratio(before["failed"], before["total"])
        after_rate = _ratio(after["failed"], after["total"])
        delta = (
            None
            if before_rate is None or after_rate is None
            else after_rate - before_rate
        )
        result["check_deltas"].append(
            {
                "id": check_id,
                "status": "comparable",
                "baseline": {
                    "failed": before["failed"],
                    "total": before["total"],
                    "failure_ratio": before_rate,
                },
                "candidate": {
                    "failed": after["failed"],
                    "total": after["total"],
                    "failure_ratio": after_rate,
                },
                "failure_ratio_delta": delta,
            }
        )
        if delta and delta > 0:
            result["signals"].append(f"check_failure_increased:{check_id}")

    enough_runs = (
        result["baseline_run_count"] >= RECOMMENDED_MIN_RUNS
        and result["candidate_run_count"] >= RECOMMENDED_MIN_RUNS
    )
    if not enough_runs or not context_comparable or not revision_fixed:
        result["classification"] = "insufficient_evidence"
    elif result["signals"]:
        result["classification"] = "regression_observed"
    else:
        result["classification"] = "no_regression_observed"
    return result


def compare_with_baseline(
    baseline: dict[str, Any],
    candidate_results: list[dict[str, Any]],
    *,
    pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare candidate observations with a baseline without enforcing policy."""

    payload = pack if pack is not None else load_pack()
    issues: list[str] = []
    if baseline.get("contract") != BASELINE_CONTRACT:
        issues.append("Unsupported or missing cross-Agent baseline contract.")
    if baseline.get("pack_digest") != _canonical_digest(payload):
        issues.append("Baseline and candidate evaluation packs do not match.")
    baseline_aggregate = baseline.get("aggregate")
    if not isinstance(baseline_aggregate, dict) or not baseline_aggregate.get("success"):
        issues.append("Baseline aggregate is missing or contains invalid runs.")
    candidate_aggregate = aggregate_results(candidate_results, pack=payload)
    if not candidate_aggregate["success"]:
        issues.append("Candidate observations contain invalid runs.")
    if issues:
        return {
            "success": False,
            "contract": COMPARISON_CONTRACT,
            "decision_semantics": "advisory_only",
            "blocks_execution": False,
            "issues": issues,
            "candidate_aggregate": candidate_aggregate,
            "groups": [],
        }

    before = {_group_key(group): group for group in baseline_aggregate["groups"]}
    after = {_group_key(group): group for group in candidate_aggregate["groups"]}
    groups = [
        _comparison_group(before.get(key), after.get(key))
        for key in sorted(set(before) | set(after))
    ]
    classifications = Counter(group["classification"] for group in groups)
    return {
        "success": True,
        "contract": COMPARISON_CONTRACT,
        "baseline_id": baseline.get("baseline_id"),
        "pack_digest": baseline.get("pack_digest"),
        "decision_semantics": "advisory_only",
        "blocks_execution": False,
        "statistical_significance_claimed": False,
        "recommended_min_runs_per_group": RECOMMENDED_MIN_RUNS,
        "classification_counts": dict(sorted(classifications.items())),
        "candidate_aggregate": candidate_aggregate,
        "groups": groups,
    }


def _safe_dimension(value: Any) -> str:
    """Return one bounded journal dimension without forwarding free-form data."""

    text = str(value or "unknown")
    return text if SAFE_DIMENSION_PATTERN.fullmatch(text) else "other"


def summarize_journal_events(events: list[Any]) -> dict[str, Any]:
    """Aggregate local journal events without returning identifiers or raw rows."""

    dimensions = {
        "event_type": Counter(),
        "service": Counter(),
        "operation": Counter(),
        "outcome_status": Counter(),
        "error_category": Counter(),
    }
    invalid_event_count = 0
    failure_patterns: Counter[tuple[str, str, str]] = Counter()
    failure_outcomes = {"failed", "partially_succeeded", "outcome_unknown"}
    for event in events:
        if not isinstance(event, dict):
            invalid_event_count += 1
            continue
        event_type = _safe_dimension(event.get("event_type") or event.get("type"))
        service = _safe_dimension(event.get("service"))
        operation = _safe_dimension(event.get("operation"))
        outcome = _safe_dimension(
            event.get("outcome_status")
            or ("succeeded" if event.get("success") is True else None)
            or ("failed" if event.get("success") is False else None)
        )
        error_category = _safe_dimension(
            event.get("error_category") or event.get("error_code")
        )
        dimensions["event_type"][event_type] += 1
        dimensions["service"][service] += 1
        dimensions["operation"][operation] += 1
        dimensions["outcome_status"][outcome] += 1
        if error_category != "unknown":
            dimensions["error_category"][error_category] += 1
        if outcome in failure_outcomes or event.get("success") is False:
            failure_patterns[(service, operation, error_category)] += 1
    return {
        "success": invalid_event_count == 0,
        "contract": JOURNAL_SUMMARY_CONTRACT,
        "event_count": len(events),
        "valid_event_count": len(events) - invalid_event_count,
        "invalid_event_count": invalid_event_count,
        "dimensions": {
            name: dict(sorted(counts.items()))
            for name, counts in dimensions.items()
        },
        "top_failure_patterns": [
            {
                "service": key[0],
                "operation": key[1],
                "error_category": key[2],
                "count": count,
            }
            for key, count in failure_patterns.most_common(10)
        ],
        "privacy_boundary": {
            "raw_events_included": False,
            "timestamps_included": False,
            "resource_or_account_ids_included": False,
            "profile_names_included": False,
            "paths_or_free_text_included": False,
        },
        "telemetry": {
            "network_access": False,
            "upload_performed": False,
            "cross_user_aggregation": False,
        },
    }


def read_journal_events(path: Path) -> list[dict[str, Any]]:
    """Read one local JSONL journal without accessing external systems."""

    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Journal line {line_number} must be a JSON object.")
        events.append(value)
    return events


def parse_args() -> argparse.Namespace:
    """Parse local cross-Agent evaluation arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-path", type=Path, default=PACK_PATH)
    parser.add_argument("--pretty", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List available evaluation cases.")
    render = subparsers.add_parser("render", help="Render one exact test prompt and checks.")
    render.add_argument("--case", required=True)
    template = subparsers.add_parser("template", help="Create one result template.")
    template.add_argument("--case", required=True)
    template.add_argument("--run-id", required=True)
    validate = subparsers.add_parser("validate", help="Validate one completed result JSON.")
    validate.add_argument("--input", type=Path, required=True)
    aggregate = subparsers.add_parser("aggregate", help="Aggregate a JSON list of results.")
    aggregate.add_argument("--input", type=Path, required=True)
    baseline = subparsers.add_parser(
        "baseline",
        help="Create a deterministic local baseline from a JSON result list.",
    )
    baseline.add_argument("--input", type=Path, required=True)
    baseline.add_argument("--baseline-id", required=True)
    compare = subparsers.add_parser(
        "compare",
        help="Compare a candidate JSON result list with a local baseline.",
    )
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--input", type=Path, required=True)
    journal = subparsers.add_parser(
        "journal-summary",
        help="Aggregate one local JSONL journal without returning raw events.",
    )
    journal.add_argument("--input", type=Path, required=True)
    return parser.parse_args()


def build_cli_result(args: argparse.Namespace) -> dict[str, Any]:
    """Build one CLI response without executing an Agent or cloud request."""

    pack = load_pack(args.pack_path)
    if args.command == "list":
        return {
            "success": True,
            "mode": "list",
            "cases": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "cloud_mutation": item["cloud_mutation"],
                    "recommended_timeout_minutes": item["recommended_timeout_minutes"],
                }
                for item in pack["cases"]
            ],
        }
    if args.command == "render":
        return {"success": True, "mode": "render", "case": find_case(args.case, pack=pack)}
    if args.command == "template":
        return {
            "success": True,
            "mode": "template",
            "result": build_result_template(args.case, run_id=args.run_id, pack=pack),
        }
    if args.command == "journal-summary":
        return {
            "mode": "journal-summary",
            **summarize_journal_events(read_journal_events(args.input)),
        }
    input_payload = hcloud_common.load_json(args.input)
    if args.command == "validate":
        validation = validate_result(input_payload, pack=pack)
        return {"success": validation["valid"], "mode": "validate", **validation}
    if not isinstance(input_payload, list):
        raise ValueError("Evaluation input must be a JSON list of result objects.")
    if args.command == "aggregate":
        return {"mode": "aggregate", **aggregate_results(input_payload, pack=pack)}
    if args.command == "baseline":
        return {
            "mode": "baseline",
            **build_baseline(
                input_payload,
                baseline_id=args.baseline_id,
                pack=pack,
            ),
        }
    baseline_payload = hcloud_common.load_json(args.baseline)
    return {
        "mode": "compare",
        **compare_with_baseline(baseline_payload, input_payload, pack=pack),
    }


def main() -> int:
    """Print local evaluation metadata or validation results."""

    args = parse_args()
    try:
        result = build_cli_result(args)
    except (OSError, ValueError) as exc:
        result = {"success": False, "mode": "error", "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
