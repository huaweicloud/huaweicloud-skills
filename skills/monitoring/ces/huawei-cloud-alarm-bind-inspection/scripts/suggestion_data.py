#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
from workspace import WORKSPACE_DIR, INTERMEDIATE_DIR

DEFAULT_BIND_REPORT = str(Path(INTERMEDIATE_DIR) / "indicator_bind_report.json")
DEFAULT_BASELINE = str(Path(INTERMEDIATE_DIR) / "indicator_baseline.json")
DEFAULT_RULES = str(Path(INTERMEDIATE_DIR) / "online_alarm_rules.json")
DEFAULT_EVENT_REPORT = str(Path(INTERMEDIATE_DIR) / "event_bind_report.json")
DEFAULT_EVENT_BASELINE = str(Path(INTERMEDIATE_DIR) / "event_baseline.json")
DEFAULT_OUTPUT = str(Path(WORKSPACE_DIR) / "suggestion_report.html")
DEFAULT_AOM_INDICATOR_REPORT = str(Path(INTERMEDIATE_DIR) / "aom_indicator_bind_report.json")
DEFAULT_AOM_EVENT_REPORT = str(Path(INTERMEDIATE_DIR) / "aom_event_bind_report.json")

CORE_TO_BASELINE_SVC = {"EIP": "VPC"}

def _safe_int(val, default=0):
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)
    return default

METRIC_DETAIL_COLUMNS = [
    ("指标ID", "指标ID"),
    ("指标名称", "指标名称"),
    ("命名空间", "命名空间"),
    ("重要告警阈值", "重要告警阈值"),
    ("紧急告警阈值", "紧急告警阈值"),
    ("告警频率", "告警频率"),
    ("采集周期(秒)", "采集周期（秒）"),
    ("比较关系", "比较关系"),
    ("连续触发次数", "连续触发次数"),
    ("默认单位", "默认单位"),
    ("备注", "备注"),
]

FIXED_TABLE_COLUMNS = ["实例ID", "Region", "服务", "指标维度"]

EVENT_DETAIL_COLUMNS = [
    "事件ID",
    "事件名称",
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_svc_summary_to_stat_data(svc_summary):
    svc_stat_data = []
    for svc_dim_key in sorted(svc_summary.keys()):
        info = svc_summary[svc_dim_key]
        if svc_dim_key.endswith("|无指标基线"):
            continue
        display_name = svc_dim_key.replace("|", " - ") if "|" in svc_dim_key else svc_dim_key
        is_no_rules = svc_dim_key.endswith("|未配置")
        is_no_baseline = svc_dim_key.endswith("|无指标基线")
        missing_metrics = info["missing_metrics"]
        baseline_metrics_count = info.get("baseline_metrics_count", 0)
        bound_baseline = info.get("bound_baseline", 0)
        total_baseline = info.get("total_baseline", 0)
        if is_no_rules or is_no_baseline:
            rate_str = "N/A"
            baseline_metrics_count = "-"
            fully_bound = "-"
            partially_bound = "-"
        else:
            if total_baseline > 0:
                rate_str = f"{bound_baseline / total_baseline * 100:.1f}%"
            else:
                rate_str = "N/A"
            fully_bound = info.get("fully_bound", 0)
            partially_bound = info.get("partially_bound", 0)
        svc_stat_data.append({
            "svc_dim": display_name,
            "total_inst": info.get("total_instances", 0),
            "baseline_metrics_count": baseline_metrics_count,
            "fully": fully_bound,
            "partially": partially_bound,
            "unbound": info.get("unbound", 0),
            "bind_rate": rate_str,
            "missing_metrics": missing_metrics,
            "is_no_rules": is_no_rules,
            "is_no_baseline": is_no_baseline,
            "bound_baseline": bound_baseline if not is_no_rules else "-",
            "total_baseline": total_baseline if not is_no_rules else "-",
            "monitor_system": "CES",
        })
    return svc_stat_data


def process_report_instances(report, baseline_by_svc_dim):
    suggestions = []
    total_missing_metrics = 0
    instances_needing_action_ids = set()
    total_bound_all = 0
    total_baseline_all = 0
    no_baseline_instances = []
    non_exist_instances = []

    for inst in report.get("by_instance", []):
        is_no_rules = inst.get("bound_status") == "no_online_rules"
        is_no_baseline = inst.get("bound_status") == "no_baseline"
        is_non_exist = inst.get("bound_status") == "instance_non_exist"

        if is_non_exist:
            ne = {
                "instance_id": inst["instance_id"],
                "service": inst["service"],
                "raw_service": inst.get("raw_service", inst["service"]),
                "region": inst.get("region", ""),
            }
            non_exist_instances.append(ne)
            continue

        if is_no_rules:
            instances_needing_action_ids.add(inst["instance_id"])
            total_bound_all += _safe_int(inst.get("baseline_metrics_bound", 0))
            total_baseline_all += _safe_int(inst.get("baseline_metrics_total", 0))
            total_missing_metrics += _safe_int(inst.get("baseline_metrics_missing", 0))

            svc = inst["service"]
            baseline_dim = inst.get("metric_dimension", "")
            missing_details = []
            if baseline_dim:
                baseline_svc = CORE_TO_BASELINE_SVC.get(svc, svc)
                svc_dim_baseline = baseline_by_svc_dim.get((baseline_svc, baseline_dim), {})
                for mid, rec in sorted(svc_dim_baseline.items()):
                    missing_details.append({
                        "指标ID": rec["指标ID"],
                        "指标名称": rec["指标名称"],
                        "命名空间": rec["命名空间"],
                        "指标维度-中文": rec.get("指标维度-中文", ""),
                        "重要告警阈值": rec.get("重要告警阈值", ""),
                        "紧急告警阈值": rec.get("紧急告警阈值", ""),
                        "告警频率": rec.get("告警频率", ""),
                        "采集周期（秒）": rec.get("采集周期（秒）", ""),
                        "比较关系": rec.get("比较关系", ""),
                        "连续触发次数": rec.get("连续触发次数", ""),
                        "默认单位": rec.get("默认单位", ""),
                        "备注": rec.get("备注", ""),
                    })

            s = {
                "instance_id": inst["instance_id"],
                "region": inst.get("region", ""),
                "service": inst["service"],
                "raw_service": inst.get("raw_service", inst["service"]),
                "metric_dimension": inst.get("metric_dimension", "未配置"),
                "metric_dimension_cn": inst.get("metric_dimension_cn", "未配置"),
                "baseline_metrics_total": inst.get("baseline_metrics_total", "N/A"),
                "baseline_metrics_bound": inst.get("baseline_metrics_bound", 0),
                "baseline_metrics_missing": inst.get("baseline_metrics_missing", "N/A"),
                "bind_rate": inst.get("bind_rate", "0.0%"),
                "bound_status": "no_online_rules",
                "missing_metrics": missing_details,
            }
            suggestions.append(s)
            continue

        if is_no_baseline:
            nb = {
                "instance_id": inst["instance_id"],
                "service": inst["service"],
                "raw_service": inst.get("raw_service", inst["service"]),
                "covering_rules_count": inst.get("covering_rules_count", 0),
            }
            no_baseline_instances.append(nb)
            continue

        metrics_coverage = inst.get("metrics_coverage", {})
        missing_ids = [mid for mid, covered in metrics_coverage.items() if not covered]
        total_bound_all += _safe_int(inst["baseline_metrics_bound"])
        total_baseline_all += _safe_int(inst["baseline_metrics_total"])
        if not missing_ids:
            continue

        svc = inst["service"]
        baseline_dim = inst.get("metric_dimension", "")
        baseline_svc = CORE_TO_BASELINE_SVC.get(svc, svc)
        svc_dim_baseline = baseline_by_svc_dim.get((baseline_svc, baseline_dim), {})

        missing_details = []
        for mid in sorted(missing_ids):
            rec = svc_dim_baseline.get(mid)
            if rec:
                missing_details.append({
                    "指标ID": rec["指标ID"],
                    "指标名称": rec["指标名称"],
                    "命名空间": rec["命名空间"],
                    "指标维度-中文": rec.get("指标维度-中文", ""),
                    "重要告警阈值": rec.get("重要告警阈值", ""),
                    "紧急告警阈值": rec.get("紧急告警阈值", ""),
                    "告警频率": rec.get("告警频率", ""),
                    "采集周期（秒）": rec.get("采集周期（秒）", ""),
                    "比较关系": rec.get("比较关系", ""),
                    "连续触发次数": rec.get("连续触发次数", ""),
                    "默认单位": rec.get("默认单位", ""),
                    "备注": rec.get("备注", ""),
                })
            else:
                missing_details.append({
                    "指标ID": mid,
                    "指标名称": "未知（基线中未找到）",
                })

        total_missing_metrics += len(missing_ids)
        instances_needing_action_ids.add(inst["instance_id"])

        s = {
            "instance_id": inst["instance_id"],
            "region": inst.get("region", ""),
            "service": svc,
            "raw_service": inst.get("raw_service", svc),
            "metric_dimension": baseline_dim,
            "metric_dimension_cn": inst.get("metric_dimension_cn", ""),
            "baseline_metrics_total": inst["baseline_metrics_total"],
            "baseline_metrics_bound": inst["baseline_metrics_bound"],
            "baseline_metrics_missing": inst["baseline_metrics_missing"],
            "bind_rate": inst["bind_rate"],
            "bound_status": inst["bound_status"],
            "missing_metrics": missing_details,
        }
        suggestions.append(s)

    return suggestions, total_missing_metrics, instances_needing_action_ids, total_bound_all, total_baseline_all, no_baseline_instances, non_exist_instances


def build_svc_summary(suggestions, report_by_service_dimension):
    svc_missing = defaultdict(lambda: {"missing_metric_ids": set(), "bound_baseline": 0, "total_baseline": 0})
    for s in suggestions:
        svc_dim_key = s["service"] + "|" + s.get("metric_dimension", "")
        svc_missing[svc_dim_key]["missing_metric_ids"].update(m.get("指标ID", "") for m in s.get("missing_metrics", []))
        if s["bound_status"] not in ("no_online_rules", "no_baseline"):
            svc_missing[svc_dim_key]["bound_baseline"] += _safe_int(s["baseline_metrics_bound"])
            svc_missing[svc_dim_key]["total_baseline"] += _safe_int(s["baseline_metrics_total"])

    svc_summary = {}
    for svc_dim_key, info in report_by_service_dimension.items():
        is_no_rules = svc_dim_key.endswith("|未配置")
        is_no_baseline = svc_dim_key.endswith("|无指标基线")
        missing_info = svc_missing.get(svc_dim_key, {"missing_metric_ids": set(), "bound_baseline": 0, "total_baseline": 0})
        if is_no_rules or is_no_baseline:
            svc_summary[svc_dim_key] = {
                "instances": 0,
                "missing_metrics": 0,
                "baseline_metrics_count": "-",
                "fully_bound": "-",
                "partially_bound": "-",
                "unbound": info.get("total_instances", 0),
                "total_instances": info.get("total_instances", 0),
                "bound_baseline": "-",
                "total_baseline": "-",
            }
        else:
            total_inst = info.get("total_instances", 0)
            bound_inst = info.get("bound_instances", 0)
            svc_summary[svc_dim_key] = {
                "instances": 0,
                "missing_metrics": len(missing_info["missing_metric_ids"]),
                "baseline_metrics_count": info.get("baseline_metrics_count", 0),
                "fully_bound": info.get("fully_bound_instances", 0),
                "partially_bound": info.get("partially_bound_instances", 0),
                "unbound": info.get("unbound_instances", 0),
                "total_instances": total_inst,
                "bound_baseline": info.get("bound_baseline", bound_inst * info.get("baseline_metrics_count", 0)),
                "total_baseline": info.get("total_baseline", total_inst * info.get("baseline_metrics_count", 0)),
            }

    return svc_summary
