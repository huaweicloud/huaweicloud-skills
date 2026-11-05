#!/usr/bin/env python3
import ipaddress
import json
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from mgc_migrate import (
    Config,
    HcApiClient,
    choose_target_flavors,
    cleanup_terminal_tasks_for_source,
    create_sms_migproject,
    create_sms_task,
    extract_boot_disk_size_gb_from_source,
    extract_data_disks_from_source,
    extract_server_id_from_ecs_job,
    get_first_available_az,
    get_candidate_eip_types,
    get_server_fixed_and_floating_ip,
    get_server_primary_fixed_ip,
    get_server_primary_floating_ip,
    get_server_security_group_ids,
    get_server_vpc_id,
    get_flavor_vcpus_ram,
    get_sms_source_detail,
    get_sms_source_server,
    get_vpc_default_security_group_id,
    list_sms_tasks,
    normalize_ip_prefix,
    parse_required_root_volume_size_from_error,
    print_step,
    start_sms_task,
    get_sms_task_state,
    unique_nonempty,
    wait_ecs_job_success,
    write_json_file,
)


class SecurityGroupRuleQuotaExceeded(RuntimeError):
    pass


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError("Missing required environment variable: %s" % name)
    return value


def env_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def env_default_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())


def env_csv(name: str) -> List[str]:
    raw = os.getenv(name, "")
    out: List[str] = []
    for item in raw.split(","):
        val = item.strip()
        if val and val not in out:
            out.append(val)
    return out


def list_projects(client: HcApiClient) -> List[dict]:
    rsp = client.request_json("GET", "https://iam.myhuaweicloud.com/v3/projects", params={"enabled": "true"})
    return rsp.get("projects", []) or []


def get_project_name_by_id(client: HcApiClient, project_id: str) -> str:
    for p in list_projects(client):
        if str(p.get("id") or "").strip() == project_id:
            return str(p.get("name") or "").strip()
    return ""


def try_get_ecs_server(client: HcApiClient, region: str, project_id: str, server_id: str) -> Optional[dict]:
    try:
        rsp = client.request_json(
            "GET",
            "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s" % (region, project_id, server_id),
        )
    except Exception:
        return None
    return rsp.get("server") or None


def find_source_server(
    source_client: HcApiClient,
    source_vm_id: str,
    preferred_region: str,
    preferred_project_id: str,
) -> dict:
    projects = list_projects(source_client)
    if not projects:
        raise RuntimeError("No IAM projects found for source account")

    checked: List[Tuple[str, str]] = []

    def candidates() -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        if preferred_region and preferred_project_id:
            out.append((preferred_region, preferred_project_id))
        for p in projects:
            region = str(p.get("name") or "").strip()
            pid = str(p.get("id") or "").strip()
            if not region or not pid:
                continue
            pair = (region, pid)
            if pair not in out:
                out.append(pair)
        return out

    for region, pid in candidates():
        checked.append((region, pid))
        server = try_get_ecs_server(source_client, region, pid, source_vm_id)
        if not server:
            continue
        return {
            "source_vm_id": source_vm_id,
            "source_region": region,
            "source_project_id": pid,
            "source_name": str(server.get("name") or ""),
            "source_fixed_ip": get_server_primary_fixed_ip(server),
            "source_floating_ip": get_server_primary_floating_ip(server),
            "source_vpc_id": get_server_vpc_id(server),
            "source_flavor_id": str((server.get("flavor") or {}).get("id") or "").strip(),
            "source_image_id": str((server.get("image") or {}).get("id") or "").strip(),
            "source_server": server,
        }

    raise RuntimeError(
        "Source ECS not found for id=%s. Checked projects=%s" % (
            source_vm_id,
            json.dumps(checked, ensure_ascii=False),
        )
    )


def list_project_servers(client: HcApiClient, region: str, project_id: str) -> List[dict]:
    rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/detail" % (region, project_id),
        params={"limit": "200"},
    )
    return rsp.get("servers", []) or []


def try_parse_ipv4_network(cidr: str) -> Optional[ipaddress.IPv4Network]:
    value = str(cidr or "").strip()
    if not value:
        return None
    try:
        net = ipaddress.ip_network(value, strict=False)
    except Exception:
        return None
    if net.version != 4:
        return None
    return net


def subnet_contains_ip(cidr: str, ip_text: str) -> bool:
    net = try_parse_ipv4_network(cidr)
    if not net:
        return False
    try:
        ip_obj = ipaddress.ip_address(str(ip_text).strip())
    except Exception:
        return False
    if ip_obj.version != 4:
        return False
    return ip_obj in net


def ipv4_subnet_within(subnet: ipaddress.IPv4Network, vpc: ipaddress.IPv4Network) -> bool:
    return (
        subnet.network_address >= vpc.network_address
        and subnet.broadcast_address <= vpc.broadcast_address
    )


def first_usable_gateway_ip(subnet: ipaddress.IPv4Network) -> str:
    hosts = subnet.hosts()
    first = next(hosts, None)
    if first is None:
        raise RuntimeError("No usable gateway IP in subnet %s" % str(subnet))
    return str(first)


def resolve_destination_context(
    dest_client: HcApiClient,
    preferred_region: str,
    preferred_project_id: str,
) -> dict:
    projects = list_projects(dest_client)
    if not projects:
        raise RuntimeError("No IAM projects found for destination account")

    if preferred_project_id:
        for p in projects:
            pid = str(p.get("id") or "").strip()
            if pid != preferred_project_id:
                continue
            region = str(p.get("name") or "").strip()
            if preferred_region and preferred_region != region:
                raise RuntimeError(
                    "DESTINATION_PROJECT_ID=%s belongs to region=%s, but DESTINATION_REGION=%s"
                    % (preferred_project_id, region, preferred_region)
                )
            return {
                "target_region": region,
                "target_project_id": pid,
                "target_project_name": region,
            }
        raise RuntimeError("Destination project id not found in IAM: %s" % preferred_project_id)

    if preferred_region:
        for p in projects:
            region = str(p.get("name") or "").strip()
            if region != preferred_region:
                continue
            pid = str(p.get("id") or "").strip()
            if pid:
                return {
                    "target_region": region,
                    "target_project_id": pid,
                    "target_project_name": region,
                }
        raise RuntimeError("No IAM project found for destination region: %s" % preferred_region)

    region = str(projects[0].get("name") or "").strip()
    pid = str(projects[0].get("id") or "").strip()
    if not region or not pid:
        raise RuntimeError("Unable to resolve destination project/region from IAM projects")
    return {
        "target_region": region,
        "target_project_id": pid,
        "target_project_name": region,
    }


def list_subnets(
    client: HcApiClient,
    region: str,
    project_id: str,
    vpc_id: str = "",
) -> List[dict]:
    params = {"limit": "200"}
    if vpc_id:
        params["vpc_id"] = vpc_id
    rsp = client.request_json(
        "GET",
        "https://vpc.%s.myhuaweicloud.com/v1/%s/subnets" % (region, project_id),
        params=params,
    )
    return rsp.get("subnets", []) or []


def find_subnet_containing_fixed_ip(subnets: List[dict], fixed_ip: str) -> Optional[dict]:
    matches: List[Tuple[int, dict]] = []
    for subnet in subnets:
        cidr = str(subnet.get("cidr") or "").strip()
        if not subnet_contains_ip(cidr, fixed_ip):
            continue
        net = try_parse_ipv4_network(cidr)
        if not net:
            continue
        # Prefer the most-specific subnet that still contains the fixed IP.
        matches.append((int(net.prefixlen), subnet))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0], reverse=True)
    return matches[0][1]


def find_vpc_by_cidr(
    client: HcApiClient,
    region: str,
    project_id: str,
    cidr: str,
) -> Optional[dict]:
    rsp = client.request_json(
        "GET",
        "https://vpc.%s.myhuaweicloud.com/v1/%s/vpcs" % (region, project_id),
        params={"limit": "200"},
    )
    for vpc in rsp.get("vpcs", []) or []:
        if str(vpc.get("cidr") or "").strip() == cidr:
            return vpc
    return None


def ensure_vpc_with_cidr(
    client: HcApiClient,
    region: str,
    project_id: str,
    cidr: str,
) -> str:
    existing = find_vpc_by_cidr(client, region, project_id, cidr)
    if existing:
        vid = str(existing.get("id") or "").strip()
        if vid:
            return vid

    name = "vm-migration-vpc-%s" % str(cidr).replace(".", "-").replace("/", "-")
    try:
        rsp = client.request_json(
            "POST",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/vpcs" % (region, project_id),
            body={"vpc": {"name": name, "cidr": cidr}},
        )
        vpc_id = str((rsp.get("vpc") or {}).get("id") or "").strip()
        if vpc_id:
            return vpc_id
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" not in err and "already exist" not in err:
            raise

    existing = find_vpc_by_cidr(client, region, project_id, cidr)
    if existing:
        vpc_id = str(existing.get("id") or "").strip()
        if vpc_id:
            return vpc_id
    raise RuntimeError("Failed to create/find destination VPC by cidr=%s" % cidr)


def ensure_subnet_with_cidr(
    client: HcApiClient,
    region: str,
    project_id: str,
    vpc_id: str,
    subnet_cidr: str,
) -> dict:
    subnets = list_subnets(client, region, project_id, vpc_id=vpc_id)
    for subnet in subnets:
        if str(subnet.get("cidr") or "").strip() != subnet_cidr:
            continue
        if str(subnet.get("id") or "").strip():
            return subnet

    subnet_net = try_parse_ipv4_network(subnet_cidr)
    if not subnet_net:
        raise RuntimeError("Invalid subnet cidr: %s" % subnet_cidr)

    subnet_name = "vm-migration-subnet-%s" % subnet_cidr.replace(".", "-").replace("/", "-")
    try:
        rsp = client.request_json(
            "POST",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/subnets" % (region, project_id),
            body={
                "subnet": {
                    "name": subnet_name,
                    "cidr": subnet_cidr,
                    "gateway_ip": first_usable_gateway_ip(subnet_net),
                    "vpc_id": vpc_id,
                    "dhcp_enable": True,
                }
            },
        )
        subnet = rsp.get("subnet") or {}
        if str(subnet.get("id") or "").strip():
            return subnet
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" not in err and "already exist" not in err:
            raise

    subnets = list_subnets(client, region, project_id, vpc_id=vpc_id)
    for subnet in subnets:
        if str(subnet.get("cidr") or "").strip() == subnet_cidr and str(subnet.get("id") or "").strip():
            return subnet
    raise RuntimeError("Failed to create/find destination subnet by cidr=%s" % subnet_cidr)


def get_source_network_profile(
    source_client: HcApiClient,
    source_region: str,
    source_project_id: str,
    source_server_id: str,
    source_fixed_ip: str,
    source_vpc_id: str,
) -> Dict[str, str]:
    subnet_id = ""
    subnet_cidr = ""
    vpc_cidr = ""

    try:
        rsp = source_client.request_json(
            "GET",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/ports" % (source_region, source_project_id),
            params={"device_id": source_server_id},
        )
        ports = rsp.get("ports", []) or []
        for port in ports:
            fixed_items = port.get("fixed_ips", []) or []
            for fixed in fixed_items:
                ip_val = str(fixed.get("ip_address") or "").strip()
                if ip_val != source_fixed_ip:
                    continue
                subnet_id = str(fixed.get("subnet_id") or "").strip()
                break
            if subnet_id:
                break
        if not subnet_id and ports:
            first_port = ports[0]
            for fixed in first_port.get("fixed_ips", []) or []:
                subnet_id = str(fixed.get("subnet_id") or "").strip()
                if subnet_id:
                    break
    except Exception:
        subnet_id = ""

    if subnet_id:
        try:
            subnet_rsp = source_client.request_json(
                "GET",
                "https://vpc.%s.myhuaweicloud.com/v1/%s/subnets/%s" % (source_region, source_project_id, subnet_id),
            )
            subnet = subnet_rsp.get("subnet") or {}
            subnet_cidr = str(subnet.get("cidr") or "").strip()
        except Exception:
            subnet_cidr = ""

    if source_vpc_id:
        try:
            vpc_rsp = source_client.request_json(
                "GET",
                "https://vpc.%s.myhuaweicloud.com/v1/%s/vpcs/%s" % (source_region, source_project_id, source_vpc_id),
            )
            vpc = vpc_rsp.get("vpc") or {}
            vpc_cidr = str(vpc.get("cidr") or "").strip()
        except Exception:
            vpc_cidr = ""

    return {
        "source_subnet_id": subnet_id,
        "source_subnet_cidr": subnet_cidr,
        "source_vpc_cidr": vpc_cidr,
    }


def choose_destination_network_for_fixed_ip(
    dest_client: HcApiClient,
    target_region: str,
    target_project_id: str,
    source_fixed_ip: str,
    source_network_profile: Dict[str, str],
) -> Dict[str, str]:
    all_subnets = list_subnets(dest_client, target_region, target_project_id)
    existing = find_subnet_containing_fixed_ip(all_subnets, source_fixed_ip)
    if existing:
        return {
            "target_vpc_id": str(existing.get("vpc_id") or "").strip(),
            "target_subnet_id": str(existing.get("id") or "").strip(),
            "target_subnet_cidr": str(existing.get("cidr") or "").strip(),
            "target_network_created": "false",
        }

    source_subnet_cidr = str(source_network_profile.get("source_subnet_cidr") or "").strip()
    source_vpc_cidr = str(source_network_profile.get("source_vpc_cidr") or "").strip()

    subnet_net = try_parse_ipv4_network(source_subnet_cidr)
    if not subnet_net or not subnet_contains_ip(str(subnet_net), source_fixed_ip):
        subnet_net = ipaddress.ip_network("%s/24" % source_fixed_ip, strict=False)

    vpc_net = try_parse_ipv4_network(source_vpc_cidr)
    if not vpc_net or not subnet_contains_ip(str(vpc_net), source_fixed_ip):
        if int(subnet_net.prefixlen) >= 16:
            vpc_net = subnet_net.supernet(new_prefix=16)
        else:
            vpc_net = subnet_net

    if not ipv4_subnet_within(subnet_net, vpc_net):
        vpc_net = subnet_net

    vpc_id = ensure_vpc_with_cidr(
        client=dest_client,
        region=target_region,
        project_id=target_project_id,
        cidr=str(vpc_net),
    )
    subnet = ensure_subnet_with_cidr(
        client=dest_client,
        region=target_region,
        project_id=target_project_id,
        vpc_id=vpc_id,
        subnet_cidr=str(subnet_net),
    )
    return {
        "target_vpc_id": vpc_id,
        "target_subnet_id": str(subnet.get("id") or "").strip(),
        "target_subnet_cidr": str(subnet.get("cidr") or "").strip(),
        "target_network_created": "true",
    }


def find_target_server_by_fixed_ip_in_project(
    dest_client: HcApiClient,
    target_fixed_ip: str,
    target_region: str,
    target_project_id: str,
) -> Optional[dict]:
    servers = list_project_servers(dest_client, target_region, target_project_id)
    for s in servers:
        fixed = get_server_primary_fixed_ip(s)
        if fixed != target_fixed_ip:
            continue
        return {
            "target_vm_id": str(s.get("id") or ""),
            "target_name": str(s.get("name") or ""),
            "target_region": target_region,
            "target_project_id": target_project_id,
            "target_project_name": target_region,
            "target_fixed_ip": fixed,
            "target_floating_ip": get_server_primary_floating_ip(s),
            "target_status": str(s.get("status") or ""),
            "target_vpc_id": get_server_vpc_id(s),
        }
    return None


def build_target_server_create_body(
    az: str,
    name: str,
    image_id: str,
    flavor_id: str,
    admin_password: str,
    vpc_id: str,
    subnet_id: str,
    fixed_ip: str,
    root_volume_type: str,
    root_volume_size_gb: int,
    data_disks: List[dict],
) -> dict:
    root_volume: Dict[str, object] = {"volumetype": root_volume_type}
    if int(root_volume_size_gb) > 0:
        root_volume["size"] = int(root_volume_size_gb)

    server: Dict[str, object] = {
        "availability_zone": az,
        "name": name,
        "imageRef": image_id,
        "flavorRef": flavor_id,
        "adminPass": admin_password,
        "vpcid": vpc_id,
        "nics": [{"subnet_id": subnet_id, "ip_address": fixed_ip}],
        "root_volume": root_volume,
        "extendparam": {"chargingMode": "postPaid"},
    }
    if data_disks:
        server["data_volumes"] = data_disks
    return {"server": server}


def create_target_server_with_fixed_ip(
    dest_client: HcApiClient,
    source_client: HcApiClient,
    source_item: dict,
    source_sms_detail: dict,
    target_region: str,
    target_project_id: str,
    target_image_id: str,
    target_flavor_id: str,
    target_admin_password: str,
    root_volume_type: str,
    data_volume_type: str,
) -> dict:
    source_vm_id = str(source_item.get("source_vm_id") or "").strip()
    source_name = str(source_item.get("source_name") or "").strip() or ("vm-%s" % source_vm_id[:8])
    source_fixed_ip = str(source_item.get("source_fixed_ip") or "").strip()
    source_region = str(source_item.get("source_region") or "").strip()
    source_project_id = str(source_item.get("source_project_id") or "").strip()
    source_vpc_id = str(source_item.get("source_vpc_id") or "").strip()
    source_flavor_id = str(source_item.get("source_flavor_id") or "").strip()
    source_image_id = str(source_item.get("source_image_id") or "").strip()

    source_network_profile = get_source_network_profile(
        source_client=source_client,
        source_region=source_region,
        source_project_id=source_project_id,
        source_server_id=source_vm_id,
        source_fixed_ip=source_fixed_ip,
        source_vpc_id=source_vpc_id,
    )
    target_network = choose_destination_network_for_fixed_ip(
        dest_client=dest_client,
        target_region=target_region,
        target_project_id=target_project_id,
        source_fixed_ip=source_fixed_ip,
        source_network_profile=source_network_profile,
    )
    target_vpc_id = str(target_network.get("target_vpc_id") or "").strip()
    target_subnet_id = str(target_network.get("target_subnet_id") or "").strip()
    if not target_vpc_id or not target_subnet_id:
        raise RuntimeError(
            "Cannot resolve destination network for source=%s fixed_ip=%s"
            % (source_vm_id, source_fixed_ip)
        )

    src_vcpus = 0
    src_ram_mb = 0
    if source_flavor_id:
        try:
            src_vcpus, src_ram_mb = get_flavor_vcpus_ram(
                client=source_client,
                region=source_region,
                project_id=source_project_id,
                flavor_id=source_flavor_id,
            )
        except Exception:
            src_vcpus, src_ram_mb = 0, 0
    if src_vcpus <= 0:
        src_vcpus = int(source_sms_detail.get("cpu_quantity") or 0)
    if src_ram_mb <= 0:
        src_ram_mb = int(int(source_sms_detail.get("memory") or 0) / (1024 * 1024))

    preferred_flavor = str(target_flavor_id or "").strip() or source_flavor_id
    flavor_candidates = choose_target_flavors(
        client=dest_client,
        target_region=target_region,
        target_project_id=target_project_id,
        preferred_flavor_id=preferred_flavor,
        src_vcpus=src_vcpus,
        src_ram_mb=src_ram_mb,
    )

    image_candidates = unique_nonempty([target_image_id, source_image_id])
    if not image_candidates:
        raise RuntimeError(
            "No valid target image candidates for source=%s. "
            "Set TARGET_IMAGE_ID or ensure source image id is available in destination account."
            % source_vm_id
        )

    az = get_first_available_az(dest_client, target_region, target_project_id)
    root_volume_size_gb = extract_boot_disk_size_gb_from_source(source_sms_detail)
    data_disks = extract_data_disks_from_source(source_sms_detail, data_volume_type)
    clean_source_name = re.sub(r"[^A-Za-z0-9-]", "-", source_name).strip("-")
    if not clean_source_name:
        clean_source_name = "vm"
    if clean_source_name[0].isdigit():
        clean_source_name = "vm-" + clean_source_name
    base_server_name = ("%s-migrate-%s" % (clean_source_name[:24], source_vm_id[:8]))[:45]

    last_error: Optional[Exception] = None
    for flavor_id in flavor_candidates:
        for image_id in image_candidates:
            create_server_name = "%s-%d" % (base_server_name, int(time.time()))
            body = build_target_server_create_body(
                az=az,
                name=create_server_name,
                image_id=image_id,
                flavor_id=flavor_id,
                admin_password=target_admin_password,
                vpc_id=target_vpc_id,
                subnet_id=target_subnet_id,
                fixed_ip=source_fixed_ip,
                root_volume_type=root_volume_type,
                root_volume_size_gb=root_volume_size_gb,
                data_disks=data_disks,
            )
            try:
                rsp = dest_client.request_json(
                    "POST",
                    "https://ecs.%s.myhuaweicloud.com/v1.1/%s/cloudservers" % (target_region, target_project_id),
                    body=body,
                )
            except Exception as exc:
                last_error = exc
                err = str(exc)
                existing = find_target_server_by_fixed_ip_in_project(
                    dest_client=dest_client,
                    target_fixed_ip=source_fixed_ip,
                    target_region=target_region,
                    target_project_id=target_project_id,
                )
                if existing:
                    return existing

                required_root_size = parse_required_root_volume_size_from_error(err)
                if "Ecs.0005" in err and required_root_size > int(root_volume_size_gb):
                    root_volume_size_gb = required_root_size
                    continue
                if "Ecs.0018" in err or "sold out" in err.lower():
                    break
                if (
                    "image" in err.lower()
                    and ("not found" in err.lower() or "invalid" in err.lower() or "not exist" in err.lower())
                ):
                    continue
                raise

            server_id = ""
            server_ids = rsp.get("serverIds") or rsp.get("server_ids") or []
            if isinstance(server_ids, list):
                for sid in server_ids:
                    sid_val = str(sid or "").strip()
                    if sid_val:
                        server_id = sid_val
                        break

            job_id = str(rsp.get("job_id") or "").strip()
            if job_id:
                job_rsp = wait_ecs_job_success(dest_client, target_region, target_project_id, job_id)
                if not server_id:
                    server_id = extract_server_id_from_ecs_job(job_rsp)

            if not server_id:
                matched = find_target_server_by_fixed_ip_in_project(
                    dest_client=dest_client,
                    target_fixed_ip=source_fixed_ip,
                    target_region=target_region,
                    target_project_id=target_project_id,
                )
                if matched:
                    return matched
                raise RuntimeError("Target ECS create response missing server id for source %s" % source_vm_id)

            for _ in range(30):
                server = try_get_ecs_server(dest_client, target_region, target_project_id, server_id)
                if server:
                    return {
                        "target_vm_id": str(server.get("id") or "").strip(),
                        "target_name": str(server.get("name") or "").strip(),
                        "target_region": target_region,
                        "target_project_id": target_project_id,
                        "target_project_name": target_region,
                        "target_fixed_ip": get_server_primary_fixed_ip(server) or source_fixed_ip,
                        "target_floating_ip": get_server_primary_floating_ip(server),
                        "target_status": str(server.get("status") or "").strip(),
                        "target_vpc_id": get_server_vpc_id(server) or target_vpc_id,
                    }
                time.sleep(2)

            matched = find_target_server_by_fixed_ip_in_project(
                dest_client=dest_client,
                target_fixed_ip=source_fixed_ip,
                target_region=target_region,
                target_project_id=target_project_id,
            )
            if matched:
                return matched
            raise RuntimeError("Created target ECS not queryable yet for source %s" % source_vm_id)

    if last_error is not None:
        raise RuntimeError("Failed to create destination ECS for source %s: %s" % (source_vm_id, str(last_error)))
    raise RuntimeError("Failed to create destination ECS for source %s" % source_vm_id)


def find_target_server_by_fixed_ip(
    dest_client: HcApiClient,
    target_fixed_ip: str,
    preferred_region: str,
    preferred_project_id: str,
) -> dict:
    projects = list_projects(dest_client)
    if not projects:
        raise RuntimeError("No IAM projects found for destination account")

    search_pairs: List[Tuple[str, str]] = []
    if preferred_region and preferred_project_id:
        search_pairs.append((preferred_region, preferred_project_id))
    for p in projects:
        region = str(p.get("name") or "").strip()
        pid = str(p.get("id") or "").strip()
        if not region or not pid:
            continue
        pair = (region, pid)
        if pair not in search_pairs:
            search_pairs.append(pair)

    for region, pid in search_pairs:
        try:
            servers = list_project_servers(dest_client, region, pid)
        except Exception:
            continue
        for s in servers:
            fixed = get_server_primary_fixed_ip(s)
            if fixed != target_fixed_ip:
                continue
            return {
                "target_vm_id": str(s.get("id") or ""),
                "target_name": str(s.get("name") or ""),
                "target_region": region,
                "target_project_id": pid,
                "target_project_name": region,
                "target_fixed_ip": fixed,
                "target_floating_ip": get_server_primary_floating_ip(s),
                "target_status": str(s.get("status") or ""),
                "target_vpc_id": get_server_vpc_id(s),
            }

    raise RuntimeError("Destination ECS not found by fixed_ip=%s" % target_fixed_ip)


def find_port_id_for_server(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    fixed_ip: str,
) -> str:
    rsp = client.request_json(
        "GET",
        "https://vpc.%s.myhuaweicloud.com/v1/%s/ports" % (region, project_id),
        params={"device_id": server_id},
    )
    ports = rsp.get("ports", []) or []
    if not ports:
        raise RuntimeError("No VPC port found for server=%s" % server_id)

    for p in ports:
        for ip_item in p.get("fixed_ips", []) or []:
            if str(ip_item.get("ip_address") or "").strip() == fixed_ip:
                pid = str(p.get("id") or "").strip()
                if pid:
                    return pid

    pid = str(ports[0].get("id") or "").strip()
    if not pid:
        raise RuntimeError("No valid port id found for server=%s" % server_id)
    return pid


def ensure_target_eip(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    fixed_ip: str,
    bandwidth_mbps: int,
) -> str:
    _, floating_ip = get_server_fixed_and_floating_ip(client, region, project_id, server_id)
    if floating_ip:
        return floating_ip

    port_id = find_port_id_for_server(client, region, project_id, server_id, fixed_ip)
    discovered = get_candidate_eip_types(client, region, project_id)
    eip_types: List[str] = []
    for candidate in ["5_bgp"] + list(discovered):
        val = str(candidate or "").strip()
        if not val:
            continue
        # v1 create endpoint expects pool type like "5_bgp", not "EIP".
        if "_" not in val:
            continue
        if val not in eip_types:
            eip_types.append(val)
    if not eip_types:
        eip_types = ["5_bgp"]

    def try_rebind_idle_eip() -> str:
        rsp = client.request_json(
            "GET",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips" % (region, project_id),
        )
        publicips = rsp.get("publicips", []) or []
        for item in publicips:
            eip_id = str(item.get("id") or "").strip()
            old_port_id = str(item.get("port_id") or "").strip()
            if not eip_id or not old_port_id:
                continue
            try:
                port_rsp = client.request_json(
                    "GET",
                    "https://vpc.%s.myhuaweicloud.com/v1/%s/ports/%s" % (region, project_id, old_port_id),
                )
            except Exception:
                continue
            port = port_rsp.get("port") or {}
            # Only reuse detached EIPs to avoid impacting running ECS.
            if str(port.get("device_id") or "").strip():
                continue
            client.request_json(
                "PUT",
                "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips/%s" % (region, project_id, eip_id),
                body={"publicip": {"port_id": None}},
            )
            try:
                client.request_json(
                    "PUT",
                    "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips/%s" % (region, project_id, eip_id),
                    body={"publicip": {"port_id": port_id}},
                )
            except Exception as exc:
                err = str(exc).lower()
                if "vpc.0510" in err and "already associated with port" in err:
                    # Keep best effort when backend association state is still converging.
                    time.sleep(2)
                    client.request_json(
                        "PUT",
                        "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips/%s" % (region, project_id, eip_id),
                        body={"publicip": {"port_id": port_id}},
                    )
                else:
                    raise
            for _ in range(30):
                _, floating = get_server_fixed_and_floating_ip(client, region, project_id, server_id)
                if floating:
                    return floating
                time.sleep(2)
        return ""

    last_err: Optional[Exception] = None
    quota_exceeded = False
    for eip_type in eip_types:
        body = {
            "publicip": {"type": eip_type},
            "bandwidth": {
                "name": "vm-migrate-%s" % server_id[:8],
                "size": int(bandwidth_mbps),
                "share_type": "PER",
                "charge_mode": "traffic",
            },
            "port_id": port_id,
        }
        created_eip_id = ""
        try:
            rsp = client.request_json(
                "POST",
                "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips" % (region, project_id),
                body=body,
            )
            created_eip_id = str((rsp.get("publicip") or {}).get("id") or "").strip()
        except Exception as exc:
            last_err = exc
            err = str(exc)
            if "EIP.7905" in err or "quota exceeded" in err.lower():
                quota_exceeded = True
                continue
            if "EIP.7904" in err or "not available" in err.lower():
                continue
            if "already" in err.lower() and "bound" in err.lower():
                break
            continue

        for _ in range(60):
            _, floating_ip = get_server_fixed_and_floating_ip(client, region, project_id, server_id)
            if floating_ip:
                return floating_ip
            time.sleep(3)

        # Some regions return success but do not actually bind in create path.
        if created_eip_id:
            try:
                client.request_json(
                    "PUT",
                    "https://vpc.%s.myhuaweicloud.com/v1/%s/publicips/%s"
                    % (region, project_id, created_eip_id),
                    body={"publicip": {"port_id": port_id}},
                )
            except Exception:
                pass

            for _ in range(30):
                _, floating_ip = get_server_fixed_and_floating_ip(client, region, project_id, server_id)
                if floating_ip:
                    return floating_ip
                time.sleep(2)

    _, floating_ip = get_server_fixed_and_floating_ip(client, region, project_id, server_id)
    if floating_ip:
        return floating_ip

    if quota_exceeded:
        floating_ip = try_rebind_idle_eip()
        if floating_ip:
            return floating_ip

    if last_err is not None:
        raise RuntimeError("Failed to create/bind EIP for server=%s: %s" % (server_id, str(last_err)))
    raise RuntimeError("Failed to create/bind EIP for server=%s" % server_id)


def create_target_sg_rule(
    client: HcApiClient,
    region: str,
    project_id: str,
    security_group_id: str,
    direction: str,
    remote_ip_prefix: str,
    description: str,
    protocol: str = "tcp",
    port_range_min: Optional[int] = None,
    port_range_max: Optional[int] = None,
) -> bool:
    proto = str(protocol or "").strip().lower()
    body = {
        "security_group_rule": {
            "security_group_id": security_group_id,
            "direction": direction,
            "ethertype": "IPv4",
            "remote_ip_prefix": normalize_ip_prefix(remote_ip_prefix),
            "description": description,
        }
    }
    if proto:
        body["security_group_rule"]["protocol"] = proto
        if port_range_min is not None:
            body["security_group_rule"]["port_range_min"] = int(port_range_min)
        if port_range_max is not None:
            body["security_group_rule"]["port_range_max"] = int(port_range_max)
    try:
        client.request_json(
            "POST",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/security-group-rules" % (region, project_id),
            body=body,
        )
        return True
    except Exception as exc:
        err = str(exc).lower()
        if "vpc.0614" in err or "quota exceeded" in err:
            raise SecurityGroupRuleQuotaExceeded(str(exc))
        if (
            "already exists" in err
            or "already exist" in err
            or "security group rule has existed" in err
            or "vpc.0608" in err
        ):
            return False
        raise


def has_target_sg_rule(
    rules: List[dict],
    direction: str,
    remote_ip_prefix: str,
    protocol: str,
    port_range_min: int,
    port_range_max: int,
) -> bool:
    want_prefix = normalize_ip_prefix(remote_ip_prefix)
    want_protocol = str(protocol or "").strip().lower()

    for rule in rules or []:
        if str(rule.get("direction") or "").lower() != direction.lower():
            continue
        if str(rule.get("ethertype") or "IPv4") != "IPv4":
            continue
        got_prefix = normalize_ip_prefix(str(rule.get("remote_ip_prefix") or "").strip())
        if got_prefix != want_prefix:
            continue

        got_protocol = str(rule.get("protocol") or "").strip().lower()
        # Existing "all protocol" rule covers required protocol.
        if got_protocol not in {"", want_protocol}:
            continue

        # Existing "all protocol" rule with same CIDR/direction is sufficient.
        if got_protocol == "":
            return True

        got_min = rule.get("port_range_min")
        got_max = rule.get("port_range_max")
        if got_min is None or got_max is None:
            # Protocol rule without explicit range is treated as wildcard.
            return True

        try:
            got_min_i = int(got_min)
            got_max_i = int(got_max)
        except Exception:
            return True

        if got_min_i <= int(port_range_min) and got_max_i >= int(port_range_max):
            return True

    return False


def find_or_create_migration_security_group(
    client: HcApiClient,
    region: str,
    project_id: str,
    vpc_id: str,
    description: str,
    target_server_id: str,
) -> str:
    name = "vm-migration-%s" % target_server_id[:8]

    def find_existing() -> str:
        rsp = client.request_json(
            "GET",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/security-groups" % (region, project_id),
            params={"vpc_id": vpc_id},
        )
        for sg in rsp.get("security_groups", []) or []:
            if str(sg.get("name") or "").strip() == name:
                sg_id = str(sg.get("id") or "").strip()
                if sg_id:
                    return sg_id
        return ""

    existing = find_existing()
    if existing:
        return existing

    try:
        rsp = client.request_json(
            "POST",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/security-groups" % (region, project_id),
            body={"security_group": {"name": name, "description": description, "vpc_id": vpc_id}},
        )
        sg_id = str((rsp.get("security_group") or {}).get("id") or "").strip()
        if sg_id:
            return sg_id
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" not in err and "already exist" not in err:
            raise

    existing = find_existing()
    if existing:
        return existing
    raise RuntimeError("Failed to create/find migration security group '%s'" % name)


def attach_security_group_to_server(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    security_group_id: str,
) -> bool:
    rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s" % (region, project_id, server_id),
    )
    server = rsp.get("server") or {}
    sg_ids = get_server_security_group_ids(server)
    if security_group_id in sg_ids:
        return False

    try:
        client.request_json(
            "POST",
            "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s/action" % (region, project_id, server_id),
            body={"addSecurityGroup": {"id": security_group_id}},
        )
        return True
    except Exception as exc:
        err = str(exc).lower()
        if "already" in err and "security group" in err:
            return False
        raise


def ensure_target_security_group_rules(
    client: HcApiClient,
    region: str,
    project_id: str,
    target_server_id: str,
    target_vpc_id: str,
    source_fixed_ip: str,
    source_floating_ip: str,
    description: str,
    source_os_type: str = "LINUX",
) -> Dict[str, object]:
    server_rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s" % (region, project_id, target_server_id),
    )
    server = server_rsp.get("server") or {}

    sg_ids = get_server_security_group_ids(server)
    fallback_default_sg = ""
    if not sg_ids:
        fallback_default_sg = get_vpc_default_security_group_id(client, region, project_id, target_vpc_id)
        sg_ids = [fallback_default_sg]

    peer_ips = unique_nonempty([source_fixed_ip, source_floating_ip])
    os_type = str(source_os_type or "").strip().upper()
    port_rules: List[Tuple[int, int]] = [(22, 22), (8900, 8900)]
    if os_type == "WINDOWS":
        port_rules.append((8899, 8899))

    required_rules: List[Tuple[str, str, str, int, int]] = []
    for peer in peer_ips:
        for direction in ("ingress", "egress"):
            for port_min, port_max in port_rules:
                required_rules.append((direction, peer, "tcp", port_min, port_max))

    if not required_rules:
        return {
            "target_security_group_ids": sg_ids,
            "target_vpc_default_security_group_id": fallback_default_sg,
            "target_security_group_rules_created": 0,
            "target_peer_ips": peer_ips,
            "target_migration_security_group_id": "",
        }

    sg_rules: Dict[str, List[dict]] = {}
    for sg_id in sg_ids:
        sg = client.request_json(
            "GET",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/security-groups/%s" % (region, project_id, sg_id),
        ).get("security_group") or {}
        sg_rules[sg_id] = sg.get("security_group_rules", []) or []

    def list_missing_rules() -> List[Tuple[str, str, str, int, int]]:
        missing: List[Tuple[str, str, str, int, int]] = []
        for direction, peer, protocol, port_min, port_max in required_rules:
            covered = False
            for rules in sg_rules.values():
                if has_target_sg_rule(
                    rules=rules,
                    direction=direction,
                    remote_ip_prefix=peer,
                    protocol=protocol,
                    port_range_min=port_min,
                    port_range_max=port_max,
                ):
                    covered = True
                    break
            if not covered:
                missing.append((direction, peer, protocol, port_min, port_max))
        return missing

    created = 0
    missing = list_missing_rules()

    # Add missing rules to as few attached SGs as possible (least-rule SG first).
    candidate_sg_ids = sorted(sg_ids, key=lambda x: len(sg_rules.get(x, [])))
    for sg_id in candidate_sg_ids:
        if not missing:
            break

        quota_hit = False
        for direction, peer, protocol, port_min, port_max in list(missing):
            try:
                added = create_target_sg_rule(
                    client=client,
                    region=region,
                    project_id=project_id,
                    security_group_id=sg_id,
                    direction=direction,
                    remote_ip_prefix=peer,
                    description=description,
                    protocol=protocol,
                    port_range_min=port_min,
                    port_range_max=port_max,
                )
            except SecurityGroupRuleQuotaExceeded:
                quota_hit = True
                break

            if added:
                created += 1
            # Keep in-memory rules in sync for duplicate-race and next checks.
            sg_rules.setdefault(sg_id, []).append(
                {
                    "direction": direction,
                    "ethertype": "IPv4",
                    "remote_ip_prefix": normalize_ip_prefix(peer),
                    "protocol": protocol,
                    "port_range_min": port_min,
                    "port_range_max": port_max,
                }
            )
            missing = list_missing_rules()
        if quota_hit:
            continue

    migration_sg_id = ""
    if missing:
        # Existing SGs are full. Create/attach a dedicated migration SG and write only missing rules there.
        migration_sg_id = find_or_create_migration_security_group(
            client=client,
            region=region,
            project_id=project_id,
            vpc_id=target_vpc_id,
            description=description,
            target_server_id=target_server_id,
        )
        attached = attach_security_group_to_server(
            client=client,
            region=region,
            project_id=project_id,
            server_id=target_server_id,
            security_group_id=migration_sg_id,
        )
        if attached:
            sg_ids.append(migration_sg_id)

        migration_rules = client.request_json(
            "GET",
            "https://vpc.%s.myhuaweicloud.com/v1/%s/security-groups/%s" % (region, project_id, migration_sg_id),
        ).get("security_group") or {}
        sg_rules[migration_sg_id] = migration_rules.get("security_group_rules", []) or []

        for direction, peer, protocol, port_min, port_max in list(missing):
            if has_target_sg_rule(
                rules=sg_rules[migration_sg_id],
                direction=direction,
                remote_ip_prefix=peer,
                protocol=protocol,
                port_range_min=port_min,
                port_range_max=port_max,
            ):
                continue
            if create_target_sg_rule(
                client=client,
                region=region,
                project_id=project_id,
                security_group_id=migration_sg_id,
                direction=direction,
                remote_ip_prefix=peer,
                description=description,
                protocol=protocol,
                port_range_min=port_min,
                port_range_max=port_max,
            ):
                created += 1
                sg_rules[migration_sg_id].append(
                    {
                        "direction": direction,
                        "ethertype": "IPv4",
                        "remote_ip_prefix": normalize_ip_prefix(peer),
                        "protocol": protocol,
                        "port_range_min": port_min,
                        "port_range_max": port_max,
                    }
                )
        missing = list_missing_rules()
        if missing:
            raise RuntimeError(
                "Failed to ensure destination SG rules for target=%s, missing=%s"
                % (target_server_id, json.dumps(missing, ensure_ascii=False))
            )

    return {
        "target_security_group_ids": sg_ids,
        "target_vpc_default_security_group_id": fallback_default_sg,
        "target_security_group_rules_created": created,
        "target_peer_ips": peer_ips,
        "target_migration_security_group_id": migration_sg_id,
    }


def make_cfg_for_task(
    source_vm_id: str,
    source_region: str,
    target_region: str,
    target_region_name: str,
    target_server_name: str,
    sms_endpoint: str,
    eip_bandwidth_mbps: int,
    result_path: str,
) -> Config:
    return Config(
        ak="",
        sk="",
        source_server_id=source_vm_id,
        source_region=source_region,
        target_region=target_region,
        target_region_name=target_region_name,
        target_vpc_name="",
        target_vpc_cidr="",
        target_subnet_cidr="",
        target_image_id="existing-target",
        target_server_name=target_server_name,
        target_flavor_id="",
        target_admin_password="",
        eip_bandwidth_mbps=eip_bandwidth_mbps,
        root_volume_type="SSD",
        data_volume_type="SSD",
        sms_endpoint=sms_endpoint,
        preferred_migration_method="sms",
        enable_rsync_fallback=False,
        source_private_ip="",
        source_network_cidr="",
        extra_peer_ips=[],
        rsync_source_host="",
        rsync_source_port=22,
        rsync_source_user="root",
        rsync_source_password="",
        rsync_target_host="",
        rsync_target_port=22,
        rsync_target_user="root",
        rsync_target_password="",
        rsync_source_paths=["/"],
        rsync_staging_dir="/tmp",
        rsync_incremental_rounds=1,
        rsync_timeout_sec=1200,
        rsync_common_args="",
        rsync_excludes=[],
        rsync_cutover_stop_cmd="",
        rsync_cutover_start_cmd="",
        rsync_target_finalize_cmd="",
        enable_vpn_bridge=False,
        enable_target_vpn_client=False,
        vpn_server_public_ip="",
        vpn_server_port=1194,
        vpn_client_common_name="",
        vpn_client_static_ip="",
        result_path=result_path,
    )


def resolve_region_name_from_tasks(client: HcApiClient, sms_endpoint: str, region_id: str) -> str:
    try:
        for t in list_sms_tasks(client, sms_endpoint):
            if str(t.get("region_id") or "").strip() == region_id:
                val = str(t.get("region_name") or "").strip()
                if val:
                    return val
    except Exception:
        pass

    default_map = {
        "ap-southeast-3": "AP-Singapore",
        "ap-southeast-4": "AP-Bangkok",
    }
    return default_map.get(region_id, region_id)


def main() -> int:
    source_ak = env_required("SOURCE_ACCESS_KEY")
    source_sk = env_required("SOURCE_SECRET_KEY")
    source_region_hint = env_default("SOURCE_REGION", "")
    source_project_id_hint = env_default("SOURCE_PROJECT_ID", "")

    dest_ak = env_required("DESTINATION_ACCESS_KEY")
    dest_sk = env_required("DESTINATION_SECRET_KEY")
    dest_region_hint = env_default("DESTINATION_REGION", "")
    dest_project_id_hint = env_default("DESTINATION_PROJECT_ID", "")
    dest_region_name_input = env_default("DESTINATION_REGION_NAME", "")

    source_server_ids = env_csv("SOURCE_SERVER_IDS")
    if not source_server_ids:
        raise RuntimeError("SOURCE_SERVER_IDS is empty")

    sms_endpoint = env_default("SMS_ENDPOINT", "https://sms.ap-southeast-3.myhuaweicloud.com").rstrip("/")
    eip_bandwidth_mbps = env_default_int("EIP_BANDWIDTH_MBPS", 100)
    sg_rule_description = env_default("SG_RULE_DESCRIPTION", "虚拟机迁移")
    target_image_id = env_default("TARGET_IMAGE_ID", "").strip()
    target_flavor_id = env_default("TARGET_FLAVOR_ID", "").strip()
    target_admin_password = env_required("TARGET_ADMIN_PASSWORD").strip()
    root_volume_type = env_default("ROOT_VOLUME_TYPE", "SSD").strip() or "SSD"
    data_volume_type = env_default("DATA_VOLUME_TYPE", "SSD").strip() or "SSD"
    result_path = env_default("RESULT_PATH", "./out/migration_result.json")

    source_client = HcApiClient(source_ak, source_sk)
    dest_client = HcApiClient(dest_ak, dest_sk)

    print_step("Accepting SMS privacy agreements on destination account")
    dest_client.request_json("POST", "%s/v3/privacy-agreements" % sms_endpoint, body={})

    target_ctx = resolve_destination_context(
        dest_client=dest_client,
        preferred_region=dest_region_hint,
        preferred_project_id=dest_project_id_hint,
    )
    target_region = str(target_ctx.get("target_region") or "").strip()
    target_project_id = str(target_ctx.get("target_project_id") or "").strip()
    target_project_name = str(target_ctx.get("target_project_name") or target_region).strip() or target_region
    if not target_region or not target_project_id:
        raise RuntimeError("Unable to resolve destination region/project")

    target_region_name = dest_region_name_input or resolve_region_name_from_tasks(dest_client, sms_endpoint, target_region)
    print_step("Using target region=%s project=%s region_name=%s" % (target_region, target_project_id, target_region_name))

    prepared_items: List[dict] = []
    used_target_vm_ids: Dict[str, str] = {}

    for source_vm_id in source_server_ids:
        print_step("Resolving source ECS for %s" % source_vm_id)
        source_item = find_source_server(
            source_client=source_client,
            source_vm_id=source_vm_id,
            preferred_region=source_region_hint,
            preferred_project_id=source_project_id_hint,
        )
        source_fixed_ip = str(source_item.get("source_fixed_ip") or "").strip()
        if not source_fixed_ip:
            raise RuntimeError("Source VM %s has no fixed IP" % source_vm_id)

        print_step("Resolving SMS source object for %s" % source_vm_id)
        try:
            sms_source = get_sms_source_server(
                client=dest_client,
                sms_endpoint=sms_endpoint,
                source_server_id=source_vm_id,
                fallback_name=str(source_item.get("source_name") or ""),
                fallback_ip=source_fixed_ip,
            )
        except Exception as exc:
            err = str(exc)
            if "Source server not found in SMS" in err:
                count = 0
                try:
                    count_rsp = dest_client.request_json(
                        "GET",
                        "%s/v3/sources" % sms_endpoint,
                        params={"limit": "1", "offset": "0"},
                    )
                    count = int(count_rsp.get("count") or 0)
                except Exception:
                    count = 0
                raise RuntimeError(
                    "Source VM %s (name=%s, fixed_ip=%s) is not registered in destination-account SMS. "
                    "Current destination account source count=%d, endpoint=%s. "
                    "Please restart SMS-Agent on source and enter DESTINATION account AK/SK plus the same SMS domain, "
                    "then retry terraform apply."
                    % (
                        source_vm_id,
                        str(source_item.get("source_name") or ""),
                        source_fixed_ip,
                        count,
                        sms_endpoint,
                    )
                )
            raise
        source_sms_id = str(sms_source.get("id") or "").strip()
        if not source_sms_id:
            raise RuntimeError("SMS source id is empty for source vm %s" % source_vm_id)
        sms_source_detail = get_sms_source_detail(dest_client, sms_endpoint, source_sms_id)

        cleanup_result = cleanup_terminal_tasks_for_source(dest_client, sms_endpoint, source_sms_id)
        active_tasks = cleanup_result.get("active_tasks") or []
        if active_tasks:
            raise RuntimeError(
                "Source %s still has active SMS tasks: %s"
                % (source_vm_id, json.dumps(active_tasks, ensure_ascii=False))
            )

        target_item = find_target_server_by_fixed_ip_in_project(
            dest_client=dest_client,
            target_fixed_ip=source_fixed_ip,
            target_region=target_region,
            target_project_id=target_project_id,
        )
        target_created = False
        if not target_item:
            print_step(
                "Destination ECS not found by fixed_ip=%s, creating target ECS with same private IP"
                % source_fixed_ip
            )
            target_item = create_target_server_with_fixed_ip(
                dest_client=dest_client,
                source_client=source_client,
                source_item=source_item,
                source_sms_detail=sms_source_detail,
                target_region=target_region,
                target_project_id=target_project_id,
                target_image_id=target_image_id,
                target_flavor_id=target_flavor_id,
                target_admin_password=target_admin_password,
                root_volume_type=root_volume_type,
                data_volume_type=data_volume_type,
            )
            target_created = True

        target_vm_id = str(target_item.get("target_vm_id") or "").strip()
        if not target_vm_id:
            raise RuntimeError("Mapped target VM id is empty for source %s" % source_vm_id)
        if target_vm_id in used_target_vm_ids:
            raise RuntimeError(
                "Target VM %s is mapped by multiple sources: %s and %s"
                % (target_vm_id, used_target_vm_ids[target_vm_id], source_vm_id)
            )
        used_target_vm_ids[target_vm_id] = source_vm_id

        prepared_items.append(
            {
                **source_item,
                **target_item,
                "source_sms_server_id": source_sms_id,
                "source_sms_detail": sms_source_detail,
                "precheck_task_cleanup": cleanup_result,
                "target_created": target_created,
            }
        )

    migproject_id = ""
    migproject_error = ""
    try:
        seed = prepared_items[0]
        seed_cfg = make_cfg_for_task(
            source_vm_id=str(seed.get("source_vm_id") or "seed"),
            source_region=str(seed.get("source_region") or ""),
            target_region=target_region,
            target_region_name=target_region_name,
            target_server_name=str(seed.get("target_name") or "target"),
            sms_endpoint=sms_endpoint,
            eip_bandwidth_mbps=eip_bandwidth_mbps,
            result_path=result_path,
        )
        print_step("Creating SMS migration project")
        migproject_id = create_sms_migproject(dest_client, seed_cfg)
    except Exception as exc:
        migproject_error = str(exc)
        print_step("Create migration project failed, continue with existing projects: %s" % migproject_error)

    results: List[dict] = []

    for item in prepared_items:
        source_vm_id = str(item.get("source_vm_id") or "")
        source_name = str(item.get("source_name") or "")
        source_fixed_ip = str(item.get("source_fixed_ip") or "")
        source_floating_ip = str(item.get("source_floating_ip") or "")
        source_region = str(item.get("source_region") or "")
        source_sms_id = str(item.get("source_sms_server_id") or "")
        source_sms_detail = item.get("source_sms_detail") or {}
        cleanup_result = item.get("precheck_task_cleanup") or {}

        target_vm_id = str(item.get("target_vm_id") or "")
        target_name = str(item.get("target_name") or "")
        target_vpc_id = str(item.get("target_vpc_id") or "")

        print_step("Ensuring EIP on target VM %s (%s)" % (target_vm_id, target_name))
        target_floating_ip = ensure_target_eip(
            client=dest_client,
            region=target_region,
            project_id=target_project_id,
            server_id=target_vm_id,
            fixed_ip=str(item.get("target_fixed_ip") or ""),
            bandwidth_mbps=eip_bandwidth_mbps,
        )

        print_step("Ensuring destination security group rules for target VM %s" % target_vm_id)
        sg_result = ensure_target_security_group_rules(
            client=dest_client,
            region=target_region,
            project_id=target_project_id,
            target_server_id=target_vm_id,
            target_vpc_id=target_vpc_id,
            source_fixed_ip=source_fixed_ip,
            source_floating_ip=source_floating_ip,
            description=sg_rule_description,
            source_os_type=str(source_sms_detail.get("os_type") or "LINUX"),
        )

        task_cfg = make_cfg_for_task(
            source_vm_id=source_vm_id,
            source_region=source_region,
            target_region=target_region,
            target_region_name=target_region_name,
            target_server_name=target_name,
            sms_endpoint=sms_endpoint,
            eip_bandwidth_mbps=eip_bandwidth_mbps,
            result_path=result_path,
        )

        print_step("Creating SMS task for source %s -> target %s" % (source_vm_id, target_vm_id))
        task_id = create_sms_task(
            client=dest_client,
            cfg=task_cfg,
            source_sms_id=source_sms_id,
            source_server=sms_source_detail,
            target_vm_id=target_vm_id,
            target_project_id=target_project_id,
            target_project_name=target_project_name,
        )

        print_step("Starting SMS task %s" % task_id)
        start_sms_task(dest_client, sms_endpoint, task_id)
        task_state = get_sms_task_state(dest_client, sms_endpoint, task_id)

        results.append(
            {
                "source_vm_id": source_vm_id,
                "source_name": source_name,
                "source_region": source_region,
                "source_project_id": str(item.get("source_project_id") or ""),
                "source_fixed_ip": source_fixed_ip,
                "source_floating_ip": source_floating_ip,
                "source_sms_server_id": source_sms_id,
                "target_created": bool(item.get("target_created")),
                "target_vm_id": target_vm_id,
                "target_name": target_name,
                "target_region": target_region,
                "target_project_id": target_project_id,
                "target_fixed_ip": str(item.get("target_fixed_ip") or ""),
                "target_floating_ip": target_floating_ip,
                "target_security_group_ids": sg_result.get("target_security_group_ids", []),
                "target_security_group_rules_created": sg_result.get("target_security_group_rules_created", 0),
                "target_peer_ips": sg_result.get("target_peer_ips", []),
                "precheck_task_cleanup": cleanup_result,
                "task_id": task_id,
                "task_state": task_state,
            }
        )

    output = {
        "mode": "sms_existing_target_batch",
        "requested_source_server_ids": source_server_ids,
        "source_project_id_input": source_project_id_hint,
        "source_region_input": source_region_hint,
        "destination_project_id_input": dest_project_id_hint,
        "destination_region_input": dest_region_hint,
        "resolved_target_project_id": target_project_id,
        "resolved_target_region": target_region,
        "resolved_target_region_name": target_region_name,
        "migration_project_id": migproject_id,
        "migration_project_create_error": migproject_error,
        "security_group_rule_description": sg_rule_description,
        "target_image_id": target_image_id,
        "target_flavor_id": target_flavor_id,
        "eip_bandwidth_mbps": eip_bandwidth_mbps,
        "results": results,
        "generated_at": int(time.time()),
    }

    write_json_file(result_path, output)
    print_step("Completed batch migration start. Result written to %s" % result_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[MGC-BATCH][ERROR] %s" % str(exc), file=sys.stderr)
        sys.exit(1)
