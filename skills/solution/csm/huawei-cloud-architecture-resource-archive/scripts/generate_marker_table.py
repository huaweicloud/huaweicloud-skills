#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone resource marker table generation (15-column format).

Reads the output directory of convert_to_tsc_json.py and generates the marker table Excel file,
column format (15 columns):

    customer name | region | resource_name | resource_id | resource_type |
    enterprise_project_id | enterprise project | is core business | business | resource group |
    downstream explicit | downstream inferred | architecture layer | spec | inference reason

Field mapping (resource_name/resource_id/
enterprise_project_id/downstream_explicit etc. are all taken from KooCLI query results).

Field format conventions (enforced uniformly when writing the table):
  - downstream inferred: one `resource name (resource ID)` per line, lines separated by newlines
  - spec: fixed key order, multi-line `key: value` — spec/vCPU/memory/image/disk(GB)/disk type
  Both accept dict / pre-formatted string / legacy comma string inputs, normalized by
  format_downstream_inferred() / format_spec().

Usage:
    python generate_marker_table.py \
      --tsc-dir <convert_to_tsc_json.py output directory> \
      --out <marker-table output directory> \
      [--customer <account-name>]

Dependency: openpyxl (pip install openpyxl)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
except ImportError:
    print("[FATAL] openpyxl is missing; install it first: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from marker_constants import (
    MARKER_TABLE_FILENAME, MARKER_TABLE_SHEET, RESOURCE_STORE_FILENAME,
    MARKER_HEADERS, HEADER_TO_KEY, CORE_HEADER, BUSINESS_HEADER, SPEC_KEYS,
    SPEC_HEADER, DOWNSTREAM_INFERRED_HEADER,
    DEFAULT_CORE_BUSINESS, DEFAULT_BUSINESS,
    REASON_VPC_LIST, REASON_OBS_BUCKETS, REASON_CCE_CLUSTER,
    REASON_ECS_SERVERS, REASON_ELB, REASON_GEIP,
)

# ═══════════════ Marker table format (15 columns) ═══════════════
# All column headers, the spec key order, and the output filename are imported
# from marker_constants.py so that customer-facing Chinese wording lives in one place.

VPC_KEYS = ["id", "name", "region", "enterprise_project_id"]
OBS_KEYS = ["bucketName", "regionId"]


def _text(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════ Field format normalization (downstream inferred / spec) ═══════════════════

def format_downstream_inferred(value) -> str:
    """Uniform format for downstream inferred: one `resource name (resource ID)` per line, separated by newlines.

    Supported inputs:
      - pre-formatted string (contains " (" or a newline) -> returned as-is, no re-processing
      - list[dict], e.g. [{"name": "subnet-a", "id": "xxx"}, ...] -> normalized output
      - list[str] / legacy comma-separated string -> one item per line
    """
    if not value:
        return ""
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ""
        if "\n" in s or " (" in s:
            return s
        items = [x.strip() for x in s.split(",") if x.strip()]
        return "\n".join(items)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                # Compatible with name/resource_name and id/resource_id/uid naming
                label = _text(item.get("name") or item.get("resource_name")
                              or item.get("resource_type") or item.get("type"))
                rid = _text(item.get("id") or item.get("resource_id") or item.get("uid"))
                if label and rid:
                    lines.append(f"{label} ({rid})")
                elif label or rid:
                    lines.append(label or rid)
            else:
                t = _text(item)
                if t:
                    lines.append(t)
        return "\n".join(lines)
    return _text(value)


def format_spec(value) -> str:
    """Uniform format for spec: multi-line `key: value`.

    Supported inputs:
      - dict (e.g. {SPEC_KEYS[0]: "ac7.xlarge.2", SPEC_KEYS[1]: "4U", ...}) -> rendered key by key, empty values dropped
      - pre-formatted string: passed through as-is when it is already `key: value` lines
        (key may be any label — ECS's 规格/vCPU..., DB's 规格/内存..., MRS's 版本/类型/...)
      - bare string (e.g. a flavor name) -> wrapped into the standard format with just that key
    """
    if not value:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_text(value.get(k))}" for k in SPEC_KEYS
                         if _text(value.get(k)))
    s = _text(value)
    if not s:
        return ""
    lines = s.splitlines()
    first_line = lines[0].strip()
    if any(first_line.startswith(k) and ":" in first_line for k in SPEC_KEYS):
        return s
    # Multi-line spec with every line matching `label: value` is already formatted
    # (service-specific labels like 版本/类型/Master); pass through unchanged.
    if len(lines) > 1 and all(": " in ln.strip() for ln in lines if ln.strip()):
        return s
    # Bare value (flavor name) or legacy "k=v" etc. -> wrap into the standard format
    return f"{SPEC_KEYS[0]}: {s}"


def _collect_rows(tsc_dir: Path, customer: str) -> list[dict]:
    """Scan the convert_to_tsc_json output directory and collect all resource rows (store fields)."""
    rows: list[dict] = []

    # VPC: {data: {list: [{id, name, region, enterprise_project_id, downstream_*}]}}
    for f in sorted((tsc_dir / "VPC" / "temp").glob("VPC_vpcs_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for v in (data.get("data") or {}).get("list") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(v.get("region")),
                "resource_name": _text(v.get("name")),
                "resource_id": _text(v.get("id")),
                "resource_type": "VPC",
                "enterprise_project_id": _text(v.get("enterprise_project_id")),
                "eps_project": v.get("eps_project") or "",
                "downstream_explicit": _text(v.get("downstream_explicit")),
                "downstream_inferred": v.get("downstream_inferred") or "",
                "inference_reason": REASON_VPC_LIST,
            })

    # OBS: {data: {detail: {_list_: [{bucketName, regionId}]}}}
    for f in sorted((tsc_dir / "OBS" / "temp").glob("obs_bucket_list_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        detail = (data.get("data") or {}).get("detail") or {}
        for b in detail.get("_list_") or []:
            name = _text(b.get("bucketName"))
            rows.append({
                "customer_name": customer,
                "region": _text(b.get("regionId")),
                "resource_name": name,
                "resource_id": name,  # OBS bucket name used as ID (globally unique)
                "resource_type": "OBS",
                "enterprise_project_id": _text(b.get("ep_id")),
                "eps_project": b.get("ep_name") or "",
                "inference_reason": REASON_OBS_BUCKETS,
            })

    # CCE: {account, interfaces: {cce_cluster_vm_new: [{metadata, region, project_id}]}}
    for f in sorted((tsc_dir / "CCE" / "temp").glob("CCE_account_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for c in (data.get("interfaces") or {}).get("cce_cluster_vm_new") or []:
            meta = c.get("metadata") or {}
            name = _text(meta.get("name"))
            uid = _text(meta.get("uid"))
            if not name:
                continue
            rows.append({
                "customer_name": customer,
                "region": _text(c.get("region")),
                "resource_name": name,
                "resource_id": uid,
                "resource_type": "CCE",
                "enterprise_project_id": _text(c.get("project_id")),
                "eps_project": c.get("eps_project") or "",
                "downstream_explicit": _text(c.get("downstream_explicit")),
                "downstream_inferred": c.get("downstream_inferred") or "",
                "spec": c.get("spec") or "",
                "spec_data": c.get("spec_data") or {},
                "inference_reason": REASON_CCE_CLUSTER,
            })

    # CCE K8s sub-resources: {rows: [{resource_name, resource_id, resource_type, ...}]}
    for f in sorted((tsc_dir / "CCE" / "temp").glob("CCE_k8s_rows_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(r.get("region")),
                "resource_name": _text(r.get("resource_name")),
                "resource_id": _text(r.get("resource_id")),
                "resource_type": _text(r.get("resource_type")) or "CCE_K8s",
                "enterprise_project_id": _text(r.get("enterprise_project_id")),
                "eps_project": r.get("eps_project") or "",
                "downstream_explicit": _text(r.get("downstream_explicit")),
                "downstream_inferred": r.get("downstream_inferred") or "",
                "inference_reason": _text(r.get("inference_reason")),
            })

    # VPC sub-services (SUBNET/ROUTETABLE/SECURITYGROUP/NETWORKACL/PEERING): {rows: [...]}
    for subdir, tag in (("SUBNET", "subnets"), ("ROUTETABLE", "route_tables"),
                        ("SECURITYGROUP", "security_groups"), ("NETWORKACL", "firewalls"),
                        ("PEERING", "vpc_peerings")):
        for f in sorted((tsc_dir / subdir / "temp").glob(f"{subdir}_{tag}_*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for r in data.get("rows") or []:
                rows.append({
                    "customer_name": customer,
                    "region": _text(r.get("region")),
                    "resource_name": _text(r.get("resource_name")),
                    "resource_id": _text(r.get("resource_id")),
                    "resource_type": _text(r.get("resource_type")) or "VPC_Sub",
                    "enterprise_project_id": _text(r.get("enterprise_project_id")),
                    "eps_project": r.get("eps_project") or "",
                    "downstream_explicit": _text(r.get("downstream_explicit")),
                    "downstream_inferred": r.get("downstream_inferred") or "",
                    "inference_reason": _text(r.get("inference_reason")),
                })

    # Database services: {rows: [...]} (RDS/DCS/DDS/DMS/GaussDB/GeminiDB/TaurusDB instances)
    for subdir in ("RDS", "DCS", "DDS", "DMS", "GAUSSDB", "GEMINIDB", "TAURUSDB"):
        for f in sorted((tsc_dir / subdir / "temp").glob(f"{subdir}_*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for r in data.get("rows") or []:
                rows.append({
                    "customer_name": customer,
                    "region": _text(r.get("region")),
                    "resource_name": _text(r.get("resource_name")),
                    "resource_id": _text(r.get("resource_id")),
                    "resource_type": _text(r.get("resource_type")) or subdir,
                    "enterprise_project_id": _text(r.get("enterprise_project_id")),
                    "eps_project": r.get("eps_project") or "",
                    "downstream_explicit": _text(r.get("downstream_explicit")),
                    "downstream_inferred": r.get("downstream_inferred") or "",
                    "spec": r.get("spec") or "",
                    "spec_data": r.get("spec_data") or {},
                    "inference_reason": _text(r.get("inference_reason")),
                })

    # LIVE streaming domains: {rows: [...]}
    for f in sorted((tsc_dir / "LIVE" / "temp").glob("LIVE_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(r.get("region")),
                "resource_name": _text(r.get("resource_name")),
                "resource_id": _text(r.get("resource_id")),
                "resource_type": _text(r.get("resource_type")) or "LIVE_Domain",
                "enterprise_project_id": _text(r.get("enterprise_project_id")),
                "eps_project": r.get("eps_project") or "",
                "downstream_explicit": _text(r.get("downstream_explicit")),
                "downstream_inferred": r.get("downstream_inferred") or "",
                "inference_reason": _text(r.get("inference_reason")),
            })

    # EIP / CDN / CCAAS / NAT / VPN / VPCEP / DNS / ER / SFS / WAF ...: {rows: [...]}
    # (spec/spec_data are passed through so converters like SFS/WAF that fill them keep them)
    for subdir in ("EIP", "CDN", "CCAAS", "NAT", "VPN", "VPCEP", "DNS", "ER", "WAF", "CFW", "CNAD", "CC2", "WORKSPACE", "DCAAS", "BMS", "CCI", "SFS", "CSS", "MRS", "DLI", "CloudTable", "BGP"):
        for f in sorted((tsc_dir / subdir / "temp").glob(f"{subdir}_*.json")):
            if "report" in f.name:
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            for r in data.get("rows") or []:
                rows.append({
                    "customer_name": customer,
                    "region": _text(r.get("region")),
                    "resource_name": _text(r.get("resource_name")),
                    "resource_id": _text(r.get("resource_id")),
                    "resource_type": _text(r.get("resource_type")) or subdir,
                    "enterprise_project_id": _text(r.get("enterprise_project_id")),
                    "eps_project": r.get("eps_project") or "",
                    "downstream_explicit": _text(r.get("downstream_explicit")),
                    "downstream_inferred": r.get("downstream_inferred") or "",
                    "spec": r.get("spec") or "",
                    "spec_data": r.get("spec_data") or {},
                    "inference_reason": _text(r.get("inference_reason")),
                })

    # ECS / ELB: {rows: [{resource_name, resource_id, spec, spec_data, downstream_*, ...}]}
    for f in sorted((tsc_dir / "ECS" / "temp").glob("ECS_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(r.get("region")),
                "resource_name": _text(r.get("resource_name")),
                "resource_id": _text(r.get("resource_id")),
                "resource_type": "ECS",
                "enterprise_project_id": _text(r.get("enterprise_project_id")),
                "eps_project": r.get("eps_project") or "",
                "downstream_explicit": _text(r.get("downstream_explicit")),
                "downstream_inferred": r.get("downstream_inferred") or "",
                "spec": r.get("spec") or "",
                "spec_data": r.get("spec_data") or {},
                "inference_reason": REASON_ECS_SERVERS,
            })
    for f in sorted((tsc_dir / "ELB" / "temp").glob("ELB_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(r.get("region")),
                "resource_name": _text(r.get("resource_name")),
                "resource_id": _text(r.get("resource_id")),
                "resource_type": "ELB",
                "enterprise_project_id": _text(r.get("enterprise_project_id")),
                "eps_project": r.get("eps_project") or "",
                "downstream_explicit": _text(r.get("downstream_explicit")),
                "downstream_inferred": r.get("downstream_inferred") or "",
                "inference_reason": REASON_ELB,
            })
    for f in sorted((tsc_dir / "GEIP" / "temp").glob("GEIP_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("rows") or []:
            rows.append({
                "customer_name": customer,
                "region": _text(r.get("region")),
                "resource_name": _text(r.get("resource_name")),
                "resource_id": _text(r.get("resource_id")),
                "resource_type": "GEIP",
                "enterprise_project_id": _text(r.get("enterprise_project_id")),
                "eps_project": r.get("eps_project") or "",
                "downstream_explicit": _text(r.get("downstream_explicit")),
                "downstream_inferred": r.get("downstream_inferred") or "",
                "inference_reason": REASON_GEIP,
            })

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate marker table from KooCLI query results")
    parser.add_argument("--tsc-dir", required=True, help="convert_to_tsc_json.py output directory")
    parser.add_argument("--out", required=True, help="Marker-table output directory")
    parser.add_argument("--customer", default="", help="Account name (defaults to the tsc-dir parent directory name)")
    args = parser.parse_args()

    tsc_dir = Path(args.tsc_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    customer = args.customer or tsc_dir.name

    rows = _collect_rows(tsc_dir, customer)
    if not rows:
        print(f"[marker] no resource rows found in {tsc_dir}", file=sys.stderr)
        return 1

    # Write Excel (15-column header)
    wb = Workbook()
    ws = wb.active
    ws.title = MARKER_TABLE_SHEET
    header_font = Font(bold=True)
    ws.append(MARKER_HEADERS)
    for cell in ws[1]:
        cell.font = header_font

    for row in rows:
        vals = []
        for h in MARKER_HEADERS:
            key = HEADER_TO_KEY[h]
            val = row.get(key, "")
            if h == DOWNSTREAM_INFERRED_HEADER:
                val = format_downstream_inferred(val)
            elif h == SPEC_HEADER:
                val = format_spec(val)
            elif h == CORE_HEADER and not _text(val):
                val = DEFAULT_CORE_BUSINESS          # Default: marked as core business
            elif h == BUSINESS_HEADER and not _text(val):
                val = DEFAULT_BUSINESS    # Default: grouped into the same business unit so the four-layer architecture renders completely
            vals.append(_text(val))
        ws.append(vals)

    # Auto-fit column widths
    for idx in range(1, len(MARKER_HEADERS) + 1):
        ws.column_dimensions[get_column_letter(idx)].width = 18

    out_path = out_dir / MARKER_TABLE_FILENAME
    wb.save(out_path)

    # Also save the store JSON (preserves structured spec/downstream_inferred)
    store = {"customer": customer, "generated_at": _now(), "rows": rows}
    store_path = out_dir / RESOURCE_STORE_FILENAME
    store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[marker] resource rows: {len(rows)}")
    print(f"[marker] marker table: {out_path}")
    print(f"[marker] store:        {store_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())