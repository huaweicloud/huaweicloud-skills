#!/usr/bin/env python3
"""
Regression tests for global option positioning (FLEXUS2-ISSUE-004).

Verifies that global options (--region/--dry-run/--confirm/--ak/--sk/
--security-token) are honored when written BEFORE the subcommand as well as
AFTER it:

    python3 flexus_lifecycle.py --dry-run unsubscribe --resource-ids <id>
    python3 flexus_lifecycle.py unsubscribe --resource-ids <id> --dry-run

The regression: global options written before the subcommand were silently
reset to their default values because the global options were registered on
both the root parser and every subcommand parser. The script now registers
global options only on the root parser and merges post-subcommand globals via
parse_known_args.

Run:
    python3 scripts/test_global_options_position.py
Exit code 0 = all tests pass.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flexus_lifecycle as fl

PASS = 0
FAIL = 0


def check(name, argv, expected):
    global PASS, FAIL
    try:
        args = fl.parse_cli_args(argv)
        actual = {k: getattr(args, k, None) for k in expected}
        if actual == expected:
            PASS += 1
            print(f"[PASS] {name}")
        else:
            FAIL += 1
            print(f"[FAIL] {name}\n  argv={argv}\n  expected={expected} got={actual}")
    except SystemExit as e:
        FAIL += 1
        print(f"[FAIL] {name}\n  argv={argv}\n  unexpected SystemExit({e})")
    except Exception:
        FAIL += 1
        print(f"[FAIL] {name}\n  argv={argv}\n  exception:\n{traceback.format_exc()}")


def all_checks(expected):
    return {k: expected[k] for k in ("region", "dry_run", "confirm", "command")}


# --- Global option BEFORE subcommand (前置写法) ---
check("region before: --region cn-east-3 show-images",
      ["--region", "cn-east-3", "show-images"],
      all_checks({"region": "cn-east-3", "dry_run": False, "confirm": False, "command": "show-images"}))

check("region before: --region=cn-east-3 show-images",
      ["--region=cn-east-3", "show-images"],
      all_checks({"region": "cn-east-3", "dry_run": False, "confirm": False, "command": "show-images"}))

check("dry-run before: --dry-run unsubscribe",
      ["--dry-run", "unsubscribe", "--resource-ids", "r-1"],
      all_checks({"region": "cn-north-4", "dry_run": True, "confirm": False, "command": "unsubscribe"}))

check("confirm before: --confirm unsubscribe",
      ["--confirm", "unsubscribe", "--resource-ids", "r-1"],
      all_checks({"region": "cn-north-4", "dry_run": False, "confirm": True, "command": "unsubscribe"}))

check("combined before: --region cn-east-3 --dry-run create-instance",
      ["--region", "cn-east-3", "--dry-run", "create-instance"],
      all_checks({"region": "cn-east-3", "dry_run": True, "confirm": False, "command": "create-instance"}))

# --- Global option AFTER subcommand (后置写法, must keep working) ---
check("region after: show-images --region cn-east-3",
      ["show-images", "--region", "cn-east-3"],
      all_checks({"region": "cn-east-3", "dry_run": False, "confirm": False, "command": "show-images"}))

check("dry-run after: unsubscribe --dry-run",
      ["unsubscribe", "--dry-run", "--resource-ids", "r-1"],
      all_checks({"region": "cn-north-4", "dry_run": True, "confirm": False, "command": "unsubscribe"}))

check("confirm after: unsubscribe --resource-ids r-1 --confirm",
      ["unsubscribe", "--resource-ids", "r-1", "--confirm"],
      all_checks({"region": "cn-north-4", "dry_run": False, "confirm": True, "command": "unsubscribe"}))

check("mixed: --region cn-east-3 show-images --dry-run",
      ["--region", "cn-east-3", "show-images", "--dry-run"],
      all_checks({"region": "cn-east-3", "dry_run": True, "confirm": False, "command": "show-images"}))

# --- Defaults preserved when global options are absent ---
check("no globals: show-images",
      ["show-images"],
      all_checks({"region": "cn-north-4", "dry_run": False, "confirm": False, "command": "show-images"}))

# --- Credentials still parsed in both positions (--ak/--sk) ---
check("ak/sk before", ["--ak", "AK", "--sk", "SK", "unsubscribe", "--resource-ids", "r-1"],
      {"ak": "AK", "sk": "SK", "region": "cn-north-4", "dry_run": False, "confirm": False, "command": "unsubscribe"})
check("ak/sk after", ["unsubscribe", "--resource-ids", "r-1", "--ak", "AK", "--sk", "SK"],
      {"ak": "AK", "sk": "SK", "region": "cn-north-4", "dry_run": False, "confirm": False, "command": "unsubscribe"})


print(f"\n=== Summary: {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL else 0)