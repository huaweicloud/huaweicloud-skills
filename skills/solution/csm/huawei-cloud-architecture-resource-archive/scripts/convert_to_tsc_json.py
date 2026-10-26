#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert KooCLI query results (API Explorer native JSON) into the marker-table store structure.

Aligns to the expected marker-table store structure
(_new_row's 19 fields) so that build_marker_table.py can directly consume KooCLI query results.

Field alignment (required by the marker table):
  - resource_name    ← resource name (CCE metadata.name / VPC name / OBS bucketName ...)
  - resource_id      ← resource UID (CCE metadata.uid / VPC id / OBS name ...)
  - enterprise_project_id ← enterprise project (CCE project_id / VPC enterprise_project_id ...)
  - downstream_explicit   ← downstream info (derived from VPC subnet/ELB relationships, can be manually supplemented)
  - downstream_inferred  ← inferred downstream services; format: `resource name (resource ID)`, one per line
  - spec                 ← specification; format: spec/vCPU/memory/image/disk(GB)/disk type, `key: value` per line
  - region / resource_type / inference_reason and the remaining 19 fields

Usage:
    python convert_to_tsc_json.py \
      --query-dir <query_resources.py output directory> \
      --customer <account-name> \
      --output <resource-output directory> \
      [--region cn-north-4]

Output: <output>/<SERVICE>/temp/*.json (structure compatible with enrich_store)
Then call generate_marker_table.py:
    python generate_marker_table.py --tsc-dir <output> --out <marker-table directory>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import infer_downstream

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from marker_constants import (
    SPEC_KEYS, SPEC_KEY_INTERNAL,
    REASON_KOOCLI_SUPPLEMENT, REASON_CCE_CLUSTER, REASON_VPC_LIST,
    REASON_OBS_BUCKETS, REASON_OBS_BUCKETS_RMS, REASON_RMS_SUMMARY,
    REASON_ECS_SERVERS, REASON_CCE_SUBRESOURCE, REASON_SIMPLE_LIST,
    REASON_EIP, REASON_LIVE_DOMAINS, REASON_CDN_DOMAINS,
    REASON_GEIP, REASON_ELB,
)

STORE_FIELDS = [
    "customer_name", "region", "resource_name", "resource_id", "resource_type",
    "enterprise_project_id", "eps_project", "is_core_business", "business", "group",
    "downstream_explicit", "downstream_inferred", "inference_reason",
]

# Fixed key order of the marker-table "spec" column (matches the display format agreed with the customer)
# SPEC_KEYS is imported from marker_constants.py; SPEC_KEY_INTERNAL maps each spec key to an internal field name.

# Type segment in CCE K8s sub-resource resource_name: CCE_<Type> -> kubectl short name
CCE_K8S_SHORT_TYPES = {
    "CCE_Deployment": "deploy",
    "CCE_StatefulSet": "sts",
    "CCE_DaemonSet": "ds",
    "CCE_Service": "svc",
    "CCE_ConfigMap": "cm",
    "CCE_Ingress": "ing",
    "CCE_NetworkPolicy": "netpol",
    "CCE_Pod": "po",
    "CCE_Endpoints": "ep",
    "CCE_Secret": "secret",
}


def _text(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _fmt_mem_gb(ram) -> str:
    """flavor.ram is in MB; convert to GB (integer when divisible, otherwise keep 1 decimal).

    Example: 4096 -> "4G", 8192 -> "8G", 5120 -> "5.0G"
    """
    if ram is None or ram == "":
        return ""
    try:
        ram = int(ram)
    except (TypeError, ValueError):
        return _text(ram)
    if ram % 1024 == 0:
        return f"{ram // 1024}G"
    return f"{round(ram / 1024, 1)}G"


def _build_spec(flavor: dict, image: dict) -> tuple[str, dict]:
    """Build the spec from ECS flavor/image.

    Returns (formatted multi-line string, structured dict); both are written to the store row.
    Disk type: ListServersDetails does not include the EVS disk type; default empty (can be supplemented via EVS queries or manual entry).
    """
    # SPEC_KEYS (customer-facing Chinese labels) and SPEC_KEY_INTERNAL (internal English keys)
    # are imported from marker_constants.py and aligned by position.
    spec_internal = dict(zip(SPEC_KEY_INTERNAL, [
        _text(flavor.get("name")),
        f"{_text(flavor.get('vcpus'))}U" if flavor.get("vcpus") not in (None, "") else "",
        _fmt_mem_gb(flavor.get("ram")),
        _text(image.get("id")) if image else "",
        _text(flavor.get("disk")),
        "",
    ]))
    spec_data = {label: spec_internal[ikey] for label, ikey in zip(SPEC_KEYS, SPEC_KEY_INTERNAL)}
    spec_str = "\n".join(f"{k}: {v}" for k, v in spec_data.items())
    return spec_str, spec_data


def _new_row(customer: str, region: str, name: str, rid: str, rtype: str,
             eps_id: str = "", reason: str = REASON_KOOCLI_SUPPLEMENT,
             downstream: str = "", group: str = "",
             downstream_inferred: str = "", spec: str = "",
             spec_data: dict | None = None, eps_project: str = "") -> dict:
    row = {
        "customer_name": customer, "region": region,
        "resource_name": name, "resource_id": rid, "resource_type": rtype,
        "enterprise_project_id": eps_id, "eps_project": eps_project,
        "is_core_business": "", "business": "", "group": group,
        "downstream_explicit": downstream,
        "downstream_inferred": downstream_inferred,
        "inference_reason": reason,
        "spec": spec,
        "spec_data": spec_data if spec_data is not None else {},
    }
    return row


def _find_list(data: dict, keys: list[str]) -> list:
    """Find the resource list in a KooCLI output dict by candidate keys."""
    for k in keys:
        if isinstance(data, dict):
            v = data.get(k)
            if isinstance(v, list):
                return v
    return []


def _clean_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ═══════════════════ KooCLI -> resource store row converters ═══════════════════

def convert_cce(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CCE ListClusters -> CCE cluster rows (spec: 版本/类型/网络模式)."""
    clusters = _find_list(data, ["items", "clusters"])
    rows = []
    for c in clusters:
        meta = c.get("metadata") or {}
        name = _text(meta.get("name"))
        uid = _text(meta.get("uid")) or _text(c.get("id"))
        if not name:
            continue
        spec = c.get("spec") or {}
        version = _text(spec.get("version"))
        ctype = _text(spec.get("type"))
        net_mode = _text((spec.get("containerNetwork") or {}).get("mode"))
        lines = []
        if version:
            lines.append(f"版本: {version}")
        if ctype:
            lines.append(f"类型: {ctype}")
        if net_mode:
            lines.append(f"网络模式: {net_mode}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, uid, "CCE",
                             eps_id=_text(c.get("project_id") or meta.get("project_id")),
                             reason=REASON_CCE_CLUSTER,
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows


def convert_vpc(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI VPC ListVpcs -> VPC rows (with enterprise_project_id / downstream inference).

    Downstream-related columns are populated uniformly by infer_downstream via cross-resource analysis:
      - Sub-resources (VPC subnets) -> downstream inferred column, with an [subtype] prefix
      - The explicit "downstream explicit" column is not auto-filled with sub-resource type lists (left for manual entry of the real downstream)
    """
    vpcs = _find_list(data, ["vpcs"])
    rows = []
    for v in vpcs:
        vid = _text(v.get("id"))
        name = _text(v.get("name"))
        if not vid:
            continue
        rows.append(_new_row(customer, region, name, vid, "VPC",
                             eps_id=_text(v.get("enterprise_project_id")),
                             reason=REASON_VPC_LIST))
    return rows


def convert_obs(data, customer: str, region: str) -> list[dict]:
    """KooCLI OBS buckets -> OBS rows (bucket name as ID).

    Compatible with two sources:
      - RMS ListAllResources --type=obs.buckets: {resources: [{id, name, region_id, ...}]}
        (query_resources.py uses this path; KooCLI has no ListBuckets operation)
      - Legacy OBS ListBuckets: {buckets: [{name, bucketName, ...}]}
    """
    def _obs_eps(b):
        """In RMS resource items the enterprise project fields are ep_id/ep_name (legacy ListBuckets uses enterprise_project_id)."""
        return (_text(b.get("ep_id") or b.get("enterprise_project_id")),
                _text(b.get("ep_name")))

    buckets = _find_list(data, ["buckets"])
    if not buckets:
        buckets = _find_list(data, ["resources"])
        rows = []
        for b in buckets:
            name = _text(b.get("name") or b.get("bucketName") or b.get("id"))
            if not name:
                continue
            r = _text(b.get("region_id") or b.get("regionId") or region)
            eps_id, eps_name = _obs_eps(b)
            rows.append(_new_row(customer, r, name, name, "OBS",
                                 eps_id=eps_id, eps_project=eps_name,
                                 reason=REASON_OBS_BUCKETS_RMS))
        return rows
    rows = []
    for b in buckets:
        name = _text(b.get("name") or b.get("bucketName"))
        if not name:
            continue
        eps_id, eps_name = _obs_eps(b)
        rows.append(_new_row(customer, region, name, name, "OBS",
                             eps_id=eps_id, eps_project=eps_name,
                             reason=REASON_OBS_BUCKETS))
    return rows

def convert_rms(data, customer: str, region: str) -> list[dict]:
    """KooCLI RMS CollectAllResourcesSummary -> summary rows.

    Verified return structure is a top-level JSON array: [{provider, types: [{type, regions: [...count...]}]}]
    (KooCLI 7.2.2); the legacy {providers: [...]} structure is also supported.
    """
    if isinstance(data, list):
        providers = data
    else:
        providers = _find_list(data, ["providers", "resource_providers"])
    rows = []
    for p in providers:
        pname = _text(p.get("provider"))
        types = p.get("types") or []
        for t in types:
            tname = _text(t.get("type"))
            if not tname:
                continue
            # Normalize resource_type = provider_type (e.g. vpc_securityGroups)
            rtype = f"{pname}_{tname}" if pname else tname
            rows.append(_new_row(customer, region, rtype, rtype, "RMS",
                                 reason=f"{REASON_RMS_SUMMARY} {pname}/{tname}"))
    return rows

def convert_ecs(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI ECS ListServersDetails -> ECS rows (with spec).

    Spec format (one `key: value` per line); keys follow SPEC_KEYS imported from marker_constants.py:
        <SPEC_KEYS[0]>: ac7.xlarge.2
        vCPU: 4U
        <SPEC_KEYS[2]>: 8G
        <SPEC_KEYS[3]>: <image_id>
        <SPEC_KEYS[4]>: 150
        <SPEC_KEYS[5]>: <GPSSD etc., not included by ListServersDetails, default empty>
    """
    servers = _find_list(data, ["servers"])
    rows = []
    for s in servers:
        sid = _text(s.get("id"))
        name = _text(s.get("name"))
        if not sid:
            continue
        flavor = s.get("flavor") or {}
        image = s.get("image") or {}
        spec_str, spec_data = _build_spec(flavor, image)
        rows.append(_new_row(customer, region, name, sid, "ECS",
                             eps_id=_text(s.get("enterprise_project_id")),
                             reason=REASON_ECS_SERVERS,
                             spec=spec_str, spec_data=spec_data))
    return rows

def convert_cce_k8s(query_dir: Path, customer: str, default_region: str) -> dict[str, list[dict]]:
    """Convert CCE_k8s_*.json from query_cce_k8s.py into store rows, grouped by region.

    Filename: CCE_k8s_<k8s_type>_<cluster_name>_<cluster_uid>_<ts>.json;
    region is taken from payload["region"] (fallback to default_region for old files without region).
    Only the latest query file for each (cluster_uid, k8s_type) is kept (no duplicate ingestion across runs).
    resource_type is taken from the file's declaration (CCE_Deployment / CCE_Service / CCE_ConfigMap etc.);
    resource_name format: cluster_name/namespace/short_type/resource_name
                  (e.g. hw-shanghai-sbgp-01/ops-bec/deploy/edge-live-studio-worker-hwsh-220624ad9b,
                    where short_type is the kubectl short name deploy/svc/cm etc.); resource_id uses the K8s object UID.
    Returns {region: [rows]}.
    """
    k8s_dir = query_dir / "CCE" / "temp"
    by_region: dict[str, list[dict]] = {}
    if not k8s_dir.exists():
        return by_region
    latest: dict[tuple, Path] = {}
    for f in k8s_dir.glob("CCE_k8s_*.json"):
        m = re.match(r"CCE_k8s_(?P<ktype>[a-z]+)_(?P<cname>.+?)_(?P<cuuid>[0-9a-fA-F-]{36})_\d{8}_\d{6}\.json",
                     f.name)
        if not m:
            continue
        key = (m.group("cuuid"), m.group("ktype"))
        cur = latest.get(key)
        if cur is None or f.stat().st_mtime > cur.stat().st_mtime:
            latest[key] = f
    seen: set = set()
    for f in latest.values():
        try:
            data = json.loads(_clean_ansi(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
        region = _text(data.get("region")) or default_region
        rows = by_region.setdefault(region, [])
        rtype = _text(data.get("resource_type")) or "CCE_K8s"
        cluster = data.get("cluster") or {}
        cname = _text(cluster.get("name"))
        short_type = CCE_K8S_SHORT_TYPES.get(rtype, rtype.lower())
        for it in data.get("items") or []:
            meta = it.get("metadata") or {}
            name = _text(meta.get("name"))
            uid = _text(meta.get("uid")) or name
            ns = _text(meta.get("namespace"))
            if not name or not uid or uid in seen:
                continue
            seen.add(uid)
            # cluster_name/namespace/short_type/resource_name
            disp = "/".join(part for part in (cname, ns, short_type, name) if part)
            rows.append(_new_row(customer, region, disp, uid, rtype,
                                 reason=f"{REASON_CCE_SUBRESOURCE} {cname}/{rtype}"))
    return by_region


def load_eps_map(query_dir: Path) -> dict[str, str]:
    """Read the EPS ListEnterpriseProject output and return {enterprise_project_id: name}."""
    eps_dir = query_dir / "EPS" / "temp"
    if not eps_dir.exists():
        return {}
    files = sorted(eps_dir.glob("EPS_enterprise_projects_*.json"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return {}
    try:
        raw = files[0].read_text(encoding="utf-8")
        data = json.loads(_clean_ansi(raw))
    except (json.JSONDecodeError, OSError):
        return {}
    out = {}
    for ep in (data.get("enterprise_projects") or []):
        eid = _text(ep.get("id"))
        name = _text(ep.get("name"))
        if eid:
            out[eid] = name
    return out


def enrich_enterprise_projects(rows: list[dict], query_dir: Path) -> None:
    """Fill eps_project (enterprise project name) for each row using the EPS id->name mapping.

    Existing names (e.g. OBS ep_name) are not overwritten; id "0" maps to default.
    """
    eps_map = load_eps_map(query_dir)
    if not eps_map:
        return
    for r in rows:
        eid = _text(r.get("enterprise_project_id"))
        if eid and not _text(r.get("eps_project")):
            r["eps_project"] = eps_map.get(eid, "default" if eid == "0" else "")


def _make_simple_converter(rtype: str, list_keys: list[str],
                            name_key: str = "name", id_key: str = "id",
                            eps_key: str = "enterprise_project_id",
                            spec_label: str = ""):
    """Build a converter for simple list resources like VPC sub-services: id/name/enterprise_project_id.

    spec_label: optional fixed `key: value` line written into the spec column
    (e.g. "类型: 云模式") — used when one resource type covers multiple deployment
    modes that the spec column can distinguish.
    """
    def conv(data: dict, customer: str, region: str) -> list[dict]:
        rows = []
        for item in _find_list(data, list_keys):
            rid = _text(item.get(id_key))
            name = _text(item.get(name_key))
            if not rid:
                continue
            spec_str = spec_label or ""
            spec_data = {}
            if spec_label:
                k, _, v = spec_label.partition(":")
                spec_data = {k.strip(): v.strip()}
            rows.append(_new_row(customer, region, name, rid, rtype,
                                 eps_id=_text(item.get(eps_key)),
                                 reason=f"{REASON_SIMPLE_LIST} {rtype}",
                                 spec=spec_str, spec_data=spec_data))
        return rows
    return conv


# Region-scoped flavor cache: {(service_dir, region): {spec_code: {"vcpus": str, "ram": str}}}
# Populated by _load_flavors() before converting each region; queried by _build_db_spec
# so DDS/DCS can fill the vCPU/RAM columns from the ListFlavors table.
_FLAVOR_CACHE: dict[tuple[str, str], dict[str, dict]] = {}


def _load_flavors(query_dir: Path, region: str) -> None:
    """Load spec_code -> vcpus/ram maps from the DDS/RDS flavor files under query_dir.

    Files are named <SERVICE>_flavors_<...>_<region>_<ts>.json; the latest parseable
    file per (service, region) wins. Absence of a flavor file is not an error — the
    cache simply stays empty for that service and the instance-provided fields are used.
    """
    _FLAVOR_CACHE.clear()
    for svc in ("DDS", "RDS", "GEMINIDB"):
        svc_dir = query_dir / svc / "temp"
        if not svc_dir.exists():
            continue
        latest = None
        for f in sorted(svc_dir.glob(f"{svc}_flavors_*.json"),
                        key=lambda f: f.stat().st_mtime, reverse=True):
            if region not in f.name:
                continue
            try:
                raw = f.read_text(encoding="utf-8")
                data = json.loads(_clean_ansi(raw))
            except (json.JSONDecodeError, OSError):
                continue
            flavors = data.get("flavors") or []
            if flavors:
                latest = flavors
                break
        if not latest:
            continue
        mapping: dict[str, dict] = {}
        for fl in latest:
            sc = _text(fl.get("spec_code"))
            if sc and fl.get("vcpus") not in (None, "") or fl.get("ram") not in (None, ""):
                mapping[sc] = {
                    "vcpus": _text(fl.get("vcpus")),
                    "ram": _text(fl.get("ram")),
                }
        if mapping:
            _FLAVOR_CACHE[(svc, region)] = mapping


def _db_flavor(kind: str, region: str, spec_code: str) -> dict:
    """Look up the flavor table for (kind, region, spec_code); returns {} on miss."""
    svc = {"dds": "DDS", "rds": "RDS", "dcs": "DCS", "gaussdb": "GAUSSDB",
           "geminidb": "GEMINIDB", "taurusdb": "TAURUSDB", "dms": "DMS"}.get(kind, "")
    if not svc:
        return {}
    return _FLAVOR_CACHE.get((svc, region), {}).get(spec_code, {})


def _build_db_spec(item: dict, kind: str, region: str = "") -> tuple[str, dict]:
    """Extract the 6-key spec display for a database instance (service-specific field shapes).

    - dds:      spec_code lives under groups[0].nodes[0]; disk under groups[0].volume
    - dcs:      spec_code / resource_spec_code; engine + engine_version; capacity (GB)
    - others:   best-effort spec_code / flavor_ref / cpu / mem / volume / datastore
    The datastore type + version maps onto the "image" slot; the vCPU/RAM numbers come
    from the instance (RDS-style cpu/mem) or from the region flavor table when present.
    """
    ds = item.get("datastore") or {}
    vol = item.get("volume") or {}
    flavor = vcpu = mem = disk = disk_type = ""
    if kind in ("dds", "geminidb"):
        # DDS / GeminiDB: spec_code lives under groups[0].nodes[0]; disk under groups[0].volume
        groups = item.get("groups") or []
        if groups:
            nodes = groups[0].get("nodes") or []
            if nodes:
                flavor = _text(nodes[0].get("spec_code"))
            gvol = groups[0].get("volume") or {}
            disk = _text(gvol.get("size"))
    elif kind == "dcs":
        flavor = _text(item.get("spec_code") or item.get("resource_spec_code"))
        disk = _text(item.get("capacity"))
        # DCS is a capacity-based service (no vCPU); memory comes from max_memory (MB).
        max_mem = item.get("max_memory")
        if max_mem not in (None, ""):
            try:
                mm = int(max_mem)
                mem = f"{mm // 1024}G" if mm % 1024 == 0 else f"{round(mm / 1024, 1)}G"
            except (TypeError, ValueError):
                mem = _text(max_mem)
    elif kind == "dms":
        # DMS Kafka: specification carries the sizing string (e.g. "kafka.2u4g.single.small * 1 broker")
        # with u4g = 2 vCPU / 4G RAM; product_id is the bare flavor code.
        spec = _text(item.get("specification") or item.get("product_id"))
        flavor = spec
        m = re.search(r"(\d+)u(\d+)g", spec.lower())
        if m:
            vcpu = f"{m.group(1)}U"
            mem = f"{m.group(2)}G"
        disk = _text(item.get("storage_space") or item.get("total_storage_space"))
        disk_type = _text(item.get("storage_spec_code"))
    else:  # rds / gaussdb / geminidb / taurusdb / dms
        flavor = _text(item.get("flavor_ref") or item.get("spec_code")
                       or item.get("resource_spec_code") or item.get("flavor")
                       or item.get("product_id"))
        # GaussDB/TaurusDB carry the sizing under flavor_info (GaussDB: vcpu/mem, TaurusDB: vcpus/ram)
        finfo = item.get("flavor_info") or {}
        vcpu = _text(item.get("cpu") or item.get("vcpus")
                     or finfo.get("vcpu") or finfo.get("vcpus"))
        mem = _text(item.get("mem") or item.get("ram")
                    or finfo.get("mem") or finfo.get("ram"))
        if mem:
            # DB APIs report memory in GB directly (e.g. RDS mem=4); some report MB.
            # Heuristic: values <= 128 are GB (append G); >= 512 are MB (convert to GB).
            try:
                mem_num = int(mem)
            except (TypeError, ValueError):
                mem_num = 0
            if mem_num and mem_num <= 128:
                mem = f"{mem_num}G"
            elif mem_num >= 512:
                mem = f"{mem_num // 1024}G" if mem_num % 1024 == 0 else f"{round(mem_num / 1024, 1)}G"
            else:
                mem = _text(mem)
        disk = _text(vol.get("size"))
        disk_type = _text(vol.get("type"))
    # Fill missing vCPU/RAM from the region flavor table (DDS has no cpu/mem in ListInstances)
    if (not vcpu or not mem) and flavor:
        fmap = _db_flavor(kind, region, flavor)
        if fmap:
            if not vcpu and fmap.get("vcpus"):
                vcpu = f"{_text(fmap['vcpus'])}U"
            if not mem and fmap.get("ram"):
                try:
                    rn = int(fmap["ram"])
                except (TypeError, ValueError):
                    rn = 0
                mem = f"{rn}G" if rn and rn <= 128 else _text(fmap["ram"])
    image = " ".join(x for x in (_text(ds.get("type") or item.get("engine")),
                                 _text(ds.get("version") or item.get("whole_version")
                                       or item.get("engine_version"))) if x)
    # Only emit non-empty keys: DB services differ in which spec dimensions exist
    # (DCS has no vCPU; DDS/DCS have no disk type), so force-filling empty keys
    # produces noise. Keep the label set for ECS (all six are populated there).
    spec_internal = dict(zip(SPEC_KEY_INTERNAL, [flavor, vcpu, mem, image, disk, disk_type]))
    non_empty = [(label, spec_internal[ikey]) for label, ikey in zip(SPEC_KEYS, SPEC_KEY_INTERNAL)
                 if spec_internal[ikey]]
    spec_data = dict(non_empty)
    spec_str = "\n".join(f"{k}: {v}" for k, v in non_empty)
    return spec_str, spec_data


def _make_db_converter(rtype: str, list_keys: list[str], kind: str,
                       name_key: str = "name", id_key: str = "id",
                       eps_key: str = "enterprise_project_id"):
    """Build a database-instance converter that also extracts the spec column.

    Database APIs return spec info in service-specific field shapes; _build_db_spec
    maps each onto the agreed 6-key spec format shared with ECS.
    """
    def conv(data: dict, customer: str, region: str) -> list[dict]:
        rows = []
        for item in _find_list(data, list_keys):
            rid = _text(item.get(id_key))
            name = _text(item.get(name_key))
            if not rid:
                continue
            spec_str, spec_data = _build_db_spec(item, kind, region)
            rows.append(_new_row(customer, region, name, rid, rtype,
                                 eps_id=_text(item.get(eps_key)),
                                 reason=f"{REASON_SIMPLE_LIST} {rtype}",
                                 spec=spec_str, spec_data=spec_data))
        return rows
    return conv


convert_subnet = _make_simple_converter("VPC_Subnet", ["subnets"])
convert_routetable = _make_simple_converter("VPC_RouteTable", ["routetables"])
convert_securitygroup = _make_simple_converter("VPC_SecurityGroup", ["security_groups"])
convert_networkacl = _make_simple_converter("VPC_NetworkACL", ["firewalls"])
convert_peering = _make_simple_converter("VPC_Peering", ["peerings"])


def convert_eip(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI EIP ListPublicips -> EIP rows (regional elastic public IPs)."""
    rows = []
    for e in _find_list(data, ["publicips"]):
        eid = _text(e.get("id"))
        if not eid:
            continue
        name = _text(e.get("name")) or _text(e.get("public_ip_address"))
        rows.append(_new_row(customer, region, name, eid, "EIP",
                             eps_id=_text(e.get("enterprise_project_id")),
                             reason=REASON_EIP))
    return rows


def convert_live(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI Live ShowDomain (no parameter returns all domains) -> LIVE streaming domain rows."""
    rows = []
    for d in _find_list(data, ["domain_info"]):
        domain = _text(d.get("domain"))
        if not domain:
            continue
        subtype = _text(d.get("domain_type")) or _text(d.get("scene"))
        reason = REASON_LIVE_DOMAINS
        rows.append(_new_row(customer, region, domain, domain, "LIVE_Domain",
                             eps_id=_text(d.get("enterprise_project_id")),
                             reason=reason))
    return rows


def convert_cdn(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CDN ListDomains -> CDN domain rows."""
    rows = []
    for d in _find_list(data, ["domains"]):
        did = _text(d.get("id"))
        if not did:
            continue
        name = _text(d.get("domain_name")) or _text(d.get("name"))
        rows.append(_new_row(customer, region, name, did, "CDN_Domain",
                             eps_id=_text(d.get("enterprise_project_id")),
                             reason=REASON_CDN_DOMAINS))
    return rows


def convert_ccaas(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CC ListCloudConnections -> CCAAS_CloudConnection rows (spec: 类型/SLA/计费)."""
    rows = []
    for c in _find_list(data, ["cloud_connections"]):
        rid = _text(c.get("id"))
        name = _text(c.get("name"))
        if not rid:
            continue
        ctype = _text(c.get("type"))
        sla = _text(c.get("sla_level"))
        billing = _text(c.get("billing_mode"))
        lines = []
        if ctype:
            lines.append(f"类型: {ctype}")
        if sla:
            lines.append(f"SLA: {sla}")
        if billing:
            lines.append(f"计费: {billing}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CCAAS_CloudConnection",
                             eps_id=_text(c.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} CCAAS_CloudConnection",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows


def convert_ccaas_irb(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CC ListInterRegionBandwidths -> rows.

    The API returns no name for IRBs; the display name is derived from the
    region pair + bandwidth (aligned with the TSC naming `区域A→区域B (带宽Mbps)`,
    e.g. cn-east-2→cn-east-3 (50Mbps)).
    """
    rows = []
    for b in _find_list(data, ["inter_region_bandwidths"]):
        rid = _text(b.get("id"))
        if not rid:
            continue
        bw = _text(b.get("bandwidth"))
        regions = [f"{_text(x.get('local_region_id'))}→{_text(x.get('remote_region_id'))}"
                   for x in (b.get("inter_regions") or []) if x.get("local_region_id")]
        # Display name: first region pair + bandwidth, e.g. cn-east-2→cn-east-3 (50Mbps)
        name = _text(b.get("name"))
        if not name and regions:
            pair = regions[0]
            name = f"{pair} ({bw}Mbps)" if bw else pair
        lines = []
        if bw:
            lines.append(f"带宽: {bw}")
        if regions:
            lines.append(f"区域: {' / '.join(regions)}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CCAAS_InterRegionBandwidth",
                             eps_id=_text(b.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} CCAAS_InterRegionBandwidth",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows


def convert_ccaas_bwp(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CC ListBandwidthPackages -> rows (spec: 带宽 + 区域)."""
    rows = []
    for b in _find_list(data, ["bandwidth_packages"]):
        rid = _text(b.get("id"))
        name = _text(b.get("name"))
        if not rid:
            continue
        bw = _text(b.get("bandwidth"))
        local = _text(b.get("local_area_id"))
        remote = _text(b.get("remote_area_id"))
        lines = []
        if bw:
            lines.append(f"带宽: {bw}")
        if local or remote:
            lines.append(f"区域: {local} - {remote}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CCAAS_BandwidthPackage",
                             eps_id=_text(b.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} CCAAS_BandwidthPackage",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows


def convert_ccaas_ni(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CC ListNetworkInstances -> rows (spec: 类型 + 区域 + 关联云连接)."""
    rows = []
    for n in _find_list(data, ["network_instances"]):
        rid = _text(n.get("id"))
        name = _text(n.get("name"))
        if not rid:
            continue
        ntype = _text(n.get("type"))
        nregion = _text(n.get("region_id"))
        ccid = _text(n.get("cloud_connection_id"))
        lines = []
        if ntype:
            lines.append(f"类型: {ntype}")
        if nregion:
            lines.append(f"区域: {nregion}")
        if ccid:
            lines.append(f"云连接: {ccid}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CCAAS_NetworkInstance",
                             eps_id=_text(n.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} CCAAS_NetworkInstance",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows


# Database service instances (ListInstances always returns the key "instances")
# Spec extraction: dcs uses spec_code/capacity; dds uses groups[0].nodes[0].spec_code + volume;
# rds/gaussdb/geminidb/taurusdb use flavor_ref/cpu/mem/volume.
convert_rds = _make_db_converter("RDS", ["instances"], "rds")
convert_dcs = _make_db_converter("DCS", ["instances"], "dcs", id_key="instance_id")
convert_dds = _make_db_converter("DDS", ["instances"], "dds")
convert_dms = _make_db_converter("DMS", ["instances"], "dms", id_key="instance_id")
convert_gaussdb = _make_db_converter("GaussDB", ["instances"], "gaussdb")
convert_geminidb = _make_db_converter("GeminiDB", ["instances"], "geminidb")
convert_taurusdb = _make_db_converter("TaurusDB", ["instances"], "taurusdb")

# ═══════════════════ NAT gateway ═══════════════════
convert_nat = _make_simple_converter("NAT", ["nat_gateways"])
convert_nat_snat = _make_simple_converter("NAT_SnatRule", ["snat_rules"])
convert_nat_dnat = _make_simple_converter("NAT_DnatRule", ["dnat_rules"])

# ═══════════════════ VPN ═══════════════════
convert_vpn = _make_simple_converter("VPN", ["vpn_gateways"])
convert_vpn_connection = _make_simple_converter("VPN_Connection", ["vpn_connections"])
convert_vpn_cgw = _make_simple_converter("VPN_PeerGateway", ["customer_gateways"])
convert_vpn_p2c = _make_simple_converter("VPN_P2CVPNGateway", ["p2c_vpn_gateways"])

# ═══════════════════ VPC endpoint ═══════════════════
convert_vpcep = _make_simple_converter("VPCEndpoint", ["endpoints"], name_key="endpoint_service_name")

# ═══════════════════ DNS ═══════════════════
convert_dns_public = _make_simple_converter("DNS_PublicZone", ["zones"])
convert_dns_private = _make_simple_converter("DNS_PrivateZone", ["zones"])
convert_dns_endpoint = _make_simple_converter("DNS_Endpoint", ["endpoints"])
convert_dns_resolver = _make_simple_converter("DNS_ResolverRule", ["resolver_rules"])

# ═══════════════════ Enterprise Router (ER) ═══════════════════
convert_er = _make_simple_converter("ER", ["instances"])
convert_er_route_table = _make_simple_converter("ER_RouteTable", ["route_tables"])
convert_er_attachment = _make_simple_converter("ER_Attachment", ["attachments"])

# ═══════════════════ WAF Web Application Firewall ═══════════════════
# Both deployment modes map to the same resource type "WAF"; the spec column
# distinguishes them: 云模式 (ListHost, shared-mode protected domains) vs
# 独享模式 (ListInstance, dedicated engine instances).
convert_waf_host = _make_simple_converter("WAF", ["hosts", "items"], spec_label="类型: 云模式")
convert_waf_instance = _make_simple_converter("WAF", ["instances", "items"], spec_label="类型: 独享模式")

# ═══════════════════ CFW Cloud Firewall ═══════════════════
convert_cfw = _make_simple_converter("CFW", ["firewalls", "items"])

# ═══════════════════ CNAD Cloud Native Anti-DDoS ═══════════════════
convert_cnad_domain = _make_simple_converter("CNAD_Domain", ["domain_info", "domains", "items"])
convert_cnad_status = _make_simple_converter("CNAD_DDoSStatus", ["ddosStatus", "ddos_status", "items"], name_key="floating_ip_address", id_key="floating_ip_id")

# ═══════════════════ CC2.0 Cloud Connect 2.0 ═══════════════════
convert_cc2 = _make_simple_converter("CC2_CloudConnection", ["cloud_connections", "items"])
convert_cc2_irb = _make_simple_converter("CC2_InterRegionBandwidth", ["inter_region_bandwidths", "items"])
convert_cc2_bwp = _make_simple_converter("CC2_BandwidthPackage", ["bandwidth_packages", "items"])

# ═══════════════════ Workspace desktop cloud ═══════════════════
def convert_workspace(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI Workspace ListDesktopsDetail -> Workspace rows.

    Spec uses the embedded product table (`_products`, from ListProducts):
    规格编码 / vCPU / 内存 / 系统 / 系统盘. product_id -> cpu/memory/system disk.
    """
    products = {_text(p.get("product_id")): p for p in (data.get("_products") or [])}
    rows = []
    for d in _find_list(data, ["desktops", "items"]):
        rid = _text(d.get("desktop_id"))
        name = _text(d.get("computer_name") or d.get("os_host_name"))
        if not rid:
            continue
        dtype = _text(d.get("desktop_type"))
        os_type = _text(d.get("os_type"))
        flavor = (d.get("flavor") or {}).get("id", "")
        product_id = _text(d.get("product_id"))
        prod = products.get(product_id) or {}
        cpu = _text(prod.get("cpu"))
        mem = _text(prod.get("memory"))
        sys_disk = _text(prod.get("system_disk_size"))
        root_vol = d.get("root_volume") or {}
        root_size = _text(root_vol.get("size")) or sys_disk
        lines = []
        if flavor:
            lines.append(f"规格: {flavor}")
        if cpu:
            lines.append(f"vCPU: {cpu}")
        if mem:
            try:
                mn = int(mem)
                lines.append(f"内存: {mn // 1024}G" if mn % 1024 == 0 else f"{round(mn / 1024, 1)}G")
            except (TypeError, ValueError):
                lines.append(f"内存: {mem}")
        if os_type:
            lines.append(f"系统: {os_type}")
        if dtype:
            lines.append(f"类型: {dtype}")
        if root_size:
            lines.append(f"系统盘: {root_size}G")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "Workspace",
                             eps_id=_text(d.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} Workspace",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows

# ═══════════════════ DCAAS cloud direct connect ═══════════════════
convert_dcaas_dc = _make_simple_converter("DCAAS_DirectConnect", ["direct_connects", "items"])
convert_dcaas_hdc = _make_simple_converter("DCAAS_HostedDirectConnect", ["hosted_direct_connects", "items"])
convert_dcaas_vg = _make_simple_converter("DCAAS_VirtualGateway", ["virtual_gateways", "items"])
convert_dcaas_vi = _make_simple_converter("DCAAS_VirtualInterface", ["virtual_interfaces", "items"])
convert_dcaas_gdc = _make_simple_converter("DCAAS_GlobalDcGateway", ["global_dc_gateways", "items"])

# ═══════════════════ BMS bare metal server ═══════════════════
convert_bms = _make_simple_converter("BMS", ["servers"])

# ═══════════════════ CCI cloud container instance ═══════════════════
def convert_cci(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CCI listNamespaces -> CCI namespace rows (k8s-style: metadata.name / metadata.uid)."""
    rows = []
    for n in _find_list(data, ["items"]):
        meta = n.get("metadata") or {}
        rid = _text(meta.get("uid"))
        name = _text(meta.get("name"))
        if not rid:
            continue
        labels = meta.get("labels") or {}
        eps_id = _text(labels.get("sys_enterprise_project_id"))
        rows.append(_new_row(customer, region, name, rid, "CCI",
                             eps_id=eps_id,
                             reason=f"{REASON_SIMPLE_LIST} CCI"))
    return rows


def convert_cci_pods(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CCI listCoreV1PodForAllNamespaces -> CCI_Pod rows (spec from container resources)."""
    rows = []
    for p in _find_list(data, ["items"]):
        meta = p.get("metadata") or {}
        rid = _text(meta.get("uid"))
        name = _text(meta.get("name"))
        if not rid:
            continue
        ns = _text(meta.get("namespace"))
        labels = meta.get("labels") or {}
        eps_id = _text(labels.get("sys_enterprise_project_id"))
        # Extract CPU/memory limits from the first container's resources.limits.
        spec = p.get("spec") or {}
        containers = spec.get("containers") or []
        cpu = mem = ""
        if containers:
            res = (containers[0].get("resources") or {}).get("limits") or {}
            cpu = _text(res.get("cpu"))
            mem = _text(res.get("memory"))
        spec_internal = dict(zip(SPEC_KEY_INTERNAL, ["", cpu, mem, "", "", ""]))
        non_empty = [(label, spec_internal[ikey]) for label, ikey in zip(SPEC_KEYS, SPEC_KEY_INTERNAL)
                     if spec_internal[ikey]]
        spec_str = "\n".join(f"{k}: {v}" for k, v in non_empty)
        full_name = f"{ns}/{name}" if ns else name
        rows.append(_new_row(customer, region, full_name, rid, "CCI_Pod",
                             eps_id=eps_id,
                             reason=f"{REASON_SIMPLE_LIST} CCI_Pod",
                             spec=spec_str, spec_data=dict(non_empty)))
    return rows

# ═══════════════════ SFS elastic file system (3 types) ═══════════════════
def convert_sfs(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI SFSTurbo ListShares -> SFS_Turbo rows (spec: 容量/协议/类型)."""
    rows = []
    for s in _find_list(data, ["shares"]):
        rid = _text(s.get("id"))
        name = _text(s.get("name"))
        if not rid:
            continue
        spec_internal = dict(zip(SPEC_KEY_INTERNAL, [
            _text(s.get("share_type")),   # 规格: STANDARD / PERFORMANCE
            "",                            # vCPU
            "",                            # 内存
            "",                            # 镜像
            _text(s.get("size")),          # 磁盘(GB): 500.00
            _text(s.get("share_proto")),   # 磁盘类型: NFS
        ]))
        non_empty = [(label, spec_internal[ikey]) for label, ikey in zip(SPEC_KEYS, SPEC_KEY_INTERNAL)
                     if spec_internal[ikey]]
        spec_str = "\n".join(f"{k}: {v}" for k, v in non_empty)
        rows.append(_new_row(customer, region, name, rid, "SFS_Turbo",
                             eps_id=_text(s.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} SFS_Turbo",
                             spec=spec_str, spec_data=dict(non_empty)))
    return rows


convert_sfs3 = _make_simple_converter("SFS3", ["file_systems"])
convert_efs = _make_simple_converter("EFS", ["file_systems"])

# ═══════════════════ CSS Cloud Search Service ═══════════════════
def convert_css(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CSS ListClustersDetails -> CSS rows (spec: 引擎版本 + 节点规格/数量)."""
    rows = []
    for c in _find_list(data, ["clusters"]):
        rid = _text(c.get("id"))
        name = _text(c.get("name"))
        if not rid:
            continue
        ds = c.get("datastore") or {}
        engine = _text(ds.get("type"))
        version = _text(ds.get("version"))
        insts = c.get("instances") or []
        spec_codes = sorted({_text(i.get("specCode")) for i in insts if i.get("specCode")})
        node_count = len(insts)
        lines = []
        if engine or version:
            lines.append(f"引擎: {engine} {version}".strip())
        if spec_codes:
            lines.append(f"节点规格: {' / '.join(spec_codes)}")
        if node_count:
            lines.append(f"节点数: {node_count}")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CSS",
                             eps_id=_text(c.get("enterpriseProjectId") or c.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} CSS",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows

# ═══════════════════ MRS MapReduce Service ═══════════════════
# clusterType: 0=分析集群 1=流式集群 2=混合集群 3=自定义集群 4=离线集群
_MRS_TYPE_LABELS = {"0": "分析集群", "1": "流式集群", "2": "混合集群", "3": "自定义集群", "4": "离线集群"}


def convert_mrs(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI MRS ListClusters -> MRS rows (clusterId/clusterName).

    Spec shows service-specific info rather than the generic 6 keys:
    版本 / 类型 / Master 节点规格×数量 / Core 节点规格×数量 / Kerberos.
    """
    rows = []
    for c in _find_list(data, ["clusters"]):
        rid = _text(c.get("clusterId"))
        name = _text(c.get("clusterName"))
        if not rid:
            continue
        version = _text(c.get("clusterVersion"))
        ctype = _MRS_TYPE_LABELS.get(_text(c.get("clusterType")), _text(c.get("clusterType")))
        master = _text(c.get("masterNodeSize"))
        master_num = _text(c.get("masterNodeNum"))
        core = _text(c.get("coreNodeSize"))
        core_num = _text(c.get("coreNodeNum"))
        krb = "开启" if str(c.get("safeMode")) == "1" else "关闭"
        lines = []
        if version:
            lines.append(f"版本: {version}")
        if ctype:
            lines.append(f"类型: {ctype}")
        if master:
            lines.append(f"Master: {master} × {master_num or '?'}")
        if core:
            lines.append(f"Core: {core} × {core_num or '?'}")
        if krb:
            lines.append(f"Kerberos: {krb}")
        spec_str = "\n".join(lines)
        spec_data = dict(l.split(": ", 1) for l in lines if ": " in l)
        rows.append(_new_row(customer, region, name, rid, "MRS",
                             eps_id=_text(c.get("enterpriseProjectId") or c.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} MRS",
                             spec=spec_str, spec_data=spec_data))
    return rows

# ═══════════════════ DLI Data Lake Insight (4 types) ═══════════════════
def convert_dli_queue(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI DLI ListQueues -> DLI_Queue rows (queue_id / queue_name; spec: CU)."""
    rows = []
    for q in _find_list(data, ["queues"]):
        rid = _text(q.get("queue_id"))
        name = _text(q.get("queue_name"))
        if not rid:
            continue
        cu = _text(q.get("cu_count"))
        spec_str = f"CU: {cu}" if cu else ""
        rows.append(_new_row(customer, region, name, rid, "DLI_Queue",
                             eps_id=_text(q.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} DLI_Queue",
                             spec=spec_str, spec_data={"CU": cu} if cu else {}))
    return rows


def convert_dli_flink(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI DLI ListFlinkJobs -> DLI_FlinkJob rows (job_list.jobs; job_id / name)."""
    rows = []
    jl = data.get("job_list") or {}
    jobs = jl.get("jobs") if isinstance(jl, dict) else _find_list(data, ["jobs"])
    for j in jobs or []:
        rid = _text(j.get("job_id"))
        name = _text(j.get("name"))
        if not rid:
            continue
        rows.append(_new_row(customer, region, name, rid, "DLI_FlinkJob",
                             reason=f"{REASON_SIMPLE_LIST} DLI_FlinkJob"))
    return rows


def convert_dli_db(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI DLI ListDatabases -> DLI_Database rows (database_name / resource_id)."""
    rows = []
    for db in _find_list(data, ["databases"]):
        rid = _text(db.get("resource_id") or db.get("database_name"))
        name = _text(db.get("database_name"))
        if not rid:
            continue
        rows.append(_new_row(customer, region, name, rid, "DLI_Database",
                             eps_id=_text(db.get("enterprise_project_id")),
                             reason=f"{REASON_SIMPLE_LIST} DLI_Database"))
    return rows


def convert_dli_cross(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI DLI ListDatasourceConnections -> DLI_CrossSource rows (connections list)."""
    rows = []
    for c in _find_list(data, ["connections", "datasource_connections"]):
        rid = _text(c.get("id") or c.get("connection_id"))
        name = _text(c.get("name") or c.get("connection_name"))
        if not rid:
            continue
        rows.append(_new_row(customer, region, name, rid, "DLI_CrossSource",
                             reason=f"{REASON_SIMPLE_LIST} DLI_CrossSource"))
    return rows

# ═══════════════════ CloudTable ═══════════════════
def convert_cloudtable(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI CloudTable ListClusters -> CloudTable rows (cluster_id/cluster_name; spec: 类型/版本/节点)."""
    rows = []
    for c in _find_list(data, ["clusters"]):
        rid = _text(c.get("cluster_id"))
        name = _text(c.get("cluster_name") or c.get("cluster_alias"))
        if not rid:
            continue
        ctype = _text(c.get("cluster_type"))
        version = _text(c.get("version"))
        data_nodes = _text(c.get("data_node_num"))
        ctrl_nodes = _text(c.get("control_node_num"))
        data_flavor = _text(c.get("data_flavor"))
        ctrl_flavor = _text(c.get("control_flavor"))
        storage = _text(c.get("data_node_total_storage_size"))
        ctrl_storage = _text(c.get("control_node_total_storage_size"))
        mode = _text(c.get("compute_storage_mode"))
        hot_cold = _text(c.get("enable_hot_cold_feature"))
        lines = []
        if ctype:
            lines.append(f"类型: {ctype}")
        if version:
            lines.append(f"版本: {version}")
        if data_flavor:
            lines.append(f"数据节点: {data_flavor} × {data_nodes or '?'}")
        if ctrl_flavor:
            lines.append(f"控制节点: {ctrl_flavor} × {ctrl_nodes or '?'}")
        if storage:
            lines.append(f"数据存储: {storage}")
        if ctrl_storage and ctrl_storage != "0G":
            lines.append(f"控制存储: {ctrl_storage}")
        if mode:
            lines.append(f"存储模式: {mode}")
        if hot_cold and hot_cold.lower() == "true":
            lines.append(f"冷热分离: 开启")
        spec_str = "\n".join(lines)
        rows.append(_new_row(customer, region, name, rid, "CloudTable",
                             eps_id=_text(c.get("eps_id")),
                             reason=f"{REASON_SIMPLE_LIST} CloudTable",
                             spec=spec_str,
                             spec_data=dict(l.split(": ", 1) for l in lines if ": " in l)))
    return rows

# ═══════════════════ BGP peering ═══════════════════
convert_bgp = _make_simple_converter("BGP", ["vpc_peerings", "peerings"])


def convert_geip(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI GEIP ListGlobalEips -> GEIP rows.

    Bound instances (downstream services) are inferred by infer_downstream from associate_instance_id/type.
    """
    eips = _find_list(data, ["global_eips"])
    rows = []
    for e in eips:
        eid = _text(e.get("id"))
        name = _text(e.get("name")) or _text(e.get("ip_address"))
        if not eid:
            continue
        rows.append(_new_row(customer, region, name, eid, "GEIP",
                             eps_id=_text(e.get("enterprise_project_id")),
                             reason=REASON_GEIP))
    return rows


def convert_elb(data: dict, customer: str, region: str) -> list[dict]:
    """KooCLI ELB ListLoadBalancers -> ELB rows.

    Backend members (downstream services) are inferred by infer_downstream from ListPools/ListMembers.
    """
    lbs = _find_list(data, ["loadbalancers", "load_balancers"])
    rows = []
    for lb in lbs:
        lid = _text(lb.get("id"))
        name = _text(lb.get("name"))
        if not lid:
            continue
        rows.append(_new_row(customer, region, name, lid, "ELB",
                             eps_id=_text(lb.get("enterprise_project_id")),
                             reason=REASON_ELB))
    return rows


# service -> (converter function, output filename, directory name expected by the enrich parser)
CONVERTERS = {
    "cce":  (convert_cce, "CCE", "cce_cluster_vm_new"),
    "vpc":  (convert_vpc, "VPC", "VPC_vpcs"),
    "obs":  (convert_obs, "OBS", "obs_bucket_list"),
    "rms":  (convert_rms, "RMS", "RMS_all_resource_summary"),
    "ecs":  (convert_ecs, "ECS", "ECS_servers"),
    "geip": (convert_geip, "GEIP", "GEIP_global_eip_list"),
    "elb":  (convert_elb, "ELB", "ELB_loadbalancers"),
    "subnet": (convert_subnet, "SUBNET", "subnets"),
    "routetable": (convert_routetable, "ROUTETABLE", "route_tables"),
    "securitygroup": (convert_securitygroup, "SECURITYGROUP", "security_groups"),
    "networkacl": (convert_networkacl, "NETWORKACL", "firewalls"),
    "peering": (convert_peering, "PEERING", "vpc_peerings"),
    "eip":  (convert_eip, "EIP", "publicips"),
    "cdn":  (convert_cdn, "CDN", "domains"),
    "ccaas": (convert_ccaas, "CCAAS", "cloud_connections"),
    "ccaas_irb": (convert_ccaas_irb, "CCAAS", "inter_region_bandwidths"),
    "ccaas_bwp": (convert_ccaas_bwp, "CCAAS", "bandwidth_packages"),
    "ccaas_ni": (convert_ccaas_ni, "CCAAS", "network_instances"),
    "rds": (convert_rds, "RDS", "instances"),
    "dcs": (convert_dcs, "DCS", "instances"),
    "dds": (convert_dds, "DDS", "instances"),
    "dms": (convert_dms, "DMS", "instances"),
    "gaussdb": (convert_gaussdb, "GAUSSDB", "instances"),
    "geminidb": (convert_geminidb, "GEMINIDB", "instances"),
    "taurusdb": (convert_taurusdb, "TAURUSDB", "instances"),
    "live": (convert_live, "LIVE", "domains"),
    "nat": (convert_nat, "NAT", "nat_gateways"),
    "nat_snat": (convert_nat_snat, "NAT", "snat_rules"),
    "nat_dnat": (convert_nat_dnat, "NAT", "dnat_rules"),
    "vpn": (convert_vpn, "VPN", "vpn_gateways"),
    "vpn_connection": (convert_vpn_connection, "VPN", "vpn_connections"),
    "vpn_cgw": (convert_vpn_cgw, "VPN", "customer_gateways"),
    "vpn_p2c": (convert_vpn_p2c, "VPN", "p2c_vpn_gateways"),
    "vpcep": (convert_vpcep, "VPCEP", "endpoints"),
    "dns_public": (convert_dns_public, "DNS", "public_zones"),
    "dns_private": (convert_dns_private, "DNS", "private_zones"),
    "dns_endpoint": (convert_dns_endpoint, "DNS", "endpoints"),
    "dns_resolver": (convert_dns_resolver, "DNS", "resolver_rules"),
    "er": (convert_er, "ER", "instances"),
    "er_route_table": (convert_er_route_table, "ER", "route_tables"),
    "er_attachment": (convert_er_attachment, "ER", "attachments"),
    "waf_host": (convert_waf_host, "WAF", "hosts"),
    "waf_instance": (convert_waf_instance, "WAF", "instances"),
    "cfw": (convert_cfw, "CFW", "firewalls"),
    "cnad_domain": (convert_cnad_domain, "CNAD", "domains"),
    "cnad_status": (convert_cnad_status, "CNAD", "ddos_status"),
    "cc2": (convert_cc2, "CC2", "cloud_connections"),
    "cc2_irb": (convert_cc2_irb, "CC2", "inter_region_bandwidths"),
    "cc2_bwp": (convert_cc2_bwp, "CC2", "bandwidth_packages"),
    "workspace": (convert_workspace, "WORKSPACE", "desktops"),
    "dcaas_dc": (convert_dcaas_dc, "DCAAS", "direct_connects"),
    "dcaas_hdc": (convert_dcaas_hdc, "DCAAS", "hosted_direct_connects"),
    "dcaas_vg": (convert_dcaas_vg, "DCAAS", "virtual_gateways"),
    "dcaas_vi": (convert_dcaas_vi, "DCAAS", "virtual_interfaces"),
    "dcaas_gdc": (convert_dcaas_gdc, "DCAAS", "global_dc_gateways"),
    "bms": (convert_bms, "BMS", "servers"),
    "cci": (convert_cci, "CCI", "namespaces"),
    "cci_pods": (convert_cci_pods, "CCI", "pods"),
    "sfs": (convert_sfs, "SFS", "sfs_shares"),
    "sfs3": (convert_sfs3, "SFS", "sfs3_file_systems"),
    "efs": (convert_efs, "SFS", "efs_file_systems"),
    "css": (convert_css, "CSS", "clusters"),
    "mrs": (convert_mrs, "MRS", "clusters"),
    "dli_queue": (convert_dli_queue, "DLI", "queues"),
    "dli_flink": (convert_dli_flink, "DLI", "flink_jobs"),
    "dli_db": (convert_dli_db, "DLI", "databases"),
    "dli_cross": (convert_dli_cross, "DLI", "datasource_connections"),
    "cloudtable": (convert_cloudtable, "CloudTable", "clusters"),
    "bgp": (convert_bgp, "BGP", "peerings"),
}


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# Per-service main file tag (load_json_files matches by tag first to avoid picking up sub-files like CCE nodes by mistake)
FILE_TAGS = {
    "cce": "cce_cluster_vm_new",
    "vpc": "VPC_vpcs",
    "obs": "obs_bucket_list",
    "rms": "all-resource-summary",
    "ecs": "ECS_servers",
    "geip": "global_eip_list",
    "elb": "loadbalancers",
    "subnet": "subnets",
    "routetable": "route_tables",
    "securitygroup": "security_groups",
    "networkacl": "firewalls",
    "peering": "vpc_peerings",
    "eip": "publicips",
    "cdn": "domains",
    "ccaas": "cloud_connections",
    "ccaas_irb": "inter_region_bandwidths",
    "ccaas_bwp": "bandwidth_packages",
    "ccaas_ni": "network_instances",
    "rds": "instances",
    "dcs": "instances",
    "dds": "instances",
    "dms": "instances",
    "gaussdb": "instances",
    "geminidb": "instances",
    "taurusdb": "instances",
    "live": "domains",
    "nat": "nat_gateways",
    "nat_snat": "snat_rules",
    "nat_dnat": "dnat_rules",
    "vpn": "VPN_vpn_gateways",
    "vpn_connection": "vpn_connections",
    "vpn_cgw": "VPN_customer_gateways",
    "vpn_p2c": "VPN_p2c_vpn_gateways",
    "vpcep": "endpoints",
    "dns_public": "public_zones",
    "dns_private": "private_zones",
    "dns_endpoint": "endpoints",
    "dns_resolver": "resolver_rules",
    "er": "instances",
    "er_route_table": "route_tables",
    "er_attachment": "attachments",
    "waf_host": "hosts",
    "waf_instance": "instances",
    "cfw": "firewalls",
    "cnad_domain": "domains",
    "cnad_status": "ddos_status",
    "cc2": "cloud_connections",
    "cc2_irb": "inter_region_bandwidths",
    "cc2_bwp": "bandwidth_packages",
    "workspace": "desktops",
    "dcaas_dc": "DCAAS_direct_connects",
    "dcaas_hdc": "DCAAS_hosted_direct_connects",
    "dcaas_vg": "DCAAS_virtual_gateways",
    "dcaas_vi": "DCAAS_virtual_interfaces",
    "dcaas_gdc": "DCAAS_global_dc_gateways",
    "bms": "BMS_servers",
    "cci": "CCI_namespaces",
    "cci_pods": "CCI_pods",
    "sfs": "SFS_sfs_shares",
    "sfs3": "SFS_sfs3_file_systems",
    "efs": "SFS_efs_file_systems",
    "css": "CSS_clusters",
    "mrs": "MRS_clusters",
    "dli_queue": "DLI_queues",
    "dli_flink": "DLI_flink_jobs",
    "dli_db": "DLI_databases",
    "dli_cross": "DLI_datasource_connections",
    "cloudtable": "CloudTable_clusters",
    "bgp": "BGP_peerings",
}


_REGION_TS_RE = re.compile(r"_\d{8}_\d{6}\.json$")


def region_from_filename(fname: str, default: str) -> str:
    """Parse the region from a filename (VPC_vpcs_cn-north-4_<ts>.json -> cn-north-4; old files without region use default)."""
    stem = _REGION_TS_RE.sub("", fname)
    parts = stem.split("_")
    if len(parts) >= 3 and parts[-1]:
        return parts[-1]
    return default


def load_json_files(query_dir: Path, default_region: str) -> dict[str, dict[str, Path]]:
    """Scan the query_resources.py output directory and return {region: {service: main JSON file}}.

    Filenames carry the region (VPC_vpcs_cn-north-4_<ts>.json); old files without a region go into default_region.
    The latest parseable file is kept per (region, service); top-level array files (RMS summary) are supported.
    """
    found: dict[str, dict[str, Path]] = {}
    for svc in CONVERTERS:
        _func, subdir, _tag2 = CONVERTERS[svc]
        svc_dir = query_dir / subdir / "temp"
        if not svc_dir.exists():
            continue
        tag = FILE_TAGS.get(svc, "")
        candidates = sorted(svc_dir.glob("*.json"),
                            key=lambda f: (tag in f.name, f.stat().st_mtime),
                            reverse=True)
        # Multiple region files may coexist: keep the latest parseable file per (region, service) (do not break on the first one).
        # WARNING: only accept main files tagged with this service (e.g. the CCE cluster file);
        # otherwise newer sub-files like nodes/members would override the main file (CCE becomes nodes, ELB becomes pools).
        best: dict[str, Path] = {}
        for f in candidates:
            if tag and tag not in f.name:
                continue
            try:
                raw = f.read_text(encoding="utf-8")
                clean = _clean_ansi(raw)
                start_json = min(p for p in (clean.find("{"), clean.find("[")) if p >= 0)
                end_json = max(clean.rfind("}"), clean.rfind("]"))
                if start_json >= 0 and end_json > start_json:
                    json.loads(clean[start_json:end_json + 1])
                    region = region_from_filename(f.name, default_region)
                    cur = best.get(region)
                    if cur is None or f.stat().st_mtime > cur.stat().st_mtime:
                        best[region] = f
            except (json.JSONDecodeError, OSError, ValueError):
                continue
        for region, f in best.items():
            found.setdefault(region, {})[svc] = f
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert KooCLI query output -> resource store JSON (multi-region)")
    parser.add_argument("--query-dir", required=True, help="query_resources.py output directory")
    parser.add_argument("--customer", required=True, help="Account name (store customer_name)")
    parser.add_argument("--region", default="cn-north-4", help="Default region (old files without a region go here)")
    parser.add_argument("--output", required=True, help="Output directory (resource-output/<account>, used as --tsc-dir for build_marker_table)")
    parser.add_argument("--no-infer", action="store_true",
                        help="Skip cross-resource downstream inference (auto-inferred by default)")
    parser.add_argument("--no-clean", action="store_true",
                        help="Do not clean old output files (cleaned by default to avoid double counting)")
    args = parser.parse_args()

    query_dir = Path(args.query_dir)
    out_root = Path(args.output)
    out_root.mkdir(parents=True, exist_ok=True)
    # Clean up old output (leftover timestamped files would cause the marker table to double-count)
    if not args.no_clean:
        import shutil
        removed = 0
        for sub in out_root.iterdir():
            if sub.is_dir():
                shutil.rmtree(sub, ignore_errors=True)
                removed += 1
        for old in out_root.glob("convert_report_*.json"):
            old.unlink(missing_ok=True)
            removed += 1
        if removed:
            print(f"[convert] cleaned up {removed} old output entries")
    ts = timestamp()

    found = load_json_files(query_dir, args.region)
    k8s_by_region = convert_cce_k8s(query_dir, args.customer, args.region)
    regions = sorted(set(found) | set(k8s_by_region))
    if not regions:
        print("[convert] no KooCLI query results found in query-dir", file=__import__("sys").stderr)
        return 1

    total = 0
    for region in regions:
        # Load the region flavor tables (DDS/RDS) so db spec conversion can fill vCPU/RAM.
        _load_flavors(query_dir, region)
        # -- Stage 1: convert this region's raw output per service -> store rows --
        converted: dict[str, list[dict]] = {}
        for svc, path in found.get(region, {}).items():
            func, subdir, filetag = CONVERTERS[svc]
            try:
                raw = path.read_text(encoding="utf-8")
                clean = _clean_ansi(raw)
                start_json = min(p for p in (clean.find("{"), clean.find("[")) if p >= 0)
                end_json = max(clean.rfind("}"), clean.rfind("]"))
                data = json.loads(clean[start_json:end_json + 1] if start_json >= 0 else clean)
            except json.JSONDecodeError as exc:
                print(f"[convert] {region}/{svc.upper()} JSON parse failed: {exc}", file=__import__("sys").stderr)
                continue
            rows = func(data, args.customer, region)
            converted[svc] = rows
            total += len(rows)

        # -- Stage 1.5: CCE K8s sub-resources (this region) --
        if region in k8s_by_region:
            converted["ccek8s"] = k8s_by_region[region]
            total += len(k8s_by_region[region])

        flat = [r for rows in converted.values() for r in rows]

        # Fill enterprise project names (EPS id -> name mapping; OBS already has ep_name, not overwritten)
        enrich_enterprise_projects(flat, query_dir)

        # -- Stage 2: downstream inference -- cross-resource binding/reference analysis --
        if not args.no_infer:
            try:
                infer_downstream.apply_inference(flat, query_dir)
            except Exception as exc:  # inference failure does not block the main flow
                print(f"[convert][warn] {region} downstream inference skipped: {exc}", file=__import__("sys").stderr)

        # -- Stage 3: persist in an enrich_store-parseable structure (filenames carry the region) --
        for svc, rows in converted.items():
            if svc == "ccek8s":
                svc_out = out_root / "CCE" / "temp"
                svc_out.mkdir(parents=True, exist_ok=True)
                payload = {"rows": rows}
                fname = f"CCE_k8s_rows_{region}_{args.customer}_{ts}.json"
                out_path = svc_out / fname
                out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[convert] {region}/CCE_K8S -> {out_path} ({len(rows)} rows)")
                continue
            func, subdir, filetag = CONVERTERS[svc]
            svc_out = out_root / subdir / "temp"
            svc_out.mkdir(parents=True, exist_ok=True)
            if svc == "cce":
                clusters = []
                for r in rows:
                    clusters.append({
                        "metadata": {"name": r["resource_name"], "uid": r["resource_id"]},
                        "region": r["region"],
                        "project_id": r["enterprise_project_id"],
                        "eps_project": r["eps_project"],
                        "downstream_explicit": r["downstream_explicit"],
                        "downstream_inferred": r["downstream_inferred"],
                        "spec": r.get("spec") or "",
                        "spec_data": r.get("spec_data") or {},
                    })
                payload = {"account": args.customer,
                           "interfaces": {"cce_cluster_vm_new": clusters}}
                fname = f"CCE_account_{region}_{args.customer}_{ts}.json"
            elif svc == "vpc":
                vpcs = []
                for r in rows:
                    vpcs.append({"id": r["resource_id"], "name": r["resource_name"],
                                 "region": r["region"],
                                 "enterprise_project_id": r["enterprise_project_id"],
                                 "eps_project": r["eps_project"],
                                 "downstream_explicit": r["downstream_explicit"],
                                 "downstream_inferred": r["downstream_inferred"]})
                payload = {"data": {"list": vpcs}}
                fname = f"VPC_vpcs_{region}_{args.customer}_{ts}.json"
            elif svc == "obs":
                buckets = [{"bucketName": r["resource_name"], "regionId": r["region"],
                            "ep_id": r["enterprise_project_id"], "ep_name": r["eps_project"]} for r in rows]
                payload = {"data": {"detail": {"_list_": buckets}}}
                fname = f"obs_bucket_list_{region}_{args.customer}_{ts}.json"
            else:
                payload = {"rows": rows}
                fname = f"{subdir}_{filetag}_{region}_{args.customer}_{ts}.json"

            out_path = svc_out / fname
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[convert] {region}/{svc.upper()} -> {out_path} ({len(rows)} rows)")

    # Summary report
    report = {"customer": args.customer, "regions": regions, "total_rows": total,
              "inferred": not args.no_infer, "converted_at": ts,
              "next_step": "Run generate_marker_table.py --tsc-dir <output> --out <marker-table directory>"}
    rpath = out_root / f"convert_report_{ts}.json"
    rpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[convert] {total} resource rows total, regions: {regions} -> {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())