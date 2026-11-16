"""Metric registry: Chinese metric name -> CES namespace/metric_name/dimensions.

Data file: skill root references/metrics.json
Keys are Chinese metric names (canonical names with service prefix, e.g. "ECS CPU使用率").
Lookup rules, by increasing tolerance:
  1. exact match
  2. exact match after stripping the service prefix (Excel may fill "CPU使用率" instead of "ECS CPU使用率")
  3. alias match (entry["aliases"] list)
  4. unique contains-match (avoid ambiguity)
  4b. when multiple hits, disambiguate with the Excel "云服务维度" (dim_label)
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from .config import strip_service_prefix


def _default_metrics_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    p = os.path.join(root, "references", "metrics.json")
    if os.path.exists(p):
        return p
    return os.path.join(here, "metrics.json")


def _entry_labels(entry: dict) -> set[str]:
    """Collect all label values of the entry's dimensions (deduped, non-empty)."""
    labels = set()
    for d in entry.get("dimensions", []):
        lbl = d.get("label")
        if lbl:
            labels.add(lbl.strip())
    return labels


class MetricRegistry:
    def __init__(self, metrics_path: Optional[str] = None):
        if metrics_path is None:
            metrics_path = _default_metrics_path()
        with open(metrics_path, encoding="utf-8") as f:
            self.data: dict[str, dict[str, Any]] = json.load(f)
        self.data = {k.lower(): v for k, v in self.data.items()}
        # Precompute a (stripped name -> canonical name) index per service
        self._stripped: dict[str, dict[str, str]] = {}
        for svc, entries in self.data.items():
            if not isinstance(entries, dict) or svc.startswith("_"):
                continue  # skip non-service keys (defensive)
            idx = {}
            for name in entries:
                idx[strip_service_prefix(name).strip()] = name
                for alias in (entries[name].get("aliases") or []):
                    idx[strip_service_prefix(alias).strip()] = name
            self._stripped[svc] = idx

    def lookup(self, instance_type: str, key_indicator: str,
               dim_label: Optional[str] = None) -> Optional[dict]:
        """Look up a metric by (实例类型, 关键指标 [, 云服务维度]).

        dim_label comes from the Excel "云服务维度" column and corresponds to
        dimensions[].label in metrics.json. It is only used to disambiguate in step 4
        (contains-match) when multiple hits occur: filter the hit entries by the one whose
        label matches. Exact/alias matching does not depend on it.
        """
        itype = (instance_type or "").strip().lower()
        svc = self.data.get(itype)
        if not svc:
            return None
        key = str(key_indicator).strip()
        if not key:
            return None
        # 1. exact
        if key in svc:
            return svc[key]
        # 2. stripped exact (bidirectional)
        stripped = strip_service_prefix(key).strip()
        idx = self._stripped.get(itype, {})
        if stripped in idx:
            return svc[idx[stripped]]
        # 3. alias exact
        for name, e in svc.items():
            if key in (e.get("aliases") or []):
                return e
        # 4. contains-match -> possibly multiple
        hits = []
        for n, e in svc.items():
            n_stripped = strip_service_prefix(n).strip()
            if stripped and (stripped in n_stripped or n_stripped in stripped):
                hits.append(e)
        if len({id(h) for h in hits}) == 1:
            return hits[0]
        # 4b. multiple hits -> disambiguate with dim_label
        if dim_label and len(hits) > 1:
            lbl = dim_label.strip()
            filtered = [e for e in hits if lbl in _entry_labels(e)]
            if len({id(e) for e in filtered}) == 1:
                return filtered[0]
        return None

    def suggested_metrics(self, instance_type: str) -> list[str]:
        itype = (instance_type or "").strip().lower()
        svc = self.data.get(itype)
        if not svc:
            return []
        return list(svc.keys())


    # ------------------------------------------------------------------
    # Expansion support (since v3.5)
    # ------------------------------------------------------------------
    # DMS subtype prefixes: metric names starting with these indicate the engine type
    DMS_SUBTYPE_PREFIXES = {
        "kafka": "DMS Kafka",
        "rabbitmq": "DMS RabbitMQ",
        "rocketmq": "DMS RocketMQ",
    }

    GEMINIDB_SUBTYPE_PREFIXES = {
        "cassandra": "GeminiDB Cassandra",
        "redis": "GeminiDB Redis",
    }

    # DCS instance type → allowed dimension label keywords
    # single/ha: only instance-level metrics (label contains '实例' but not '数据节点'/'Proxy')
    # cluster: instance-level + data-node metrics (label contains '实例' or '数据节点')
    # proxy: proxy-node metrics (label contains 'Proxy')
    DCS_SUBTYPE_LABELS = {
        "single":  ["实例"],
        "ha":      ["实例"],
        "cluster": ["实例", "数据节点"],
        "proxy":   ["Proxy"],
    }

    def metrics_for_service(self, instance_type: str,
                            subtype: Optional[str] = None) -> list[dict[str, Any]]:
        """Return all metric entries for a service, optionally filtered by DMS subtype.

        Each returned dict is the full metric entry from metrics.json (with an added
        'metric_name_cn' key for convenience).

        For DMS, subtype can be 'kafka'/'rabbitmq'/'rocketmq' to filter by engine type.
        For GeminiDB, subtype can be 'cassandra'/'redis' to filter by engine type.
        For DCS, subtype can be 'single'/'ha'/'cluster'/'proxy' to filter by instance type.
        For other services, subtype is ignored (all metrics returned).
        """
        itype = (instance_type or "").strip().lower()
        svc = self.data.get(itype)
        if not svc:
            return []
        results = []
        for name, entry in svc.items():
            if subtype and itype == "dms":
                prefix = self.DMS_SUBTYPE_PREFIXES.get(subtype)
                if not prefix or not name.startswith(prefix):
                    continue
            if subtype and itype == "geminidb":
                prefix = self.GEMINIDB_SUBTYPE_PREFIXES.get(subtype)
                if not prefix or not name.startswith(prefix):
                    continue
            if subtype and itype == "dcs":
                allowed_labels = self.DCS_SUBTYPE_LABELS.get(subtype)
                if allowed_labels:
                    # Get the metric's dimension label
                    dim_label = ""
                    for d in entry.get("dimensions", []):
                        lbl = d.get("label", "")
                        if lbl:
                            dim_label = lbl
                            break
                    # Check if the label matches any allowed keyword
                    if not any(kw in dim_label for kw in allowed_labels):
                        continue
            e = dict(entry)
            e["metric_name_cn"] = name
            results.append(e)
        return results

    @staticmethod
    def get_dim_info(entry: dict) -> dict[str, Any]:
        """Extract dimension info from a metric entry.

        Returns:
          {
            "label": str,                    # dimension label for 云服务维度 column
            "needs_dim_resource_id": bool,   # whether 云服务维度资源ID is needed
            "instance_dim_name": str|None,   # dimension name with source="instance_id"
            "dim_resource_dim_name": str|None,  # dimension name with source="dim_resource_id"
          }
        """
        labels = set()
        needs_dim_res = False
        instance_dim_name = None
        dim_resource_dim_name = None
        for d in entry.get("dimensions", []):
            lbl = d.get("label")
            if lbl:
                labels.add(lbl.strip())
            if d.get("source") == "instance_id":
                instance_dim_name = d.get("name")
            elif d.get("source") == "dim_resource_id":
                needs_dim_res = True
                dim_resource_dim_name = d.get("name")
        return {
            "label": "、".join(sorted(labels)) if labels else "",
            "needs_dim_resource_id": needs_dim_res,
            "instance_dim_name": instance_dim_name,
            "dim_resource_dim_name": dim_resource_dim_name,
        }


def build_registry_path(cli_arg: Optional[str]) -> str:
    if cli_arg:
        return cli_arg
    return _default_metrics_path()
