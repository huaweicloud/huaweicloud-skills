#!/usr/bin/env python3
"""Regression tests for list rendering across the five service entries.

Covers Issue #1122 (dual-engine QA): list subcommands used to fail with
``unexpected response shape ... no list field found`` because the shared
renderer only probed a handful of attribute names, and legitimate empty
results were treated as errors.

The cases exercise every list operation in ECS/BMS/IMS/AS/CCE for both an
empty response and a non-empty response.  They do not call any cloud API:
a lightweight response double stands in for the SDK response object.
"""

import argparse
import contextlib
import importlib.util
import io
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import _common  # noqa: E402

SERVICE_MODULES = {
    "ecs": os.path.join(SCRIPTS_DIR, "huawei_ecs.py"),
    "bms": os.path.join(SCRIPTS_DIR, "huawei_bms.py"),
    "ims": os.path.join(SCRIPTS_DIR, "huawei_ims.py"),
    "as": os.path.join(SCRIPTS_DIR, "huawei_as.py"),
    "cce": os.path.join(SCRIPTS_DIR, "huawei_cce.py"),
}

REPRESENTATIVE_OPS = {
    "ecs": "list_flavors",
    "bms": "list_bare_metal_servers",
    "ims": "list_images",
    "as": "list_scaling_groups",
    "cce": "list_clusters",
}

SAMPLE_ITEMS = {
    "ecs": {"id": "s6.small.1", "name": "s6.small.1", "status": "available"},
    "bms": {"id": "bms-1", "name": "bms-one", "status": "ACTIVE"},
    "ims": {"id": "image-1", "name": "ubuntu", "status": "active"},
    "as": {
        "scaling_group_id": "group-1",
        "scaling_group_name": "web",
        "scaling_group_status": "INSERVICE",
    },
    "cce": {
        "metadata": {"uid": "cluster-1", "name": "prod"},
        "status": {"phase": "Available"},
    },
}

SDK_RESPONSES = {
    ("ecs", "list_flavors"): ("huaweicloudsdkecs.v2.model", "ListFlavorsResponse"),
    ("bms", "list_bare_metal_servers"): (
        "huaweicloudsdkbms.v1.model",
        "ListBareMetalServersResponse",
    ),
    ("ims", "list_images"): ("huaweicloudsdkims.v2.model", "ListImagesResponse"),
    ("as", "list_scaling_groups"): ("huaweicloudsdkas.v1.model", "ListScalingGroupsResponse"),
    ("cce", "list_clusters"): ("huaweicloudsdkcce.v3.model", "ListClustersResponse"),
}


def load_registry(service):
    path = SERVICE_MODULES[service]
    spec = importlib.util.spec_from_file_location(
        "skill_" + os.path.basename(path)[:-3], path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.REGISTRY


class ResponseDouble:
    def __init__(self, **attributes):
        for name, value in attributes.items():
            setattr(self, name, value)


def render(service, op_name, response):
    registry = load_registry(service)
    op = registry[op_name]
    args = argparse.Namespace(
        command=op_name, limit=20, all=False, json=False, fields=None
    )
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        _common._render_list(service, op, args, response)
    return buffer.getvalue()


def test_every_list_operation_declares_a_response_field():
    for service in SERVICE_MODULES:
        for op_name, op in load_registry(service).items():
            if not op.get("list"):
                continue
            fields = op.get("resp") or []
            assert fields, f"{service}:{op_name} declares no response list field"
            assert all(isinstance(field, str) and field for field in fields), (
                f"{service}:{op_name} has an invalid response list field: {fields}"
            )


def test_empty_results_render_zero_rows_for_all_services():
    for service, op_name in REPRESENTATIVE_OPS.items():
        op = load_registry(service)[op_name]
        response = ResponseDouble(**{op["resp"][0]: []})
        output = render(service, op_name, response)
        assert "共 0 条" in output, f"{service}:{op_name} did not render an empty result:\n{output}"
        assert "unexpected response shape" not in output


def test_non_empty_results_render_rows_for_all_services():
    for service, op_name in REPRESENTATIVE_OPS.items():
        op = load_registry(service)[op_name]
        response = ResponseDouble(**{op["resp"][0]: [SAMPLE_ITEMS[service]]})
        output = render(service, op_name, response)
        assert "共 1 条" in output, f"{service}:{op_name} did not render one row:\n{output}"
        assert "unexpected response shape" not in output


def test_empty_results_render_for_every_list_operation():
    for service in SERVICE_MODULES:
        for op_name, op in load_registry(service).items():
            if not op.get("list"):
                continue
            response = ResponseDouble(**{op["resp"][0]: []})
            output = render(service, op_name, response)
            assert "共 0 条" in output, (
                f"{service}:{op_name} did not render an empty result:\n{output}"
            )


def test_none_valued_response_field_is_a_known_empty_result():
    op = load_registry("ecs")["list_flavors"]
    response = ResponseDouble(**{op["resp"][0]: None})
    output = render("ecs", "list_flavors", response)
    assert "共 0 条" in output, output


def test_unknown_response_shape_still_raises():
    response = ResponseDouble(unrelated="value")
    args = argparse.Namespace(
        command="list_flavors", limit=20, all=False, json=False, fields=None
    )
    try:
        _common._render_list("ecs", {"resp": []}, args, response)
    except _common.RuntimeFailure as exc:
        assert "unexpected response shape" in str(exc)
    else:
        raise AssertionError("an unknown response shape must raise RuntimeFailure")


def test_real_sdk_response_fields_match_the_registry_when_sdk_is_installed():
    for (service, op_name), (module_path, class_name) in SDK_RESPONSES.items():
        try:
            module = __import__(module_path, fromlist=[class_name])
        except ImportError:
            continue
        response_class = getattr(module, class_name)
        op = load_registry(service)[op_name]
        for field in op["resp"]:
            assert hasattr(response_class, field), (
                f"{class_name} has no attribute {field!r} required by "
                f"{service}:{op_name}"
            )
