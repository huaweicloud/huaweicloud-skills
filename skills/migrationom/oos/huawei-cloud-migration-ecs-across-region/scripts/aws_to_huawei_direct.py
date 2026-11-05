#!/usr/bin/env python3
"""
Direct AWS to Huawei Cloud migration using rsync.
Uses the correct Huawei Cloud API signature implementation.
"""

import hashlib
import hmac
import ipaddress
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def env_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def env_default_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


def rfc3986_encode(value: str) -> str:
    return urllib.parse.quote(str(value), safe="-_.~")


def canonical_uri(path: str) -> str:
    if not path:
        return "/"
    normalized = path if path.endswith("/") else path + "/"
    return urllib.parse.quote(normalized, safe="/-_.~")


def canonical_query_string(query_items: List[Tuple[str, str]]) -> str:
    encoded = [(rfc3986_encode(k), rfc3986_encode(v)) for k, v in query_items]
    encoded.sort(key=lambda x: (x[0], x[1]))
    return "&".join([f"{k}={v}" for k, v in encoded])


def hash_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(secret: str, data: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()


class HcApiClient:
    def __init__(self, ak: str, sk: str):
        self.ak = ak
        self.sk = sk

    def _signed_headers(self, method: str, url: str, body_bytes: bytes, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc

        headers = {
            "host": host,
            "x-sdk-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        }
        if extra_headers:
            for k, v in extra_headers.items():
                headers[k.lower()] = v.strip()

        if method.upper() in {"POST", "PUT", "PATCH"} and "content-type" not in headers:
            headers["content-type"] = "application/json;charset=utf-8"

        query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        canonical_qs = canonical_query_string(query_items)

        signed_header_keys = sorted(headers.keys())
        canonical_headers = "".join([f"{k}:{headers[k]}\n" for k in signed_header_keys])
        signed_headers = ";".join(signed_header_keys)

        payload_hash = hash_hex(body_bytes)
        canonical_req = "\n".join([
            method.upper(),
            canonical_uri(parsed.path),
            canonical_qs,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        string_to_sign = "\n".join([
            "SDK-HMAC-SHA256",
            headers["x-sdk-date"],
            hash_hex(canonical_req.encode("utf-8")),
        ])

        signature = hmac_sha256_hex(self.sk, string_to_sign)
        authorization = f"SDK-HMAC-SHA256 Access={self.ak}, SignedHeaders={signed_headers}, Signature={signature}"

        out = {
            "X-Sdk-Date": headers["x-sdk-date"],
            "Authorization": authorization,
        }
        if "content-type" in headers:
            out["Content-Type"] = headers["content-type"]
        return out

    def request_json(self, method: str, url: str, body: Optional[dict] = None, params: Optional[Dict[str, str]] = None) -> dict:
        query_items: List[Tuple[str, str]] = []
        
        parsed = urllib.parse.urlparse(url)
        if parsed.query:
            query_items.extend(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        if params:
            for k, v in params.items():
                query_items.append((k, str(v)))
        
        canonical_qs = canonical_query_string(query_items)
        request_url = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            canonical_qs,
            parsed.fragment,
        ))
        
        body_bytes = b""
        if body is not None:
            body_bytes = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        
        signed_headers = self._signed_headers(method, request_url, body_bytes, {})
        
        req = urllib.request.Request(request_url, method=method.upper())
        for k, v in signed_headers.items():
            req.add_header(k, v)
        
        if body is not None:
            req.data = body_bytes
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} {method.upper()} {request_url}: {detail}")


def print_step(msg: str) -> None:
    print(f"[AWS-TO-HUAWEI] {msg}", flush=True)


def write_json_file(path: str, data: object) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


TARGET_SSH_KEY_GUIDANCE = (
    "rsync fallback requires an operator-provisioned SSH private key. "
    "Set TARGET_RSYNC_SSH_KEY to the private key path on the source host; its "
    "public half must already be trusted by the target, or operations must "
    "pre-establish source->target passwordless SSH. Alternatively use the "
    "MGC/SMS console migration path. The rsync fallback never writes "
    "authorized_keys, modifies sshd_config, or restarts sshd."
)


def ssh_base_args(port: int) -> List[str]:
    return [
        "ssh",
        "-p",
        str(port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ServerAliveInterval=20",
        "-o",
        "ServerAliveCountMax=6",
    ]


def build_ssh_target(user: str, host: str) -> str:
    return f"{user}@{host}"


def run_source_remote_command(source_host: str, source_port: int, source_user: str,
                              source_password: str, remote_cmd: str,
                              timeout_sec: int) -> subprocess.CompletedProcess:
    cmd = ["sshpass", "-p", source_password] + ssh_base_args(source_port) + [
        build_ssh_target(source_user, source_host),
        remote_cmd,
    ]
    return subprocess.run(
        cmd,
        timeout=timeout_sec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def wait_for_target_ssh_via_source(source_host: str, source_port: int, source_user: str,
                                   source_password: str, target_host: str, target_port: int,
                                   target_user: str, target_rsync_ssh_key: str,
                                   timeout_sec: int = 300, interval_sec: int = 5) -> None:
    key_path = str(target_rsync_ssh_key or "").strip()
    if not key_path:
        raise RuntimeError(TARGET_SSH_KEY_GUIDANCE)
    probe_remote = " ".join(
        shlex.quote(x)
        for x in ssh_base_args(target_port) + [
            "-i", key_path,
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            build_ssh_target(target_user, target_host),
            "echo 'SSH ready'",
        ]
    )
    started = time.time()
    last_error = ""
    while True:
        try:
            proc = run_source_remote_command(
                source_host, source_port, source_user, source_password,
                probe_remote, max(20, interval_sec + 10),
            )
            if proc.returncode == 0:
                print_step("Target SSH is ready")
                return
            last_error = proc.stderr or proc.stdout
        except Exception as e:
            last_error = str(e)
        if time.time() - started > timeout_sec:
            raise RuntimeError(
                f"Target SSH not reachable via source after {timeout_sec}s "
                f"(target={target_host}:{target_port}). Ensure the target's public key is "
                f"trusted and TARGET_RSYNC_SSH_KEY points at the private key on the source "
                f"host, or use the MGC/SMS console migration path.\n{str(last_error)[-2000:]}"
            )
        time.sleep(max(2, interval_sec))


def ensure_source_rsync_ready(source_host: str, source_port: int, source_user: str,
                              source_password: str, timeout_sec: int = 30) -> None:
    """Fail early when the source host cannot run rsync for the sync phases."""
    probe = "command -v rsync >/dev/null 2>&1 && rsync --version | head -n 1"
    try:
        proc = run_source_remote_command(
            source_host, source_port, source_user, source_password, probe, timeout_sec,
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to check rsync on source host {source_host}: {e}. "
            "Install rsync on the source host and retry, or use the MGC/SMS console "
            "migration path instead."
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"rsync is required on the source host {source_host} for the AWS migration path, "
            "but `command -v rsync` failed there. Install it on the source host "
            "(for example `yum -y install rsync` or `apt-get install -y rsync`) and retry, "
            "or use the MGC/SMS console migration path instead."
        )
    print_step(f"Source host rsync available: {proc.stdout.strip()}")


def get_region_project(client: HcApiClient, region_code: str) -> Tuple[str, str]:
    rsp = client.request_json(
        "GET",
        "https://iam.myhuaweicloud.com/v3/projects",
        params={"name": region_code},
    )
    projects = rsp.get("projects", [])
    if not projects:
        raise RuntimeError(f"No IAM project found for region: {region_code}")
    
    for p in projects:
        if p.get("name") == region_code:
            return p["id"], p["name"]
    
    first = projects[0]
    return first["id"], first.get("name", region_code)


def describe_candidates(items: List[dict]) -> str:
    return ", ".join(
        f"{item.get('id')}(name={item.get('name')},cidr={item.get('cidr', '-')})"
        for item in items
    ) or "none"


def get_or_create_vpc(client: HcApiClient, region: str, project_id: str, vpc_name: str, vpc_cidr: str) -> str:
    """Reuse an exactly matching VPC or create one.

    The VPC list API may ignore the name filter, so matching is done client-side
    on name and CIDR; the first returned item is never used blindly.
    """
    desired_name = str(vpc_name or "").strip()
    desired_cidr = str(vpc_cidr or "").strip()
    if not desired_name or not desired_cidr:
        raise RuntimeError("VPC name and CIDR must both be provided")

    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs",
        params={"name": desired_name},
    )
    vpcs = rsp.get("vpcs", []) or []
    matches = [v for v in vpcs if str(v.get("name", "")).strip() == desired_name]

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple VPCs named '{desired_name}' found; refusing to guess. "
            f"Candidates: {describe_candidates(matches)}"
        )
    if len(matches) == 1:
        vpc = matches[0]
        actual_cidr = str(vpc.get("cidr", "")).strip()
        if actual_cidr != desired_cidr:
            raise RuntimeError(
                f"VPC '{desired_name}' already exists with CIDR {actual_cidr} "
                f"(id={vpc.get('id')}), expected {desired_cidr}; refusing to reuse it."
            )
        print_step(f"Using existing VPC: {vpc['id']} ({desired_name}, {actual_cidr})")
        return vpc["id"]

    print_step(f"Creating VPC {desired_name} with CIDR {desired_cidr}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs",
        body={
            "vpc": {
                "name": desired_name,
                "cidr": desired_cidr,
            }
        },
    )
    vpc_id = rsp["vpc"]["id"]
    
    for _ in range(30):
        rsp = client.request_json(
            "GET",
            f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs/{vpc_id}",
        )
        if rsp["vpc"]["status"] == "OK":
            break
        time.sleep(2)
    
    return vpc_id


def first_usable_gateway_ip(subnet_cidr: str) -> str:
    """Return the first usable host address of the subnet, as Huawei Cloud requires."""
    try:
        network = ipaddress.IPv4Network(str(subnet_cidr).strip(), strict=False)
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as exc:
        raise RuntimeError(f"Invalid subnet CIDR for gateway_ip: {subnet_cidr}") from exc
    first = next(network.hosts(), None)
    if first is None:
        raise RuntimeError(f"No usable gateway IP in subnet {network}")
    return str(first)


def get_or_create_subnet(client: HcApiClient, region: str, project_id: str, vpc_id: str, subnet_cidr: str) -> str:
    """Reuse an exactly matching subnet or create one.

    Matching is client-side on VPC, name and CIDR because the list API filter may
    be ignored; the first returned item is never used blindly.
    """
    subnet_name = "subnet-migration"
    desired_cidr = str(subnet_cidr or "").strip()
    desired_vpc = str(vpc_id or "").strip()
    if not desired_vpc or not desired_cidr:
        raise RuntimeError("Subnet VPC ID and CIDR must both be provided")

    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/subnets",
        params={"vpc_id": desired_vpc},
    )
    subnets = rsp.get("subnets", []) or []
    matches = [
        s for s in subnets
        if str(s.get("name", "")).strip() == subnet_name
        and str(s.get("vpc_id", "")).strip() == desired_vpc
    ]

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple subnets named '{subnet_name}' found in VPC {desired_vpc}; "
            f"refusing to guess. Candidates: {describe_candidates(matches)}"
        )
    if len(matches) == 1:
        subnet = matches[0]
        actual_cidr = str(subnet.get("cidr", "")).strip()
        if actual_cidr != desired_cidr:
            raise RuntimeError(
                f"Subnet '{subnet_name}' already exists in VPC {desired_vpc} with CIDR "
                f"{actual_cidr} (id={subnet.get('id')}), expected {desired_cidr}; "
                f"refusing to reuse it."
            )
        print_step(f"Using existing subnet: {subnet['id']} ({subnet_name}, {actual_cidr})")
        return subnet["id"]

    print_step(f"Creating subnet {subnet_name} with CIDR {desired_cidr}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/subnets",
        body={
            "subnet": {
                "name": subnet_name,
                "cidr": desired_cidr,
                "gateway_ip": first_usable_gateway_ip(desired_cidr),
                "vpc_id": desired_vpc,
            }
        },
    )
    subnet_id = rsp["subnet"]["id"]
    
    for _ in range(30):
        rsp = client.request_json(
            "GET",
            f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/subnets/{subnet_id}",
        )
        if rsp["subnet"]["status"] == "ACTIVE":
            break
        time.sleep(2)
    
    return subnet_id


def get_or_create_security_group(client: HcApiClient, region: str, project_id: str, vpc_id: str, sg_name: str) -> str:
    """Reuse an exactly matching security group or create one."""
    desired_name = str(sg_name or "").strip()
    desired_vpc = str(vpc_id or "").strip()
    if not desired_name or not desired_vpc:
        raise RuntimeError("Security group name and VPC ID must both be provided")

    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups",
        params={"name": desired_name, "vpc_id": desired_vpc},
    )
    sgs = rsp.get("security_groups", []) or []
    matches = [
        g for g in sgs
        if str(g.get("name", "")).strip() == desired_name
        and str(g.get("vpc_id", "")).strip() == desired_vpc
    ]

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple security groups named '{desired_name}' found in VPC {desired_vpc}; "
            f"refusing to guess. Candidates: {describe_candidates(matches)}"
        )
    if len(matches) == 1:
        print_step(f"Using existing security group: {matches[0]['id']} ({desired_name})")
        return matches[0]["id"]

    print_step(f"Creating security group {desired_name}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups",
        body={
            "security_group": {
                "name": desired_name,
                "vpc_id": desired_vpc,
            }
        },
    )
    return rsp["security_group"]["id"]


def add_security_group_rule(client: HcApiClient, region: str, project_id: str, sg_id: str, 
                            direction: str, port_range_min: int, port_range_max: int, 
                            remote_ip_prefix: str, protocol: str = "tcp") -> None:
    """Add security group rule"""
    try:
        client.request_json(
            "POST",
            f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-group-rules",
            body={
                "security_group_rule": {
                    "direction": direction,
                    "port_range_min": port_range_min,
                    "port_range_max": port_range_max,
                    "remote_ip_prefix": remote_ip_prefix,
                    "protocol": protocol,
                    "security_group_id": sg_id,
                }
            },
        )
        print_step(f"Added {direction} rule: {protocol} {port_range_min}-{port_range_max} from {remote_ip_prefix}")
    except Exception as e:
        if "already exists" not in str(e).lower():
            print_step(f"Warning: failed to add rule: {e}")


def create_target_ecs(client: HcApiClient, region: str, project_id: str, 
                      image_id: str, flavor_id: str, name: str, 
                      vpc_id: str, subnet_id: str, sg_id: str,
                      admin_pass: str, root_volume_type: str = "SSD",
                      eip_bandwidth: int = 100) -> Tuple[str, str, str]:
    """Create target ECS with EIP"""
    
    print_step(f"Creating target ECS {name}")
    try:
        rsp = client.request_json(
            "POST",
            f"https://ecs.{region}.myhuaweicloud.com/v1.1/{project_id}/cloudservers",
            body={
                "server": {
                    "name": name,
                    "imageRef": image_id,
                    "flavorRef": flavor_id,
                    "availability_zone": f"{region}a",
                    "vpcid": vpc_id,
                    "nics": [{"subnet_id": subnet_id}],
                    "security_groups": [{"id": sg_id}],
                    "root_volume": {"volumetype": root_volume_type, "size": 40},
                    "adminPass": admin_pass,
                    "publicip": {
                        "eip": {
                            "iptype": "5_bgp",
                            "bandwidth": {
                                "size": eip_bandwidth,
                                "sharetype": "PER",
                            }
                        }
                    },
                    "extendparam": {"chargingMode": "postPaid"},
                }
            },
        )
    except Exception as e:
        print_step(f"ECS creation failed: {e}")
        raise
    
    if "server" in rsp:
        server_id = rsp["server"]["id"]
    elif "serverIds" in rsp and rsp["serverIds"]:
        server_id = rsp["serverIds"][0]
        print_step(f"ECS creation job: {rsp.get('job_id')}")
        # Wait for ECS to be fully registered
        time.sleep(15)
    else:
        print_step(f"Unexpected response: {json.dumps(rsp, indent=2)}")
        raise RuntimeError("ECS creation response missing server ID")
    print_step(f"Waiting for ECS {server_id} to become active")
    
    for i in range(120):
        try:
            rsp = client.request_json(
                "GET",
                f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
            )
            status = rsp["server"]["status"]
            if status == "ACTIVE":
                break
            if status == "ERROR":
                raise RuntimeError(f"ECS creation failed with status: {status}")
        except Exception as e:
            if i < 10:  # Give it some time to register
                print_step(f"ECS not yet available, waiting... ({i+1}/10)")
                time.sleep(5)
                continue
            raise
        time.sleep(5)
    
    # Get fixed IP and EIP
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
    )
    addresses = rsp["server"].get("addresses", {})
    fixed_ip = ""
    floating_ip = ""
    
    print_step(f"Debug: addresses = {json.dumps(addresses, indent=2)}")
    
    # Try to get from addresses first
    for network_name, ips in addresses.items():
        for ip_info in ips:
            ip_type = ip_info.get("OS-EXT-IPS:type")
            print_step(f"Debug: IP {ip_info.get('addr')} type={ip_type}")
            if ip_type == "fixed":
                fixed_ip = ip_info["addr"]
            elif ip_type == "floating":
                floating_ip = ip_info["addr"]
    
    # If not found, try network_interfaces
    if not floating_ip:
        network_interfaces = rsp["server"].get("network_interfaces", [])
        print_step(f"Debug: network_interfaces = {json.dumps(network_interfaces, indent=2)}")
        for nic in network_interfaces:
            association = nic.get("association", {})
            if association and "public_ip_address" in association:
                floating_ip = association["public_ip_address"]
                break
    
    print_step(f"Debug: fixed_ip={fixed_ip}, floating_ip={floating_ip}")
    
    return server_id, fixed_ip, floating_ip


def run_rsync_migration(source_host: str, source_port: int, source_user: str, source_password: str,
                        target_host: str, target_port: int, target_user: str, target_rsync_ssh_key: str,
                        incremental_rounds: int = 0, timeout_sec: int = 7200) -> Dict[str, object]:
    """Execute rsync migration phases.

    rsync is invoked on the source host and pushes to the target, so each
    transfer has exactly one remote side (rsync cannot run remote-to-remote).
    """
    key_path = str(target_rsync_ssh_key or "").strip()
    if not key_path:
        raise RuntimeError(TARGET_SSH_KEY_GUIDANCE)
    ensure_source_rsync_ready(source_host, source_port, source_user, source_password)

    result = {
        "phases": [],
        "success": False,
        "error": None,
        "auth_mode": "ssh_key",
    }

    target_ssh_command = " ".join(
        shlex.quote(x)
        for x in ssh_base_args(target_port) + ["-i", key_path, "-o", "BatchMode=yes"]
    )
    rsync_base_cmd = [
        "rsync", "-avz",
        "--numeric-ids",
        "--info=stats2,progress2",
        "--partial",
        "--exclude=/dev/*",
        "--exclude=/proc/*",
        "--exclude=/sys/*",
        "--exclude=/tmp/*",
        "--exclude=/run/*",
        "--exclude=/mnt/*",
        "--exclude=/media/*",
        "--exclude=/lost+found",
        "--exclude=/swapfile",
        "--exclude=/var/tmp/*",
        "--exclude=/var/run/*",
        "--exclude=/boot/efi/*",
        "--exclude=/etc/fstab",
    ]
    remote_rsync_cmd = " ".join(
        shlex.quote(x)
        for x in rsync_base_cmd + [
            "-e", target_ssh_command,
            "/",
            f"{build_ssh_target(target_user, target_host)}:/",
        ]
    )

    phases = ["full_sync"]
    for i in range(incremental_rounds):
        phases.append(f"incremental_sync_{i+1}")
    phases.append("cutover_sync")

    for phase in phases:
        print_step(f"Executing rsync phase: {phase}")

        if phase == "cutover_sync":
            print_step("Flushing source filesystem buffers for cutover")
            try:
                stop_cmd = run_source_remote_command(
                    source_host, source_port, source_user, source_password, "sync", 60,
                )
                if stop_cmd.returncode != 0:
                    print_step(f"Warning: source sync returned {stop_cmd.returncode}: {stop_cmd.stderr}")
            except Exception as e:
                print_step(f"Warning: failed to flush source filesystem: {e}")

        try:
            proc = run_source_remote_command(
                source_host, source_port, source_user, source_password,
                remote_rsync_cmd, timeout_sec,
            )

            phase_result = {
                "phase": phase,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
                "stderr": proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr,
            }
            result["phases"].append(phase_result)

            if proc.returncode != 0:
                result["error"] = f"Rsync failed in phase {phase}: {proc.stderr}"
                return result

            print_step(f"Phase {phase} completed successfully")

        except subprocess.TimeoutExpired:
            result["error"] = f"Rsync timed out in phase {phase}"
            return result
        except Exception as e:
            result["error"] = f"Rsync failed in phase {phase}: {str(e)}"
            return result

    print_step("Finalizing target system")
    finalize_remote = " ".join(
        shlex.quote(x)
        for x in ssh_base_args(target_port) + [
            "-i", key_path,
            "-o", "BatchMode=yes",
            build_ssh_target(target_user, target_host),
            "grub-install /dev/vda || true; update-grub || true; sync; reboot",
        ]
    )
    try:
        proc = run_source_remote_command(
            source_host, source_port, source_user, source_password, finalize_remote, 120,
        )
        if proc.returncode != 0:
            print_step(f"Warning: finalize command failed: {proc.stderr}")
    except Exception as e:
        print_step(f"Warning: finalize command failed: {e}")

    result["success"] = True
    return result


def main() -> int:
    ak = env_required("HC_AK")
    sk = env_required("HC_SK")
    
    target_region = env_required("TARGET_REGION")
    target_vpc_name = env_default("TARGET_VPC_NAME", "vpc-migration")
    target_vpc_cidr = env_default("TARGET_VPC_CIDR", "10.250.0.0/16")
    target_subnet_cidr = env_default("TARGET_SUBNET_CIDR", "10.250.1.0/24")
    target_image_id = env_required("TARGET_IMAGE_ID")
    target_server_name = env_default("TARGET_SERVER_NAME", "aws-to-huawei-migrated")
    target_flavor_id = env_default("TARGET_FLAVOR_ID", "s6.large.2")
    target_admin_password = env_required("TARGET_ADMIN_PASSWORD")
    eip_bandwidth_mbps = env_default_int("EIP_BANDWIDTH_MBPS", 100)
    root_volume_type = env_default("ROOT_VOLUME_TYPE", "SSD")
    
    rsync_source_host = env_required("RSYNC_SOURCE_HOST")
    rsync_source_port = env_default_int("RSYNC_SOURCE_PORT", 22)
    rsync_source_user = env_default("RSYNC_SOURCE_USER", "root")
    rsync_source_password = env_required("RSYNC_SOURCE_PASSWORD")
    target_rsync_ssh_key = env_default("TARGET_RSYNC_SSH_KEY", "")
    rsync_incremental_rounds = env_default_int("RSYNC_INCREMENTAL_ROUNDS", 0)
    rsync_timeout_sec = env_default_int("RSYNC_TIMEOUT_SEC", 7200)

    print_step("Checking rsync availability on the AWS source host")
    ensure_source_rsync_ready(
        rsync_source_host, rsync_source_port, rsync_source_user, rsync_source_password,
    )
    
    result_path = env_default("RESULT_PATH", "./out/migration_result.json")
    
    client = HcApiClient(ak, sk)
    
    print_step("Starting AWS to Huawei Cloud migration")
    
    print_step(f"Resolving target project for region: {target_region}")
    target_project_id, target_project_name = get_region_project(client, target_region)
    print_step(f"Target project ID: {target_project_id}")
    
    print_step(f"Setting up VPC: {target_vpc_name}")
    vpc_id = get_or_create_vpc(client, target_region, target_project_id, target_vpc_name, target_vpc_cidr)
    
    print_step("Setting up subnet")
    subnet_id = get_or_create_subnet(client, target_region, target_project_id, vpc_id, target_subnet_cidr)
    
    print_step("Setting up security group")
    sg_id = get_or_create_security_group(client, target_region, target_project_id, vpc_id, "sg-migration")
    
    print_step("Configuring security group rules")
    add_security_group_rule(client, target_region, target_project_id, sg_id, "ingress", 22, 22, "0.0.0.0/0")
    add_security_group_rule(client, target_region, target_project_id, sg_id, "egress", 1, 65535, "0.0.0.0/0", "tcp")
    add_security_group_rule(client, target_region, target_project_id, sg_id, "egress", 1, 65535, "0.0.0.0/0", "udp")
    add_security_group_rule(client, target_region, target_project_id, sg_id, "egress", -1, -1, "0.0.0.0/0", "icmp")
    
    target_server_id, target_fixed_ip, target_eip = create_target_ecs(
        client, target_region, target_project_id,
        target_image_id, target_flavor_id, target_server_name,
        vpc_id, subnet_id, sg_id, target_admin_password, root_volume_type,
        eip_bandwidth_mbps
    )
    
    print_step(f"Target ECS created: {target_server_id}")
    print_step(f"Target Fixed IP: {target_fixed_ip}")
    print_step(f"Target EIP: {target_eip}")
    
    print_step("Waiting for target ECS to be ready for SSH")
    wait_for_target_ssh_via_source(
        rsync_source_host, rsync_source_port, rsync_source_user, rsync_source_password,
        target_eip, 22, "root", target_rsync_ssh_key,
    )
    
    print_step("Starting rsync migration")
    rsync_result = run_rsync_migration(
        rsync_source_host, rsync_source_port, rsync_source_user, rsync_source_password,
        target_eip, 22, "root", target_rsync_ssh_key,
        rsync_incremental_rounds, rsync_timeout_sec
    )
    
    result = {
        "migration_method": "rsync",
        "source_host": rsync_source_host,
        "target_region": target_region,
        "target_project_id": target_project_id,
        "target_server_id": target_server_id,
        "target_server_name": target_server_name,
        "target_fixed_ip": target_fixed_ip,
        "target_eip": target_eip,
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "security_group_id": sg_id,
        "rsync_result": rsync_result,
        "success": rsync_result.get("success", False),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    write_json_file(result_path, result)
    
    if rsync_result.get("success"):
        print_step("Migration completed successfully!")
        print_step(f"Target ECS: {target_server_id}")
        print_step(f"Target EIP: {target_eip}")
        print_step(f"SSH: root@{target_eip}")
        return 0
    else:
        print_step(f"Migration failed: {rsync_result.get('error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
