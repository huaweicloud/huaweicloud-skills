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
    # Align the response to request order (match namespace+metric_name+dimension names)
    out: list[dict[str, Any]] = []
    for req in specs:
        hit = None
        for m in data["metrics"]:
            if (m.get("namespace") == req["namespace"]
                    and m.get("metric_name") == req["metric_name"]
                    and [d.get("name") for d in m.get("dimensions", [])]
                    == [d.get("name") for d in req.get("dimensions", [])]):
                hit = m
                break
        if hit is None:
            out.append({"req": req, "datapoints": [], "error": "返回中未找到该指标"})
        else:
            out.append({"req": req, "datapoints": hit.get("datapoints", []),
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
    return [d.get("name") for d in s.get("dimensions", [])] \
        == [d.get("name") for d in req.get("dimensions", [])]


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
        for s in data["samples"]:
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