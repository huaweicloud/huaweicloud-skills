#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OBS lifecycle analyzer — the executable entry for huawei-cloud-obs-lifecycle-management.

Implements the 9 skill actions on top of the hcloud obs CLI (obsutil passthrough):

  Query (R3):   list-rules, get-rule, list-objects
  Analyze (R3): diagnose, cost, preview
  Manage:       create-rule (R2), update-rule (R2), delete-rule (R1)

All mutating actions require preview + explicit user confirmation (--apply only
when the user already confirmed through another channel). Credentials are NEVER
hardcoded: the script shells out to `hcloud obs` which reads the obsutil
config / environment.

Quality reporting: automatic telemetry via `skill-quality-cli` (see SKILL.md /
references/cli-installation-guide.md); this script contains no reporting code.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

DEFAULT_PRICES = {
    "standard": 0.099,
    "warm": 0.06,
    "cold": 0.03,
    "deep_archive": 0.014,
}
STORAGE_CLASS_MAP = {"WARM": "warm", "COLD": "cold", "DEEP_ARCHIVE": "deep_archive"}
# obsutil `ls` prints LastModified as ISO-8601 UTC (e.g. 2026-09-21T11:09:13Z).
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")


def _run_hcloud_obs(args: list, timeout: int = 60, ok_codes: tuple = ()) -> str:
    """Run `hcloud obs ...` and return stdout; raises SystemExit on failure."""
    cmd = ["hcloud", "obs"] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        sys.exit("ERROR: hcloud CLI not found — see references/cli-installation-guide.md")
    except subprocess.TimeoutExpired:
        sys.exit("ERROR: hcloud obs timed out")
    if proc.returncode != 0 and proc.returncode not in ok_codes:
        err = (proc.stderr or "").strip() or proc.stdout.strip()
        sys.exit(f"ERROR: command failed ({proc.returncode}): {' '.join(cmd)}\n{err}")
    return proc.stdout


def get_lifecycle_config(bucket: str) -> dict:
    """Fetch the current lifecycle configuration JSON of a bucket."""
    out = _run_hcloud_obs(["lifecycle", f"obs://{bucket}", "-method=get"], ok_codes=(-1, 255))
    if "NoSuchLifecycleConfiguration" in out:
        return {"Rules": []}
    # obsutil prints the JSON (possibly multi-line) plus a trailing
    # "Get lifecycle rules succeed" line; accumulate until the JSON parses.
    lines = out.splitlines()
    for start in range(len(lines)):
        if not lines[start].lstrip().startswith("{"):
            continue
        buf = lines[start]
        for end in range(start + 1, len(lines) + 1):
            try:
                return json.loads(buf)
            except json.JSONDecodeError:
                if end >= len(lines):
                    break
                buf += "\n" + lines[end]
        break
    sys.exit(f"ERROR: could not parse lifecycle config for {bucket} — is the bucket OBS-lifecycle-capable?\n{out}")


def _parse_size(s: str) -> int:
    """Parse obsutil human-readable size (6B, 1.5KB, 3MB, 1GB ...) into bytes."""
    s = (s or "").strip().upper()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        pass
    units = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
    for suffix, mult in sorted(units.items(), key=lambda kv: -len(kv[0])):
        if s.endswith(suffix):
            try:
                return int(float(s[: -len(suffix)]) * mult)
            except ValueError:
                return 0
    return 0


def list_objects(bucket: str, prefix: str = "", limit: int = 1000) -> list:
    """List objects (key, LastModified, size, storage_class) via `hcloud obs ls`.

    Parses the detailed tabular output (no -s) which has columns
    key / LastModified / Size / StorageClass / ETag.

    obsutil wraps long entries: when `obs://bucket/key` exceeds the key column
    width, the full key is printed on one line and the metadata columns appear
    on the FOLLOWING line(s). A single record can therefore span two lines and
    must be reassembled before parsing, otherwise long keys are misread as
    folders (or their key text is garbled into the metadata fields). Metadata
    columns are always taken from the END of the record so object keys that
    contain spaces parse correctly; common-prefix/folder entries (key ending
    with '/', listed by obsutil in the "Folder list" section with no metadata)
    are excluded — they are not real objects and have no age.
    """
    url = f"obs://{bucket}" + (f"/{prefix.lstrip('/')}" if prefix else "")
    out = _run_hcloud_obs(["ls", url, f"-limit={limit}"])
    objects = []
    bucket_prefix = f"obs://{bucket}"

    def emit(key: str, meta: Optional[list] = None) -> None:
        # Folder markers have no metadata and their key ends with '/'.
        if not key or key.endswith("/") or meta is None or _TS_RE.match(str(meta[0])) is None:
            return
        objects.append({"key": key, "size": _parse_size(meta[1]),
                        "last_modified": meta[0], "storage_class": meta[2]})

    header_seen = False
    pending_key = None  # key-only line of a wrapped record, waiting for metadata
    for ln in out.splitlines():
        stripped = ln.strip()
        if not stripped:
            continue
        if "LastModified" in stripped and "Size" in stripped:
            header_seen = True
            continue
        if not header_seen:
            continue
        if stripped.startswith("obs://"):
            # New record: a wrapped record's key line was never completed.
            if pending_key is not None:
                emit(pending_key, None)
                pending_key = None
            parts = stripped.split()
            if len(parts) >= 5 and _TS_RE.match(parts[-4]):
                # Single-line record: key + trailing metadata columns.
                key = " ".join(parts[:-4])[len(bucket_prefix):].lstrip("/")
                emit(key, parts[-4:])
            else:
                # Wrapped record: key line only; metadata is on the next line.
                pending_key = stripped[len(bucket_prefix):].lstrip("/")
        elif pending_key is not None:
            # Metadata continuation line for the pending (wrapped) record.
            parts = stripped.split()
            if len(parts) >= 4 and _TS_RE.match(parts[0]):
                emit(pending_key, parts)
                pending_key = None
    if pending_key is not None:
        emit(pending_key, None)
    return objects


def _parse_ts(s: str):
    """Parse object LastModified into a tz-aware datetime."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None


def _age_days(last_modified: str, now: datetime) -> int:
    ts = _parse_ts(last_modified)
    if ts is None:
        return 0
    return max(0, int((now - ts).total_seconds() // 86400))


def _rule_effective_prefix(rule: dict) -> str:
    """The prefix a rule actually applies to, tolerant of OBS echo quirks.

    OBS echoes rules with a rule-level `Prefix` AND a `Filter.Prefix` field;
    when neither is configured it returns `Filter: {"Prefix": ""}` (an EMPTY
    STRING, not null). An empty Filter.Prefix must be treated as "no prefix at
    the filter level" — it must not shadow the real rule-level Prefix (e.g.
    'data/'), otherwise every rule looks like a bucket-wide (empty-prefix) rule.
    """
    f = rule.get("Filter") or {}
    filter_prefix = f.get("Prefix")
    if filter_prefix:  # non-empty Filter.Prefix is authoritative
        return filter_prefix
    return rule.get("Prefix") or ""


def _rule_actions(rule: dict) -> list:
    """Return a rule's actions as (kind, days, storage_class, date_iso).

    Age-based rules (Expiration.Days / Transitions[].Days) set `days` and keep
    date_iso=None; absolute-date rules (Expiration.Date / Transitions[].Date)
    keep days=None and carry the ISO date in `date_iso` so diagnosis compares
    against the calendar date instead of a truncated day count.
    """
    actions = []
    exp = rule.get("Expiration") or {}
    if exp.get("Days") is not None:
        actions.append(("expire", int(exp["Days"]), None, None))
    elif exp.get("Date"):
        actions.append(("expire", None, None, exp.get("Date")))
    for t in rule.get("Transitions") or []:
        if t.get("Days") is not None:
            actions.append(("transition", int(t["Days"]), t.get("StorageClass", "COLD"), None))
        elif t.get("Date"):
            actions.append(("transition", None, t.get("StorageClass", "COLD"), t.get("Date")))
    return actions


def _action_reached(kind: str, days, date_iso, last_modified: str, now: datetime) -> bool:
    """Whether an object satisfies an action trigger.

    Date-based actions trigger when `now >= date`; age-based actions trigger
    when the object's age is at least `days`.
    """
    if date_iso:
        d = _parse_ts(date_iso)
        return d is not None and now >= d
    return days is not None and _age_days(last_modified, now) >= days


# ---------------------------------------------------------------------------
# Analyze actions
# ---------------------------------------------------------------------------

def diagnose(bucket: str, prefix: str = "", rule_id: str = "", limit: int = 1000) -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    objects = list_objects(bucket, prefix, limit)
    now = datetime.now(timezone.utc)

    findings = []
    if not rules:
        findings.append({"severity": "HIGH", "code": "NO_RULES",
                         "msg": f"Bucket {bucket} has no lifecycle rules at all — no object will ever be expired/transitioned."})

    for rule in rules:
        if rule_id and rule.get("ID") != rule_id:
            continue
        rid = rule.get("ID", "(unnamed)")
        eff_prefix = _rule_effective_prefix(rule)
        if (rule.get("Status") or "Enabled") != "Enabled":
            findings.append({"severity": "HIGH", "code": "RULE_DISABLED", "rule_id": rid,
                             "msg": f"Rule '{rid}' is Disabled — it never takes effect."})
            continue
        if prefix and not eff_prefix.startswith(prefix) and not prefix.startswith(eff_prefix):
            continue  # out of the requested scan scope
        actions = _rule_actions(rule)
        if not actions:
            findings.append({"severity": "MEDIUM", "code": "RULE_NO_ACTION", "rule_id": rid,
                             "msg": f"Rule '{rid}' has no expiration/transition action (only versioning/multipart actions)."})
        matching = [o for o in objects if o["key"].startswith(eff_prefix)]
        eligible = 0
        for o in matching:
            for kind, days, _cls, date_iso in actions:
                # both 'expire' and 'transition' count as eligible once reached
                if _action_reached(kind, days, date_iso, o["last_modified"], now):
                    eligible += 1
                    break
        if matching and eligible == 0:
            findings.append({"severity": "MEDIUM", "code": "AGE_NOT_ELAPSED", "rule_id": rid,
                             "msg": f"Rule '{rid}' (prefix '{eff_prefix}') matches {len(matching)} object(s) but none has reached the configured days — check rule '{rid}' expiration/transition days."})
        if not matching:
            findings.append({"severity": "MEDIUM", "code": "PREFIX_NO_MATCH", "rule_id": rid,
                             "msg": f"Rule '{rid}' prefix '{eff_prefix}' matches no scanned object{' under prefix ' + prefix if prefix else ''} — verify the prefix spelling."})

    # overlapping-prefix heuristic
    enabled = [r for r in rules if (r.get("Status") or "Enabled") == "Enabled"]
    for i, r1 in enumerate(enabled):
        p1 = _rule_effective_prefix(r1)
        for r2 in enabled[i + 1:]:
            p2 = _rule_effective_prefix(r2)
            if p1 and p2 and (p1.startswith(p2) or p2.startswith(p1)):
                findings.append({"severity": "LOW", "code": "PREFIX_OVERLAP",
                                 "msg": f"Rules '{r1.get('ID')}' (prefix '{p1}') and '{r2.get('ID')}' (prefix '{p2}') overlap — first matching rule wins, which can look like a rule 'not working'."})

    return {"bucket": bucket, "rule_count": len(rules), "scanned_objects": len(objects),
            "findings": findings,
            "summary": f"{len(findings)} finding(s); {sum(1 for f in findings if f['severity'] == 'HIGH')} high, {sum(1 for f in findings if f['severity'] == 'MEDIUM')} medium, {sum(1 for f in findings if f['severity'] == 'LOW')} low"}


def cost(bucket: str, prefix: str = "", limit: int = 1000, price_file: str = "") -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    objects = list_objects(bucket, prefix, limit)
    prices = dict(DEFAULT_PRICES)
    if price_file:
        with open(price_file, encoding="utf-8") as fh:
            prices.update(json.load(fh))
    now = datetime.now(timezone.utc)

    total_bytes = sum(o["size"] for o in objects)
    gb = total_bytes / (1024 ** 3)
    rows = []
    current_class = "standard"
    monthly = prices[current_class] * gb
    plan = []
    actionable_bytes = 0
    for rule in rules:
        if (rule.get("Status") or "Enabled") != "Enabled":
            continue
        p = _rule_effective_prefix(rule)
        matching = [o for o in objects if o["key"].startswith(p)]
        for kind, days, cls, date_iso in _rule_actions(rule):
            affected = [o for o in matching if _action_reached(kind, days, date_iso, o["last_modified"], now)]
            affected_gb = sum(o["size"] for o in affected) / (1024 ** 3)
            actionable_bytes += sum(o["size"] for o in affected)
            plan.append({"rule_id": rule.get("ID"), "prefix": p, "action": kind,
                         "days": days, "date": date_iso, "storage_class": cls or "COLD",
                         "affected_objects": len(affected), "affected_gb": round(affected_gb, 3)})
    optimized_monthly = 0.0
    for row in plan:
        cls = STORAGE_CLASS_MAP.get(row.get("storage_class", "COLD"), "cold")
        optimized_monthly += prices[cls] * row["affected_gb"]
    remaining_gb = max(0.0, gb - actionable_bytes / (1024 ** 3))
    optimized_monthly += prices["standard"] * remaining_gb
    return {
        "bucket": bucket, "scanned_objects": len(objects), "total_gb": round(gb, 3),
        "current_monthly_est": round(monthly, 2),
        "optimized_monthly_est": round(optimized_monthly, 2),
        "monthly_savings_est": round(monthly - optimized_monthly, 2),
        "plan": plan,
        "note": "Cost estimation uses a fixed price table (references/lifecycle-rule-format.md); actual billing comes from BSS and varies by region/negotiated price.",
    }


def preview(bucket: str, prefix: str = "", rule_id: str = "", days: int = 0,
            action: str = "", limit: int = 1000) -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    objects = list_objects(bucket, prefix, limit)
    now = datetime.now(timezone.utc)
    results = []
    total = 0
    total_size = 0
    scanned = [o for o in objects if o["key"].startswith(prefix)]

    if rule_id and days == 0 and not action:
        rule = next((r for r in rules if r.get("ID") == rule_id), None)
        if not rule:
            sys.exit(f"ERROR: rule '{rule_id}' not found in bucket {bucket}")
        effective = _rule_effective_prefix(rule)
        useprefix = effective
        input_objects = [o for o in objects if o["key"].startswith(useprefix)]
        for kind, d, cls, date_iso in _rule_actions(rule):
            affected = [o for o in input_objects if _action_reached(kind, d, date_iso, o["last_modified"], now)]
            results.append({"rule_id": rule_id, "prefix": useprefix, "action": kind,
                            "days": d, "date": date_iso, "storage_class": cls or "COLD",
                            "objects": [{"key": o["key"], "age_days": _age_days(o["last_modified"], now)} for o in affected]})
            total += len(affected)
            total_size += sum(o["size"] for o in affected)
    else:
        p = prefix
        d = days
        act = action or "expire"
        affected = [o for o in scanned if _age_days(o["last_modified"], now) >= d]
        results.append({"rule_id": rule_id or "(simulated)", "prefix": p, "action": act,
                        "days": d, "storage_class": "COLD" if act == "transition" else None,
                        "objects": [{"key": o["key"], "age_days": _age_days(o["last_modified"], now)} for o in affected]})
        total = len(affected)
        total_size = sum(o["size"] for o in affected)

    return {"bucket": bucket, "scanned_objects": len(scanned), "affected_objects": total,
            "affected_size_gb": round(total_size / (1024 ** 3), 4), "results": results,
            "note": "Dry-run preview only — no lifecycle configuration was changed."}


# ---------------------------------------------------------------------------
# Manage actions (R2/R1): preview + confirmation gate
# ---------------------------------------------------------------------------

def _confirm(message: str, apply: bool) -> None:
    if apply:
        print(f"[confirm-gate] SKIPPED (--apply provided; user confirmation assumed given elsewhere): {message}")
        return
    print(f"\n⚠️  {message}")
    answer = input("Type 'yes' to continue, anything else to abort: ").strip().lower()
    if answer != "yes":
        sys.exit("Aborted by user.")


def _put_config(bucket: str, cfg: dict) -> None:
    rule_file = f"/tmp/obs_lifecycle_{bucket}.json"
    with open(rule_file, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    out = _run_hcloud_obs(["lifecycle", f"obs://{bucket}", "-method=put", f"-localfile={rule_file}"])
    print(out.strip().splitlines()[-1] if out.strip() else f"put ok for {bucket}")


def _delete_config(bucket: str) -> None:
    """Remove the entire lifecycle configuration.

    OBS rejects an empty rule set — neither ``{"Rules": []}`` nor ``{}`` is
    accepted (400 MalformedXML) — so deleting the LAST rule is done with
    ``-method=delete``, which removes the whole configuration.
    """
    out = _run_hcloud_obs(["lifecycle", f"obs://{bucket}", "-method=delete"])
    print(out.strip().splitlines()[-1] if out.strip() else f"delete ok for {bucket}")


def create_rule(bucket: str, rule_id: str, prefix: str, action: str, days: int,
                storage_class: str = "", apply: bool = False) -> dict:
    if action not in ("expire", "transition"):
        sys.exit("ERROR: --action must be 'expire' or 'transition'")
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    if any(r.get("ID") == rule_id for r in rules):
        sys.exit(f"ERROR: rule ID '{rule_id}' already exists in bucket {bucket} — use update-rule instead")
    pv = preview(bucket, prefix=prefix, days=days, action=action, limit=1000)
    print("[preview] {} object(s), {} GB would be affected".format(pv["affected_objects"], pv["affected_size_gb"]))
    rule = {"ID": rule_id, "Prefix": prefix, "Status": "Enabled"}
    if action == "expire":
        rule["Expiration"] = {"Days": days}
    else:
        rule["Transitions"] = [{"Days": days, "StorageClass": storage_class or "COLD"}]
    new_cfg = {"Rules": rules + [rule]}
    _confirm(f"PUT will REPLACE the whole lifecycle configuration of {bucket} with {len(new_cfg['Rules'])} rule(s). Preview showed {pv['affected_objects']} affected object(s). Proceed?", apply)
    _put_config(bucket, new_cfg)
    return {"action": "create_rule", "rule": rule, "total_rules": len(new_cfg["Rules"]), "bucket": bucket}


def _has_meaningful_expiration(rule: dict) -> bool:
    """True when the rule has a real expiration action.

    OBS echoes an ``Expiration`` object even for transition-only rules (e.g.
    ``{"Days": 0, "Date": "0001-01-01T00:00:00Z", ...}``). A rule counts as
    having an expiration only when Days > 0 or a real (non-zero) Date is set —
    the same semantics ``_rule_actions`` uses.
    """
    exp = rule.get("Expiration")
    if not isinstance(exp, dict):
        return False
    if exp.get("Days"):
        return True
    d = exp.get("Date")
    return bool(d and "0001" not in d)


def update_rule(bucket: str, rule_id: str, prefix: str = "", days: int = 0,
                storage_class: str = "", action: str = "", apply: bool = False) -> dict:
    """Update an existing lifecycle rule (R2 — preview + explicit confirm).

    ``--action`` selects which action to modify:
      - ``expire``     → touch ``Expiration`` only
      - ``transition`` → touch ``Transitions[].Days/StorageClass`` only
    When omitted, the action the rule ALREADY has is updated; a rule with BOTH
    actions requires an explicit ``--action`` (never guess, never add a new
    action type silently).
    """
    if action and action not in ("expire", "transition"):
        sys.exit("ERROR: --action must be 'expire' or 'transition'")
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    rule = next((r for r in rules if r.get("ID") == rule_id), None)
    if not rule:
        sys.exit(f"ERROR: rule '{rule_id}' not found in bucket {bucket}")
    if prefix:
        rule["Prefix"] = prefix
        if rule.get("Filter"):
            rule["Filter"]["Prefix"] = prefix

    has_exp = bool(_has_meaningful_expiration(rule))
    has_trans = bool(rule.get("Transitions"))

    if days > 0:
        if action == "expire":
            # Explicit expiration update — only touch Expiration.
            exp = rule.get("Expiration")
            if exp:
                exp["Days"] = days
            else:
                rule["Expiration"] = {"Days": days}
        elif action == "transition":
            # Explicit transition update — only touch Transitions.
            trans = rule.get("Transitions")
            if trans:
                trans[0]["Days"] = days
            else:
                rule["Transitions"] = [{"Days": days, "StorageClass": storage_class or "COLD"}]
        elif has_trans and not has_exp:
            # Transition-only rule: update the transition days.
            rule["Transitions"][0]["Days"] = days
        elif has_exp and not has_trans:
            # Expiration-only rule: update the expiration days.
            rule["Expiration"]["Days"] = days
        elif has_exp and has_trans:
            # Both actions present — refuse to guess; the caller must choose.
            sys.exit("ERROR: rule has both Expiration and Transitions — pass --action expire or --action transition to select which days to update")
        else:
            # Rule has neither action — do not invent one silently.
            sys.exit("ERROR: rule has no Expiration/Transitions action — pass --action expire or --action transition to add one explicitly")

    if storage_class:
        # StorageClass only makes sense for a transition action; never add a
        # new action type implicitly.
        if action == "transition" or (not action and has_trans):
            if rule.get("Transitions"):
                rule["Transitions"][0]["StorageClass"] = storage_class
        elif action == "expire":
            sys.exit("ERROR: --storage-class is not valid for --action expire")
        else:
            sys.exit("ERROR: rule has no Transitions — cannot update --storage-class")

    eff_prefix = _rule_effective_prefix(rule)
    pv = preview(bucket, prefix=eff_prefix, rule_id=rule_id, limit=1000)
    _confirm(f"Updating rule '{rule_id}' of {bucket}. Preview: {pv['affected_objects']} object(s), {pv['affected_size_gb']} GB would be affected by the updated rule. Proceed?", apply)
    _put_config(bucket, cfg)
    return {"action": "update_rule", "rule_id": rule_id, "rule": rule, "bucket": bucket}


def delete_rule(bucket: str, rule_id: str, apply: bool = False) -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    rule = next((r for r in rules if r.get("ID") == rule_id), None)
    if not rule:
        sys.exit(f"ERROR: rule '{rule_id}' not found in bucket {bucket}")
    remaining = [r for r in rules if r.get("ID") != rule_id]
    _confirm(f"Deleting rule '{rule_id}' from {bucket} is IRREVERSIBLE. {len(rules) - len(remaining)} rule(s) will be removed, {len(remaining)} kept. Proceed?", apply)
    if remaining:
        _put_config(bucket, {"Rules": remaining})
    else:
        # Last rule: OBS rejects {"Rules": []} (400 MalformedXML), so remove
        # the whole lifecycle configuration instead.
        _delete_config(bucket)
    return {"action": "delete_rule", "rule_id": rule_id, "removed": True, "remaining_rules": len(remaining), "bucket": bucket}


# ---------------------------------------------------------------------------
# Query actions
# ---------------------------------------------------------------------------

def list_rules(bucket: str) -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    return {"bucket": bucket, "rule_count": len(rules), "rules": rules}


def get_rule(bucket: str, rule_id: str) -> dict:
    cfg = get_lifecycle_config(bucket)
    rules = cfg.get("Rules") or []
    rule = next((r for r in rules if r.get("ID") == rule_id), None)
    if not rule:
        sys.exit(f"ERROR: rule '{rule_id}' not found in bucket {bucket}")
    return {"bucket": bucket, "rule": rule}


def list_objects_action(bucket: str, prefix: str = "", limit: int = 1000) -> dict:
    objects = list_objects(bucket, prefix, limit)
    return {"bucket": bucket, "prefix": prefix, "object_count": len(objects), "objects": objects}


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OBS lifecycle analyzer (huawei-cloud-obs-lifecycle-management)")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (("list-rules", "list lifecycle rules (R3)"), ("get-rule", "get one rule (R3)"),
                            ("list-objects", "list objects (R3)"), ("diagnose", "diagnose ineffective rules (R3)"),
                            ("cost", "lifecycle cost analysis (R3)"), ("preview", "dry-run preview (R3)"),
                            ("create-rule", "create lifecycle rule (R2)"), ("update-rule", "update lifecycle rule (R2)"),
                            ("delete-rule", "delete lifecycle rule (R1)")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--bucket", required=True)
        p.add_argument("--prefix", default="")
        p.add_argument("--rule-id", default="")
        p.add_argument("--days", type=int, default=0)
        p.add_argument("--action", choices=["expire", "transition"], default="")
        p.add_argument("--storage-class", default="")
        p.add_argument("--limit", type=int, default=1000)
        p.add_argument("--price-file", default="")
        p.add_argument("--apply", action="store_true",
                       help="skip the interactive confirmation (only after user confirmation was given elsewhere)")

    args = parser.parse_args()
    cmd = args.command
    if cmd == "list-rules":
        result = list_rules(args.bucket)
    elif cmd == "get-rule":
        result = get_rule(args.bucket, args.rule_id)
    elif cmd == "list-objects":
        result = list_objects_action(args.bucket, args.prefix, args.limit)
    elif cmd == "diagnose":
        result = diagnose(args.bucket, args.prefix, args.rule_id, args.limit)
    elif cmd == "cost":
        result = cost(args.bucket, args.prefix, args.limit, args.price_file)
    elif cmd == "preview":
        result = preview(args.bucket, args.prefix, args.rule_id, args.days, args.action, args.limit)
    elif cmd == "create-rule":
        result = create_rule(args.bucket, args.rule_id, args.prefix, args.action, args.days, args.storage_class, args.apply)
    elif cmd == "update-rule":
        result = update_rule(args.bucket, args.rule_id, args.prefix, args.days, args.storage_class, args.action, args.apply)
    elif cmd == "delete-rule":
        result = delete_rule(args.bucket, args.rule_id, args.apply)
    else:
        parser.error(f"unknown command {cmd}")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())