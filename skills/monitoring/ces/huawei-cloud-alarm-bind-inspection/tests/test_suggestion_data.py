import pytest
from collections import defaultdict
from suggestion_data import process_report_instances, build_svc_summary, convert_svc_summary_to_stat_data
from bind_analysis import _analyze


@pytest.fixture
def report(core_instances, rules, baseline):
    return _analyze(core_instances, rules, baseline)


@pytest.fixture
def baseline_by_svc_dim(baseline):
    b = defaultdict(list)
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        b[(svc, dim)].append(rec)
    b_dict = {}
    for k, v in b.items():
        b_dict[k] = {r["指标ID"]: r for r in v}
    return b_dict


class TestProcessReportInstances:
    def test_return_tuple_length(self, report, baseline_by_svc_dim):
        result = process_report_instances(report, baseline_by_svc_dim)
        assert len(result) == 7

    def test_non_exist_collected(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, non_exist = process_report_instances(report, baseline_by_svc_dim)
        assert len(non_exist) == 1
        assert non_exist[0]["instance_id"] == "non-exist-instance-001"

    def test_no_baseline_collected(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, no_baseline, _ = process_report_instances(report, baseline_by_svc_dim)
        assert len(no_baseline) == 1
        assert no_baseline[0]["instance_id"] == "cfw-instance-001"

    def test_no_online_rules_with_dim_has_missing_metrics(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        elb_002 = [s for s in suggestions if s["instance_id"] == "elb-instance-002"]
        assert len(elb_002) == 1
        assert elb_002[0]["metric_dimension_cn"] == "弹性负载均衡"
        assert len(elb_002[0]["missing_metrics"]) > 0

    def test_no_online_rules_without_dim_has_empty_missing(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        pg_001 = [s for s in suggestions if s["instance_id"] == "pg-instance-001"]
        assert len(pg_001) == 1
        assert pg_001[0]["metric_dimension_cn"] == "未配置"
        assert pg_001[0]["missing_metrics"] == []

    def test_fully_bound_not_in_suggestions(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        ids = {s["instance_id"] for s in suggestions}
        assert "mysql-instance-001" not in ids
        assert "mysql-instance-002" not in ids

    def test_instances_needing_action(self, report, baseline_by_svc_dim):
        _, _, action_ids, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        assert "elb-instance-002" in action_ids
        assert "pg-instance-001" in action_ids
        assert "non-exist-instance-001" not in action_ids
        assert "cfw-instance-001" not in action_ids
        assert "mysql-instance-001" not in action_ids


class TestBuildSvcSummary:
    def test_weipei_in_summary(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        svc_summary = build_svc_summary(suggestions, report["by_service_dimension"])
        assert "RDS|未配置" in svc_summary
        assert svc_summary["RDS|未配置"]["total_instances"] == 1

    def test_no_baseline_in_summary(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        svc_summary = build_svc_summary(suggestions, report["by_service_dimension"])
        assert "CFW|无指标基线" in svc_summary


class TestConvertSvcSummaryToStatData:
    def test_weipei_treated_as_no_rules(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        svc_summary = build_svc_summary(suggestions, report["by_service_dimension"])
        stat_data = convert_svc_summary_to_stat_data(svc_summary)
        weipei = [s for s in stat_data if "未配置" in s["svc_dim"]]
        assert len(weipei) >= 1
        assert weipei[0]["is_no_rules"] is True

    def test_no_baseline_excluded_from_stat(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        svc_summary = build_svc_summary(suggestions, report["by_service_dimension"])
        stat_data = convert_svc_summary_to_stat_data(svc_summary)
        no_baseline = [s for s in stat_data if "无指标基线" in s["svc_dim"]]
        assert len(no_baseline) == 0
