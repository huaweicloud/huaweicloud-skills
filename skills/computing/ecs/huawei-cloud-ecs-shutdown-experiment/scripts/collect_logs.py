#!/usr/bin/env python3
"""
collect_logs.py — Collect logs from LTS, query ECS instance endpoints,
and check the LTS log-collection pipeline (ICagent → host group →
access config → log data).

Queries Huawei Cloud LTS for logs within the experiment time window, fetches
endpoint info (private IP / DNS / EIP) of target ECS instances, and verifies
that the LTS collection chain is actually producing data before trusting any
log query result. Outputs structured log data.

Usage:
    python3 collect_logs.py --start-time "2026-09-08T10:00:00Z" --end-time "2026-09-08T10:10:00Z" --log-group-id xxx
    python3 collect_logs.py --start-time ... --end-time ... --log-group-id xxx --keywords ERROR
    python3 collect_logs.py --check-pipeline --instance-ids i-xxx,i-yyy --start-time ... --end-time ... [--log-group-id xxx --log-stream-id yyy]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def iso_to_epoch_ms(ts_str):
    """Convert ISO 8601 timestamp to epoch milliseconds."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return 0


# hcloud CLI authenticates via its own config file (~/.hcloud/config.default),
# not via AK/SK env vars — scripts do not read or pass sensitive data.


def _build_env(region=None):
    """Build a minimal environment dict with only needed variables."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": os.environ.get("LANG", ""),
        "LC_ALL": os.environ.get("LC_ALL", ""),
    }
    region_val = os.environ.get("HW_REGION_NAME")
    if region:
        env["HW_REGION_NAME"] = region
    elif region_val:
        env["HW_REGION_NAME"] = region_val
    return env


def _normalize_kccli_args(args):
    """Normalize ['--flag', value] pairs to ['--flag=value'].

    KooCLI 7.2.x rejects space-separated flags with [USE_ERROR] (e.g.
    '参数xxx的格式错误,正确格式为:--param=value'). This was the root cause of
    silently empty API results (dependency endpoints, LTS logs). Flags already
    in --flag=value form and bare flags are passed through untouched.
    """
    out = []
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and "=" not in a and i + 1 < len(args) and not args[i + 1].startswith("--"):
            out.append(f"{a}={args[i + 1]}")
            i += 2
        else:
            out.append(a)
            i += 1
    return out


def run_hcloud(args, region=None):
    """Run hcloud CLI command and return (success, parsed_json_or_stderr)."""
    args = _normalize_kccli_args(args)
    cmd = ["hcloud"] + args
    if region and "--cli-region" not in args:
        cmd.append(f"--cli-region={region}")
    env = _build_env(region)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=120
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        output = result.stdout.strip()
        try:
            return True, json.loads(output)
        except json.JSONDecodeError:
            for i in range(len(output)):
                if output[i] in "[{":
                    try:
                        return True, json.loads(output[i:])
                    except json.JSONDecodeError:
                        continue
            return True, {"raw": output}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def collect_lts_logs(log_group_id, log_stream_id, start_time, end_time,
                     keywords=None, region=None, stream_name="", stream_type=""):
    """Query LTS logs within the specified time window (single API call)."""
    start_ms = iso_to_epoch_ms(start_time)
    end_ms = iso_to_epoch_ms(end_time)

    # LTS ListLogs: log_group_id / log_stream_id are path params (CLI flags);
    # start_time / end_time / keywords are body params (CLI flags).
    command = ["LTS", "ListLogs", "--cli-output=json",
               "--log_group_id", log_group_id]
    if log_stream_id:
        command += ["--log_stream_id", log_stream_id]
    command += ["--start_time", str(start_ms), "--end_time", str(end_ms)]
    if keywords:
        command += ["--keywords", keywords]

    success, data = run_hcloud(command, region=region)

    if not success:
        return {"source": "lts", "success": False, "error": str(data), "logs": []}

    # Parse log entries locally (no per-entry network calls)
    logs = []
    if isinstance(data, dict):
        log_list = data.get("logs", data.get("items", data.get("results", [])))
    elif isinstance(data, list):
        log_list = data
    else:
        log_list = []

    for entry in log_list:
        if isinstance(entry, dict):
            logs.append({
                "timestamp": entry.get("timestamp", entry.get("@timestamp", "")),
                "level": entry.get("level", entry.get("severity", "")),
                "message": entry.get("message", entry.get("content", entry.get("log", ""))),
                "source": "lts",
            })
        elif isinstance(entry, str):
            logs.append({"timestamp": "", "level": "", "message": entry, "source": "lts"})

    return {
        "source": "lts",
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "stream_name": stream_name,
        "stream_type": stream_type,
        "success": True,
        "count": len(logs),
        "logs": logs,
    }


def get_instance_endpoints(instance_ids, region):
    """Get private IP, private DNS, and EIP for each ECS instance.
    Uses a single batch API call for all instances, then processes locally.
    """
    if not instance_ids:
        return {}

    # ListServersDetails is a GET operation: no --body.
    # Filter by target IDs via query param --server_id (comma-separated, max 100).
    success, data = run_hcloud(
        ["ECS", "ListServersDetails", "--cli-output=json",
         "--server_id", ",".join(instance_ids)],
        region=region
    )
    if not success or data is None:
        return {}

    if isinstance(data, dict):
        servers = data.get("servers", data.get("items", []))
    elif isinstance(data, list):
        servers = data
    else:
        servers = []

    # Process all servers locally (no per-server network calls)
    endpoints = {}
    for srv in servers:
        sid = srv.get("id", "")
        info = {
            "id": sid,
            "name": srv.get("name", ""),
            "private_ips": [],
            "private_dns": srv.get("metadata", {}).get("__system__name", ""),
            "eip": "",
        }
        # Extract private IPs from addresses (local processing)
        addresses = srv.get("addresses", {})
        for net_name, addr_list in addresses.items():
            if isinstance(addr_list, list):
                for addr in addr_list:
                    if isinstance(addr, dict):
                        ip = addr.get("addr", "")
                        addr_type = addr.get("OS-EXT-IPS:type", "")
                        if addr_type == "fixed":
                            info["private_ips"].append(ip)
                        elif addr_type == "floating":
                            info["eip"] = ip
        endpoints[sid] = info

    return endpoints


# ---------------------------------------------------------------------------
# LTS collection pipeline checks.
#
# Gate philosophy (from real incident): a 0-log LTS query result is NOT proof
# that "the app was unaffected" — it usually means the collection chain is
# broken somewhere. Before trusting/quoting any LTS log count, verify the whole
# chain: ICAgent installed & running → host group bound → access config exists
# → log data actually present. If ANY gate fails, stop digging into LTS logs
# and report "application behavior unobserved" instead.
#
# Gates:
#   1. icagent_running   — LTS ListHost: a host entry whose host_id == ECS
#                          instance ID must have host_status == "running"
#   2. host_group_binding— LTS ListHostGroup: at least one group must contain
#                          the instance ID in host_id_list
#   3. access_config     — LTS ListAccessConfig: at least one config must exist
#                          targeting the instance's host group (or the given
#                          log group/stream). NOTE: ListAccessConfig with NO
#                          filter params can return empty even when configs
#                          exist — always query filtered by host group name or
#                          log group name.
#   4. log_data          — LTS ListLogHistogram: count > 0 in the window
# ---------------------------------------------------------------------------


def check_icagent_running(instance_ids, region=None):
    """Gate 1: ICAgent installed and running on target instances.

    Queries LTS ListHost once, filters locally by host_id == ECS instance ID.
    """
    target_set = set(instance_ids or [])
    if not target_set:
        return {"gate": "icagent_running", "passed": False, "checked": False,
                "message": "No target instances to check"}

    success, data = run_hcloud(["LTS", "ListHost", "--cli-output=json"], region=region)
    if not success or not isinstance(data, dict):
        return {"gate": "icagent_running", "passed": False, "checked": False,
                "message": f"ListHost query failed: {data}"}

    hosts = data.get("result", []) or []
    matches = [h for h in hosts if h.get("host_id") in target_set]
    running = [h for h in matches if h.get("host_status") == "running"]

    if not matches:
        return {"gate": "icagent_running", "passed": False, "checked": True,
                "message": f"ICAent not registered in LTS for instances {sorted(target_set)} — likely not installed",
                "hosts": []}
    if not running:
        statuses = {h.get("host_id"): h.get("host_status") for h in matches}
        return {"gate": "icagent_running", "passed": False, "checked": True,
                "message": f"ICAent registered but not running: {statuses}",
                "hosts": matches}
    return {"gate": "icagent_running", "passed": True, "checked": True,
            "message": f"ICAent running for {len(running)} target instance(s)",
            "hosts": running}


def check_host_group_binding(instance_ids, region=None):
    """Gate 2: at least one LTS host group contains the target instance."""
    target_set = set(instance_ids or [])
    if not target_set:
        return {"gate": "host_group_binding", "passed": False, "checked": False,
                "message": "No target instances to check"}

    success, data = run_hcloud(["LTS", "ListHostGroup", "--cli-output=json"], region=region)
    if not success or not isinstance(data, dict):
        return {"gate": "host_group_binding", "passed": False, "checked": False,
                "message": f"ListHostGroup query failed: {data}"}

    groups = data.get("result", []) or []
    bound = []
    for g in groups:
        ids = g.get("host_id_list", []) or []
        hit = [iid for iid in target_set if iid in ids]
        if hit:
            bound.append({"host_group_id": g.get("host_group_id"),
                          "host_group_name": g.get("host_group_name"),
                          "bound_instance_ids": hit})

    if not bound:
        return {"gate": "host_group_binding", "passed": False, "checked": True,
                "message": f"No LTS host group contains instance(s) {sorted(target_set)}",
                "host_groups": []}
    names = ", ".join(b["host_group_name"] for b in bound)
    return {"gate": "host_group_binding", "passed": True, "checked": True,
            "message": f"Instance(s) bound to host group(s): {names}",
            "host_groups": bound}


def check_access_config(host_group_names=None, log_group_id=None,
                        log_stream_id=None, region=None):
    """Gate 3: at least one access config targets the instance's host group
    (or the given log group/stream).

    CRITICAL: ListAccessConfig with NO filter params can return total=0 even
    when configs exist (observed in production). Always filter by host group
    name and/or log group name, never trust an unfiltered call.
    """
    command = ["LTS", "ListAccessConfig", "--cli-output=json"]

    # Filter by host group names if known (array param, numbered form)
    added_filter = False
    for i, name in enumerate(host_group_names or [], 1):
        command.append(f"--host_group_name_list.{i}={name}")
        added_filter = True

    success, data = run_hcloud(command, region=region)
    if not success or not isinstance(data, dict):
        return {"gate": "access_config", "passed": False, "checked": False,
                "message": f"ListAccessConfig query failed: {data}", "configs": []}

    configs = data.get("result", []) or []
    total = data.get("total", len(configs))

    # Match locally: config must reference the given log group/stream if provided
    candidates = []
    for c in configs:
        log_info = c.get("log_info", {}) or {}
        c_group_id = log_info.get("log_group_id")
        c_stream_id = log_info.get("log_stream_id")
        c_paths = (c.get("access_config_detail", {}) or {}).get("paths", []) or []
        if log_group_id and c_group_id and c_group_id != log_group_id:
            continue
        if log_stream_id and c_stream_id and c_stream_id != log_stream_id:
            continue
        candidates.append({
            "access_config_id": c.get("access_config_id"),
            "access_config_name": c.get("access_config_name"),
            "log_group_id": c_group_id,
            "log_stream_id": c_stream_id,
            "paths": c_paths,
        })

    if not candidates:
        return {"gate": "access_config", "passed": False, "checked": True,
                "message": (f"No access config found (filtered={added_filter}, "
                            f"api_total={total}, matched={len(candidates)})"),
                "configs": []}
    names = ", ".join(c["access_config_name"] for c in candidates)
    return {"gate": "access_config", "passed": True, "checked": True,
            "message": f"Access config(s) exist: {names}",
            "configs": candidates}


def _find_lts_system_stream(region=None):
    """Auto-discover the built-in lts-system log group and an active stream.

    The lts-system group is created by Huawei Cloud for every account. We list
    its streams and pick the first one. Returns (group_id, stream_id) or
    (None, None) if not found.
    """
    # The lts-system group name is constant across accounts; find its ID.
    ok, data = run_hcloud(
        ["LTS", "ListLogGroups", "--cli-output=json"],
        region=region
    )
    if not ok or not isinstance(data, dict):
        return None, None
    groups = data.get("log_groups", [])
    sys_group_id = None
    for g in groups:
        if g.get("log_group_name") == "lts-system":
            sys_group_id = g.get("log_group_id")
            break
    if not sys_group_id:
        return None, None

    # List streams under lts-system, pick the first active one.
    ok2, data2 = run_hcloud(
        ["LTS", "ListLogStreams", "--cli-output=json",
         "--group_id", sys_group_id],
        region=region
    )
    if not ok2 or not isinstance(data2, dict):
        return sys_group_id, None
    streams = data2.get("log_streams", [])
    if streams:
        return sys_group_id, streams[0].get("log_stream_id")
    return sys_group_id, None


def check_log_data(log_group_id, log_stream_id, start_time, end_time,
                   region=None, keywords=None,
                   cross_check_group=None, cross_check_stream=None):
    """Gate 4: log data actually present in the target group/stream.

    Uses ListLogHistogram (count over the whole window). A count of 0 means no
    log ever entered the stream — cross-check with a known-working stream to
    prove the query chain works before blaming the collection side.

    If cross_check_group/stream are not provided, auto-discovers the built-in
    lts-system log group and its first stream. If discovery fails, cross-check
    is skipped (reported as n/a).
    """
    if not log_group_id or not log_stream_id:
        return {"gate": "log_data", "passed": False, "checked": False,
                "message": "log_group_id/log_stream_id required for log-data check",
                "count": 0, "cross_check": None}

    start_ms = iso_to_epoch_ms(start_time)
    end_ms = iso_to_epoch_ms(end_time)

    command = ["LTS", "ListLogHistogram", "--cli-output=json",
               "--group_id", log_group_id, "--stream_id", log_stream_id,
               "--start_time", str(start_ms), "--end_time", str(end_ms),
               "--step_interval", str(max(3600000, (end_ms - start_ms) // 5)),
               "--key_word", keywords or ""]

    success, data = run_hcloud(command, region=region)
    if not success or not isinstance(data, dict):
        return {"gate": "log_data", "passed": False, "checked": False,
                "message": f"ListLogHistogram query failed: {data}", "count": 0,
                "cross_check": None}

    count = data.get("count", 0)

    # Cross-check the query chain against a known-active LTS system stream.
    # If cross_check_group/stream are not provided, auto-discover lts-system.
    cross_check = None
    if count == 0:
        if not cross_check_group or not cross_check_stream:
            cc_group, cc_stream = _find_lts_system_stream(region=region)
            cross_check_group = cross_check_group or cc_group
            cross_check_stream = cross_check_stream or cc_stream

        if cross_check_group and cross_check_stream:
            x_ok, x_data = run_hcloud(
                ["LTS", "ListLogHistogram", "--cli-output=json",
                 "--group_id", cross_check_group,
                 "--stream_id", cross_check_stream,
                 "--start_time", str(start_ms), "--end_time", str(end_ms),
                 "--step_interval", str(max(3600000, (end_ms - start_ms) // 5)),
                 "--key_word", ""],
                region=region
            )
            if x_ok and isinstance(x_data, dict):
                cross_check = {"stream": f"lts-system/{cross_check_stream}",
                               "count": x_data.get("count", 0)}
        else:
            cross_check = {"stream": "lts-system (auto-discovery failed)",
                           "count": "n/a"}

    if count == 0:
        ck = f" (cross-check lts-system count={cross_check['count'] if cross_check else 'n/a'})"
        return {"gate": "log_data", "passed": False, "checked": True,
                "message": f"No log data in window (count=0){ck}",
                "count": 0, "cross_check": cross_check}
    return {"gate": "log_data", "passed": True, "checked": True,
            "message": f"Log data present (count={count})",
            "count": count, "cross_check": cross_check}


def check_lts_pipeline(instance_ids, start_time, end_time,
                       log_group_id=None, log_stream_id=None,
                       cross_check_group=None, cross_check_stream=None,
                       region=None, keywords=None):
    """Run the full LTS collection-chain check.

    Returns a dict with per-gate results plus an overall verdict.
    `chain_ok` is True only if ALL gates pass. When chain_ok is False, a 0-log
    LTS query result MUST be reported as "application behavior unobserved",
    not "application unaffected".

    Also returns detected host group names so the caller can query access
    configs with the correct filter.
    """
    gates = []
    host_group_names = []

    # Gate 1: ICAgent running
    g1 = check_icagent_running(instance_ids, region)
    gates.append(g1)

    # Gate 2: host group binding
    g2 = check_host_group_binding(instance_ids, region)
    gates.append(g2)
    if g2.get("host_groups"):
        host_group_names = [g["host_group_name"] for g in g2["host_groups"]]

    # Gate 3: access config (only meaningful if host group exists)
    if g2.get("passed") or host_group_names:
        g3 = check_access_config(host_group_names=host_group_names,
                                 log_group_id=log_group_id,
                                 log_stream_id=log_stream_id,
                                 region=region)
    else:
        g3 = {"gate": "access_config", "passed": False, "checked": False,
              "message": "Skipped: no host group binding", "configs": []}
    gates.append(g3)

    # Gate 4: log data (needs a concrete group/stream; derive if not given)
    target_group = log_group_id
    target_stream = log_stream_id
    if (not target_group or not target_stream) and g3.get("configs"):
        cfg = g3["configs"][0]
        target_group = target_group or cfg.get("log_group_id")
        target_stream = target_stream or cfg.get("log_stream_id")

    if g3.get("passed") and target_group and target_stream:
        g4 = check_log_data(target_group, target_stream, start_time, end_time,
                            region, keywords,
                            cross_check_group=cross_check_group,
                            cross_check_stream=cross_check_stream)
    elif g3.get("checked") and not g3.get("passed"):
        g4 = {"gate": "log_data", "passed": False, "checked": False,
              "message": "Skipped: no access config → nothing to query",
              "count": 0, "cross_check": None}
    else:
        g4 = {"gate": "log_data", "passed": False, "checked": False,
              "message": "Skipped: missing group/stream", "count": 0,
              "cross_check": None}
    gates.append(g4)

    chain_ok = all(g.get("passed") for g in gates if g.get("checked", True))

    return {
        "chain_ok": chain_ok,
        "gates": gates,
        "host_group_names": host_group_names,
        "log_group_id": target_group,
        "log_stream_id": target_stream,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect logs from LTS during experiment, query ECS endpoints, "
                    "and check the LTS collection pipeline."
    )
    parser.add_argument("--start-time", required=True, help="Start time (ISO 8601)")
    parser.add_argument("--end-time", required=True, help="End time (ISO 8601)")
    parser.add_argument("--cli-region", dest="region",
                        default=os.environ.get("HW_REGION_NAME", "cn-north-4"),
                        help="Huawei Cloud region (e.g. cn-north-4)")

    # LTS options
    parser.add_argument("--log-group-id", help="LTS log group ID")
    parser.add_argument("--log-stream-id", help="LTS log stream ID (single, backward compatible)")
    parser.add_argument("--log-stream-ids", help="Comma-separated LTS stream IDs (queried with --keywords)")
    parser.add_argument("--keywords", help="Log search keywords (e.g., ERROR)")
    parser.add_argument("--cross-check-group", dest="cross_check_group",
                        help="LTS group ID for cross-check (auto-discovers lts-system if omitted)")
    parser.add_argument("--cross-check-stream", dest="cross_check_stream",
                        help="LTS stream ID for cross-check (auto-discovers first lts-system stream if omitted)")

    # Pipeline check options
    parser.add_argument("--check-pipeline", action="store_true",
                        help="Run LTS collection-chain checks (4 gates) and print verdict")
    parser.add_argument("--instance-ids", help="Comma-separated ECS instance IDs "
                                               "(required with --check-pipeline)")

    parser.add_argument("--output-file", help="Write result to file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    results = {
        "start_time": args.start_time,
        "end_time": args.end_time,
        "collected_at": now_iso(),
        "sources": [],
    }

    # Pipeline checks (LTS collection chain)
    if args.check_pipeline:
        print("Checking LTS collection pipeline ...")
        if args.dry_run:
            print("  [DRY RUN] Skipping pipeline checks")
            results["lts_pipeline"] = {"chain_ok": True, "dry_run": True,
                                       "gates": [],
                                       "host_group_names": []}
        else:
            instance_ids = [s.strip() for s in (args.instance_ids or "").split(",") if s.strip()]
            if not instance_ids:
                print("Error: --instance-ids is required with --check-pipeline",
                      file=sys.stderr)
                sys.exit(1)
            pipeline = check_lts_pipeline(
                instance_ids, args.start_time, args.end_time,
                log_group_id=args.log_group_id,
                log_stream_id=args.log_stream_id,
                region=args.region, keywords=args.keywords,
                cross_check_group=getattr(args, "cross_check_group", None),
                cross_check_stream=getattr(args, "cross_check_stream", None)
            )
            results["lts_pipeline"] = pipeline
            print(f"  chain_ok={pipeline['chain_ok']}")
            for g in pipeline["gates"]:
                mark = "PASS" if g.get("passed") else ("SKIP" if not g.get("checked") else "FAIL")
                print(f"  [{mark}] {g['gate']}: {g.get('message','')}")

    # Collect LTS logs (one API call per stream)
    if args.log_group_id:
        stream_ids = []
        if args.log_stream_id:
            stream_ids.append(args.log_stream_id)
        for s in (args.log_stream_ids or "").split(","):
            s = s.strip()
            if s and s not in stream_ids:
                stream_ids.append(s)

        if args.dry_run:
            for sid in (stream_ids or [None]):
                print(f"[DRY RUN] Would query LTS {args.log_group_id} "
                      f"stream={sid or '(none)'} keywords={args.keywords}")
                results["sources"].append({
                    "source": "lts", "log_group_id": args.log_group_id,
                    "log_stream_id": sid, "keywords": args.keywords,
                    "success": True, "count": 0, "logs": [], "dry_run": True
                })
        else:
            print(f"Querying LTS logs from group {args.log_group_id} ...")
            if stream_ids:
                for sid in stream_ids:
                    lts_result = collect_lts_logs(
                        args.log_group_id, sid,
                        args.start_time, args.end_time,
                        args.keywords, args.region
                    )
                    print(f"  stream {sid}: {lts_result.get('count', 0)} entries "
                          f"(keywords={args.keywords})")
                    results["sources"].append(lts_result)
            else:
                lts_result = collect_lts_logs(
                    args.log_group_id, None,
                    args.start_time, args.end_time,
                    args.keywords, args.region
                )
                print(f"  Collected {lts_result.get('count', 0)} log entries")
                results["sources"].append(lts_result)

    if not args.log_group_id and not args.check_pipeline:
        print("Warning: no log source specified. Use --log-group-id or --check-pipeline.")

    output = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output_file:
        with open(args.output_file, "w") as f:
            f.write(output)
        print(f"\nResult written to {args.output_file}")
    else:
        print(f"\n{output}")


if __name__ == "__main__":
    main()
