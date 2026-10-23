import json
import pytest
from collections import Counter
from bind_analysis import _analyze
from suggestion_data import process_report_instances


@pytest.fixture
def report(core_instances, rules, baseline):
    return _analyze(core_instances, rules, baseline)


@pytest.fixture
def baseline_by_svc_dim(baseline):
    b = {}
    for rec in baseline["records"]:
        svc = rec["云服务简称"]
        dim = rec.get("指标维度", "")
        key = (svc, dim)
        if key not in b:
            b[key] = {}
        b[key][rec["指标ID"]] = rec
    return b


class TestRegressionBoundStatus:
    """回归测试：确保各 bound_status 的实例数量不发生意外变化"""

    def test_total_instance_count(self, report):
        assert report["summary"]["total_instances"] == 8

    def test_bound_status_distribution(self, report):
        counter = Counter(i["bound_status"] for i in report["by_instance"])
        assert counter["fully_bound"] == 4
        assert counter["no_online_rules"] == 2
        assert counter["no_baseline"] == 1
        assert counter["instance_non_exist"] == 1

    def test_no_default_dim_assignment_regression(self, report):
        """回归：无 metric_dimension 的实例不应被默认分配维度"""
        pg = [i for i in report["by_instance"] if i["instance_id"] == "pg-instance-001"]
        assert len(pg) == 1
        assert pg[0]["metric_dimension"] == ""
        assert pg[0]["metric_dimension_cn"] == "未配置"
        assert "postgresql_cluster_id" not in pg[0]["metric_dimension"]


class TestRegressionSuggestionOutput:
    """回归测试：确保补齐建议输出结构不发生意外变化"""

    def test_suggestion_count(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        assert len(suggestions) == 2

    def test_non_exist_not_in_suggestions(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, non_exist = process_report_instances(report, baseline_by_svc_dim)
        ids = {s["instance_id"] for s in suggestions}
        assert "non-exist-instance-001" not in ids
        assert len(non_exist) == 1

    def test_no_baseline_not_in_suggestions(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, no_baseline, _ = process_report_instances(report, baseline_by_svc_dim)
        ids = {s["instance_id"] for s in suggestions}
        assert "cfw-instance-001" not in ids
        assert len(no_baseline) == 1

    def test_weipei_instance_has_empty_missing_metrics(self, report, baseline_by_svc_dim):
        suggestions, _, _, _, _, _, _ = process_report_instances(report, baseline_by_svc_dim)
        pg = [s for s in suggestions if s["instance_id"] == "pg-instance-001"]
        assert len(pg) == 1
        assert pg[0]["missing_metrics"] == []


class TestRegressionServiceDimension:
    """回归测试：确保 by_service_dimension 结构不发生意外变化"""

    def test_weipei_key_exists(self, report):
        assert "RDS|未配置" in report["by_service_dimension"]

    def test_no_baseline_key_exists(self, report):
        assert "CFW|无指标基线" in report["by_service_dimension"]

    def test_non_exist_not_in_service_dimension(self, report):
        for key in report["by_service_dimension"]:
            assert "non-exist" not in key.lower()
            assert "无该实例" not in key

    def test_weipei_has_n_a_rate(self, report):
        info = report["by_service_dimension"]["RDS|未配置"]
        assert info["avg_bind_rate"] == "N/A"
        assert info["bound_instances"] == "-"
        assert info["baseline_metrics_count"] == "-"


class TestRegressionSummary:
    """回归测试：确保 summary 字段完整"""

    def test_summary_fields(self, report):
        s = report["summary"]
        assert "total_instances" in s
        assert "bound_instances" in s
        assert "overall_rate" in s
        assert "total_bound_baseline" in s
        assert "total_baseline_metrics" in s
        assert "no_rules_instances" in s
        assert "no_baseline_instances" in s

    def test_no_rules_count(self, report):
        assert report["summary"]["no_rules_instances"] == 2

    def test_no_baseline_count(self, report):
        assert report["summary"]["no_baseline_instances"] == 1
