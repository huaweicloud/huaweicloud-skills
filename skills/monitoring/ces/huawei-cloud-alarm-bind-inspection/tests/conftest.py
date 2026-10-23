import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def baseline_data():
    with open(FIXTURES_DIR / "indicator_baseline_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def rules_data():
    with open(FIXTURES_DIR / "online_alarm_rules_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def core_data():
    with open(FIXTURES_DIR / "core_instances_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def core_instances():
    return {
        "RDS": [
            {"instance_id": "mysql-instance-001", "raw_service": "RDS", "region": "cn-east-2", "metric_dimension": "rds_cluster_id"},
            {"instance_id": "mysql-instance-002", "raw_service": "RDS", "region": "cn-east-2", "metric_dimension": "rds_cluster_id"},
            {"instance_id": "pg-instance-001", "raw_service": "RDS", "region": "cn-east-2"},
            {"instance_id": "non-exist-instance-001", "raw_service": "RDS", "region": "cn-east-2", "instance_non_exist": True},
        ],
        "ELB": [
            {"instance_id": "elb-instance-001", "raw_service": "ELB", "region": "cn-east-2", "metric_dimension": "lbaas_instance_id"},
            {"instance_id": "elb-instance-002", "raw_service": "ELB", "region": "cn-north-1", "metric_dimension": "lbaas_instance_id"},
        ],
        "EIP": [
            {"instance_id": "eip-instance-001", "raw_service": "EIP", "region": "cn-east-2", "metric_dimension": "publicip_id"},
        ],
        "CFW": [
            {"instance_id": "cfw-instance-001", "raw_service": "CFW", "region": "cn-east-2"},
        ],
    }


@pytest.fixture
def rules():
    with open(FIXTURES_DIR / "online_alarm_rules_sample.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["rules"]


@pytest.fixture
def baseline():
    with open(FIXTURES_DIR / "indicator_baseline_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)
