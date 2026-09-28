"""Orchestration module: chains read -> collect -> compute -> write into one
callable tool for the model.

Boundary: orchestrates other modules; all numeric computation goes to calculator/collector, no recomputation here.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Optional

from . import calculator, collector
from .config import convert_value, resolve_region
from .excel_io import base_name, read_excel, write_updates
from .registry import MetricRegistry

SERVICE_CN = {
    "nat": "NAT Gateway", "rds": "RDS", "ecs": "ECS", "elb": "ELB", "eip": "EIP",
    "css": "CSS", "dds": "DDS", "dws": "DWS", "dcs": "DCS",
    "dms": "DMS", "taurusdb": "TaurusDB", "geminidb": "GeminiDB", "dc": "DC",
    "er": "ER", "evs": "EVS", "efsturbo": "EFS Turbo", "apig": "APIG",
    "drs": "DRS", "vpcep": "VPCEP", "bandwidth": "Bandwidth",
    "cce": "CCE",
}

OUTPUT_COLUMNS_HIST = ["峰谷值倍数", "压力系数", "预计节日上限", "扩容建议"]
T24_COLUMN_MAP = {
    "t-24峰谷值增长倍数": "峰谷值倍数",
    "t-24压力系数": "压力系数",
    "t-24预计节日上限": "预计节日上限",
    "t-24是否需要扩容": "扩容建议",
}


def _cell_map(row: dict) -> dict[str, Any]:
    """Build a base-name -> value map from a read_excel row."""
    m: dict[str, Any] = {}
    for k, v in row["cells"].items():
        b = base_name(k)
        if b and b not in m:
            m[b] = v
    return m


def _split_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    s = str(raw).strip()
    parts = re.split(r"[,，;；\n\r\s]+", s)
    return [p for p in parts if p][:50]


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _build_spec(entry: dict, instance_id: str, dim_resource_id: Optional[str]) -> Optional[dict]:
    specs = []
    for d in entry.get("dimensions", []):
        if d.get("source") == "instance_id":
            specs.append({"name": d["name"], "value": instance_id})
        elif d.get("source") == "dim_resource_id":
            if not dim_resource_id:
                return None
            specs.append({"name": d["name"], "value": dim_resource_id})
        elif d.get("value"):
            specs.append({"name": d["name"], "value": d["value"]})
    return {"namespace": entry["namespace"], "metric_name": entry["metric_name"],
            "dimensions": specs, "unit": entry.get("unit", "")}


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"cannot parse time: {s!r}, supported YYYY-MM-DD[ HH:MM[:SS]]")


class Assessor:
    def __init__(self, metrics_path: Optional[str] = None,
                 hcloud: str = "hcloud"):
        self.registry = MetricRegistry(metrics_path)
        self.hcloud = hcloud
        self._t24_cache: dict[tuple, dict] = {}

    # ------------------------------------------------------------------
    # Single-row assessment
    # ------------------------------------------------------------------
    def assess_row(self, xlsx: str, row_no: int, mode: str,
                   start: Optional[str] = None, end: Optional[str] = None,
                   period: int = 300, endpoint: Optional[str] = None,
                   sheet: Optional[str] = None) -> dict[str, Any]:
        """Assess one row in the Excel file; return that row's write updates + failure info."""
        doc = read_excel(xlsx, sheet)
        row = next((r for r in doc["rows"] if r["row"] == row_no), None)
        if row is None:
            return {"row": row_no, "ok": False, "error": f"row {row_no} does not exist"}
        cells = _cell_map(row)

        region_raw = cells.get("region")
        itype_raw = cells.get("实例类型")
        instance_id = str(cells.get("实例ID") or "").strip()
        key_indicator = str(cells.get("关键指标") or "").strip()
        entrance_ids = _split_ids(cells.get("入口实例ID"))
        dimension = str(cells.get("云服务维度") or "").strip()
        dim_resource_id = str(cells.get("云服务维度资源ID") or "").strip() or None
        growth = _num(cells.get("活动增长倍数")) or 1.0

        miss = [c for c in ["region", "实例类型", "实例ID", "关键指标", "入口实例ID"]
                if not (cells.get(c) and str(cells.get(c)).strip())]
        if miss:
            return {"row": row_no, "ok": False, "error": f"required fields missing: {miss}",
                    "skipped": "missing_required"}

        itype = str(itype_raw).strip().lower()
        entry = self.registry.lookup(itype, key_indicator, dim_label=dimension)
        if entry is None:
            return {
                "row": row_no, "ok": False, "skipped": "metric_mismatch",
                "instance_id": instance_id, "instance_type": itype,
                "key_indicator": key_indicator,
                "skip_reason": "metric_mismatch" if itype in self.registry.data else "unsupported_service",
                "suggested_metrics": self.registry.suggested_metrics(itype),
            }

        # Cross-check: whether the Excel "云服务维度" matches the metrics.json label
        dim_warning = None
        if dimension:
            entry_labels = set()
            for d in entry.get("dimensions", []):
                lbl = d.get("label")
                if lbl:
                    entry_labels.add(lbl.strip())
            if entry_labels and dimension not in entry_labels:
                dim_warning = (
                    f"Excel 云服务维度='{dimension}' does not match the metric definition"
                    f"(expected {', '.join(sorted(entry_labels))})"
                )

        try:
            region = resolve_region(region_raw)
        except ValueError as e:
            return {"row": row_no, "ok": False, "collection_failure": True,
                    "instance_id": instance_id, "instance_type": itype,
                    "key_indicator": key_indicator, "error": str(e)}

        # 资源上限 (optional column): prefer the user-entered Excel value; fall back to the metrics.json
        # registry default ceiling when empty
        ceiling_user = _num(cells.get("资源上限"))
        ceiling = ceiling_user if ceiling_user is not None else entry.get("ceiling")
        display_unit = entry.get("unit", "")

        spec = _build_spec(entry, instance_id, dim_resource_id)
        if spec is None:
            return {"row": row_no, "ok": False, "collection_failure": True,
                    "instance_id": instance_id, "instance_type": itype,
                    "key_indicator": key_indicator,
                    "error": "该指标需要云服务维度资源ID,但 Excel 此列为空",
                    "dim_warning": dim_warning}
        # Data backend: declared in the metrics.json entry, default ces; CCE etc. cloud-native metrics go to aom
        backend = entry.get("backend", "ces")

        # Collect the target
        if mode == calculator.HIST:
            if not start or not end:
                return {"row": row_no, "ok": False, "error": "historical mode requires --start and --end"}
            target = collector.collect_metric(
                region, spec, _parse_dt(start), _parse_dt(end),
                period=period, hcloud=self.hcloud, endpoint=endpoint, backend=backend)
        else:
            # Manual-first (T-24 only): if the row already has t-24峰值/t-24谷值, use them directly, no collection
            t24p = cells.get("t-24峰值")
            t24v = cells.get("t-24谷值")
            target = None
            if (t24p is not None and t24v is not None
                    and str(t24p).strip() != "" and str(t24v).strip() != ""):
                pp, vv = _num(t24p), _num(t24v)
                if pp is not None and vv is not None:
                    target = {"ok": True, "spec": spec, "peak": pp, "valley": vv,
                              "unit": spec.get("unit", ""), "dates": [], "datapoints": 0,
                              "manual": True}
            if target is None:
                target = collector.collect_t24(region, spec, period=period,
                                               hcloud=self.hcloud, endpoint=endpoint,
                                               backend=backend)
        if not target.get("ok"):
            return {"row": row_no, "ok": False, "collection_failure": True,
                    "instance_id": instance_id, "instance_type": itype,
                    "key_indicator": key_indicator, "error": target.get("error", "collection failed")}

        # Collect the entrance instance
        entrances = self._collect_entrances(region, itype, key_indicator, entrance_ids,
                                            cells, doc, mode, start, end, period,
                                            target, endpoint)
        if entrances.get("error"):
            return {"row": row_no, "ok": False, "collection_failure": True,
                    "instance_id": instance_id, "instance_type": itype,
                    "key_indicator": key_indicator, "error": entrances["error"]}

        # Common-date alignment (historical mode)
        aligned_target, aligned_entrances = self._align_common_dates(
            target, entrances["items"], mode == calculator.HIST)

        # Convert units to the display unit
        tp_disp, conv_ok_t = convert_value(aligned_target["peak"],
                                           target.get("unit") or "", display_unit)
        tv_disp, _ = convert_value(aligned_target["valley"],
                                   target.get("unit") or "", display_unit)
        t_disp = {"peak": tp_disp, "valley": tv_disp, "unit": display_unit}
        e_disp = []
        for e in aligned_entrances:
            # The entrance only participates in 峰谷值倍数 (a dimensionless ratio); no need to convert
            # to the target unit; keep the entrance's raw unit so calculator can judge multi-entry compatibility.
            e_disp.append({"peak": e["peak"], "valley": e["valley"],
                           "unit": e.get("unit", "")})

        res = calculator.assess(mode, t_disp, e_disp, ceiling, growth)
        values = res.as_dict()

        # Assemble write updates
        updates: list[dict] = []
        updates.append({"row": row_no, "column": "资源上限",
                        "value": ceiling if ceiling is not None else ""})
        updates.append({"row": row_no, "column": "单位", "value": display_unit})
        if mode == calculator.HIST:
            for c in OUTPUT_COLUMNS_HIST:
                updates.append({"row": row_no, "column": c, "value": values[c]})
            for d in aligned_target.get("dates", []):
                dp, _ = convert_value(d["peak"], target.get("unit") or "", display_unit)
                dv, _ = convert_value(d["valley"], target.get("unit") or "", display_unit)
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                updates.append({"row": row_no, "column": f"{dt.month}/{dt.day}峰值", "value": dp})
                updates.append({"row": row_no, "column": f"{dt.month}/{dt.day}谷值", "value": dv})
        else:
            updates.append({"row": row_no, "column": "t-24峰值", "value": tp_disp})
            updates.append({"row": row_no, "column": "t-24谷值", "value": tv_disp})
            for c, src in T24_COLUMN_MAP.items():
                updates.append({"row": row_no, "column": c, "value": values[src]})

        return {
            "row": row_no, "ok": True,
            "instance_id": instance_id, "instance_type": itype,
            "key_indicator": key_indicator, "region": region,
            "mode": mode,
            "assessment": values,
            "updates": updates,
            "dates": aligned_target.get("dates", []),
            "manual_t24": target.get("manual", False),
            "unit_converted": conv_ok_t,
            "dim_warning": dim_warning,
        }

    def _collect_entrances(self, region, itype, key_indicator, entrance_ids,
                           cells, doc, mode, start, end, period,
                           target_result, endpoint):
        """Collect/reuse entrance-instance data. If the entrance is the same instance and metric as the target,
        reuse the target result directly.

        T-24 full mode: cache collection results per (region, metric, instance) in-process to avoid
        re-collecting when multiple rows share the same entrance instance.
        """
        items = []
        for eid in entrance_ids:
            eid = str(eid).strip()
            if not eid:
                continue
            # entrance == target instance and same metric -> reuse
            if eid == str(cells.get("实例ID") or "").strip():
                r = {k: target_result.get(k) for k in ("peak", "valley", "unit", "dates", "ok")}
                r["spec"] = target_result.get("spec")
                items.append(r)
                continue
            # Entrance metric: prefer the entrance instance's own key indicator from its row in Excel
            # (type/metric/dimension/region all come from that row); fall back to the target metric
            # when no such row is found. Computation only depends on 峰谷值倍数 (a dimensionless ratio),
            # so the entrance metric need not match the target.
            spec = None
            entrance_region = region  # default: target row's region
            row_entry = self._find_instance_row(doc, eid)
            if row_entry:
                r_cells = _cell_map(row_entry)
                e_region_raw = r_cells.get("region")
                if e_region_raw and str(e_region_raw).strip():
                    try:
                        entrance_region = resolve_region(e_region_raw)
                    except ValueError:
                        pass  # fall back to the target region when the entrance row's region cannot be parsed
                e_type = str(r_cells.get("实例类型") or "").strip().lower()
                e_metric = str(r_cells.get("关键指标") or "").strip()
                e_dim = str(r_cells.get("云服务维度") or "").strip()
                e_dim_res = str(r_cells.get("云服务维度资源ID") or "").strip() or None
                e_entry = self.registry.lookup(e_type, e_metric, dim_label=e_dim) if e_type and e_metric else None
                if e_entry:
                    spec = _build_spec(e_entry, eid, e_dim_res)
                    e_backend = e_entry.get("backend", "ces")
            if spec is None:
                # fallback: entrance not in Excel, use the target row's same metric
                entry = self.registry.lookup(itype, key_indicator)
                spec = _build_spec(entry, eid, None) if entry else None
                e_backend = entry.get("backend", "ces") if entry else "ces"
            if spec is None:
                return {"error": f"entrance instance {eid}: cannot determine the collection metric"}
            cache_key = (entrance_region, spec["namespace"], spec["metric_name"],
                         tuple((d["name"], d["value"]) for d in spec["dimensions"]))
            if mode != calculator.HIST and cache_key in self._t24_cache:
                r = self._t24_cache[cache_key]
            else:
                if mode == calculator.HIST:
                    r = collector.collect_metric(entrance_region, spec, _parse_dt(start), _parse_dt(end),
                                                 period=period, hcloud=self.hcloud, endpoint=endpoint,
                                                 backend=e_backend)
                else:
                    r = collector.collect_t24(entrance_region, spec, period=period,
                                              hcloud=self.hcloud, endpoint=endpoint,
                                              backend=e_backend)
                if r.get("ok") and mode != calculator.HIST:
                    self._t24_cache[cache_key] = r
            if not r.get("ok"):
                return {"error": f"entrance instance {eid} collection failed: {r.get('error')}"}
            items.append(r)
        if not items:
            return {"error": "entrance instances are empty"}
        return {"items": items}

    def _find_instance_row(self, doc, instance_id):
        for r in doc["rows"]:
            m = _cell_map(r)
            if str(m.get("实例ID") or "").strip() == str(instance_id).strip():
                return r
        return None

    def _align_common_dates(self, target, entrances, need_dates: bool):
        """Align the target and entrance common dates; for T-24 / no-date data use directly.

        When there are no common dates, mark the entrance (None, None) so the calculator outputs the
        no_common_date error wording.
        """
        if not need_dates:
            return target, entrances
        t_map = {d["date"]: d for d in target.get("dates", [])}
        e_maps = [{d["date"]: d for d in e.get("dates", [])} for e in entrances]
        common = sorted(set(t_map.keys()).intersection(*(set(m.keys()) for m in e_maps))) \
            if e_maps else sorted(t_map.keys())
        if not common:
            return target, [{"peak": None, "valley": None,
                             "unit": e.get("unit", "")} for e in entrances]
        t_dates = [t_map[d] for d in common]
        t_out = {
            "peak": max(d["peak"] for d in t_dates),
            "valley": min(d["valley"] for d in t_dates),
            "unit": target.get("unit", ""),
            "dates": t_dates,
        }
        e_out = []
        for e, em in zip(entrances, e_maps):
            ed = [em[d] for d in common]
            e_out.append({
                "peak": max(d["peak"] for d in ed),
                "valley": min(d["valley"] for d in ed),
                "unit": e.get("unit", ""),
            })
        return t_out, e_out

    # ------------------------------------------------------------------
    # Full assessment (supports background)
    # ------------------------------------------------------------------
    def assess_all(self, xlsx: str, mode: str, start: Optional[str] = None,
                   end: Optional[str] = None, period: int = 300,
                   sheet: Optional[str] = None, endpoint: Optional[str] = None,
                   progress_file: Optional[str] = None,
                   max_rows: Optional[int] = None) -> dict[str, Any]:
        doc = read_excel(xlsx, sheet)
        rows = doc["rows"]
        if max_rows:
            rows = rows[:max_rows]
        all_updates = []
        skipped_rows = []
        collection_failures = []
        ok_count = 0

        def log(line: dict):
            if progress_file:
                with open(progress_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")

        for i, r in enumerate(rows, start=1):
            try:
                rr = self.assess_row(xlsx, r["row"], mode, start, end, period,
                                     endpoint=endpoint, sheet=sheet)
            except Exception as e:  # a single-row exception does not abort the full run
                rr = {"row": r["row"], "ok": False, "collection_failure": True,
                      "instance_id": _cell_map(r).get("实例ID"),
                      "instance_type": _cell_map(r).get("实例类型"),
                      "key_indicator": _cell_map(r).get("关键指标"),
                      "error": f"script exception: {e}"}
            if rr.get("skipped"):
                skipped_rows.append({
                    "row": rr["row"], "instance_id": rr.get("instance_id"),
                    "instance_type": rr.get("instance_type"),
                    "key_indicator": rr.get("key_indicator"),
                    "skip_reason": rr.get("skip_reason", "missing_required"),
                    "suggested_metrics": rr.get("suggested_metrics", []),
                })
                log({"row": rr["row"], "status": "skipped", "reason": rr.get("skip_reason")})
            elif not rr.get("ok"):
                collection_failures.append({
                    "row": rr["row"], "instance_id": rr.get("instance_id"),
                    "instance_type": rr.get("instance_type"),
                    "key_indicator": rr.get("key_indicator"),
                    "error": rr.get("error", "unknown error"),
                })
                log({"row": rr["row"], "status": "failed", "error": rr.get("error")})
            else:
                all_updates.extend(rr["updates"])
                ok_count += 1
                log({"row": rr["row"], "status": "ok"})
            if progress_file:
                log({"progress": i, "total": len(rows)})

        wr = write_updates(xlsx, all_updates, sheet=sheet)
        result = {
            "done": True,
            "excel_path": os.path.abspath(xlsx),
            "write": wr,
            "total_rows": len(rows),
            "ok_count": ok_count,
            "skipped_rows": skipped_rows,
            "collection_failures": collection_failures,
        }
        if progress_file:
            log(result)
        return result