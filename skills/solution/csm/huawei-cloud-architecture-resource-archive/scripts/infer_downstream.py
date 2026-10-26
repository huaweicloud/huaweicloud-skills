#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource binding relationship → inferred downstream services inference engine.

Principle: extract binding/reference relationships between resources from KooCLI raw output
(query-dir of query_resources.py), and compute the "downstream inferred" content for each resource row.
Output format: one `resource name (resource ID)` per line, lines separated by newlines
(rendered uniformly by generate_marker_table).
Relationships without a name and without an ID (e.g. VPC cloud_resources route tables with only type+count) are dropped.

Supported relationships (by data source):
  - GEIP elastic public IP → bound instance
        ListGlobalEips returns associate_instance_id / associate_instance_type
        (type can be ECS/ELB/NAT etc.; if a name can be resolved in the resource table, show the name, otherwise show the type)
  - ECS → used image
        image.id of ListServersDetails (ListServersDetails does not contain the image name; the label is "image")
  - ELB load balancer → backend servers
        ListLoadBalancers + ListPools per LB + ListMembers per Pool
        if member.instance_id matches an ECS in the resource table → show the ECS name; otherwise fall back to member.address
  - CCE cluster → cluster nodes
        node spec.clusterID / spec.cluster_id of ListNodes links to the owning cluster
  - VPC → subnets/route tables etc.
        cloud_resources of ListVpcs (falls back to resource_type as label when resource_name is missing)

Unified relationship model (5-tuple):
    (from_type, from_id, to_type, to_label, to_id)
      from_type/from_id  source row (resource table row)
      to_type/to_id      target resource (bound object); empty to_id means a pure label relationship (e.g. IP only)
      to_label           target display name: prefer a resolvable resource name, otherwise use this label
                        (use type label when resource name is missing; ELB-IP members use address)
    Note: sub-resources (CCE nodes/VPC subnets) are displayed in the same format as downstream bindings `name (ID)`;
          relationships with only a type and no name/ID are not displayed (e.g. VPC cloud_resources route tables)

Usage (called internally by convert_to_tsc_json.py):
    import infer_downstream
    infer_downstream.apply_inference(rows, query_dir)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marker_constants import (
    TYPE_LABELS, IMAGE_LABEL, SUBNET_LABEL, ROUTE_TABLE_LABEL, CCE_NODE_LABEL,
    INTER_REGION_BANDWIDTH_LABEL, CCAAS_INTER_REGION_BANDWIDTH_LABEL,
    ASSOCIATED_INSTANCE_LABEL, ASSOCIATED_RESOURCE_LABEL, BACKEND_SERVER_LABEL,
    HCLOUD_MULTI_VERSION_PROMPT_HINT,
)

# TYPE_LABELS is imported from marker_constants.py.


def _text(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _clean_json(raw: str) -> str:
    """Strip ANSI codes and KooCLI prompt lines (the "<op>有多个版本" hint); return the JSON text starting from the first { or [."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    # Drop the KooCLI multi-version prompt line if present (HCLOUD_MULTI_VERSION_PROMPT_HINT is the Chinese substring we match on).
    p1 = clean.find("{")
    p2 = clean.find("[")
    pos = p1 if p1 >= 0 and (p2 < 0 or p1 < p2) else p2
    return clean[pos:] if pos >= 0 else ""


def _load_list(path: Path, keys: list[str]) -> list:
    """Read a JSON file and return the resource list by candidate key; supports top-level arrays."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(_clean_json(raw))
    except (json.JSONDecodeError, OSError, ValueError):
        return []
    if isinstance(data, list):
        return data
    for k in keys:
        if isinstance(data.get(k), list):
            return data[k]
    return []


def _latest(query_dir: Path, rel: str, pattern: str) -> list[Path]:
    """Return files in the directory sorted by mtime descending."""
    d = query_dir / rel
    if not d.exists():
        return []
    return sorted(d.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)


def build_registry(rows: list[dict]) -> dict[str, dict]:
    """Resource registry: key = "TYPE:ID", value = {name, type}.

    Used to resolve binding IDs into resource names (e.g. GEIP.associate_instance_id -> ECS name).
    """
    registry: dict[str, dict] = {}
    for r in rows:
        rid = _text(r.get("resource_id"))
        rtype = _text(r.get("resource_type"))
        name = _text(r.get("resource_name"))
        if rid:
            registry[f"{rtype.upper()}:{rid}"] = {"name": name, "type": rtype}
    return registry


def resolve_name(registry: dict[str, dict], rtype: str, rid: str) -> str:
    """Resolve a resource name by (type, ID); falls back to a full-table scan by ID when the type is uncertain."""
    rid = _text(rid)
    if not rid:
        return ""
    hit = registry.get(f"{_text(rtype).upper()}:{rid}")
    if hit and hit["name"]:
        return hit["name"]
    # Fallback: some resource type field names are inconsistent (e.g. geip's ecs vs the table's ECS)
    for key, info in registry.items():
        if key.endswith(":" + rid) and info.get("name"):
            return info["name"]
    return ""


def _norm_type(t) -> str:
    t = _text(t).lower()
    if not t:
        return ""
    return TYPE_LABELS.get(t, t.title())


# ═══════════════════ Per-data-source relationship extraction ═══════════════════

def _links_geip(query_dir: Path, ecs_by_port: dict[str, str]) -> list[tuple]:
    """GEIP elastic public IP -> bound instance (associate_instance_id / associate_instance_type)."""
    links = []
    for f in _latest(query_dir, "GEIP/temp", "GEIP_global_eip_list_*.json"):
        for eip in _load_list(f, ["global_eips"]):
            eid = _text(eip.get("id"))
            if not eid:
                continue
            assoc_id = _text(eip.get("associate_instance_id") or eip.get("instance_id"))
            if not assoc_id:
                continue
            raw_gtype = _text(eip.get("associate_instance_type") or eip.get("instance_type")).upper()
            if raw_gtype == "PORT":
                ecs = ecs_by_port.get(assoc_id)
                if ecs:
                    links.append(("GEIP", eid, "ECS", "", ecs))
                continue  # Port itself is not shown as downstream
            assoc_type = _norm_type(eip.get("associate_instance_type") or eip.get("instance_type") or "")
            links.append(("GEIP", eid, assoc_type or ASSOCIATED_INSTANCE_LABEL, "",
                          assoc_id))
    return links


def _links_ecs_image(query_dir: Path) -> list[tuple]:
    """ECS -> used image (image.id; no image name available, the label is IMAGE_LABEL)."""
    links = []
    for f in _latest(query_dir, "ECS/temp", "ECS_servers_*.json"):
        for s in _load_list(f, ["servers"]):
            sid = _text(s.get("id"))
            if not sid:
                continue
            image = s.get("image") or {}
            img_id = _text(image.get("id"))
            if img_id:
                links.append(("ECS", sid, IMAGE_LABEL, IMAGE_LABEL, img_id))
    return links


def _cluster_name_to_uid(query_dir: Path) -> dict[str, str]:
    """Read the CCE cluster list and return cluster_name -> cluster UID."""
    out: dict[str, str] = {}
    for f in _latest(query_dir, "CCE/temp", "*cluster_vm_new_*.json"):
        for c in _load_list(f, ["items", "clusters"]):
            meta = c.get("metadata") or {}
            uid = _text(meta.get("uid")) or _text(c.get("id"))
            name = _text(meta.get("name"))
            if uid and name and name not in out:
                out[name] = uid
    return out


def _cluster_id_from_filename(fname: str, name_to_uid: dict[str, str]) -> str:
    """Parse the cluster ID from a node filename (priority: embedded UID in filename -> cluster name lookup)."""
    m = re.match(r"CCE_vm_nodes_new_(?P<name>.+?)_(?P<uid>[0-9a-fA-F-]{36})_(?:[a-z0-9-]+_)?\d{8}_\d{6}\.json",
                 fname)
    if m:
        return m.group("uid")
    m = re.match(r"CCE_vm_nodes_new_(?P<cname>.+)_\d{8}_\d{6}\.json", fname)
    if m:
        return name_to_uid.get(m.group("cname"), "")
    return ""


def _links_cce_nodes(query_dir: Path) -> list[tuple]:
    """CCE cluster -> cluster nodes.

    Cluster ID resolution priority:
      1) node spec.clusterID / spec.cluster_id (new APIs may include this)
      2) cluster UID embedded in the node filename (query_resources new naming CCE_vm_nodes_new_<name>_<uid>_<ts>.json)
      3) cluster name in the node filename -> cluster UID via the cluster list (legacy naming fallback)
    """
    links = []
    name_to_uid = _cluster_name_to_uid(query_dir)
    for f in _latest(query_dir, "CCE/temp", "CCE_vm_nodes_new_*.json"):
        for n in _load_list(f, ["items"]):
            meta = n.get("metadata") or {}
            nid = _text(meta.get("uid")) or _text(n.get("id"))
            if not nid:
                continue
            spec = n.get("spec") or {}
            cid = _text(spec.get("clusterID") or spec.get("cluster_id"))
            if not cid:
                cid = _cluster_id_from_filename(f.name, name_to_uid)
            if not cid:
                continue
            # Sub-resource (not downstream): tag with an [subtype] prefix (empty label = no type segment; the node name already carries the cluster prefix)
            links.append(("CCE", cid, CCE_NODE_LABEL,
                          _text(meta.get("name")) or nid, nid, ""))
    return links


def _load_subnets(query_dir: Path) -> dict[str, list[dict]]:
    """Read the ListSubnets output (merging all region files) and return {vpc_id: [subnet]}.

    Multi-region runs produce multiple SUBNET_subnets_<region>_<ts>.json; all are merged,
    and duplicates are removed per vpc_id (vpc_id is globally unique).
    """
    out: dict[str, list[dict]] = {}
    seen: set = set()
    for f in _latest(query_dir, "SUBNET/temp", "SUBNET_subnets_*.json"):
        for sub in _load_list(f, ["subnets"]):
            vid = _text(sub.get("vpc_id"))
            sid = _text(sub.get("id"))
            name = _text(sub.get("name"))
            if not vid or not sid:
                continue
            if (vid, sid) in seen:
                continue
            seen.add((vid, sid))
            out.setdefault(vid, []).append({"id": sid, "name": name})
    return out


def _load_route_tables(query_dir: Path) -> dict[str, list[dict]]:
    """Read the ListRouteTables output (merging all region files) and return {vpc_id: [route_table]}."""
    out: dict[str, list[dict]] = {}
    seen: set = set()
    for f in _latest(query_dir, "ROUTETABLE/temp", "ROUTETABLE_route_tables_*.json"):
        for rt in _load_list(f, ["routetables"]):
            vid = _text(rt.get("vpc_id"))
            rid = _text(rt.get("id"))
            name = _text(rt.get("name"))
            if not vid or not rid:
                continue
            if (vid, rid) in seen:
                continue
            seen.add((vid, rid))
            out.setdefault(vid, []).append({"id": rid, "name": name})
    return out


def _links_vpc(query_dir: Path) -> list[tuple]:
    """VPC -> subnets/route tables (ListSubnets / ListRouteTables details, sub-resource [subtype] prefix).

    When subnets and route tables have details (name+ID), show [subtype]<name> (<ID>);
    cloud_resources entries that are only type+count (virsubnet/routetable summary) are skipped;
    summary entries without a name and without an ID are not displayed (theoretical fallback).
    """
    subnets_by_vpc = _load_subnets(query_dir)
    rts_by_vpc = _load_route_tables(query_dir)
    links = []
    for f in _latest(query_dir, "VPC/temp", "VPC_vpcs_*.json"):
        for v in _load_list(f, ["vpcs"]):
            vid = _text(v.get("id"))
            if not vid:
                continue
            # Subnet details (ListSubnets) — sub-resource, tagged with [subtype] prefix
            for sub in subnets_by_vpc.get(vid, []):
                links.append(("VPC", vid, SUBNET_LABEL, sub["name"], sub["id"], ""))
            # Route table details (ListRouteTables) — sub-resource, tagged with [subtype] prefix
            for rt in rts_by_vpc.get(vid, []):
                links.append(("VPC", vid, ROUTE_TABLE_LABEL, rt["name"] or rt["id"], rt["id"], ""))
            has_subnet_detail = vid in subnets_by_vpc
            has_rt_detail = vid in rts_by_vpc
            # cloud_resources summary: virsubnet/routetable skipped when details exist;
            # summary entries without a resource name and without a resource id are not displayed
            for cr in v.get("cloud_resources") or []:
                raw_type = _text(cr.get("resource_type")).lower()
                rtype = _norm_type(cr.get("resource_type"))
                rid = _text(cr.get("resource_id"))
                label = _text(cr.get("resource_name"))
                if raw_type in ("virsubnet", "subnet") and has_subnet_detail:
                    continue
                if raw_type in ("routetable", "route_table") and has_rt_detail:
                    continue
                if not rid and not label:
                    continue
                links.append(("VPC", vid, rtype or ASSOCIATED_RESOURCE_LABEL, label, rid))
    return links


def _links_elb(query_dir: Path) -> list[tuple]:
    """ELB load balancer -> backend servers (pool -> member chain).

    Data files: ELB/temp/ELB_loadbalancers_*.json (LB list),
                ELB_pools_<lb_name>_*.json (pools, contains loadbalancers[].id),
                ELB_members_<pool_id>_*.json (members, filename contains the pool id).
    """
    links = []
    pool_files = {f.name: f for f in _latest(query_dir, "ELB/temp", "ELB_pools_*.json")}
    member_files = {f.name: f for f in _latest(query_dir, "ELB/temp", "ELB_members_*.json")}
    if not pool_files or not member_files:
        return links

    # pool id -> lb id
    pool_to_lb: dict[str, str] = {}
    lb_names: dict[str, str] = {}
    for f in _latest(query_dir, "ELB/temp", "ELB_loadbalancers_*.json"):
        for lb in _load_list(f, ["loadbalancers", "load_balancers"]):
            lbid = _text(lb.get("id"))
            if lbid:
                lb_names[lbid] = _text(lb.get("name")) or lbid
    for fname, f in pool_files.items():
        for pool in _load_list(f, ["pools"]):
            pid = _text(pool.get("id"))
            if not pid:
                continue
            for ref in pool.get("loadbalancers") or []:
                lbid = _text(ref.get("id"))
                if lbid:
                    pool_to_lb[pid] = lbid

    # member file -> pool id (filename ELB_members_<pool_id>[_{region}]_<ts>.json)
    m = re.compile(r"ELB_members_([^_]+)_(?:[a-z0-9-]+_)?\d{8}_\d{6}\.json")
    for fname, f in member_files.items():
        mm = m.match(fname)
        if not mm:
            continue
        pid = mm.group(1)
        lbid = pool_to_lb.get(pid)
        if not lbid:
            continue
        for mem in _load_list(f, ["members"]):
            inst_id = _text(mem.get("instance_id"))
            addr = _text(mem.get("address"))
            if inst_id:
                # Bound to an ECS instance: show the name if resolvable, otherwise fall back to address
                links.append(("ELB", lbid, "ECS", addr or BACKEND_SERVER_LABEL, inst_id))
            elif addr:
                # Pure IP member (no instance_id): show the address
                links.append(("ELB", lbid, "IP", addr, ""))
    return links


def _ecs_by_port(query_dir: Path) -> dict[str, str]:
    """Build a port_id -> ecs_id map from ECS addresses (used to drill through EIP/GEIP PORT bindings).

    ECS ListServersDetails addresses.<net>[].OS-EXT-IPS:port_id is the NIC Port ID;
    when the EIP associate_instance_type is PORT, associate_instance_id is this port_id.
    All region files are merged; port_id is globally unique.
    """
    out: dict[str, str] = {}
    for f in _latest(query_dir, "ECS/temp", "ECS_servers_*.json"):
        for srv in _load_list(f, ["servers"]):
            sid = _text(srv.get("id"))
            if not sid:
                continue
            for _net, ports in (srv.get("addresses") or {}).items():
                for pinfo in (ports if isinstance(ports, list) else []):
                    pid = _text(pinfo.get("OS-EXT-IPS:port_id") or pinfo.get("port_id"))
                    if pid and pid not in out:
                        out[pid] = sid
    return out


def _links_eip(query_dir: Path, ecs_by_port: dict[str, str]) -> list[tuple]:
    """EIP elastic public IP -> bound instance (publicip.instance_id/instance_type)."""
    links = []
    for f in _latest(query_dir, "EIP/temp", "EIP_publicips_*.json"):
        for e in _load_list(f, ["publicips"]):
            eid = _text(e.get("id"))
            # EIP v3 returns associate_instance_id/type (same naming as GEIP)
            inst_id = _text(e.get("associate_instance_id") or e.get("instance_id"))
            if not eid or not inst_id:
                continue
            raw_type = _text(e.get("associate_instance_type") or e.get("instance_type")).upper()
            if raw_type == "PORT":
                # Drill through the NIC Port -> ECS (Port is an intermediate resource, not queried separately)
                ecs = ecs_by_port.get(inst_id)
                if ecs:
                    links.append(("EIP", eid, "ECS", "", ecs))
                continue  # Port itself is not shown as downstream
            inst_type = _norm_type(e.get("associate_instance_type") or e.get("instance_type") or "ECS")
            links.append(("EIP", eid, inst_type, "", inst_id))
    return links


def _links_ccaas(query_dir: Path) -> list[tuple]:
    """CC cloud connection -> inter-region bandwidth (sub-resource, [subtype] prefix + type label).

    Format example: [subtype]<CCAAS_INTER_REGION_BANDWIDTH_LABEL>:cn-east-2->cn-east-3 (50Mbps) (id)
    """
    links = []
    for f in _latest(query_dir, "CCAAS/temp", "CCAAS_inter_region_bandwidths_*.json"):
        for bw in _load_list(f, ["inter_region_bandwidths"]):
            bid = _text(bw.get("id"))
            ccid = _text(bw.get("cloud_connection_id"))
            if not bid or not ccid:
                continue
            local = _text(bw.get("local_region_id")) or "?"
            remote = _text(bw.get("remote_region_id")) or "?"
            speed = _text(bw.get("bandwidth"))
            label = f"{local}->{remote} ({speed}Mbps)" if speed else f"{local}->{remote}"
            links.append(("CCAAS_CloudConnection", ccid, INTER_REGION_BANDWIDTH_LABEL,
                          label, bid, CCAAS_INTER_REGION_BANDWIDTH_LABEL))
    return links


# ═══════════════════ Aggregation and application ═══════════════════

def _links_peering(query_dir: Path) -> list[tuple]:
    """VPC Peering -> the two VPCs it connects (request_vpc + accept_vpc).

    Each peering record has request_vpc_info.vpc_id and accept_vpc_info.vpc_id.
    We link the peering to both VPCs as downstream (the peering connects them).
    """
    links = []
    for f in _latest(query_dir, "PEERING/temp", "PEERING_vpc_peerings_*.json"):
        for p in _load_list(f, ["peerings", "vpc_peerings"]):
            pid = _text(p.get("id"))
            if not pid:
                continue
            # Request VPC
            req = p.get("request_vpc_info") or {}
            req_vid = _text(req.get("vpc_id"))
            if req_vid:
                links.append(("VPC_Peering", pid, "VPC", "", req_vid))
            # Accept VPC
            acc = p.get("accept_vpc_info") or {}
            acc_vid = _text(acc.get("vpc_id"))
            if acc_vid:
                links.append(("VPC_Peering", pid, "VPC", "", acc_vid))
    return links


def _links_vpcep(query_dir: Path) -> list[tuple]:
    """VPCEndpoint -> the VPC and subnet it belongs to.

    Each endpoint record has vpc_id and subnet_id.
    We link the endpoint to both as downstream (the endpoint resides in them).
    """
    links = []
    for f in _latest(query_dir, "VPCEP/temp", "VPCEP_endpoints_*.json"):
        for ep in _load_list(f, ["endpoints"]):
            eid = _text(ep.get("id"))
            if not eid:
                continue
            # VPC
            vid = _text(ep.get("vpc_id"))
            if vid:
                links.append(("VPCEndpoint", eid, "VPC", "", vid))
            # Subnet
            sid = _text(ep.get("subnet_id"))
            if sid:
                links.append(("VPCEndpoint", eid, "VPC_Subnet", "", sid))
    return links


def _links_vpn(query_dir: Path) -> list[tuple]:
    """VPN -> VPC (gateway belongs to a VPC); VPN_Connection -> VPN gateway + customer gateway.

    - VPN gateway has vpc_id → link to VPC
    - VPN connection has vgw_id → link to VPN gateway, and cgw_id → link to VPN_PeerGateway
    """
    links = []
    # VPN gateway → VPC
    for f in _latest(query_dir, "VPN/temp", "VPN_vpn_gateways_*.json"):
        for gw in _load_list(f, ["vpn_gateways"]):
            gid = _text(gw.get("id"))
            if not gid:
                continue
            vid = _text(gw.get("vpc_id"))
            if vid:
                links.append(("VPN", gid, "VPC", "", vid))
    # VPN connection → VPN gateway + customer gateway
    for f in _latest(query_dir, "VPN/temp", "VPN_vpn_connections_*.json"):
        for conn in _load_list(f, ["vpn_connections"]):
            cid = _text(conn.get("id"))
            if not cid:
                continue
            vgw_id = _text(conn.get("vgw_id"))
            if vgw_id:
                links.append(("VPN_Connection", cid, "VPN", "", vgw_id))
            cgw_id = _text(conn.get("cgw_id"))
            if cgw_id:
                links.append(("VPN_Connection", cid, "VPN_PeerGateway", "", cgw_id))
    return links


def _links_dns(query_dir: Path) -> list[tuple]:
    """DNS_PrivateZone -> associated VPCs (routers).

    ListPrivateZones does not return the VPC association. We query ShowPrivateZone
    per zone (saved as DNS_private_zone_routers_<zone_id>_*.json), which returns a
    `routers` array; each router_id is the associated VPC ID.
    """
    links = []
    for f in _latest(query_dir, "DNS/temp", "DNS_private_zone_routers_*.json"):
        try:
            raw = f.read_text(encoding="utf-8")
            data = json.loads(_clean_json(raw))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        zid = _text(data.get("id"))
        if not zid:
            continue
        for router in data.get("routers") or []:
            rid = _text(router.get("router_id"))
            if rid:
                links.append(("DNS_PrivateZone", zid, "VPC", "", rid))
    return links


def _links_er(query_dir: Path) -> list[tuple]:
    """ER attachments -> owning ER + attached resource + route table.

    Each attachment has:
      - er_id → owning enterprise router
      - resource_id + resource_type → the attached resource (vpc / vpn / peering etc.)
      - route_table_id → the associated route table
    """
    links = []
    for f in _latest(query_dir, "ER/temp", "ER_attachments_*.json"):
        for att in _load_list(f, ["attachments"]):
            aid = _text(att.get("id"))
            if not aid:
                continue
            # owning ER
            er_id = _text(att.get("er_id"))
            if er_id:
                links.append(("ER_Attachment", aid, "ER", "", er_id))
            # attached resource (map resource_type → marker-table type)
            rid = _text(att.get("resource_id"))
            rtype = _text(att.get("resource_type")).lower()
            if rid and rtype:
                if rtype == "vpc":
                    links.append(("ER_Attachment", aid, "VPC", "", rid))
                elif rtype == "vpn":
                    links.append(("ER_Attachment", aid, "VPN", "", rid))
                elif rtype == "peering":
                    links.append(("ER_Attachment", aid, "VPC_Peering", "", rid))
                else:
                    links.append(("ER_Attachment", aid, rtype.upper(), "", rid))
            # associated route table
            rt_id = _text(att.get("route_table_id"))
            if rt_id:
                links.append(("ER_Attachment", aid, "ER_RouteTable", "", rt_id))
    return links


def collect_links(query_dir: Path) -> list[tuple]:
    """Collect relationships from all data sources and return unified 5-tuple Links."""
    links = []
    ecs_by_port = _ecs_by_port(query_dir)
    links += _links_geip(query_dir, ecs_by_port)
    links += _links_cce_nodes(query_dir)
    links += _links_vpc(query_dir)
    links += _links_elb(query_dir)
    links += _links_ccaas(query_dir)
    links += _links_eip(query_dir, ecs_by_port)
    links += _links_peering(query_dir)
    links += _links_vpcep(query_dir)
    links += _links_vpn(query_dir)
    links += _links_dns(query_dir)
    links += _links_er(query_dir)
    return links


def render_link(link: tuple, registry: dict[str, dict]) -> str:
    """Render a relationship as marker-table content: `resource name (resource ID)`.

    Sub-resources (CCE nodes / VPC subnets) are displayed in the same format as downstream bindings;
    entries without a name and without an ID (only a type, e.g. VPC cloud_resources route tables) return an empty string and are dropped by the caller.
    """
    is_subtype = len(link) >= 6
    subtype_label = link[5] if is_subtype else ""
    _, _, to_type, to_label, to_id = link[:5]
    name = resolve_name(registry, to_type, to_id) or to_label
    if to_id:
        if is_subtype:
            # Sub-resource: [subtype]<name> (<id>); when there is a type label: [subtype]<label>:<name> (<id>)
            if subtype_label:
                return f"[subtype]{subtype_label}:{name} ({to_id})" if name else f"[subtype]{subtype_label} ({to_id})"
            return f"[subtype]{name} ({to_id})" if name else f"[subtype] ({to_id})"
        # True downstream: <name> (<id>)
        return f"{name or _norm_type(to_type)} ({to_id})" if (name or to_type) else to_id
    # No ID: sub-resource with only a type label keeps the marker; without name and without ID it is dropped (e.g. route tables)
    if is_subtype:
        if subtype_label:
            return f"[subtype]{subtype_label}:{name}" if name else f"[subtype]{subtype_label}"
        return ""
    return name or _norm_type(to_type)


def apply_inference(rows: list[dict], query_dir: Path) -> list[dict]:
    """Core entry: fill downstream_inferred for each resource row.

    Returns the original rows (modified in place); each row's downstream_inferred becomes multi-line `resource name (ID)`.
    """
    registry = build_registry(rows)
    links = collect_links(query_dir)
    # Group from -> [link] (exact match by type+ID of the resource-table row)
    grouped: dict[tuple[str, str], list[tuple]] = {}
    for link in links:
        from_type, from_id = link[0], link[1]
        grouped.setdefault((from_type, from_id), []).append(link)

    for r in rows:
        key = (_text(r.get("resource_type")), _text(r.get("resource_id")))
        line_links = grouped.get(key, [])
        if not line_links:
            continue
        lines = []
        seen = set()
        for link in line_links:
            line = render_link(link, registry)
            if not line or line in seen:
                continue
            seen.add(line)
            lines.append(line)
        if lines:
            r["downstream_inferred"] = "\n".join(sorted(lines))

    return rows