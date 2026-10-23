import pytest
from bind_analysis import (
    _analyze,
    _collect_instance_online_dims,
    _extract_service_from_namespace,
    _is_wildcard_rule,
    _match_instance_in_resources,
    get_rule_service,
    get_rule_metrics,
    _dim_key_matches_rule,
)


class TestExtractServiceFromNamespace:
    def test_normal(self):
        assert _extract_service_from_namespace("SYS.RDS") == "RDS"

    def test_no_prefix(self):
        assert _extract_service_from_namespace("RDS") == "RDS"

    def test_empty(self):
        assert _extract_service_from_namespace("") == ""


class TestIsWildcardRule:
    def test_empty_resources(self, rules):
        elb_rule = [r for r in rules if r["namespace"] == "SYS.ELB"][0]
        assert _is_wildcard_rule(elb_rule) is True

    def test_non_wildcard(self, rules):
        rds_rule = [r for r in rules if r["namespace"] == "SYS.RDS"][0]
        assert _is_wildcard_rule(rds_rule) is False


class TestMatchInstanceInResources:
    def test_match(self, rules):
        rds_rule = [r for r in rules if r["namespace"] == "SYS.RDS"][0]
        result = _match_instance_in_resources("mysql-instance-001", rds_rule.get("resources", []))
        assert result == "rds_cluster_id"

    def test_no_match(self, rules):
        rds_rule = [r for r in rules if r["namespace"] == "SYS.RDS"][0]
        result = _match_instance_in_resources("non-existent", rds_rule.get("resources", []))
        assert result is None


class TestGetRuleService:
    def test_rds(self, rules):
        rds_rule = [r for r in rules if r["namespace"] == "SYS.RDS"][0]
        assert get_rule_service(rds_rule) == "RDS"

    def test_vpc_eip(self, rules):
        eip_rule = [r for r in rules if r["namespace"] == "SYS.VPC"][0]
        assert get_rule_service(eip_rule) == "EIP"


class TestGetRuleMetrics:
    def test_normal(self, rules):
        rds_rule = [r for r in rules if r["namespace"] == "SYS.RDS"][0]
        metrics = get_rule_metrics(rds_rule)
        assert "rds_mysql_metric1" in metrics


class TestCollectInstanceOnlineDims:
    def test_non_wildcard_match(self, rules, baseline):
        from collections import defaultdict
        baseline_by_svc_dim = defaultdict(list)
        for rec in baseline["records"]:
            svc = rec["云服务简称"]
            dim = rec.get("指标维度", "")
            baseline_by_svc_dim[(svc, dim)].append(rec)

        rds_rules = [r for r in rules if get_rule_service(r) == "RDS"]
        dim_metrics, count = _collect_instance_online_dims(
            "mysql-instance-001", rds_rules,
            inst_region="cn-east-2",
            inst_metric_dimension="rds_cluster_id",
            baseline_svc="RDS",
            baseline_by_svc_dim=baseline_by_svc_dim,
        )
        assert count == 1
        assert "rds_cluster_id" in dim_metrics
        assert "rds_mysql_metric1" in dim_metrics["rds_cluster_id"]

    def test_wildcard_match(self, rules, baseline):
        from collections import defaultdict
        baseline_by_svc_dim = defaultdict(list)
        for rec in baseline["records"]:
            svc = rec["云服务简称"]
            dim = rec.get("指标维度", "")
            baseline_by_svc_dim[(svc, dim)].append(rec)

        elb_rules = [r for r in rules if get_rule_service(r) == "ELB"]
        dim_metrics, count = _collect_instance_online_dims(
            "elb-instance-001", elb_rules,
            inst_region="cn-east-2",
            inst_metric_dimension="lbaas_instance_id",
            baseline_svc="ELB",
            baseline_by_svc_dim=baseline_by_svc_dim,
        )
        assert count == 1
        assert "lbaas_instance_id" in dim_metrics
        assert "elb_metric1" in dim_metrics["lbaas_instance_id"]

    def test_no_match(self, rules, baseline):
        from collections import defaultdict
        baseline_by_svc_dim = defaultdict(list)
        for rec in baseline["records"]:
            svc = rec["云服务简称"]
            dim = rec.get("指标维度", "")
            baseline_by_svc_dim[(svc, dim)].append(rec)

        rds_rules = [r for r in rules if get_rule_service(r) == "RDS"]
        dim_metrics, count = _collect_instance_online_dims(
            "non-existent-instance", rds_rules,
            inst_region="cn-east-2",
            inst_metric_dimension="rds_cluster_id",
            baseline_svc="RDS",
            baseline_by_svc_dim=baseline_by_svc_dim,
        )
        assert count == 0
        assert len(dim_metrics) == 0

    def test_vpc_eip_wildcard(self, rules, baseline):
        from collections import defaultdict
        baseline_by_svc_dim = defaultdict(list)
        for rec in baseline["records"]:
            svc = rec["云服务简称"]
            dim = rec.get("指标维度", "")
            baseline_by_svc_dim[(svc, dim)].append(rec)

        eip_rules = [r for r in rules if get_rule_service(r) == "EIP"]
        dim_metrics, count = _collect_instance_online_dims(
            "eip-instance-001", eip_rules,
            inst_region="cn-east-2",
            inst_metric_dimension="publicip_id",
            baseline_svc="VPC",
            baseline_by_svc_dim=baseline_by_svc_dim,
        )
        assert count == 1
        assert "publicip_id" in dim_metrics
        assert "eip_metric1" in dim_metrics["publicip_id"]


class TestAnalyze:
    def test_instance_count(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        assert report["summary"]["total_instances"] == 8

    def test_instance_non_exist(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        non_exist = [i for i in report["by_instance"] if i["bound_status"] == "instance_non_exist"]
        assert len(non_exist) == 1
        assert non_exist[0]["instance_id"] == "non-exist-instance-001"
        assert non_exist[0]["metric_dimension_cn"] == "无该实例"

    def test_no_baseline(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        no_baseline = [i for i in report["by_instance"] if i["bound_status"] == "no_baseline"]
        assert len(no_baseline) == 1
        assert no_baseline[0]["instance_id"] == "cfw-instance-001"
        assert no_baseline[0]["metric_dimension_cn"] == "无指标基线"

    def test_fully_bound(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        fully_bound = [i for i in report["by_instance"] if i["bound_status"] == "fully_bound"]
        assert len(fully_bound) == 4
        ids = {i["instance_id"] for i in fully_bound}
        assert "mysql-instance-001" in ids
        assert "mysql-instance-002" in ids
        assert "elb-instance-001" in ids
        assert "eip-instance-001" in ids

    def test_no_online_rules_with_metric_dimension(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        no_rules = [i for i in report["by_instance"] if i["bound_status"] == "no_online_rules"]
        elb_002 = [i for i in no_rules if i["instance_id"] == "elb-instance-002"]
        assert len(elb_002) == 1
        assert elb_002[0]["metric_dimension"] == "lbaas_instance_id"
        assert elb_002[0]["metric_dimension_cn"] == "弹性负载均衡"

    def test_no_online_rules_without_metric_dimension(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        no_rules = [i for i in report["by_instance"] if i["bound_status"] == "no_online_rules"]
        pg_001 = [i for i in no_rules if i["instance_id"] == "pg-instance-001"]
        assert len(pg_001) == 1
        assert pg_001[0]["metric_dimension"] == ""
        assert pg_001[0]["metric_dimension_cn"] == "未配置"

    def test_no_default_dim_assignment(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        pg_001 = [i for i in report["by_instance"] if i["instance_id"] == "pg-instance-001"]
        assert len(pg_001) == 1
        assert pg_001[0]["metric_dimension"] == ""
        assert pg_001[0]["metric_dimension_cn"] == "未配置"
        assert pg_001[0]["bound_status"] == "no_online_rules"

    def test_by_service_dimension_has_weipei(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        svc_dims = report["by_service_dimension"]
        assert "RDS|未配置" in svc_dims
        assert svc_dims["RDS|未配置"]["total_instances"] == 1

    def test_by_service_dimension_has_no_baseline(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        svc_dims = report["by_service_dimension"]
        assert "CFW|无指标基线" in svc_dims
        assert svc_dims["CFW|无指标基线"]["total_instances"] == 1

    def test_instance_non_exist_not_in_svc_dimension(self, core_instances, rules, baseline):
        report = _analyze(core_instances, rules, baseline)
        svc_dims = report["by_service_dimension"]
        for key in svc_dims:
            assert "non-exist" not in key.lower()

    def test_dedup_instances(self, rules, baseline):
        core_instances = {
            "RDS": [
                {"instance_id": "dup-instance-001", "raw_service": "RDS", "region": "cn-east-2", "metric_dimension": "rds_cluster_id"},
                {"instance_id": "dup-instance-001", "raw_service": "RDS", "region": "cn-east-2", "metric_dimension": "rds_cluster_id"},
            ],
        }
        report = _analyze(core_instances, rules, baseline)
        assert report["summary"]["total_instances"] == 1
