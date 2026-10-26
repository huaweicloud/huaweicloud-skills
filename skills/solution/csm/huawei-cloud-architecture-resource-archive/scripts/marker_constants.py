#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration loader for the marker-table pipeline.

Loads all customer-facing business strings from `templates/marker_config.json`
(per 规范 6.1, configuration templates live under templates/ as JSON) and exposes
them as module-level constants with the same names the rest of the codebase imports.

Why JSON instead of YAML: the standard library has no YAML parser, so JSON keeps the
pipeline dependency-free. The Chinese values are business data (customer-agreed column
headers, filenames, and default values), which 规范 3.3 allows in data/config — the
code itself stays English-only.
"""

from __future__ import annotations

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "templates" / "marker_config.json"


def _load() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Failed to load marker-table config from {_CONFIG_PATH}: {exc}"
        ) from exc


_cfg = _load()

# ── Output filenames (Excel + JSON) ──────────────────────────────
MARKER_TABLE_FILENAME = _cfg["output"]["marker_table_filename"]
MARKER_TABLE_SHEET = _cfg["output"]["marker_table_sheet"]
RESOURCE_STORE_FILENAME = _cfg["output"]["resource_store_filename"]

# ── Excel column headers (15 columns, customer-facing) ───────────
_h = _cfg["headers"]
CORE_HEADER = _h["core"]
CUSTOMER_HEADER = _h["customer"]
ENTERPRISE_PROJECT_HEADER = _h["enterprise_project"]
BUSINESS_HEADER = _h["business"]
RESOURCE_GROUP_HEADER = _h["resource_group"]
DOWNSTREAM_EXPLICIT_HEADER = _h["downstream_explicit"]
DOWNSTREAM_INFERRED_HEADER = _h["downstream_inferred"]
ARCHITECTURE_LAYER_HEADER = _h["architecture_layer"]
SPEC_HEADER = _h["spec"]
INFERENCE_REASON_HEADER = _h["inference_reason"]

MARKER_HEADERS = [
    CUSTOMER_HEADER,
    "region",
    "resource_name",
    "resource_id",
    "resource_type",
    "enterprise_project_id",
    ENTERPRISE_PROJECT_HEADER,
    CORE_HEADER,
    BUSINESS_HEADER,
    RESOURCE_GROUP_HEADER,
    DOWNSTREAM_EXPLICIT_HEADER,
    DOWNSTREAM_INFERRED_HEADER,
    ARCHITECTURE_LAYER_HEADER,
    SPEC_HEADER,
    INFERENCE_REASON_HEADER,
]

# Mapping from the customer-facing header to the internal store row key.
HEADER_TO_KEY = {
    CUSTOMER_HEADER: "customer_name",
    "region": "region",
    "resource_name": "resource_name",
    "resource_id": "resource_id",
    "resource_type": "resource_type",
    "enterprise_project_id": "enterprise_project_id",
    ENTERPRISE_PROJECT_HEADER: "eps_project",
    CORE_HEADER: "is_core_business",
    BUSINESS_HEADER: "business",
    RESOURCE_GROUP_HEADER: "group",
    DOWNSTREAM_EXPLICIT_HEADER: "downstream_explicit",
    DOWNSTREAM_INFERRED_HEADER: "downstream_inferred",
    ARCHITECTURE_LAYER_HEADER: "architecture_layer",
    SPEC_HEADER: "spec",
    INFERENCE_REASON_HEADER: "inference_reason",
}

# ── Spec column: fixed key order ─────────────────────────────────
# Each entry is {label, key}: label is the customer-facing Chinese key,
# key is the parallel internal English identifier used by call sites.
SPEC_KEYS = [entry["label"] for entry in _cfg["spec_keys"]]
SPEC_KEY_INTERNAL = [entry["key"] for entry in _cfg["spec_keys"]]
SPEC_KEY_TO_INTERNAL = dict(zip(SPEC_KEYS, SPEC_KEY_INTERNAL))

# ── Default cell values (when the field is empty) ────────────────
_d = _cfg["defaults"]
DEFAULT_CORE_BUSINESS = _d["core_business"]
DEFAULT_BUSINESS = _d["business"]

# ── Downstream relationship labels ───────────────────────────────
_dl = _cfg["downstream_labels"]
TYPE_LABELS = _dl["type_labels"]
SUBNET_LABEL = _dl["subnet"]
ROUTE_TABLE_LABEL = _dl["route_table"]
IMAGE_LABEL = _dl["image"]
CCE_NODE_LABEL = _dl["cce_node"]
INTER_REGION_BANDWIDTH_LABEL = _dl["inter_region_bandwidth"]
CCAAS_INTER_REGION_BANDWIDTH_LABEL = _dl["ccaas_inter_region_bandwidth"]
ASSOCIATED_INSTANCE_LABEL = _dl["associated_instance"]
ASSOCIATED_RESOURCE_LABEL = _dl["associated_resource"]
BACKEND_SERVER_LABEL = _dl["backend_server"]

# ── inference_reason literals (provenance written to store JSON) ─
_r = _cfg["reasons"]
REASON_KOOCLI_SUPPLEMENT = _r["koocli_supplement"]
REASON_CCE_CLUSTER = _r["cce_cluster"]
REASON_VPC_LIST = _r["vpc_list"]
REASON_OBS_BUCKETS = _r["obs_buckets"]
REASON_OBS_BUCKETS_RMS = _r["obs_buckets_rms"]
REASON_RMS_SUMMARY = _r["rms_summary"]
REASON_ECS_SERVERS = _r["ecs_servers"]
REASON_CCE_SUBRESOURCE = _r["cce_subresource"]
REASON_SIMPLE_LIST = _r["simple_list"]
REASON_EIP = _r["eip"]
REASON_LIVE_DOMAINS = _r["live_domains"]
REASON_CDN_DOMAINS = _r["cdn_domains"]
REASON_GEIP = _r["geip"]
REASON_ELB = _r["elb"]

# ── KooCLI runtime match strings (hcloud returns these Chinese prompts) ─
_hp = _cfg["hcloud_prompts"]
HCLOUD_CONFIG_OK_PROMPT = _hp["config_ok"]
HCLOUD_MULTI_VERSION_PROMPT_HINT = _hp["multi_version_hint"]
