"""Regression tests for the t-24 output columns and DCS instance-type detection.

Covered defects (QA round on PR #946):
  1. The writer emits "近一天（t-24）峰值" while the workbook template ships "t-24峰值";
     the mismatch appended a second copy of every t-24 column and wrote nothing into the
     template's own columns (`written=0`, column count 25 -> 31).
  2. `detect_dcs_instance_type` used the namespace-only CES query without attributing the
     returned metrics to the queried instance, so any cluster instance in the same region
     made a single-node instance look like a cluster; with no usable data it returned
     "single" instead of None.
"""

import json
import shutil
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from capacity import collector, excel_io
from capacity.excel_io import canonical_name, cell_get, read_excel, write_updates

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "capacity_assessment_template.xlsx"
SHEET = "保障重点实例_容量管理模板"

T24_SPELLINGS = [
    ("峰值", "近一天（t-24）峰值", 1.5),
    ("谷值", "近一天（t-24）谷值", 0.5),
    ("峰谷值增长倍数", "近一天（t-24）峰谷值增长倍数", 3.0),
    ("压力系数", "近一天（t-24）压力系数", 1.1),
    ("预计节日上限", "近一天（t-24）预计节日上限", 2.2),
    ("是否需要扩容", "近一天（t-24）是否需要扩容", "建议扩容"),
]


def _headers(ws):
    return [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)]


def _col(ws, name):
    """1-based column index located by canonical header name (template headers carry （必填）suffixes)."""
    target = canonical_name(name)
    for i in range(1, ws.max_column + 1):
        h = ws.cell(row=1, column=i).value
        if h is not None and canonical_name(h) == target:
            return i
    raise AssertionError(f"column not found: {name}")


@pytest.fixture()
def template_copy(tmp_path):
    dst = tmp_path / "template.xlsx"
    shutil.copyfile(TEMPLATE, dst)
    return str(dst)


def test_template_ships_t24_headers():
    """The shipped template must keep the t-24* header spelling the canonical map targets."""
    wb = load_workbook(str(TEMPLATE))
    try:
        ws = wb[SHEET]
        headers = _headers(ws)
    finally:
        wb.close()
    for suffix, writer_spelling, _ in T24_SPELLINGS:
        assert f"t-24{suffix}" in headers, f"template lost header t-24{suffix}"
        assert canonical_name(f"t-24{suffix}") == canonical_name(writer_spelling)


def test_write_updates_fills_template_t24_columns(template_copy):
    """written>0 and the column count must not grow: the t-24 values land in the template columns."""
    wb = load_workbook(template_copy)
    try:
        before = wb[SHEET].max_column
    finally:
        wb.close()

    updates = [{"row": 2, "column": "资源上限", "value": 100},
               {"row": 2, "column": "单位", "value": "GB"}]
    updates += [{"row": 2, "column": spelling, "value": value}
                for _, spelling, value in T24_SPELLINGS]

    result = write_updates(template_copy, updates)
    assert result["ok"] is True
    assert result["errors"] == []
    assert result["written"] == len(updates) > 0
    assert result["created_columns"] == []

    wb = load_workbook(template_copy)
    try:
        ws = wb[SHEET]
        assert ws.max_column == before, "t-24 write must not append duplicate columns"
        headers = _headers(ws)
        assert "近一天（t-24）峰值" not in headers
        assert len([h for h in headers if h and h.startswith("t-24")]) == 6
        for suffix, _, value in T24_SPELLINGS:
            col = headers.index(f"t-24{suffix}") + 1
            assert ws.cell(row=2, column=col).value == value
    finally:
        wb.close()


def test_write_updates_creates_template_spelling_once(tmp_path):
    """A workbook without t-24 columns gets exactly six columns, spelled like the template."""
    path = str(tmp_path / "bare.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    for i, header in enumerate(["region", "实例类型", "实例ID", "入口实例ID"], start=1):
        ws.cell(row=1, column=i, value=header)
    wb.save(path)

    updates = [{"row": 2, "column": spelling, "value": value}
               for _, spelling, value in T24_SPELLINGS]
    result = write_updates(path, updates)
    assert result["ok"] is True and result["written"] == 6
    assert sorted(result["created_columns"]) == sorted(f"t-24{s}" for s, _, _ in T24_SPELLINGS)

    wb = load_workbook(path)
    try:
        assert wb[SHEET].max_column == 4 + 6
        headers = _headers(wb[SHEET])
        assert len([h for h in headers if h and h.startswith("t-24")]) == 6
        assert not [h for h in headers if h and "近一天" in h]
    finally:
        wb.close()

    # Idempotent: a second write finds every column and adds none.
    second = write_updates(path, updates)
    assert second["written"] == 6 and second["created_columns"] == []
    wb = load_workbook(path)
    try:
        assert wb[SHEET].max_column == 4 + 6
    finally:
        wb.close()


def test_manual_t24_values_are_visible_in_both_spellings(template_copy):
    """Manual-first t-24 mode reads the template's own t-24峰值/谷值 columns."""
    wb = load_workbook(template_copy)
    try:
        ws = wb[SHEET]
        for header, value in (("t-24峰值", 12.0), ("t-24谷值", 4.0), ("实例ID", "dcs-1"),
                              ("实例类型", "DCS"), ("region", "cn-east-3")):
            ws.cell(row=2, column=_col(ws, header), value=value)
    finally:
        wb.save(template_copy)

    doc = read_excel(template_copy)
    cells = doc["rows"][0]["cells"]
    assert cell_get(cells, "近一天（t-24）峰值") == 12.0
    assert cell_get(cells, "t-24谷值") == 4.0
    # assessor builds its cell map canonically, so both spellings resolve to one key.
    from capacity.assessor import _cell_map
    cmap = _cell_map(doc["rows"][0])
    assert cmap["t-24峰值"] == 12.0 and cmap["t-24谷值"] == 4.0


def test_date_columns_still_insert_once(tmp_path):
    """Historical mode date columns keep working (insert after the anchor, no duplicates)."""
    path = str(tmp_path / "hist.xlsx")
    shutil.copyfile(TEMPLATE, path)
    result = write_updates(path, [{"row": 2, "column": "7/1峰值", "value": 3.0}])
    assert result["ok"] is True and result["written"] == 1
    wb = load_workbook(path)
    try:
        ws = wb[SHEET]
        headers = _headers(ws)
        assert headers.count("7/1峰值") == 1
        assert ws.cell(row=2, column=headers.index("7/1峰值") + 1).value == 3.0
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# DCS instance-type detection (CES namespace scoping)
# ---------------------------------------------------------------------------
class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ""


def _metric(name, dims):
    return {"metric_name": name,
            "dimensions": [{"name": n, "value": v} for n, v in dims]}


def _fake_run_factory(metrics_by_variant):
    """Stub subprocess.run: IAM/DCS probes fail, CES ListMetrics answers per query variant."""

    def _run(cmd, capture_output=True, text=True, timeout=None):
        if "KeystoneListUserProjects" in cmd:
            return _FakeProc("[]")
        if "ShowInstance" in cmd:
            return _FakeProc(json.dumps({"error_code": "DCS.0001"}))
        if "ListMetrics" in cmd:
            filtered = any(str(a).startswith("--dim.0=dcs_instance_id") for a in cmd)
            key = "filtered" if filtered else "namespace"
            return _FakeProc(json.dumps({"metrics": metrics_by_variant.get(key, [])}))
        return _FakeProc("", 1)

    return _run


def test_dcs_namespace_metrics_of_other_instances_do_not_pollute(monkeypatch):
    """Another instance's dcs_cluster_redis_node must not turn this single-node instance into a cluster."""
    metrics = {
        "filtered": [_metric("cpu_usage", [("dcs_instance_id", "inst-1")])],
        "namespace": [_metric("cpu_usage", [("dcs_instance_id", "inst-1")]),
                      _metric("node_memory_usage",
                              [("dcs_instance_id", "inst-other"),
                               ("dcs_cluster_redis_node", "node-1")])],
    }
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory(metrics))
    assert collector.detect_dcs_instance_type("cn-east-3", "inst-1") == "single"


def test_dcs_own_sub_nodes_still_detected(monkeypatch):
    """Metrics carrying this instance's id and a node dimension still classify as cluster."""
    metrics = {
        "filtered": [_metric("node_memory_usage",
                             [("dcs_instance_id", "inst-1"),
                              ("dcs_cluster_redis_node", "node-1")])],
        "namespace": [],
    }
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory(metrics))
    assert collector.detect_dcs_instance_type("cn-east-3", "inst-1") == "cluster"


def test_dcs_returns_none_when_no_metric_belongs_to_instance(monkeypatch):
    """Namespace-only data about other instances is no evidence: return None (expand all), not 'single'."""
    metrics = {
        "filtered": [],
        "namespace": [_metric("cpu_usage", [("dcs_instance_id", "inst-other")])],
    }
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory(metrics))
    assert collector.detect_dcs_instance_type("cn-east-3", "inst-1") is None


def test_dcs_returns_none_when_every_probe_fails(monkeypatch):
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory({}))
    assert collector.detect_dcs_instance_type("cn-east-3", "inst-1") is None


# ---------------------------------------------------------------------------
# JSON null-safety: CES answers {"metrics": null} for instances without metrics
# (nonexistent / unmonitored instance). Iterating null raised TypeError and took
# the whole `expand` command down instead of degrading gracefully.
# ---------------------------------------------------------------------------
def _null_payload_run_factory(payload):
    """Stub subprocess.run: IAM/DCS probes fail, every CES/AOM query returns `payload`."""

    def _run(cmd, capture_output=True, text=True, timeout=None):
        if "KeystoneListUserProjects" in cmd:
            return _FakeProc("[]")
        if "ShowInstance" in cmd or "ListInstances" in cmd:
            return _FakeProc("", 1)
        if "ListMetrics" in cmd or "ListSeries" in cmd:
            return _FakeProc(json.dumps(payload))
        return _FakeProc("", 1)

    return _run


def test_dcs_null_metrics_returns_none(monkeypatch):
    """{"metrics": null} must be treated as 'no evidence' (None), not crash the caller."""
    monkeypatch.setattr(collector.subprocess, "run",
                        _null_payload_run_factory({"metrics": None}))
    assert collector.detect_dcs_instance_type("cn-east-3", "inst-1") is None


def test_dms_and_geminidb_null_metrics_return_none(monkeypatch):
    monkeypatch.setattr(collector.subprocess, "run",
                        _null_payload_run_factory({"metrics": None}))
    assert collector.detect_dms_subtype("cn-east-3", "inst-1") is None
    assert collector.detect_geminidb_subtype("cn-east-3", "inst-1") is None


def test_discover_dim_values_tolerate_null_metrics(monkeypatch):
    monkeypatch.setattr(collector.subprocess, "run",
                        _null_payload_run_factory({"metrics": None}))
    assert collector._discover_via_ces("cn-east-3", "SYS.DCS", "dcs_instance_id",
                                       "inst-1", "dcs_cluster_redis_node",
                                       "hcloud", None, 10) == []
    monkeypatch.setattr(collector.subprocess, "run",
                        _null_payload_run_factory({"series": None}))
    assert collector._discover_via_aom("cn-east-3", "SYS.DCS", "dcs_instance_id",
                                       "inst-1", "dcs_cluster_redis_node",
                                       "hcloud", None, 10) == []


# ---------------------------------------------------------------------------
# Dimension discovery for node-level metrics + dimension-order-insensitive matching.
#
# CES matches --dim.0 on the *exact* dimension set, so an instance-filtered ListMetrics
# never returns node/broker-level metrics (they also carry dcs_cluster_redis_node /
# kafka_broker).  `expand` then fell back to the instance ID as 云服务维度资源ID and every
# node-level row failed to collect.  The discovery must retry the namespace-wide listing
# and attribute each metric by its instance dimension; and the response match must compare
# dimensions as a set, because CES returns them alphabetically.
# ---------------------------------------------------------------------------
def test_discover_dim_values_falls_back_to_namespace_listing(monkeypatch):
    metrics = {
        "filtered": [_metric("cpu_usage", [("dcs_instance_id", "inst-1")])],
        "namespace": [
            _metric("cpu_usage", [("dcs_instance_id", "inst-1")]),
            _metric("node_memory_usage",
                    [("dcs_instance_id", "inst-1"), ("dcs_cluster_redis_node", "node-1")]),
            _metric("node_memory_usage",
                    [("dcs_instance_id", "inst-1"), ("dcs_cluster_redis_node", "node-2")]),
            # another instance's nodes must not leak into the result
            _metric("node_memory_usage",
                    [("dcs_instance_id", "inst-other"), ("dcs_cluster_redis_node", "node-x")]),
        ],
    }
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory(metrics))
    warns: list[str] = []
    values = collector.discover_dim_values("cn-east-3", "SYS.DCS", "dcs_instance_id",
                                           "inst-1", "dcs_cluster_redis_node",
                                           warnings=warns)
    assert values == ["node-1", "node-2"]
    assert any("namespace-wide" in w for w in warns), warns


def test_discover_dim_values_falls_back_to_instance_id_with_warning(monkeypatch):
    """Nothing attributable to this instance → empty list, and the caller is told so."""
    metrics = {
        "filtered": [],
        "namespace": [_metric("cpu_usage", [("dcs_instance_id", "inst-other")])],
    }
    monkeypatch.setattr(collector.subprocess, "run", _fake_run_factory(metrics))
    warns: list[str] = []
    values = collector.discover_dim_values("cn-east-3", "SYS.DCS", "dcs_instance_id",
                                           "inst-1", "dcs_cluster_redis_node",
                                           warnings=warns)
    assert values == []
    assert any("falling back to the instance ID" in w for w in warns), warns


def test_call_batch_matches_dimensions_regardless_of_order(monkeypatch):
    """CES returns dimensions alphabetically; the request order must not decide the match."""
    response = {"metrics": [{
        "namespace": "SYS.DCS",
        "metric_name": "cpu_usage",
        "dimensions": [{"name": "dcs_cluster_redis_node", "value": "node-1"},
                       {"name": "dcs_instance_id", "value": "inst-1"}],
        "datapoints": [{"max": 42, "timestamp": 1}],
    }]}

    def _run(cmd, capture_output=True, text=True, timeout=None):
        return _FakeProc(json.dumps(response))

    monkeypatch.setattr(collector.subprocess, "run", _run)
    hit = collector.call_batch("cn-east-3", [{
        "namespace": "SYS.DCS", "metric_name": "cpu_usage",
        "dimensions": [{"name": "dcs_instance_id", "value": "inst-1"},
                       {"name": "dcs_cluster_redis_node", "value": "node-1"}],
    }], 0, 1000)
    assert hit[0]["datapoints"] == [{"max": 42, "timestamp": 1}]

    # A different node value is still a miss — the set comparison must not be over-broad.
    miss = collector.call_batch("cn-east-3", [{
        "namespace": "SYS.DCS", "metric_name": "cpu_usage",
        "dimensions": [{"name": "dcs_instance_id", "value": "inst-1"},
                       {"name": "dcs_cluster_redis_node", "value": "node-2"}],
    }], 0, 1000)
    assert miss[0]["error"] == "返回中未找到该指标"