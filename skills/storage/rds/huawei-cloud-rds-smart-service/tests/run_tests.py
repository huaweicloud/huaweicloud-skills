#!/usr/bin/env python3
"""RDS Smart Service - Test Runner

Executes test cases defined in test_cases.json and reports results.
Usage: python3 run_tests.py [--instance_id=xxx] [--category=basic_qa] [--dry-run]
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEST_CASES_FILE = os.path.join(SCRIPT_DIR, "test_cases.json")


def load_test_cases():
    """Load test cases from JSON file."""
    with open(TEST_CASES_FILE, "r") as f:
        return json.load(f)


def run_test_case(test_case, instance_id=None, dry_run=False):
    """Execute a single test case."""
    result = {
        "id": test_case["id"],
        "name": test_case["name"],
        "category": test_case["category"],
        "status": "PENDING",
        "duration_ms": 0,
        "error": None,
    }

    # Substitute instance_id placeholder
    command = test_case["command"]
    if instance_id:
        command = command.replace("${INSTANCE_ID}", instance_id)

    # Check if instance_id is required but not provided
    if test_case.get("requires_instance") and not instance_id:
        result["status"] = "SKIPPED"
        result["error"] = "Requires INSTANCE_ID but none provided"
        return result

    # Check confirmation for mutating operations
    if test_case.get("requires_confirmation"):
        if dry_run:
            result["status"] = "SKIPPED"
            result["error"] = "Mutating operation skipped in dry-run mode"
            return result
        print(f"\n  ⚠️  MUTATING OPERATION: {test_case['name']}")
        confirm = input("  Confirm execution? (yes/no): ").strip().lower()
        if confirm != "yes":
            result["status"] = "SKIPPED"
            result["error"] = "User declined confirmation"
            return result

    if dry_run:
        result["status"] = "DRY_RUN"
        result["command"] = command
        return result

    # Execute command
    start_time = time.time()
    try:
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        elapsed = (time.time() - start_time) * 1000
        result["duration_ms"] = round(elapsed, 2)

        if process.returncode == 0:
            result["status"] = "PASS"
            result["output"] = process.stdout[:500]  # Truncate for readability
        else:
            result["status"] = "FAIL"
            result["error"] = process.stderr[:500] if process.stderr else "Unknown error"
            result["output"] = process.stdout[:500]
    except subprocess.TimeoutExpired:
        result["status"] = "TIMEOUT"
        result["error"] = "Command timed out after 60 seconds"
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def main():
    instance_id = None
    category_filter = None
    dry_run = False

    for arg in sys.argv[1:]:
        if arg.startswith("--instance_id="):
            instance_id = arg.split("=", 1)[1]
        elif arg.startswith("--category="):
            category_filter = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry_run = True

    test_data = load_test_cases()
    test_cases = test_data["test_cases"]

    if category_filter:
        test_cases = [tc for tc in test_cases if tc["category"] == category_filter]

    print(f"{'='*60}")
    print(f"RDS Smart Service - Test Runner")
    print(f"{'='*60}")
    print(f"Total test cases: {len(test_cases)}")
    print(f"Instance ID: {instance_id or 'Not provided'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    if category_filter:
        print(f"Category filter: {category_filter}")
    print(f"{'='*60}\n")

    results = []
    for tc in test_cases:
        print(f"[{tc['id']}] {tc['name']} ({tc['category']})")
        result = run_test_case(tc, instance_id, dry_run)
        results.append(result)

        status_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "SKIP": "⏭️",
            "TIMEOUT": "⏱️",
            "ERROR": "💥",
            "DRY_RUN": "📝",
        }.get(result["status"], "❓")

        print(f"  {status_icon} {result['status']}", end="")
        if result.get("duration_ms"):
            print(f" ({result['duration_ms']}ms)", end="")
        if result.get("error"):
            print(f" - {result['error']}", end="")
        print()

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"  Total: {len(results)}")

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "instance_id": instance_id,
        "dry_run": dry_run,
        "results": results,
        "summary": status_counts,
    }
    report_file = os.path.join(SCRIPT_DIR, "test_results.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to: {report_file}")

    # Exit code
    failed = status_counts.get("FAIL", 0) + status_counts.get("ERROR", 0)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
