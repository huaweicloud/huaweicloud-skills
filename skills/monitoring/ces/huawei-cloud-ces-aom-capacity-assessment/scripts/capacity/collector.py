"""Monitoring data collection module: collects monitoring data through hcloud (KooCLI).

Two data backends (decided by metrics.json entry["backend"], default ces):
- backend="ces": calls hcloud CES BatchListMetricData (the original path, filter=max)
- backend="aom": calls hcloud AOM ListSample (AOM 2.0, statistics=maximum,
  used for CCE and other cloud-native metrics)

Boundary: only collects and formats data, no capacity computation, no Excel writes.

Key points:
- Cross-day time windows are split by day boundaries, called day by day
- Peak/valley extraction (the two backends share the same semantics): peak = max(collected values), valley = min(collected values)
  CES uses filter=max to get datapoints.max; AOM uses statistics=maximum to get each point's maximum
- from/to are millisecond timestamps
- Batching: CES can carry multiple metrics per call (max 500); AOM ListSample samples must not exceed 20
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from typing import Any, Optional


class CollectError(Exception):
    pass


# ---------------------------------------------------------------------------
# CES backend (hcloud CES BatchListMetricData)
# ---------------------------------------------------------------------------
def _dims_key(dimensions: Optional[list[dict[str, Any]]]) -> frozenset:
    """Order-insensitive identity of a dimension list, used to match responses to requests.

    Cloud APIs may reorder dimensions (CES returns them alphabetically), so comparing
    dimension lists element by element produced false mismatches for 2+ dimension metrics.
    """
    return frozenset((str(d.get("name") or ""), str(d.get("value") or ""))
                     for d in dimensions or [])


def build_metric_args(specs: list[dict[str, Any]]) -> list[str]:
    """Convert a batch of metric specs into KooCLI --metrics.N.* arguments.

    spec: {"namespace": str, "metric_name": str, "dimensions": [{"name","value"}, ...]}
    """
    args = []
    for i, m in enumerate(specs, start=1):
        args += [f"--metrics.{i}.namespace={m['namespace']}",
                 f"--metrics.{i}.metric_name={m['metric_name']}"]
        for j, d in enumerate(m.get("dimensions", []), start=1):
            args += [f"--metrics.{i}.dimensions.{j}.name={d['name']}",
                     f"--metrics.{i}.dimensions.{j}.value={d['value']}"]
    return args

def gen_windows(start: datetime, end: datetime, tz) -> list[tuple[datetime, datetime]]:
    """Split [start, end] by day boundaries, returning [(day_start, day_end), ...] (inclusive).

    Naive times are interpreted in the regional timezone tz (mainland China cn-* is UTC+8).
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=tz)
    if end.tzinfo is None:
        end = end.replace(tzinfo=tz)
    cur = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
    windows = []
    while cur <= end_day:
        ws = max(cur, start)
        we = min(cur + timedelta(days=1) - timedelta(seconds=1), end)
        if we >= ws:
            windows.append((ws, we))
        cur += timedelta(days=1)
    return windows


def call_batch(region: str, specs: list[dict[str, Any]],
               from_ms: int, to_ms: int, period: int = 300,
               filter_agg: str = "max",
               hcloud: str = "hcloud", endpoint: Optional[str] = None,
               timeout: int = 120) -> list[dict[str, Any]]:
    """Call hcloud CES BatchListMetricData; returns metric results in request order."""
    cmd = [hcloud, "CES", "BatchListMetricData", f"--cli-region={region}"]
    cmd += build_metric_args(specs)
    cmd += [f"--from={from_ms}", f"--to={to_ms}",
            f"--period={period}", f"--filter={filter_agg}", "--cli-output=json"]
    if endpoint:
        cmd.append(f"--cli-endpoint={endpoint}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise CollectError(f"hcloud (KooCLI) executable not found: {hcloud!r}; install it first or pass --hcloud")
    if proc.returncode != 0:
        raise CollectError(f"hcloud call failed (exit={proc.returncode}): {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except Exception:
        raise CollectError(f"hcloud returned non-JSON: {proc.stdout[:300]}")
    if "metrics" not in data:
        raise CollectError(f"hcloud returned unexpected: {json.dumps(data, ensure_ascii=False)[:300]}")
    # Align the response to request order (match namespace+metric_name+dimensions).
    # CES reorders the dimensions of the returned metric (alphabetically), so the match must
    # compare the dimension name/value pairs as an unordered set — comparing the ordered name
    # list left every multi-dimension request (e.g. DCS node-level metrics) unmatched.
    out: list[dict[str, Any]] = []
    for req in specs:
        hit = None
        req_key = _dims_key(req.get("dimensions"))
        for m in data.get("metrics") or []:
            if (m.get("namespace") == req["namespace"]
                    and m.get("metric_name") == req["metric_name"]
                    and _dims_key(m.get("dimensions")) == req_key):
                hit = m
                break
        if hit is None:
            out.append({"req": req, "datapoints": [], "error": "返回中未找到该指标"})
        else:
            out.append({"req": req, "datapoints": hit.get("datapoints") or [],
                        "unit": hit.get("unit", "")})
    return out


# ---------------------------------------------------------------------------
# AOM backend (hcloud AOM ListSample)
#
# Corresponding AOM API: POST /v2/{project_id}/samples (query time series, ListSample)
# Input: samples[].namespace/metric_name/dimensions, period(60/300/900/3600),
#        statistics[](maximum/minimum/sum/average/sampleCount),
#        time_range(startMs.endMs.durationInMinutes), query.fill_value
# Response: samples[].sample{namespace,metric_name,dimensions} +
#           samples[].data_points[]{timestamp,unit,statistics[]{statistic,value}}
# ---------------------------------------------------------------------------
def build_aom_args(specs: list[dict[str, Any]], from_ms: int, to_ms: int,
                   period: int = 300, statistics: tuple[str, ...] = ("maximum",)) -> list[str]:
    """Convert one or more metric specs into hcloud AOM ListSample arguments.

    The spec structure is identical to CES: {"namespace","metric_name","dimensions":[{"name","value"}]}.
    Note: AOM ListSample accepts at most 20 samples per request.
    """
    duration_min = max(1, int((to_ms - from_ms) / 60000))
    time_range = f"{from_ms}.{to_ms}.{duration_min}"
    args = []
    for i, m in enumerate(specs, start=1):
        args += [f"--samples.{i}.namespace={m['namespace']}",
                 f"--samples.{i}.metric_name={m['metric_name']}"]
        for j, d in enumerate(m.get("dimensions", []), start=1):
            args += [f"--samples.{i}.dimensions.{j}.name={d['name']}",
                     f"--samples.{i}.dimensions.{j}.value={d['value']}"]
    args += [f"--period={period}"]
    for k, s in enumerate(statistics, start=1):
        args += [f"--statistics.{k}={s}"]
    args += [f"--time_range={time_range}", "--fill_value=null", "--cli-output=json"]
    # fill_value=null: AOM returns null at breakpoints (not -1/0 placeholders), naturally skipped during
    # parsing, avoiding treating placeholder values as real data (false success).
    return args


def _match_aom_sample(sample: dict[str, Any], req: dict[str, Any]) -> bool:
    """Match an AOM response sample against a request spec by namespace+metric_name+dimension names."""
    s = sample.get("sample") or sample
    if s.get("namespace") != req["namespace"]:
        return False
    if s.get("metric_name") != req["metric_name"]:
        return False
    return _dims_key(s.get("dimensions")) == _dims_key(req.get("dimensions"))


def _extract_statistic(data_points: list[dict[str, Any]], statistic: str) -> list[float]:
    """Extract the numeric series of the given statistic (e.g. maximum) from AOM data_points."""
    vals = []
    for dp in data_points or []:
        for st in dp.get("statistics", []) or []:
            if st.get("statistic") == statistic:
                try:
                    vals.append(float(st["value"]))
                except (TypeError, ValueError, KeyError):
                    continue
    return vals


def call_aom_batch(region: str, specs: list[dict[str, Any]],
                   from_ms: int, to_ms: int, period: int = 300,
                   statistic: str = "maximum",
                   hcloud: str = "hcloud", endpoint: Optional[str] = None,
                   timeout: int = 120) -> list[dict[str, Any]]:
    """Call hcloud AOM ListSample; returns metric results in request order.

    Return structure is identical to call_batch (CES):
    [{"req": spec, "datapoints": [{"timestamp": ms, "max": value, ...}], "unit": str}]
    where "max" is the value of the specified statistic (named max on the CES side too),
    so the upper peak/valley extraction does not need to know the backend difference.
    """
    cmd = [hcloud, "AOM", "ListSample", f"--cli-region={region}"]
    cmd += build_aom_args(specs, from_ms, to_ms, period=period, statistics=(statistic,))
    if endpoint:
        cmd.append(f"--cli-endpoint={endpoint}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise CollectError(f"hcloud (KooCLI) executable not found: {hcloud!r}; install it first or pass --hcloud")
    if proc.returncode != 0:
        raise CollectError(f"hcloud call failed (exit={proc.returncode}): {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
    except Exception:
        raise CollectError(f"hcloud returned non-JSON: {proc.stdout[:300]}")
    if "samples" not in data:
        raise CollectError(f"hcloud returned unexpected: {json.dumps(data, ensure_ascii=False)[:300]}")
    out: list[dict[str, Any]] = []
    for req in specs:
        hit = None
        for s in data.get("samples") or []:
            if _match_aom_sample(s, req):
                hit = s
                break
        if hit is None:
            out.append({"req": req, "datapoints": [], "error": "返回中未找到该指标"})
            continue
        dps = []
        unit = ""
        for dp in hit.get("data_points", []) or []:
            ts = dp.get("timestamp")
            vals = _extract_statistic([dp], statistic)
            if vals:
                if not unit:
                    _u = str(dp.get("unit") or "").strip()
                    if _u and _u.lower() not in ("unknown", "none"):
                        unit = _u
                dps.append({"timestamp": ts, "max": vals[0]})
        out.append({"req": req, "datapoints": dps, "unit": unit})
    return out


# ---------------------------------------------------------------------------
# Collection entry points (routed by backend)
# ---------------------------------------------------------------------------
def _aggregate_days(results: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    """Aggregate per-day batch results into peak/valley + per-day details (shared by both backends).

    results: [{"day": "YYYY-MM-DD", "batch": {"req","datapoints","unit","error"}}]
    datapoints are normalized to [{"timestamp","max"}, ...]; peak=max(max), valley=min(max).
    """
    total = 0
    dates = []
    day_peaks: list[float] = []
    day_valleys: list[float] = []
    ces_unit = ""
    for r in results:
        dps = r["batch"].get("datapoints", []) or []
        if r["batch"].get("error") and not dps:
            return {"ok": False, "spec": spec, "error": r["batch"]["error"]}
        vals = [float(dp["max"]) for dp in dps if "max" in dp]
        total += len(vals)
        if vals:
            if not ces_unit:
                _u = str(r["batch"].get("unit") or "").strip()
                if _u and _u.lower() not in ("unknown", "none"):
                    ces_unit = r["batch"]["unit"]
            day_peaks.append(max(vals))
            day_valleys.append(min(vals))
            dates.append({"date": r["day"], "peak": max(vals), "valley": min(vals)})
    if not day_peaks:
        return {"ok": False, "spec": spec, "error": "该时间窗口内无监控数据(可能实例未接入监控或指标无数据)"}
    return {
        "ok": True,
        "spec": spec,
        "peak": max(day_peaks),
        "valley": min(day_valleys),
        "unit": ces_unit or spec.get("unit", ""),
        "dates": dates,
        "datapoints": total,
    }


def collect_metric_ces(
    region: str,
    spec: dict[str, Any],
    start: datetime,
    end: datetime,
    period: int = 300,
    hcloud: str = "hcloud",
    endpoint: Optional[str] = None,
    tz=None,
) -> dict[str, Any]:
    """Collect a single CES metric in [start,end]; output peak/valley + per-day details."""
    if tz is None:
        from .config import region_timezone
        tz = region_timezone(region)
    windows = gen_windows(start, end, tz)
    results: list[dict[str, Any]] = []
    try:
        for ws, we in windows:
            from_ms = int(ws.timestamp() * 1000)
            to_ms = int(we.timestamp() * 1000)
            day_start = ws.astimezone(tz)
            batch = call_batch(region, [spec], from_ms, to_ms, period=period,
                               hcloud=hcloud, endpoint=endpoint)
            results.append({"day": day_start.date().isoformat(), "batch": batch[0]})
    except CollectError as e:
        return {"ok": False, "spec": spec, "error": str(e)}
    return _aggregate_days(results, spec)


def collect_metric_aom(
    region: str,
    spec: dict[str, Any],
    start: datetime,
    end: datetime,
    period: int = 300,
    statistic: str = "maximum",
    hcloud: str = "hcloud",
    endpoint: Optional[str] = None,
    tz=None,
) -> dict[str, Any]:
    """Collect a single AOM metric (CCE and other cloud-native) in [start,end].

    Output structure is identical to collect_metric_ces;
    datapoints are taken from the specified statistic (default maximum) of the AOM ListSample response.
    """
    if tz is None:
        from .config import region_timezone
        tz = region_timezone(region)
    windows = gen_windows(start, end, tz)
    results: list[dict[str, Any]] = []
    try:
        for ws, we in windows:
            from_ms = int(ws.timestamp() * 1000)
            to_ms = int(we.timestamp() * 1000)
            day_start = ws.astimezone(tz)
            batch = call_aom_batch(region, [spec], from_ms, to_ms, period=period,
                                   statistic=statistic, hcloud=hcloud, endpoint=endpoint)
            results.append({"day": day_start.date().isoformat(), "batch": batch[0]})
    except CollectError as e:
        return {"ok": False, "spec": spec, "error": str(e)}
    return _aggregate_days(results, spec)


def collect_metric(
    region: str,
    spec: dict[str, Any],
    start: datetime,
    end: datetime,
    period: int = 300,
    hcloud: str = "hcloud",
    endpoint: Optional[str] = None,
    tz=None,
    backend: str = "ces",
) -> dict[str, Any]:
    """Collect a single metric in [start,end]; output peak/valley + per-day details.

    backend: "ces" | "aom" (default ces, backward compatible)
    Returns: {"ok", "spec", "peak", "valley", "unit", "dates", "datapoints"} or {"ok": false, "error"}
    """
    if backend == "aom":
        return collect_metric_aom(region, spec, start, end, period=period,
                                  hcloud=hcloud, endpoint=endpoint, tz=tz)
    return collect_metric_ces(region, spec, start, end, period=period,
                              hcloud=hcloud, endpoint=endpoint, tz=tz)


def collect_t24(region: str, spec: dict[str, Any], now: Optional[datetime] = None,
                period: int = 300, hcloud: str = "hcloud",
                endpoint: Optional[str] = None,
                backend: str = "ces") -> dict[str, Any]:
    """T-24 mode: last 24-hour window, single collection."""
    if now is None:
        now = datetime.now()
    start = now - timedelta(hours=24)
    return collect_metric(region, spec, start, now, period=period,
                          hcloud=hcloud, endpoint=endpoint, backend=backend)


def hcloud_smoke(region: str, hcloud: str = "hcloud") -> tuple[bool, str]:
    """Connectivity self-check: probe both CES and AOM data backends.

    - ces: hcloud CES ListMetrics (the first SYS.ECS metric)
    - aom: hcloud AOM ListMetadataAomPromGet (the CCE and other cloud-native metric backend)
    Either failing returns (False, summary), with the failing backend marked in the message.

    Note the hcloud pitfall: usage/network errors (e.g. unsupported region) print a
    `[USE_ERROR]`/`[NETWORK_ERROR]` prefix to stdout AND exit with code 0,
    so we cannot rely only on returncode/stderr; we must also verify stdout is valid JSON.
    """
    probes = {
        "CES": [hcloud, "CES", "ListMetrics", f"--cli-region={region}",
                "--namespace=SYS.ECS", "--limit=1", "--cli-output=json"],
        "AOM": [hcloud, "AOM", "ListMetadataAomPromGet", f"--cli-region={region}",
                "--cli-output=json"],
    }
    checks: list[str] = []
    all_ok = True
    for backend, cmd in probes.items():
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except Exception as e:
            checks.append(f"{backend}: hcloud execution failed {e}")
            all_ok = False
            continue
        if proc.returncode != 0:
            checks.append(f"{backend}: exit={proc.returncode} {(proc.stderr or proc.stdout).strip()[:300]}")
            all_ok = False
            continue
        out = proc.stdout.strip()
        # hcloud usage/network errors: [USE_ERROR] / [NETWORK_ERROR] prefixes, exit 0, output on stdout
        if out.startswith("[") and not out.startswith("{"):
            checks.append(f"{backend}: {out[:300]}")
            all_ok = False
            continue
        if not out.startswith("{"):
            checks.append(f"{backend}: returned non-JSON: {out[:300]}")
            all_ok = False
            continue
        try:
            data = json.loads(out)
        except Exception:
            checks.append(f"{backend}: returned non-JSON: {out[:300]}")
            all_ok = False
            continue
        if backend == "CES" and "metrics" not in data:
            checks.append(f"{backend}: returned unexpected: {json.dumps(data, ensure_ascii=False)[:200]}")
            all_ok = False
            continue
        if backend == "AOM" and data.get("status") != "success":
            checks.append(f"{backend}: returned unexpected: {json.dumps(data, ensure_ascii=False)[:200]}")
            all_ok = False
            continue
        checks.append(f"{backend}: ok")
    return all_ok, "; ".join(checks)

# ---------------------------------------------------------------------------
# DMS subtype detection (since v3.5)
# ---------------------------------------------------------------------------
DMS_SUBTYPE_DIMS = {
    "kafka": "kafka_instance_id",
    "rabbitmq": "rabbitmq_instance_id",
    "rocketmq": "reliablemq_instance_id",
}

# hcloud service name + operation for each DMS engine
DMS_SUBTYPE_APIS = {
    "kafka":      ("Kafka",    "ShowInstance"),
    "rabbitmq":   ("RabbitMQ", "ShowInstance"),
    "rocketmq":   ("RocketMQ", "ShowInstance"),
}


def detect_dms_subtype(region: str, instance_id: str,
                       hcloud: str = "hcloud",
                       endpoint: Optional[str] = None,
                       timeout: int = 30) -> Optional[str]:
    """Determine the DMS engine type (kafka/rabbitmq/rocketmq) via ShowInstance API.

    Tries `hcloud <Service> ShowInstance --instance_id=xxx` for each engine.
    The first one that returns a non-error response indicates the engine type.
    Falls back to CES ListMetrics probing if all ShowInstance calls fail.

    Returns 'kafka'/'rabbitmq'/'rocketmq', or None if all probes fail.
    """
    # Strategy 1: ShowInstance (direct, reliable, serial)
    # DMS ShowInstance requires --project_id path parameter (same as DCS)
    project_id = _get_project_id(region, hcloud=hcloud, endpoint=endpoint)
    for subtype, (svc, op) in DMS_SUBTYPE_APIS.items():
        cmd = [hcloud, svc, op, f"--cli-region={region}",
               f"--instance_id={instance_id}", "--cli-output=json"]
        if project_id:
            cmd.append(f"--project_id={project_id}")
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            data = json.loads(out)
        except Exception:
            continue
        # ShowInstance returns error_code when instance not found
        if "error_code" not in data:
            return subtype

    # Strategy 2: fallback to CES ListMetrics probing
    for subtype, dim_name in DMS_SUBTYPE_DIMS.items():
        cmd = [hcloud, "CES", "ListMetrics", f"--cli-region={region}",
               "--namespace=SYS.DMS",
               f"--dim.0={dim_name},{instance_id}",
               "--cli-output=json", "--limit=1"]
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            data = json.loads(out)
        except Exception:
            continue
        metrics = data.get("metrics") or []
        if metrics:
            return subtype
    return None


# GeminiDB engine types and their CES dimension names
GEMINIDB_SUBTYPE_DIMS = {
    "cassandra": "cassandra_cluster_id",
    "redis": "redis_cluster_id",
}


def detect_geminidb_subtype(region: str, instance_id: str,
                            hcloud: str = "hcloud",
                            endpoint: Optional[str] = None,
                            timeout: int = 30) -> Optional[str]:
    """Determine the GeminiDB engine type (cassandra/redis).

    Strategy 1: GaussDBforNoSQL ListInstances --id=xxx --datastore_type=<type>
    Strategy 2: CES ListMetrics probing with cassandra_cluster_id / redis_cluster_id

    Returns 'cassandra'/'redis', or None if all probes fail.
    """
    # Strategy 1: GaussDBforNoSQL ListInstances
    for subtype in GEMINIDB_SUBTYPE_DIMS:
        cmd = [hcloud, "GaussDBforNoSQL", "ListInstances",
               f"--cli-region={region}",
               f"--id={instance_id}",
               f"--datastore_type={subtype}",
               "--cli-output=json"]
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            data = json.loads(out)
        except Exception:
            continue
        if data.get("instances"):
            return subtype

    # Strategy 2: CES ListMetrics probing
    for subtype, dim_name in GEMINIDB_SUBTYPE_DIMS.items():
        cmd = [hcloud, "CES", "ListMetrics", f"--cli-region={region}",
               "--namespace=SYS.NoSQL",
               f"--dim.0={dim_name},{instance_id}",
               "--cli-output=json", "--limit=1"]
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            data = json.loads(out)
        except Exception:
            continue
        metrics = data.get("metrics") or []
        if metrics:
            return subtype
    return None


def discover_dim_values(region: str, namespace: str,
                        instance_dim_name: str, instance_id: str,
                        dim_resource_dim_name: str,
                        backend: str = "ces",
                        hcloud: str = "hcloud",
                        endpoint: Optional[str] = None,
                        timeout: int = 60,
                        warnings: Optional[list[str]] = None) -> list[str]:
    """Discover all available dimension resource IDs for a given instance.

    Queries `hcloud CES ListMetrics` (or CCE-specific APIs for AOM backend) with the
    instance dimension to list all available metrics, then extracts the unique values
    of the dim_resource_dim_name dimension.

    `warnings` (optional, appended in place) receives a human-readable note whenever the
    instance-level discovery came back empty or had to use the namespace-wide fallback,
    so the caller can surface it instead of silently substituting the instance ID.

    Returns a list of dimension resource ID values (e.g. node IDs, broker IDs, POD names).
    Returns an empty list if the query fails or no values are found.
    """
    if backend == "aom":
        # CCE: try AOM ListSeries first (most reliable for AOM namespaces),
        # then CES ListMetrics, then CCE ShowClusterNodes for hostID
        values = _discover_via_aom(region, namespace, instance_dim_name, instance_id,
                                   dim_resource_dim_name, hcloud, endpoint, timeout)
        if values:
            return values
        values = _discover_via_ces(region, namespace, instance_dim_name, instance_id,
                                   dim_resource_dim_name, hcloud, endpoint, timeout,
                                   warnings=warnings)
        if values:
            return values
        if dim_resource_dim_name == "hostID":
            values = _discover_cce_nodes(region, instance_id, hcloud, endpoint, timeout)
            if values:
                return values
        _add_warning(warnings, _empty_dim_warning(namespace, instance_dim_name, instance_id,
                                                 dim_resource_dim_name))
        return []

    # CES-backed services
    values = _discover_via_ces(region, namespace, instance_dim_name, instance_id,
                               dim_resource_dim_name, hcloud, endpoint, timeout,
                               warnings=warnings)
    if not values:
        _add_warning(warnings, _empty_dim_warning(namespace, instance_dim_name, instance_id,
                                                 dim_resource_dim_name))
    return values


def _empty_dim_warning(namespace: str, instance_dim_name: str, instance_id: str,
                       dim_resource_dim_name: str) -> str:
    return (f"dimension discovery: no {dim_resource_dim_name} values found for {namespace} "
            f"(dim {instance_dim_name}={instance_id}); falling back to the instance ID")


def _add_warning(warnings: Optional[list[str]], message: str) -> None:
    if warnings is not None and message not in warnings:
        warnings.append(message)


def _list_metrics_ces(region: str, namespace: str, hcloud: str,
                      endpoint: Optional[str], timeout: int,
                      dim_filter: Optional[str] = None,
                      limit: int = 1000,
                      max_pages: int = 5) -> tuple[list[dict], bool]:
    """Run CES ListMetrics for one namespace, following the marker pagination.

    dim_filter: optional "name,value" sent as --dim.0 (CES matches the **exact**
    dimension set of a metric, so a metric carrying an extra dimension is not returned).

    Returns (metrics, ok): metrics are de-duplicated across pages; ok is False when at
    least one page could not be read and no page succeeded (CLI/JSON failure).
    """
    collected: list[dict] = []
    seen: set[tuple] = set()
    start = ""
    ok = False
    for _ in range(max_pages):
        cmd = [hcloud, "CES", "ListMetrics", f"--cli-region={region}",
               f"--namespace={namespace}", "--cli-output=json", f"--limit={limit}"]
        if dim_filter:
            cmd.append(f"--dim.0={dim_filter}")
        if start:
            cmd.append(f"--start={start}")
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            break
        if proc.returncode != 0:
            break
        out = proc.stdout.strip()
        if not out.startswith("{"):
            break
        try:
            data = json.loads(out)
        except Exception:
            break
        ok = True
        page = data.get("metrics") or []
        added = 0
        for m in page:
            key = (str(m.get("metric_name") or ""),
                   tuple(sorted((str(d.get("name") or ""), str(d.get("value") or ""))
                                for d in (m.get("dimensions") or []))))
            if key in seen:
                continue
            seen.add(key)
            collected.append(m)
            added += 1
        meta = data.get("meta_data") or {}
        marker = str(meta.get("marker") or "").strip()
        total = meta.get("total")
        if not marker or marker == start or not page or not added:
            break
        if isinstance(total, int) and total > 0 and len(collected) >= total:
            break
        start = marker
    return collected, ok


def _extract_dim_values(metrics: list[dict], dim_name: str) -> list[str]:
    values = set()
    for m in metrics:
        for d in m.get("dimensions") or []:
            if d.get("name") == dim_name and d.get("value"):
                values.add(str(d.get("value")).strip())
    values.discard("")
    return sorted(values)


def _metric_belongs_to_instance(metric: dict, instance_dim_name: str, instance_id: str) -> bool:
    """A namespace-wide metric counts for this instance only when its instance dimension says so."""
    ids = {str(d.get("value")).strip() for d in metric.get("dimensions") or []
           if d.get("name") == instance_dim_name}
    return instance_id in ids


def _discover_via_ces(region: str, namespace: str,
                      instance_dim_name: str, instance_id: str,
                      dim_resource_dim_name: str,
                      hcloud: str, endpoint: Optional[str], timeout: int,
                      warnings: Optional[list[str]] = None) -> list[str]:
    """Use CES ListMetrics to discover available dimension values.

    Since CES filters on the exact dimension set, an instance-dimension-filtered query
    misses every metric that carries an extra dimension — DCS/DMS node, broker and shard
    level metrics only expose e.g. dcs_cluster_redis_node through a namespace-wide
    listing.  When the filtered query yields no dim-resource values, the namespace-wide
    listing is used and each metric is attributed to this instance by its instance
    dimension, so metrics of other instances in the region cannot leak into the result
    (same attribution rule as detect_dcs_instance_type).
    """
    filtered, _ = _list_metrics_ces(region, namespace, hcloud, endpoint, timeout,
                                   dim_filter=f"{instance_dim_name},{instance_id}")
    values = _extract_dim_values(filtered, dim_resource_dim_name)
    if values:
        return values

    # Fallback: namespace-wide listing + per-instance attribution
    wide, _ = _list_metrics_ces(region, namespace, hcloud, endpoint, timeout)
    scoped = [m for m in wide if _metric_belongs_to_instance(m, instance_dim_name, instance_id)]
    values = _extract_dim_values(scoped, dim_resource_dim_name)
    if values:
        _add_warning(warnings,
                     f"dimension discovery: instance-filtered ListMetrics on {namespace} "
                     f"(dim {instance_dim_name}={instance_id}) returned no "
                     f"{dim_resource_dim_name} values; recovered {len(values)} value(s) from a "
                     f"namespace-wide listing attributed by {instance_dim_name}")
    return values


def _discover_via_aom(region: str, namespace: str,
                      instance_dim_name: str, instance_id: str,
                      dim_resource_dim_name: str,
                      hcloud: str, endpoint: Optional[str], timeout: int) -> list[str]:
    """Use AOM ListSeries to discover available dimension values for AOM-backed metrics."""
    cmd = [hcloud, "AOM", "ListSeries", f"--cli-region={region}",
           f"--series.1.namespace={namespace}",
           f"--series.1.dimensions.1.name={instance_dim_name}",
           f"--series.1.dimensions.1.value={instance_id}",
           "--limit=500", "--cli-output=json"]
    if endpoint:
        cmd.append(f"--cli-endpoint={endpoint}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out = proc.stdout.strip()
    if not out.startswith("{"):
        return []
    try:
        data = json.loads(out)
    except Exception:
        return []
    values = set()
    # AOM ListSeries response: {"series": [{"dimensions": [{"name":.., "value":..}, ...]}, ...]}
    for s in data.get("series") or []:
        for d in s.get("dimensions") or []:
            if d.get("name") == dim_resource_dim_name and d.get("value"):
                values.add(d["value"])
    return sorted(values)


def _discover_cce_nodes(region: str, cluster_id: str,
                        hcloud: str, endpoint: Optional[str], timeout: int) -> list[str]:
    """Use CCE ShowClusterNodes to discover node hostIDs."""
    cmd = [hcloud, "CCE", "ShowClusterNodes", f"--cli-region={region}",
           f"--cluster_id={cluster_id}", "--cli-output=json"]
    if endpoint:
        cmd.append(f"--cli-endpoint={endpoint}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    out = proc.stdout.strip()
    if not out.startswith("{"):
        return []
    try:
        data = json.loads(out)
    except Exception:
        return []
    nodes = data.get("nodes") or (data.get("body") or {}).get("nodes") or []
    host_ids = []
    for n in nodes:
        hid = n.get("hostID") or n.get("host_id") or n.get("id")
        if hid:
            host_ids.append(str(hid))
    return sorted(set(host_ids))

# ---------------------------------------------------------------------------
# DCS instance type detection (since v3.6)
# ---------------------------------------------------------------------------
# DCS instance types and their identifying keywords in the ShowInstance response
# 单机 -> "single", 主备 -> "ha", Cluster集群 -> "cluster", Proxy集群 -> "proxy"
DCS_INSTANCE_TYPE_MAP = {
    "single": "single",
    "ha": "ha",
    "cluster": "cluster",
    "proxy": "proxy",
    "master_standby": "ha",
    "master-standby": "ha",
    "proxy_cluster": "proxy",
    "proxy-cluster": "proxy",
}

# Keywords in description field for each DCS instance type
DCS_DESCRIPTION_KEYWORDS = {
    "proxy": ["proxy", "代理"],
    "cluster": ["cluster", "集群"],
    "ha": ["ha", "主备", "replication"],
    "single": ["single", "单机"],
}


def _get_project_id(region: str, hcloud: str = "hcloud",
                    endpoint: Optional[str] = None,
                    timeout: int = 15) -> Optional[str]:
    """Resolve project_id for a region via IAM KeystoneListUserProjects."""
    cmd = [hcloud, "IAM", "KeystoneListUserProjects", f"--cli-region={region}",
           "--cli-output=json"]
    if endpoint:
        cmd.append(f"--cli-endpoint={endpoint}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out.startswith("["):
        return None
    try:
        projects = json.loads(out)
    except Exception:
        return None
    if projects and isinstance(projects, list):
        # Prefer the project whose name matches the target region
        for p in projects:
            if str(p.get("name", "")).strip() == region:
                pid = p.get("id")
                if pid:
                    return str(pid)
        # Fallback: first project (single-region accounts)
        pid = projects[0].get("id")
        if pid:
            return str(pid)
    return None


def detect_dcs_instance_type(region: str, instance_id: str,
                             hcloud: str = "hcloud",
                             endpoint: Optional[str] = None,
                             timeout: int = 30) -> Optional[str]:
    """Determine the DCS instance type (single/ha/cluster/proxy).

    Strategy 1: DCS ShowInstance API — check cache_mode / instance_type / type /
                description fields.  Tries with --project_id first, then without
                (KooCLI auto-fills --project_id from the configured profile).
    Strategy 2: CES ListMetrics probing — check if dcs_cluster_redis_node dimension
                exists for this instance (indicates cluster or proxy); distinguish
                by checking metric_name patterns in the response.  Falls back to a
                namespace-only query (no dim filter) if the instance-dim query
                finds no sub-nodes, because DCS node-level metrics may carry only
                dcs_cluster_redis_node without dcs_instance_id.  Namespace-only
                results are attributed to this instance via their dcs_instance_id
                dimension, so metrics of other DCS instances in the region cannot
                change the verdict.

    Returns 'single'/'ha'/'cluster'/'proxy'.  Returns None when no probe yields
    instance-attributable evidence (expand all DCS metrics rather than guessing).
    """
    # Strategy 1: DCS ShowInstance
    project_id = _get_project_id(region, hcloud=hcloud, endpoint=endpoint)

    # Build candidate command variants: with --project_id first, then without
    # (KooCLI can auto-fill --project_id from the configured profile, same as
    # the DMS detection code in detect_dms_engine_type).
    use_pid_variants = []
    if project_id:
        use_pid_variants.append(True)   # with --project_id (preferred)
    use_pid_variants.append(False)      # without --project_id (fallback)

    for use_pid in use_pid_variants:
        cmd = [hcloud, "DCS", "ShowInstance", f"--cli-region={region}",
               f"--instance_id={instance_id}", "--cli-output=json"]
        if use_pid:
            cmd.append(f"--project_id={project_id}")
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            inst = json.loads(out)
        except Exception:
            continue
        # ShowInstance returns error_code on failure (wrong project, permissions, etc.)
        if "error_code" in inst:
            continue
        # Check cache_mode first (primary DCS API field for instance architecture),
        # then instance_type / type as fallbacks for older API versions.
        for field in ("cache_mode", "instance_type", "type"):
            val = inst.get(field)
            if val is not None:
                val_str = str(val).strip().lower()
                if val_str in DCS_INSTANCE_TYPE_MAP:
                    return DCS_INSTANCE_TYPE_MAP[val_str]
        # Check description field for keywords
        desc = str(inst.get("description") or "").strip().lower()
        if desc:
            for subtype, keywords in DCS_DESCRIPTION_KEYWORDS.items():
                if any(kw in desc for kw in keywords):
                    return subtype

    # Strategy 2: CES ListMetrics probing
    # Query all metrics for this DCS instance and check dimension/metric patterns.
    # Try two query variants:
    #   (a) filtered by dcs_instance_id  (b) namespace-only (no dim filter)
    # Variant (b) is needed because DCS node-level metrics may carry only
    # dcs_cluster_redis_node without dcs_instance_id, so the filtered query
    # would miss them.  Variant (b) returns the metrics of *every* DCS instance in the
    # region, so each returned metric must be attributed to this instance before it can
    # influence the verdict — otherwise one cluster instance in the same region makes
    # every single-node instance look like a cluster (cross-instance pollution).
    has_sub_nodes = False
    metric_names: set[str] = set()
    scoped_metrics = 0

    for dim_filter in (True, False):
        cmd = [hcloud, "CES", "ListMetrics", f"--cli-region={region}",
               "--namespace=SYS.DCS", "--cli-output=json", "--limit=500"]
        if dim_filter:
            cmd.append(f"--dim.0=dcs_instance_id,{instance_id}")
        if endpoint:
            cmd.append(f"--cli-endpoint={endpoint}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0:
            continue
        out = proc.stdout.strip()
        if not out.startswith("{"):
            continue
        try:
            resp = json.loads(out)
        except Exception:
            continue
        for m in resp.get("metrics") or []:
            dims = m.get("dimensions") or []
            inst_ids = {str(d.get("value")).strip() for d in dims
                        if d.get("name") == "dcs_instance_id"}
            if dim_filter:
                # The server-side filter already scoped the result to this instance; reject
                # only metrics that explicitly carry another instance's id.
                belongs = (not inst_ids) or (instance_id in inst_ids)
            else:
                # Namespace-wide query: attribute a metric to this instance only when its
                # dcs_instance_id dimension names this instance.
                belongs = instance_id in inst_ids
            if not belongs:
                continue
            scoped_metrics += 1
            if any(d.get("name") == "dcs_cluster_redis_node" for d in dims):
                has_sub_nodes = True
            metric_names.add(str(m.get("metric_name", "")).lower())
        # If the filtered query already found sub-nodes, skip the broader query
        if has_sub_nodes:
            break

    if not scoped_metrics:
        # No metric attributable to this instance: the namespace-only result says nothing
        # about it, so return None (= expand every DCS metric) instead of guessing "single".
        return None

    if not has_sub_nodes:
        # No instance-level sub-node dimension → single or ha (both use only instance-level
        # metrics); CES cannot tell them apart, "single" is the documented instance-metric default.
        return "single"

    # Has sub-nodes → cluster or proxy; distinguish by metric name patterns
    # Proxy instances have proxy-specific metrics (e.g., proxy_node_*)
    if any("proxy" in mn for mn in metric_names):
        return "proxy"
    # Cluster instances have data-node-specific metrics
    if any("data" in mn or "node" in mn for mn in metric_names):
        return "cluster"

    # Fallback: can't distinguish, return None to expand all
    return None

