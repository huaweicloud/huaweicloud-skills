#!/usr/bin/env python3
"""
Direct AWS to Huawei Cloud migration using rsync.
Uses the correct Huawei Cloud API signature implementation.
"""

import base64
import hashlib
import hmac
import json
import os
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


def get_or_create_vpc(client: HcApiClient, region: str, project_id: str, vpc_name: str, vpc_cidr: str) -> str:
    """Get existing VPC or create new one"""
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs",
        params={"name": vpc_name},
    )
    vpcs = rsp.get("vpcs", [])
    if vpcs:
        print_step(f"Using existing VPC: {vpcs[0]['id']}")
        return vpcs[0]["id"]
    
    print_step(f"Creating VPC {vpc_name} with CIDR {vpc_cidr}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs",
        body={
            "vpc": {
                "name": vpc_name,
                "cidr": vpc_cidr,
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


def get_or_create_subnet(client: HcApiClient, region: str, project_id: str, vpc_id: str, subnet_cidr: str) -> str:
    """Get existing subnet or create new one"""
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/subnets",
        params={"vpc_id": vpc_id},
    )
    subnets = rsp.get("subnets", [])
    if subnets:
        print_step(f"Using existing subnet: {subnets[0]['id']}")
        return subnets[0]["id"]
    
    print_step(f"Creating subnet with CIDR {subnet_cidr}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/subnets",
        body={
            "subnet": {
                "name": "subnet-migration",
                "cidr": subnet_cidr,
                "vpc_id": vpc_id,
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
    """Get or create security group"""
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups",
        params={"name": sg_name, "vpc_id": vpc_id},
    )
    sgs = rsp.get("security_groups", [])
    if sgs:
        print_step(f"Using existing security group: {sgs[0]['id']}")
        return sgs[0]["id"]
    
    print_step(f"Creating security group {sg_name}")
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups",
        body={
            "security_group": {
                "name": sg_name,
                "vpc_id": vpc_id,
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
    
    user_data = f"""#cloud-config
password: {admin_pass}
chpasswd:
  expire: false
ssh_pwauth: true
disable_root: false
"""
    user_data_b64 = base64.b64encode(user_data.encode("utf-8")).decode("ascii")
    
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
                    "user_data": user_data_b64,
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
                        target_host: str, target_port: int, target_user: str, target_password: str,
                        incremental_rounds: int = 0, timeout_sec: int = 7200) -> Dict[str, object]:
    """Execute rsync migration phases"""
    
    result = {
        "phases": [],
        "success": False,
        "error": None,
    }
    
    phases = ["full_sync"]
    for i in range(incremental_rounds):
        phases.append(f"incremental_sync_{i+1}")
    phases.append("cutover_sync")
    
    for phase in phases:
        print_step(f"Executing rsync phase: {phase}")
        
        if phase == "cutover_sync":
            print_step("Stopping services on source for cutover")
            stop_cmd = [
                "sshpass", "-p", source_password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-p", str(source_port),
                f"{source_user}@{source_host}",
                "systemctl stop sshd || true; sync"
            ]
            try:
                subprocess.run(stop_cmd, timeout=60, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                print_step(f"Warning: failed to stop services: {e}")
        
        rsync_cmd = [
            "sshpass", "-p", source_password,
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
            "-e", f"ssh -o StrictHostKeyChecking=no -p {source_port}",
            f"{source_user}@{source_host}:/",
            f"{target_user}@{target_host}:/"
        ]
        
        try:
            proc = subprocess.run(
                rsync_cmd,
                timeout=timeout_sec,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
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
    
    # Finalize target
    print_step("Finalizing target system")
    finalize_cmd = [
        "sshpass", "-p", target_password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-p", str(target_port),
        f"{target_user}@{target_host}",
        "grub-install /dev/vda || true; update-grub || true; sync; reboot"
    ]
    try:
        subprocess.run(finalize_cmd, timeout=120, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    rsync_incremental_rounds = env_default_int("RSYNC_INCREMENTAL_ROUNDS", 0)
    rsync_timeout_sec = env_default_int("RSYNC_TIMEOUT_SEC", 7200)
    
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
    for i in range(60):
        try:
            test_cmd = [
                "sshpass", "-p", target_admin_password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                f"root@{target_eip}",
                "echo 'SSH ready'"
            ]
            subprocess.run(test_cmd, timeout=10, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print_step("Target SSH is ready")
            break
        except:
            time.sleep(5)
    
    print_step("Starting rsync migration")
    rsync_result = run_rsync_migration(
        rsync_source_host, rsync_source_port, rsync_source_user, rsync_source_password,
        target_eip, 22, "root", target_admin_password,
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
