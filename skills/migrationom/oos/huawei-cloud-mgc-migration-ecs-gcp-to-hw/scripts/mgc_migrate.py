#!/usr/bin/env python3
import base64
import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, NamedTuple, Optional, Set, Tuple
from copy import deepcopy


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


def env_default_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def env_default_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


def env_csv_list(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return list(default)
    out: List[str] = []
    for item in raw.split(","):
        value = item.strip()
        if value:
            out.append(value)
    return out


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


class Config(NamedTuple):
    ak: str
    sk: str
    source_server_id: str
    source_region: str
    target_region: str
    target_region_name: str
    target_vpc_name: str
    target_vpc_cidr: str
    target_subnet_cidr: str
    target_image_id: str
    target_server_name: str
    target_flavor_id: str
    target_admin_password: str
    eip_bandwidth_mbps: int
    root_volume_type: str
    data_volume_type: str
    sms_endpoint: str
    preferred_migration_method: str
    enable_rsync_fallback: bool
    source_private_ip: str
    source_network_cidr: str
    extra_peer_ips: List[str]
    rsync_source_host: str
    rsync_source_port: int
    rsync_source_user: str
    rsync_source_password: str
    rsync_target_host: str
    rsync_target_port: int
    rsync_target_user: str
    rsync_target_password: str
    rsync_source_paths: List[str]
    rsync_staging_dir: str
    rsync_incremental_rounds: int
    rsync_timeout_sec: int
    rsync_common_args: str
    rsync_excludes: List[str]
    rsync_cutover_stop_cmd: str
    rsync_cutover_start_cmd: str
    rsync_target_finalize_cmd: str
    enable_vpn_bridge: bool
    local_vpc_id: str
    enable_target_vpn_client: bool
    vpn_server_public_ip: str
    vpn_server_port: int
    vpn_client_common_name: str
    vpn_client_static_ip: str
    result_path: str


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
        authorization = (
            f"SDK-HMAC-SHA256 Access={self.ak}, SignedHeaders={signed_headers}, Signature={signature}"
        )

        out = {k: v for k, v in headers.items()}
        out["authorization"] = authorization
        return out

    def request_json(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]] = None,
        body: Optional[dict] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> dict:
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

        signed_headers = self._signed_headers(method, request_url, body_bytes, extra_headers)

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
    print(f"[MGC-MIGRATE] {msg}", flush=True)


def sanitize_name(raw: str, max_len: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw or "")
    if not cleaned:
        cleaned = "task"
    if cleaned[0].isdigit():
        cleaned = "t" + cleaned
    return cleaned[:max_len]


def write_json_file(path: str, data: object) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_migration_method(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"", "sms"}:
        return "sms"
    if value == "rsync":
        return "rsync"
    if value == "auto":
        return "sms"
    return "sms"


def unique_nonempty(items: List[str]) -> List[str]:
    out: List[str] = []
    for item in items:
        val = str(item or "").strip()
        if val and val not in out:
            out.append(val)
    return out


def is_ipv4_prefix(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        if "/" in raw:
            network = ipaddress.ip_network(raw, strict=False)
            return bool(network.version == 4)
        ipaddress.IPv4Address(raw)
        return True
    except Exception:
        return False


def build_out_path(result_path: str, filename: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(result_path)) or "."
    return os.path.join(base_dir, filename)


def shlex_split_extra_args(extra_args: str) -> List[str]:
    raw = str(extra_args or "").strip()
    if not raw:
        return []
    return shlex.split(raw)


def run_local_command(cmd: List[str], timeout_sec: int, input_text: str = "") -> Tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if input_text else None,
        universal_newlines=True,
    )
    try:
        stdout, _ = proc.communicate(input=input_text if input_text else None, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        raise RuntimeError(
            "Command timeout after %ds: %s\n%s"
            % (timeout_sec, " ".join(cmd), str(stdout or "").strip()[-1000:])
        )
    return proc.returncode or 0, str(stdout or "")


def run_interactive_command_with_password(
    cmd: List[str],
    passwords: object,
    timeout_sec: int,
) -> Tuple[int, str]:
    try:
        import pexpect
    except Exception as exc:
        raise RuntimeError(
            "Rsync fallback requires python module 'pexpect'. Install it and retry."
        ) from exc

    command_line = " ".join([shlex.quote(part) for part in cmd])
    child = pexpect.spawn(
        "/bin/bash",
        ["-lc", command_line],
        encoding="utf-8",
        timeout=max(30, int(timeout_sec)),
    )
    transcript: List[str] = []
    pass_count = 0
    yesno_count = 0
    start_at = time.time()
    password_list: List[str] = []
    if isinstance(passwords, list):
        for p in passwords:
            val = str(p or "").strip()
            if val:
                password_list.append(val)
    else:
        val = str(passwords or "").strip()
        if val:
            password_list.append(val)
    patterns = [
        r"(?i)are you sure you want to continue connecting",
        r"(?i)(?:password|passphrase).*:",
        pexpect.EOF,
        pexpect.TIMEOUT,
    ]

    while True:
        idx = child.expect(patterns)
        if child.before:
            transcript.append(child.before)

        if idx == 0:
            yesno_count += 1
            if yesno_count > 8:
                child.close(force=True)
                raise RuntimeError(
                    "Too many host key confirmation prompts for command: %s" % command_line
                )
            child.sendline("yes")
            continue

        if idx == 1:
            pass_count += 1
            if not password_list:
                child.close(force=True)
                raise RuntimeError("Password prompt encountered but password is empty.")
            if pass_count > 12:
                child.close(force=True)
                raise RuntimeError("Too many password prompts for command: %s" % command_line)
            pwd_index = min(pass_count - 1, len(password_list) - 1)
            child.sendline(password_list[pwd_index])
            continue

        if idx == 2:
            break

        if idx == 3:
            child.close(force=True)
            elapsed = int(time.time() - start_at)
            raise RuntimeError(
                "Timeout after %ds for command: %s\n%s"
                % (elapsed, command_line, "".join(transcript)[-1200:])
            )

    child.close()
    rc = 1
    if child.exitstatus is not None:
        rc = int(child.exitstatus)
    elif child.signalstatus is not None:
        rc = int(child.signalstatus)
    out = "".join(transcript)
    return rc, out


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def normalize_ipv4_cidr(value: str, default_prefix: int = 24) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        if "/" in raw:
            net = ipaddress.ip_network(raw, strict=False)
        else:
            net = ipaddress.ip_network(f"{raw}/{default_prefix}", strict=False)
        if net.version != 4:
            return ""
        return str(net)
    except Exception:
        return ""


def cidr_to_route_components(cidr: str) -> Tuple[str, str]:
    net = ipaddress.ip_network(cidr, strict=False)
    if net.version != 4:
        raise RuntimeError(f"Only IPv4 CIDR is supported for OpenVPN route push: {cidr}")
    return str(net.network_address), str(net.netmask)


def ensure_target_vpn_client_bundle(cfg: Config) -> Tuple[str, str]:
    if not cfg.enable_target_vpn_client:
        return "", ""

    server_ip = str(cfg.vpn_server_public_ip or "").strip()
    if not server_ip:
        raise RuntimeError(
            "ENABLE_TARGET_VPN_CLIENT=true but VPN server public IP is empty. "
            "Set VPN_SERVER_PUBLIC_IP explicitly (no longer auto-detected via the "
            "cloud metadata endpoint)."
        )
    if not is_ipv4_prefix(server_ip) or "/" in server_ip:
        raise RuntimeError(f"Invalid VPN server public IP: {server_ip}")

    vpn_client_ip = str(cfg.vpn_client_static_ip or "").strip()
    if not is_ipv4_prefix(vpn_client_ip) or "/" in vpn_client_ip:
        raise RuntimeError(f"Invalid VPN_CLIENT_STATIC_IP: {vpn_client_ip}")

    cn = str(cfg.vpn_client_common_name or "").strip()
    if not cn:
        raise RuntimeError("VPN_CLIENT_COMMON_NAME cannot be empty")

    base_dir = "/etc/openvpn/server"
    easy_rsa_dir = f"{base_dir}/easy-rsa"
    ca_path = f"{base_dir}/ca.crt"
    tls_crypt_path = f"{base_dir}/tls-crypt.key"
    cert_path = f"{easy_rsa_dir}/pki/issued/{cn}.crt"
    key_path = f"{easy_rsa_dir}/pki/private/{cn}.key"
    ccd_dir = f"{base_dir}/ccd"
    ccd_file = f"{ccd_dir}/{cn}"

    for path in (ca_path, tls_crypt_path, f"{easy_rsa_dir}/easyrsa"):
        if not os.path.exists(path):
            raise RuntimeError(f"OpenVPN required file not found: {path}")

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print_step(f"OpenVPN client cert '{cn}' not found, building with easy-rsa")
        rc, out = run_local_command(
            [
                "bash",
                "-lc",
                "cd %s && EASYRSA_BATCH=1 ./easyrsa build-client-full %s nopass"
                % (shlex.quote(easy_rsa_dir), shlex.quote(cn)),
            ],
            timeout_sec=120,
        )
        if rc != 0:
            raise RuntimeError(
                "Failed to build OpenVPN client certificate '%s':\n%s" % (cn, maybe_tail(out, 2000))
            )

    os.makedirs(ccd_dir, exist_ok=True)
    rc, out = run_local_command(
        [
            "bash",
            "-lc",
            "chgrp nobody %s && chmod 750 %s"
            % (shlex.quote(ccd_dir), shlex.quote(ccd_dir)),
        ],
        timeout_sec=20,
    )
    if rc != 0:
        raise RuntimeError(f"Failed to set ccd directory permissions: {maybe_tail(out, 800)}")

    with open(ccd_file, "w", encoding="utf-8") as f:
        f.write("ifconfig-push %s 255.255.255.0\n" % vpn_client_ip)
    rc, out = run_local_command(
        [
            "bash",
            "-lc",
            "chown root:nobody %s && chmod 640 %s"
            % (shlex.quote(ccd_file), shlex.quote(ccd_file)),
        ],
        timeout_sec=20,
    )
    if rc != 0:
        raise RuntimeError(f"Failed to set ccd file permissions: {maybe_tail(out, 800)}")

    ca_text = read_text_file(ca_path)
    cert_text = read_text_file(cert_path)
    key_text = read_text_file(key_path)
    tls_crypt_text = read_text_file(tls_crypt_path)

    ovpn = "\n".join(
        [
            "client",
            "dev tun",
            "proto udp",
            "remote %s %d" % (server_ip, int(cfg.vpn_server_port)),
            "resolv-retry infinite",
            "nobind",
            "persist-key",
            "persist-tun",
            "remote-cert-tls server",
            "cipher AES-256-GCM",
            "auth SHA256",
            "verb 3",
            "<ca>",
            ca_text,
            "</ca>",
            "<cert>",
            cert_text,
            "</cert>",
            "<key>",
            key_text,
            "</key>",
            "<tls-crypt>",
            tls_crypt_text,
            "</tls-crypt>",
            "",
        ]
    )
    return ovpn, vpn_client_ip


def parse_openvpn_status_for_cn(path: str, common_name: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.startswith("CLIENT_LIST,"):
                    continue
                cols = line.strip().split(",")
                # CLIENT_LIST,Common Name,Real Address,Virtual Address,...
                if len(cols) >= 4 and cols[1] == common_name:
                    vip = cols[3].strip()
                    if vip and is_ipv4_prefix(vip) and "/" not in vip:
                        return vip
    except Exception:
        pass
    return ""


def wait_for_openvpn_client_virtual_ip(common_name: str, timeout_sec: int = 300) -> str:
    status_files = [
        "/var/log/openvpn/server-status.log",
        "/run/openvpn-server/status-server.log",
    ]
    started = time.time()
    while True:
        for path in status_files:
            vip = parse_openvpn_status_for_cn(path, common_name)
            if vip:
                return vip
        if time.time() - started > timeout_sec:
            return ""
        time.sleep(5)


def list_vpc_peerings(client: HcApiClient, region: str) -> List[dict]:
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings",
    )
    return rsp.get("peerings", []) or []


def find_vpc_peering(peerings: List[dict], vpc_a: str, vpc_b: str) -> Optional[dict]:
    for p in peerings:
        req_vpc = str((p.get("request_vpc_info") or {}).get("vpc_id") or "").strip()
        acc_vpc = str((p.get("accept_vpc_info") or {}).get("vpc_id") or "").strip()
        if {req_vpc, acc_vpc} == {vpc_a, vpc_b}:
            return p
    return None


def ensure_vpc_peering_active(
    client: HcApiClient,
    region: str,
    project_id: str,
    request_vpc_id: str,
    accept_vpc_id: str,
) -> Dict[str, object]:
    peerings = list_vpc_peerings(client, region)
    existing = find_vpc_peering(peerings, request_vpc_id, accept_vpc_id)
    if existing:
        peering_id = str(existing.get("id") or "").strip()
        status = str(existing.get("status") or "").upper()
        if peering_id and status != "ACTIVE":
            client.request_json(
                "PUT",
                f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings/{peering_id}",
                body={"peering": {"status": "ACTIVE"}},
            )
            check = client.request_json(
                "GET",
                f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings/{peering_id}",
            )
            existing = check.get("peering") or existing
        return {
            "id": str(existing.get("id") or ""),
            "name": str(existing.get("name") or ""),
            "status": str(existing.get("status") or ""),
            "created": False,
        }

    body = {
        "peering": {
            "name": "mgc-vpn-bridge",
            "description": "mgcvpnbridge",
            "request_vpc_info": {"vpc_id": request_vpc_id},
            "accept_vpc_info": {"tenant_id": project_id, "vpc_id": accept_vpc_id},
        }
    }
    rsp = client.request_json(
        "POST",
        f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings",
        body=body,
    )
    peering = rsp.get("peering") or {}
    peering_id = str(peering.get("id") or "").strip()
    status = str(peering.get("status") or "").upper()
    if peering_id and status != "ACTIVE":
        client.request_json(
            "PUT",
            f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings/{peering_id}",
            body={"peering": {"status": "ACTIVE"}},
        )
        check = client.request_json(
            "GET",
            f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/peerings/{peering_id}",
        )
        peering = check.get("peering") or peering
    return {
        "id": str(peering.get("id") or ""),
        "name": str(peering.get("name") or ""),
        "status": str(peering.get("status") or ""),
        "created": True,
    }


def list_vpc_routes(client: HcApiClient, region: str) -> List[dict]:
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/routes",
    )
    return rsp.get("routes", []) or []


def ensure_vpc_route(
    client: HcApiClient,
    region: str,
    vpc_id: str,
    destination: str,
    nexthop: str,
) -> Dict[str, object]:
    routes = list_vpc_routes(client, region)
    for r in routes:
        if (
            str(r.get("vpc_id") or "").strip() == vpc_id
            and str(r.get("destination") or "").strip() == destination
            and str(r.get("nexthop") or "").strip() == nexthop
            and str(r.get("type") or "").strip().lower() == "peering"
        ):
            return {
                "id": str(r.get("id") or ""),
                "destination": destination,
                "vpc_id": vpc_id,
                "created": False,
            }

    body = {
        "route": {
            "type": "peering",
            "destination": destination,
            "vpc_id": vpc_id,
            "nexthop": nexthop,
        }
    }
    try:
        rsp = client.request_json(
            "POST",
            f"https://vpc.{region}.myhuaweicloud.com/v2.0/vpc/routes",
            body=body,
        )
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" in err or "already exist" in err or "vpc.0608" in err:
            routes = list_vpc_routes(client, region)
            for r in routes:
                if (
                    str(r.get("vpc_id") or "").strip() == vpc_id
                    and str(r.get("destination") or "").strip() == destination
                    and str(r.get("nexthop") or "").strip() == nexthop
                ):
                    return {
                        "id": str(r.get("id") or ""),
                        "destination": destination,
                        "vpc_id": vpc_id,
                        "created": False,
                    }
        raise

    route = rsp.get("route") or {}
    return {
        "id": str(route.get("id") or ""),
        "destination": destination,
        "vpc_id": vpc_id,
        "created": True,
    }


def get_vpc_cidr(client: HcApiClient, region: str, project_id: str, vpc_id: str) -> str:
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/vpcs/{vpc_id}",
    )
    vpc = rsp.get("vpc") or {}
    return normalize_ipv4_cidr(str(vpc.get("cidr") or "").strip())


def ensure_openvpn_push_route(target_cidr: str) -> Dict[str, object]:
    cidr = normalize_ipv4_cidr(target_cidr)
    if not cidr:
        raise RuntimeError(f"Invalid target CIDR for OpenVPN route push: {target_cidr}")
    network_ip, netmask = cidr_to_route_components(cidr)
    line = f'push "route {network_ip} {netmask}"'
    conf = "/etc/openvpn/server/server.conf"

    text = ""
    try:
        with open(conf, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as exc:
        raise RuntimeError(f"Cannot read OpenVPN server config: {conf}") from exc

    if line in text:
        return {"line": line, "changed": False, "server_restarted": False}

    with open(conf, "a", encoding="utf-8") as f:
        if not text.endswith("\n"):
            f.write("\n")
        f.write(line + "\n")

    rc, out = run_local_command(
        ["bash", "-lc", "systemctl restart openvpn-server@server"],
        timeout_sec=30,
    )
    if rc != 0:
        raise RuntimeError(
            "Failed to restart OpenVPN service after route push update:\n%s"
            % maybe_tail(out, 1200)
        )
    return {"line": line, "changed": True, "server_restarted": True}


def ensure_local_forward_rule(src_cidr: str, dst_cidr: str, in_if: str, out_if: str) -> bool:
    if not src_cidr or not dst_cidr:
        return False
    cmd = (
        "iptables -C FORWARD -i %s -o %s -s %s -d %s -j ACCEPT 2>/dev/null || "
        "iptables -I FORWARD -i %s -o %s -s %s -d %s -j ACCEPT"
        % (
            shlex.quote(in_if),
            shlex.quote(out_if),
            shlex.quote(src_cidr),
            shlex.quote(dst_cidr),
            shlex.quote(in_if),
            shlex.quote(out_if),
            shlex.quote(src_cidr),
            shlex.quote(dst_cidr),
        )
    )
    rc, out = run_local_command(["bash", "-lc", cmd], timeout_sec=20)
    if rc != 0:
        raise RuntimeError(f"Failed to ensure local FORWARD rule: {maybe_tail(out, 1200)}")
    return True


def infer_source_network_cidr(cfg: Config) -> str:
    explicit_cidr = str(cfg.source_network_cidr or "").strip()
    if explicit_cidr:
        cidr = normalize_ipv4_cidr(explicit_cidr)
        if not cidr:
            raise RuntimeError(
                f"Invalid SOURCE_NETWORK_CIDR (source_network_cidr): {explicit_cidr!r}. "
                "Expected an IPv4 CIDR such as 192.168.1.0/24."
            )
        return cidr

    source_private_ip = str(cfg.source_private_ip or "").strip()
    cidr = normalize_ipv4_cidr(source_private_ip)
    if cidr:
        return cidr
    if is_ipv4_prefix(source_private_ip) and "/" not in source_private_ip:
        return normalize_ipv4_cidr(source_private_ip, default_prefix=24)

    raise RuntimeError(
        "Cannot infer the source network CIDR: both SOURCE_NETWORK_CIDR "
        "(source_network_cidr) and SOURCE_PRIVATE_IP (source_private_ip) are empty or "
        "not an IPv4 address. Set source_network_cidr in terraform.tfvars when "
        "enable_vpn_bridge=true; refusing to fall back to a hard-coded network."
    )


def ensure_source_route_to_target_network(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_cidr: str,
) -> Dict[str, object]:
    target_cidr_norm = normalize_ipv4_cidr(target_cidr)
    if not target_cidr_norm:
        raise RuntimeError(f"Invalid target CIDR for source route setup: {target_cidr}")
    remote_cmd = (
        "set -e; "
        "VPN_GW=$(ip route | awk '/^10\\.8\\.0\\.0\\/24 / {for(i=1;i<=NF;i++) if($i==\"via\") {print $(i+1); exit}}'); "
        "VPN_IF=$(ip route | awk '/^10\\.8\\.0\\.0\\/24 / {for(i=1;i<=NF;i++) if($i==\"dev\") {print $(i+1); exit}}'); "
        "if [ -z \"$VPN_GW\" ] || [ -z \"$VPN_IF\" ]; then "
        "VPN_GW=$(ip route get 10.8.0.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i==\"via\") {print $(i+1); exit}}'); "
        "VPN_IF=$(ip route get 10.8.0.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i==\"dev\") {print $(i+1); exit}}'); "
        "fi; "
        "if [ -z \"$VPN_GW\" ] || [ -z \"$VPN_IF\" ]; then "
        "echo 'WARN: cannot infer VPN gateway/interface for source route'; "
        "ip route get 10.8.0.1 || true; "
        "exit 0; "
        "fi; "
        "ip route replace %s via \"$VPN_GW\" dev \"$VPN_IF\" metric 90; "
        "ip route get %s"
        % (shlex.quote(target_cidr_norm), shlex.quote(str(ipaddress.ip_network(target_cidr_norm, strict=False).network_address)))
    )
    return run_remote_ssh_command(
        host=source_host,
        port=cfg.rsync_source_port,
        user=cfg.rsync_source_user,
        password=source_password,
        remote_cmd=remote_cmd,
        timeout_sec=120,
        step_name="ensure_source_route_to_target_vpc_via_vpn",
    )


def ensure_vpn_bridge_connectivity(
    client: HcApiClient,
    cfg: Config,
    target_project_id: str,
    target_vpc_id: str,
    source_host: str,
    source_password: str,
) -> Dict[str, object]:
    local_vpc_id = str(cfg.local_vpc_id or "").strip()
    if not local_vpc_id:
        raise RuntimeError(
            "ENABLE_VPN_BRIDGE=true but LOCAL_VPC_ID is empty. Set LOCAL_VPC_ID explicitly "
            "to the Codex/bridge host's own VPC ID (no longer auto-detected via the cloud "
            "metadata endpoint)."
        )

    target_cidr = normalize_ipv4_cidr(cfg.target_vpc_cidr)
    if not target_cidr:
        raise RuntimeError(f"Invalid TARGET_VPC_CIDR: {cfg.target_vpc_cidr}")
    local_vpc_cidr = get_vpc_cidr(client, cfg.target_region, target_project_id, local_vpc_id)
    if not local_vpc_cidr:
        raise RuntimeError(f"Cannot query local VPC CIDR for VPC '{local_vpc_id}'")
    source_cidr = infer_source_network_cidr(cfg)

    peering = ensure_vpc_peering_active(
        client=client,
        region=cfg.target_region,
        project_id=target_project_id,
        request_vpc_id=local_vpc_id,
        accept_vpc_id=target_vpc_id,
    )
    peering_id = str(peering.get("id") or "").strip()
    if not peering_id:
        raise RuntimeError("Failed to determine VPC peering ID for VPN bridge")

    routes = []
    routes.append(ensure_vpc_route(client, cfg.target_region, local_vpc_id, target_cidr, peering_id))
    routes.append(ensure_vpc_route(client, cfg.target_region, target_vpc_id, local_vpc_cidr, peering_id))
    if source_cidr and source_cidr != local_vpc_cidr:
        routes.append(ensure_vpc_route(client, cfg.target_region, target_vpc_id, source_cidr, peering_id))

    openvpn_route = ensure_openvpn_push_route(target_cidr)

    forward_rules = []
    forward_rules.append(ensure_local_forward_rule("10.8.0.0/24", target_cidr, "tun0", "eth0"))
    forward_rules.append(ensure_local_forward_rule(target_cidr, "10.8.0.0/24", "eth0", "tun0"))
    if source_cidr and source_cidr != "10.8.0.0/24":
        forward_rules.append(ensure_local_forward_rule(source_cidr, target_cidr, "tun0", "eth0"))
        forward_rules.append(ensure_local_forward_rule(target_cidr, source_cidr, "eth0", "tun0"))

    source_route = ensure_source_route_to_target_network(
        cfg=cfg,
        source_host=source_host,
        source_password=source_password,
        target_cidr=target_cidr,
    )
    return {
        "enabled": True,
        "local_vpc_id": local_vpc_id,
        "local_vpc_cidr": local_vpc_cidr,
        "target_vpc_id": target_vpc_id,
        "target_vpc_cidr": target_cidr,
        "source_network_cidr": source_cidr,
        "peering": peering,
        "routes": routes,
        "openvpn_route": openvpn_route,
        "forward_rules_applied": forward_rules,
        "source_route_setup": source_route,
    }


def get_region_project(client: HcApiClient, region_code: str) -> Tuple[str, str]:
    rsp = client.request_json(
        "GET",
        "https://iam.myhuaweicloud.com/v3/projects",
        params={"name": region_code},
    )
    projects = rsp.get("projects", [])
    if not projects:
        raise RuntimeError(f"No IAM project found for region: {region_code}")

    # Prefer exact match on project name.
    for p in projects:
        if p.get("name") == region_code:
            return p["id"], p["name"]

    first = projects[0]
    return first["id"], first.get("name", region_code)


def list_sms_sources(client: HcApiClient, sms_endpoint: str, params: Dict[str, str]) -> List[dict]:
    rsp = client.request_json("GET", f"{sms_endpoint}/v3/sources", params=params)
    return rsp.get("source_servers", [])


def list_sms_tasks(client: HcApiClient, sms_endpoint: str, limit: int = 200) -> List[dict]:
    out: List[dict] = []
    offset = 0
    while True:
        rsp = client.request_json(
            "GET",
            f"{sms_endpoint}/v3/tasks",
            params={"limit": str(limit), "offset": str(offset)},
        )
        tasks = rsp.get("tasks", [])
        if not tasks:
            break
        out.extend(tasks)
        if len(tasks) < limit:
            break
        offset += len(tasks)
    return out


def delete_sms_task(client: HcApiClient, sms_endpoint: str, task_id: str) -> None:
    client.request_json("DELETE", f"{sms_endpoint}/v3/tasks/{task_id}")


def cleanup_failed_tasks_for_source(client: HcApiClient, sms_endpoint: str, source_sms_id: str) -> int:
    tasks = list_sms_tasks(client, sms_endpoint)
    deleted = 0
    allowed_states = {
        "MIGRATE_FAIL",
        "CUTOVER_FAIL",
        "SYNC_FAIL",
        "REPLICATE_FAIL",
        "FAIL",
        "ERROR",
        "ABORT",
    }
    for t in tasks:
        source_id = str((t.get("source_server") or {}).get("id") or "").strip()
        state = str(t.get("state") or "").upper()
        task_id = str(t.get("id") or "").strip()
        if source_id == source_sms_id and task_id and state in allowed_states:
            try:
                delete_sms_task(client, sms_endpoint, task_id)
                deleted += 1
            except Exception as exc:
                err = str(exc)
                # Task may have entered deleting/running transition, keep best-effort cleanup.
                if "SMS.7719" in err:
                    continue
                raise
    return deleted


def cleanup_terminal_tasks_for_source(client: HcApiClient, sms_endpoint: str, source_sms_id: str) -> Dict[str, object]:
    tasks = list_sms_tasks(client, sms_endpoint)
    terminal_states = {
        "MIGRATE_SUCCESS",
        "CUTOVER_SUCCESS",
        "SYNC_SUCCESS",
        "REPLICATE_SUCCESS",
        "MIGRATE_FAIL",
        "CUTOVER_FAIL",
        "SYNC_FAIL",
        "REPLICATE_FAIL",
        "FAIL",
        "ERROR",
        "ABORT",
    }
    deleted_tasks: List[dict] = []
    active_tasks: List[dict] = []
    matched_count = 0

    for t in tasks:
        source_id = str((t.get("source_server") or {}).get("id") or "").strip()
        if source_id != source_sms_id:
            continue
        matched_count += 1
        state = str(t.get("state") or "").upper()
        task_id = str(t.get("id") or "").strip()
        item = {
            "id": task_id,
            "name": str(t.get("name") or ""),
            "state": state,
            "target_vm_id": str((t.get("target_server") or {}).get("vm_id") or ""),
        }
        if task_id and state in terminal_states:
            try:
                delete_sms_task(client, sms_endpoint, task_id)
                item["deleted"] = True
                deleted_tasks.append(item)
            except Exception as exc:
                err = str(exc)
                if "SMS.7719" in err:
                    # Deletion window race: backend reports non-deletable transition state.
                    item["deleted"] = False
                    item["delete_error"] = err
                    active_tasks.append(item)
                else:
                    raise
        else:
            item["deleted"] = False
            active_tasks.append(item)

    return {
        "source_sms_server_id": source_sms_id,
        "matched_count": matched_count,
        "deleted_count": len(deleted_tasks),
        "deleted_tasks": deleted_tasks,
        "active_tasks": active_tasks,
        "generated_at": int(time.time()),
    }


def pick_preferred_source(items: List[dict]) -> Optional[dict]:
    if not items:
        return None
    ranked = sorted(
        items,
        key=lambda x: (
            0 if x.get("connected") is True else 1,
            0 if str(x.get("state", "")).lower() not in {"unavailable", "deleted"} else 1,
            -int(x.get("add_date") or 0),
        ),
    )
    return ranked[0]


def get_source_ecs_detail(
    client: HcApiClient,
    source_region: str,
    source_project_id: str,
    source_server_id: str,
) -> Optional[dict]:
    try:
        rsp = client.request_json(
            "GET",
            f"https://ecs.{source_region}.myhuaweicloud.com/v1/{source_project_id}/cloudservers/{source_server_id}",
        )
    except Exception:
        return None
    return rsp.get("server")


def get_server_primary_fixed_ip(server: Optional[dict]) -> str:
    if not server:
        return ""
    for items in (server.get("addresses") or {}).values():
        for item in items:
            if str(item.get("OS-EXT-IPS:type", "")).lower() == "fixed":
                ip = str(item.get("addr") or "").strip()
                if ip:
                    return ip
    return ""


def get_server_primary_floating_ip(server: Optional[dict]) -> str:
    if not server:
        return ""
    for items in (server.get("addresses") or {}).values():
        for item in items:
            if str(item.get("OS-EXT-IPS:type", "")).lower() == "floating":
                ip = str(item.get("addr") or "").strip()
                if ip:
                    return ip
    return ""


def get_server_vpc_id(server: Optional[dict]) -> str:
    if not server:
        return ""
    metadata = server.get("metadata") or {}
    vpc_id = str(metadata.get("vpc_id") or "").strip()
    if vpc_id:
        return vpc_id
    for items in (server.get("addresses") or {}).values():
        for item in items:
            vpc = str(item.get("vpc_id") or "").strip()
            if vpc:
                return vpc
    return ""


def get_sms_source_server(
    client: HcApiClient,
    sms_endpoint: str,
    source_server_id: str,
    fallback_name: str = "",
    fallback_ip: str = "",
) -> dict:
    # First try the ID as an SMS source ID.
    by_id = list_sms_sources(
        client,
        sms_endpoint,
        {"id": source_server_id, "limit": "1", "offset": "0"},
    )
    preferred = pick_preferred_source(by_id)
    if preferred:
        return preferred

    # If user provided an ECS ID, try matching SMS source by vm_id.
    by_vm_id = list_sms_sources(
        client,
        sms_endpoint,
        {"vm_id": source_server_id, "limit": "200", "offset": "0"},
    )
    preferred = pick_preferred_source(by_vm_id)
    if preferred:
        matched = preferred
        print_step(
            f"Input '{source_server_id}' matched SMS source '{matched.get('id', '')}' by vm_id"
        )
        return matched

    # For external sources, users often pass the source hostname/instance name directly.
    by_input_name = list_sms_sources(
        client,
        sms_endpoint,
        {"name": source_server_id, "limit": "200", "offset": "0"},
    )
    preferred = pick_preferred_source(by_input_name)
    if preferred:
        matched = preferred
        print_step(
            f"Input '{source_server_id}' matched SMS source '{matched.get('id', '')}' by input name"
        )
        return matched

    # Non-Huawei sources are often provided as the source public/private IP.
    # Treat an IPv4 input as an SMS source IP lookup before falling back to
    # ECS-derived fields.
    if is_ipv4_prefix(source_server_id) and "/" not in source_server_id:
        by_input_ip = list_sms_sources(
            client,
            sms_endpoint,
            {"ip": source_server_id, "limit": "200", "offset": "0"},
        )
        preferred = pick_preferred_source(by_input_ip)
        if preferred:
            matched = preferred
            print_step(
                f"Input '{source_server_id}' matched SMS source '{matched.get('id', '')}' by input ip"
            )
            return matched

    # Fallback by source private IP if available.
    if fallback_ip:
        by_ip = list_sms_sources(
            client,
            sms_endpoint,
            {"ip": fallback_ip, "limit": "200", "offset": "0"},
        )
        preferred = pick_preferred_source(by_ip)
        if preferred:
            matched = preferred
            print_step(
                f"Input '{source_server_id}' matched SMS source '{matched.get('id', '')}' by ip={fallback_ip}"
            )
            return matched

    # Fallback by source ECS name if available.
    if fallback_name:
        by_name = list_sms_sources(
            client,
            sms_endpoint,
            {"name": fallback_name, "limit": "200", "offset": "0"},
        )
        preferred = pick_preferred_source(by_name)
        if preferred:
            matched = preferred
            print_step(
                f"Input '{source_server_id}' matched SMS source '{matched.get('id', '')}' by name={fallback_name}"
            )
            return matched

    # Last resort: if exactly one SMS source exists, use it.
    all_sources = list_sms_sources(client, sms_endpoint, {"limit": "200", "offset": "0"})
    if len(all_sources) == 1:
        matched = all_sources[0]
        print_step(
            f"Input '{source_server_id}' used the only SMS source '{matched.get('id', '')}'"
        )
        return matched

    raise RuntimeError(
        "Source server not found in SMS by id/vm_id/ip: "
        f"{source_server_id}. SMS requires source registration by Agent first."
    )


def get_sms_source_detail(client: HcApiClient, sms_endpoint: str, source_sms_id: str) -> dict:
    return client.request_json("GET", f"{sms_endpoint}/v3/sources/{source_sms_id}")


def parse_ipv4_network(cidr: str, field_name: str) -> ipaddress.IPv4Network:
    raw = str(cidr or "").strip()
    if not raw:
        raise RuntimeError(f"{field_name} is empty")
    try:
        net = ipaddress.ip_network(raw, strict=False)
    except Exception:
        raise RuntimeError(f"Invalid {field_name}: {raw}")
    if net.version != 4:
        raise RuntimeError(f"{field_name} must be IPv4 CIDR: {raw}")
    return net


def first_usable_gateway_ip(subnet: ipaddress.IPv4Network) -> str:
    hosts = subnet.hosts()
    first = next(hosts, None)
    if first is None:
        raise RuntimeError(f"No usable gateway IP in subnet {str(subnet)}")
    return str(first)


def ipv4_subnet_within(subnet: ipaddress.IPv4Network, vpc: ipaddress.IPv4Network) -> bool:
    return (
        subnet.network_address >= vpc.network_address
        and subnet.broadcast_address <= vpc.broadcast_address
    )


def get_target_vpc_and_subnet(
    client: HcApiClient,
    target_region: str,
    target_project_id: str,
    vpc_name: str,
    vpc_cidr: str,
    subnet_cidr: str,
) -> Tuple[str, str]:
    want_name = str(vpc_name or "").strip()
    if not want_name:
        raise RuntimeError("TARGET_VPC_NAME cannot be empty")

    def list_vpcs() -> List[dict]:
        vpc_rsp = client.request_json(
            "GET",
            f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/vpcs",
            params={"limit": "200"},
        )
        return vpc_rsp.get("vpcs", [])

    def match_vpc_by_name(vpcs: List[dict], name: str) -> Optional[dict]:
        want = str(name).strip().lower()
        for v in vpcs:
            if str(v.get("name") or "").strip().lower() == want:
                return v
        return None

    vpc_net = parse_ipv4_network(vpc_cidr, "TARGET_VPC_CIDR")
    subnet_net = parse_ipv4_network(subnet_cidr, "TARGET_SUBNET_CIDR")
    if not ipv4_subnet_within(subnet_net, vpc_net):
        raise RuntimeError(
            f"TARGET_SUBNET_CIDR ({str(subnet_net)}) must be within TARGET_VPC_CIDR ({str(vpc_net)})"
        )

    vpcs = list_vpcs()
    picked = match_vpc_by_name(vpcs, want_name)
    if not picked:
        print_step(f"Target VPC '{want_name}' not found, creating with CIDR {str(vpc_net)}")
        try:
            create_rsp = client.request_json(
                "POST",
                f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/vpcs",
                body={"vpc": {"name": want_name, "cidr": str(vpc_net)}},
            )
            picked = create_rsp.get("vpc") or {}
        except Exception as exc:
            err = str(exc).lower()
            # Handle race/retry where vpc was created by a concurrent attempt.
            if "already exists" not in err and "already exist" not in err:
                raise
        if not picked or not str(picked.get("id") or "").strip():
            picked = match_vpc_by_name(list_vpcs(), want_name)
        if not picked:
            raise RuntimeError(f"Failed to create/find target VPC '{want_name}' in region {target_region}")

    vpc_id = str(picked.get("id") or "").strip()
    if not vpc_id:
        raise RuntimeError(f"Matched VPC '{want_name}' has empty ID")

    subnet_rsp = client.request_json(
        "GET",
        f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/subnets",
        params={"vpc_id": vpc_id},
    )
    subnets = subnet_rsp.get("subnets", [])
    if subnets:
        return vpc_id, str(subnets[0]["id"])

    gateway_ip = first_usable_gateway_ip(subnet_net)
    subnet_name = f"{want_name}-subnet"
    print_step(
        f"Target VPC '{want_name}' has no subnet, creating subnet '{subnet_name}' with CIDR {str(subnet_net)}"
    )
    try:
        create_subnet_rsp = client.request_json(
            "POST",
            f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/subnets",
            body={
                "subnet": {
                    "name": subnet_name,
                    "cidr": str(subnet_net),
                    "gateway_ip": gateway_ip,
                    "vpc_id": vpc_id,
                    "dhcp_enable": True,
                }
            },
        )
        subnet_id = str((create_subnet_rsp.get("subnet") or {}).get("id") or "").strip()
        if subnet_id:
            return vpc_id, subnet_id
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" not in err and "already exist" not in err:
            raise

    # Retry fetch after potential concurrent creation or delayed response.
    subnet_rsp = client.request_json(
        "GET",
        f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/subnets",
        params={"vpc_id": vpc_id},
    )
    subnets = subnet_rsp.get("subnets", [])
    if not subnets:
        raise RuntimeError(f"No subnet found in VPC {want_name} ({vpc_id}) after create attempt")
    return vpc_id, str(subnets[0]["id"])


def list_security_groups(
    client: HcApiClient,
    region: str,
    project_id: str,
    params: Optional[Dict[str, str]] = None,
) -> List[dict]:
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups",
        params=params or {},
    )
    return rsp.get("security_groups", [])


def get_security_group_detail(
    client: HcApiClient,
    region: str,
    project_id: str,
    security_group_id: str,
) -> dict:
    rsp = client.request_json(
        "GET",
        f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-groups/{security_group_id}",
    )
    return rsp.get("security_group", {})


def get_vpc_default_security_group_id(
    client: HcApiClient,
    region: str,
    project_id: str,
    vpc_id: str,
) -> str:
    sgs = list_security_groups(
        client=client,
        region=region,
        project_id=project_id,
        params={"vpc_id": vpc_id},
    )
    if not sgs:
        # Some regions return "default"/empty for default VPC SG binding.
        sgs = list_security_groups(
            client=client,
            region=region,
            project_id=project_id,
            params={},
        )
    if not sgs:
        raise RuntimeError(f"No security groups found in region {region}")

    def score(sg: dict) -> Tuple[int, int, int, str]:
        sg_vpc_id = str(sg.get("vpc_id") or "").strip()
        name = str(sg.get("name") or "").strip().lower()
        desc = str(sg.get("description") or "").strip().lower()
        return (
            0 if sg_vpc_id == vpc_id else 1,
            0 if sg_vpc_id in {"default", ""} else 1,
            0 if name in {"default", "vpc-default", "sys-default"} else 1,
            0 if "default" in name else 1,
            0 if "default" in desc or vpc_id in desc else 1,
            name,
        )

    ranked = sorted(sgs, key=score)
    picked = ranked[0]
    sg_id = str(picked.get("id") or "").strip()
    if not sg_id:
        raise RuntimeError(f"Matched security group in VPC {vpc_id} has no ID")
    return sg_id


def get_server_security_group_ids(server: Optional[dict]) -> List[str]:
    if not server:
        return []
    out: List[str] = []
    for sg in server.get("security_groups", []) or []:
        sg_id = str(sg.get("id") or "").strip()
        if sg_id and sg_id not in out:
            out.append(sg_id)
    return out


def is_likely_aws_instance_id(value: str) -> bool:
    return bool(re.match(r"^i-[0-9a-fA-F]{8,32}$", str(value or "").strip()))


def normalize_aws_region_hint(region_hint: str) -> str:
    raw = str(region_hint or "").strip().lower().replace("_", "-")
    if not raw:
        return "us-east-2"
    aliases = {
        "ohio": "us-east-2",
        "us-east-2": "us-east-2",
    }
    return aliases.get(raw, raw)


def normalize_aws_protocol(raw_protocol: str) -> str:
    proto = str(raw_protocol or "").strip().lower()
    if proto in {"", "-1", "all", "any"}:
        return ""
    if proto in {"6", "tcp"}:
        return "tcp"
    if proto in {"17", "udp"}:
        return "udp"
    if proto in {"1", "icmp"}:
        return "icmp"
    if proto in {"58", "icmpv6"}:
        return "icmpv6"
    return proto


def int_or_none(value: object) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def fetch_aws_source_security_profile(
    source_server_id: str,
    access_key: str,
    secret_key: str,
    region_hint: str,
    session_token: str = "",
) -> Optional[Dict[str, object]]:
    server_id = str(source_server_id or "").strip()
    if not is_likely_aws_instance_id(server_id):
        return None

    ak = str(access_key or "").strip()
    sk = str(secret_key or "").strip()
    if not ak or not sk:
        raise RuntimeError(
            "AWS source instance ID detected but AWS_SOURCE_ACCESS_KEY/AWS_SOURCE_SECRET_KEY is empty."
        )

    aws_region = normalize_aws_region_hint(region_hint)
    try:
        import boto3
    except Exception as exc:
        raise RuntimeError("Python module 'boto3' is required to query AWS source security groups.") from exc

    client_kwargs: Dict[str, object] = {
        "service_name": "ec2",
        "region_name": aws_region,
        "aws_access_key_id": ak,
        "aws_secret_access_key": sk,
    }
    token = str(session_token or "").strip()
    if token:
        client_kwargs["aws_session_token"] = token

    ec2 = boto3.client(**client_kwargs)  # type: ignore[arg-type]

    try:
        describe_rsp = ec2.describe_instances(InstanceIds=[server_id])
    except Exception as exc:
        raise RuntimeError(
            "Failed to query AWS EC2 instance '%s' in region '%s': %s"
            % (server_id, aws_region, str(exc))
        )

    instance = None
    for reservation in describe_rsp.get("Reservations", []) or []:
        for item in reservation.get("Instances", []) or []:
            if str(item.get("InstanceId") or "").strip() == server_id:
                instance = item
                break
        if instance:
            break
    if not instance:
        raise RuntimeError(
            "AWS EC2 instance '%s' not found in region '%s'."
            % (server_id, aws_region)
        )

    private_ip = str(instance.get("PrivateIpAddress") or "").strip()
    public_ip = str(instance.get("PublicIpAddress") or "").strip()
    source_sg_ids = unique_nonempty(
        [str(g.get("GroupId") or "").strip() for g in (instance.get("SecurityGroups") or [])]
    )

    flattened_rules: List[Dict[str, object]] = []
    skipped_ipv6_rules = 0
    skipped_group_reference_rules = 0
    skipped_non_cidr_rules = 0
    unsupported_protocols: Set[str] = set()

    if source_sg_ids:
        try:
            sg_rsp = ec2.describe_security_groups(GroupIds=source_sg_ids)
        except Exception as exc:
            raise RuntimeError(
                "Failed to query AWS source security groups for '%s': %s"
                % (server_id, str(exc))
            )

        for sg in sg_rsp.get("SecurityGroups", []) or []:
            sg_id = str(sg.get("GroupId") or "").strip()
            for aws_key, direction in (
                ("IpPermissions", "ingress"),
                ("IpPermissionsEgress", "egress"),
            ):
                for perm in sg.get(aws_key, []) or []:
                    protocol = normalize_aws_protocol(str(perm.get("IpProtocol") or ""))
                    if protocol == "icmpv6":
                        unsupported_protocols.add("icmpv6")
                        continue
                    if protocol not in {"", "tcp", "udp", "icmp"}:
                        unsupported_protocols.add(protocol or str(perm.get("IpProtocol") or "unknown"))
                        continue

                    port_range_min = int_or_none(perm.get("FromPort"))
                    port_range_max = int_or_none(perm.get("ToPort"))
                    if protocol in {"tcp", "udp"}:
                        if port_range_min is None or port_range_max is None:
                            port_range_min = 1
                            port_range_max = 65535
                    elif protocol == "icmp":
                        if port_range_min is None:
                            port_range_min = -1
                        if port_range_max is None:
                            port_range_max = -1
                    else:
                        port_range_min = None
                        port_range_max = None

                    ipv4_ranges = unique_nonempty(
                        [str(x.get("CidrIp") or "").strip() for x in (perm.get("IpRanges") or [])]
                    )
                    skipped_ipv6_rules += len(
                        [x for x in (perm.get("Ipv6Ranges") or []) if str(x.get("CidrIpv6") or "").strip()]
                    )
                    skipped_group_reference_rules += len(perm.get("UserIdGroupPairs") or [])
                    if not ipv4_ranges:
                        skipped_non_cidr_rules += 1
                        continue

                    for cidr in ipv4_ranges:
                        flattened_rules.append(
                            {
                                "direction": direction,
                                "remote_ip_prefix": cidr,
                                "protocol": protocol,
                                "port_range_min": port_range_min,
                                "port_range_max": port_range_max,
                                "aws_security_group_id": sg_id,
                            }
                        )

    deduped_rules: List[Dict[str, object]] = []
    seen: Set[Tuple[str, str, str, Optional[int], Optional[int]]] = set()
    for rule in flattened_rules:
        key = (
            str(rule.get("direction") or "").lower(),
            normalize_ip_prefix(str(rule.get("remote_ip_prefix") or "")),
            str(rule.get("protocol") or "").lower(),
            int_or_none(rule.get("port_range_min")),
            int_or_none(rule.get("port_range_max")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped_rules.append(rule)

    return {
        "instance_id": server_id,
        "region": aws_region,
        "private_ip": private_ip,
        "public_ip": public_ip,
        "security_group_ids": source_sg_ids,
        "rules": deduped_rules,
        "rules_total": len(deduped_rules),
        "skipped_ipv6_rules": skipped_ipv6_rules,
        "skipped_group_reference_rules": skipped_group_reference_rules,
        "skipped_non_cidr_rules": skipped_non_cidr_rules,
        "unsupported_protocols": sorted(list(unsupported_protocols)),
    }


def normalize_ip_prefix(ip: str) -> str:
    value = str(ip or "").strip()
    if not value:
        return ""
    if "/" in value:
        return value
    return f"{value}/32"


def has_security_group_rule(
    rules: List[dict],
    direction: str,
    remote_ip_prefix: str,
) -> bool:
    want_prefix = normalize_ip_prefix(remote_ip_prefix)
    for r in rules or []:
        if str(r.get("direction") or "").lower() != direction.lower():
            continue
        if str(r.get("ethertype") or "IPv4") != "IPv4":
            continue
        got_prefix = normalize_ip_prefix(str(r.get("remote_ip_prefix") or "").strip())
        if got_prefix == want_prefix:
            return True
    return False


def create_security_group_rule(
    client: HcApiClient,
    region: str,
    project_id: str,
    security_group_id: str,
    direction: str,
    remote_ip_prefix: str,
) -> bool:
    body = {
        "security_group_rule": {
            "security_group_id": security_group_id,
            "direction": direction,
            "ethertype": "IPv4",
            "remote_ip_prefix": normalize_ip_prefix(remote_ip_prefix),
            "description": "auto-added by mgc cross-region migration",
        }
    }
    try:
        client.request_json(
            "POST",
            f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-group-rules",
            body=body,
        )
        return True
    except Exception as exc:
        err = str(exc).lower()
        if (
            "already exists" in err
            or "already exist" in err
            or "vpc.0608" in err
            or "security group rule has existed" in err
        ):
            return False
        raise


def normalize_sg_protocol(protocol: str) -> str:
    raw = str(protocol or "").strip().lower()
    if raw in {"", "-1", "all", "any"}:
        return ""
    if raw in {"6", "tcp"}:
        return "tcp"
    if raw in {"17", "udp"}:
        return "udp"
    if raw in {"1", "icmp"}:
        return "icmp"
    return raw


def has_security_group_rule_advanced(
    rules: List[dict],
    direction: str,
    remote_ip_prefix: str,
    protocol: str = "",
    port_range_min: Optional[int] = None,
    port_range_max: Optional[int] = None,
) -> bool:
    want_prefix = normalize_ip_prefix(remote_ip_prefix)
    want_protocol = normalize_sg_protocol(protocol)
    want_port_min = int_or_none(port_range_min)
    want_port_max = int_or_none(port_range_max)

    for rule in rules or []:
        if str(rule.get("direction") or "").lower() != str(direction or "").lower():
            continue
        if str(rule.get("ethertype") or "IPv4") != "IPv4":
            continue
        got_prefix = normalize_ip_prefix(str(rule.get("remote_ip_prefix") or "").strip())
        if got_prefix != want_prefix:
            continue
        got_protocol = normalize_sg_protocol(str(rule.get("protocol") or ""))
        if got_protocol != want_protocol:
            continue

        if want_protocol in {"tcp", "udp", "icmp"}:
            got_port_min = int_or_none(rule.get("port_range_min"))
            got_port_max = int_or_none(rule.get("port_range_max"))
            if got_port_min != want_port_min or got_port_max != want_port_max:
                continue
        return True
    return False


def create_security_group_rule_advanced(
    client: HcApiClient,
    region: str,
    project_id: str,
    security_group_id: str,
    direction: str,
    remote_ip_prefix: str,
    protocol: str = "",
    port_range_min: Optional[int] = None,
    port_range_max: Optional[int] = None,
) -> bool:
    normalized_protocol = normalize_sg_protocol(protocol)
    body_rule: Dict[str, object] = {
        "security_group_id": security_group_id,
        "direction": direction,
        "ethertype": "IPv4",
        "remote_ip_prefix": normalize_ip_prefix(remote_ip_prefix),
        "description": "auto-copied from source security group policy",
    }

    if normalized_protocol:
        body_rule["protocol"] = normalized_protocol
        if normalized_protocol in {"tcp", "udp", "icmp"}:
            if port_range_min is not None:
                body_rule["port_range_min"] = int(port_range_min)
            if port_range_max is not None:
                body_rule["port_range_max"] = int(port_range_max)

    try:
        client.request_json(
            "POST",
            f"https://vpc.{region}.myhuaweicloud.com/v1/{project_id}/security-group-rules",
            body={"security_group_rule": body_rule},
        )
        return True
    except Exception as exc:
        err = str(exc).lower()
        if (
            "already exists" in err
            or "already exist" in err
            or "vpc.0608" in err
            or "security group rule has existed" in err
        ):
            return False
        raise


def ensure_target_security_group_rules_from_policy(
    client: HcApiClient,
    region: str,
    project_id: str,
    target_security_group_ids: List[str],
    policy_rules: List[Dict[str, object]],
) -> Dict[str, object]:
    if not target_security_group_ids or not policy_rules:
        return {
            "input_rules": len(policy_rules or []),
            "created": 0,
            "already_existing": 0,
            "skipped_unsupported": 0,
        }

    target_rules_map: Dict[str, List[dict]] = {}
    for sg_id in target_security_group_ids:
        detail = get_security_group_detail(client, region, project_id, sg_id)
        target_rules_map[sg_id] = detail.get("security_group_rules", []) or []

    created = 0
    already_existing = 0
    skipped_unsupported = 0
    failed_rules: List[Dict[str, object]] = []

    for rule in policy_rules:
        direction = str(rule.get("direction") or "").strip().lower()
        remote_ip_prefix = str(rule.get("remote_ip_prefix") or "").strip()
        protocol = normalize_sg_protocol(str(rule.get("protocol") or ""))
        port_range_min = int_or_none(rule.get("port_range_min"))
        port_range_max = int_or_none(rule.get("port_range_max"))

        if direction not in {"ingress", "egress"} or not remote_ip_prefix:
            skipped_unsupported += 1
            continue
        if protocol not in {"", "tcp", "udp", "icmp"}:
            skipped_unsupported += 1
            continue

        exists = False
        for rules in target_rules_map.values():
            if has_security_group_rule_advanced(
                rules=rules,
                direction=direction,
                remote_ip_prefix=remote_ip_prefix,
                protocol=protocol,
                port_range_min=port_range_min,
                port_range_max=port_range_max,
            ):
                exists = True
                break
        if exists:
            already_existing += 1
            continue

        applied = False
        last_quota_error = ""
        for sg_id in sorted(target_security_group_ids, key=lambda x: len(target_rules_map.get(x, []))):
            try:
                added = create_security_group_rule_advanced(
                    client=client,
                    region=region,
                    project_id=project_id,
                    security_group_id=sg_id,
                    direction=direction,
                    remote_ip_prefix=remote_ip_prefix,
                    protocol=protocol,
                    port_range_min=port_range_min,
                    port_range_max=port_range_max,
                )
            except Exception as exc:
                err = str(exc)
                low = err.lower()
                if "vpc.0614" in low or "quota exceeded" in low:
                    last_quota_error = err
                    continue
                raise

            applied = True
            if added:
                created += 1
                target_rules_map.setdefault(sg_id, []).append(
                    {
                        "direction": direction,
                        "ethertype": "IPv4",
                        "remote_ip_prefix": normalize_ip_prefix(remote_ip_prefix),
                        "protocol": protocol,
                        "port_range_min": port_range_min,
                        "port_range_max": port_range_max,
                    }
                )
            break

        if not applied:
            failed_rules.append(
                {
                    "direction": direction,
                    "remote_ip_prefix": remote_ip_prefix,
                    "protocol": protocol,
                    "port_range_min": port_range_min,
                    "port_range_max": port_range_max,
                    "last_error": last_quota_error,
                }
            )

    if failed_rules:
        raise RuntimeError(
            "Failed to copy source security-group policy rules to target security groups. "
            "failed_count=%d sample=%s"
            % (len(failed_rules), json.dumps(failed_rules[:3], ensure_ascii=False))
        )

    return {
        "input_rules": len(policy_rules),
        "created": created,
        "already_existing": already_existing,
        "skipped_unsupported": skipped_unsupported,
    }


def ensure_security_group_connectivity(
    client: HcApiClient,
    region: str,
    project_id: str,
    security_group_id: str,
    peer_ips: List[str],
) -> int:
    detail = get_security_group_detail(client, region, project_id, security_group_id)
    rules = detail.get("security_group_rules", []) or []

    created = 0
    for ip in peer_ips:
        prefix = normalize_ip_prefix(ip)
        if not prefix:
            continue
        for direction in ("ingress", "egress"):
            if has_security_group_rule(rules, direction, prefix):
                continue
            added = create_security_group_rule(
                client=client,
                region=region,
                project_id=project_id,
                security_group_id=security_group_id,
                direction=direction,
                remote_ip_prefix=prefix,
            )
            if added:
                created += 1
                rules.append({
                    "direction": direction,
                    "ethertype": "IPv4",
                    "remote_ip_prefix": prefix,
                })
    return created


def ensure_source_target_security_groups(
    client: HcApiClient,
    source_region: str,
    source_project_id: str,
    source_server: Optional[dict],
    target_region: str,
    target_project_id: str,
    target_vpc_id: str,
    target_vm_id: str,
    source_fixed_ip: str,
    source_floating_ip: str,
    additional_target_peer_ips: Optional[List[str]] = None,
    aws_source_profile: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    target_server_rsp = client.request_json(
        "GET",
        f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/{target_vm_id}",
    )
    target_server = target_server_rsp.get("server", {})

    target_fixed_ip = get_server_primary_fixed_ip(target_server)
    target_floating_ip = get_server_primary_floating_ip(target_server)
    target_sg_ids = get_server_security_group_ids(target_server)

    fallback_vpc_default_sg = get_vpc_default_security_group_id(
        client=client,
        region=target_region,
        project_id=target_project_id,
        vpc_id=target_vpc_id,
    )
    if not target_sg_ids:
        target_sg_ids = [fallback_vpc_default_sg]
        print_step(
            "Target ECS has no attached security groups in detail response, "
            "fallback to vpc-default security group"
        )

    target_peers = unique_nonempty(
        [source_fixed_ip, source_floating_ip] + list(additional_target_peer_ips or [])
    )

    target_added = 0
    for sg_id in target_sg_ids:
        target_added += ensure_security_group_connectivity(
            client=client,
            region=target_region,
            project_id=target_project_id,
            security_group_id=sg_id,
            peer_ips=target_peers,
        )

    aws_policy_result = {
        "input_rules": 0,
        "created": 0,
        "already_existing": 0,
        "skipped_unsupported": 0,
    }
    aws_source_sg_ids: List[str] = []
    aws_source_rules_total = 0
    aws_source_skipped_ipv6 = 0
    aws_source_skipped_group_ref = 0
    aws_source_skipped_non_cidr = 0
    aws_source_unsupported_protocols: List[str] = []

    if aws_source_profile:
        aws_source_sg_ids = unique_nonempty(
            [str(x or "").strip() for x in (aws_source_profile.get("security_group_ids") or [])]
        )
        aws_source_rules_total = int(aws_source_profile.get("rules_total") or 0)
        aws_source_skipped_ipv6 = int(aws_source_profile.get("skipped_ipv6_rules") or 0)
        aws_source_skipped_group_ref = int(aws_source_profile.get("skipped_group_reference_rules") or 0)
        aws_source_skipped_non_cidr = int(aws_source_profile.get("skipped_non_cidr_rules") or 0)
        aws_source_unsupported_protocols = list(aws_source_profile.get("unsupported_protocols") or [])
        aws_rules = list(aws_source_profile.get("rules") or [])

        if aws_rules:
            print_step(
                "Copying AWS source security-group policies to target security groups "
                f"(rules={len(aws_rules)})"
            )
            aws_policy_result = ensure_target_security_group_rules_from_policy(
                client=client,
                region=target_region,
                project_id=target_project_id,
                target_security_group_ids=target_sg_ids,
                policy_rules=aws_rules,
            )

    source_sg_ids = get_server_security_group_ids(source_server)
    source_added = 0
    if source_sg_ids:
        for sg_id in source_sg_ids:
            source_added += ensure_security_group_connectivity(
                client=client,
                region=source_region,
                project_id=source_project_id,
                security_group_id=sg_id,
                peer_ips=[target_fixed_ip, target_floating_ip],
            )
    else:
        print_step("Source ECS has no security group IDs in detail response, skipped source SG updates")

    return {
        "source_security_group_ids": source_sg_ids,
        "target_security_group_ids": target_sg_ids,
        "target_peer_ips": target_peers,
        "target_vpc_default_security_group_id": fallback_vpc_default_sg,
        "source_security_group_rules_created": source_added,
        "target_security_group_rules_created": target_added,
        "aws_source_instance_id": str((aws_source_profile or {}).get("instance_id") or ""),
        "aws_source_region": str((aws_source_profile or {}).get("region") or ""),
        "aws_source_security_group_ids": aws_source_sg_ids,
        "aws_source_security_group_rules_total": aws_source_rules_total,
        "aws_source_security_group_rules_copied": int(aws_policy_result.get("created") or 0),
        "aws_source_security_group_rules_existing": int(aws_policy_result.get("already_existing") or 0),
        "aws_source_security_group_rules_skipped_unsupported": (
            int(aws_policy_result.get("skipped_unsupported") or 0)
            + aws_source_skipped_ipv6
            + aws_source_skipped_group_ref
            + aws_source_skipped_non_cidr
        ),
        "aws_source_security_group_rules_skipped_ipv6": aws_source_skipped_ipv6,
        "aws_source_security_group_rules_skipped_group_reference": aws_source_skipped_group_ref,
        "aws_source_security_group_rules_skipped_non_cidr": aws_source_skipped_non_cidr,
        "aws_source_unsupported_protocols": aws_source_unsupported_protocols,
        "source_fixed_ip": source_fixed_ip,
        "source_floating_ip": source_floating_ip,
        "target_fixed_ip": target_fixed_ip,
        "target_floating_ip": target_floating_ip,
    }


def get_first_available_az(client: HcApiClient, target_region: str, target_project_id: str) -> str:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/availability-zones",
    )

    # Newer ECS API format.
    az_items_v2 = rsp.get("availability_zones", [])
    for item in az_items_v2:
        az_id = str(item.get("availability_zone_id") or "").strip()
        if az_id:
            return az_id

    az_items = rsp.get("availabilityZoneInfo", [])
    for item in az_items:
        if str(item.get("zoneState", {}).get("available", True)).lower() == "true":
            if item.get("zoneName"):
                return item["zoneName"]

    if az_items and az_items[0].get("zoneName"):
        return az_items[0]["zoneName"]

    raise RuntimeError(f"Unable to get availability zone in {target_region}")


def parse_vcpus_ram_from_flavor_id(flavor_id: str) -> Tuple[int, int]:
    # Common pattern: "<family>.<vcpus>u.<ram_gb>g"
    m = re.search(r"\.(\d+)u\.(\d+)g", flavor_id)
    if not m:
        return 0, 0
    return int(m.group(1)), int(m.group(2)) * 1024


def get_flavor_vcpus_ram(
    client: HcApiClient,
    region: str,
    project_id: str,
    flavor_id: str,
) -> Tuple[int, int]:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/flavors",
    )
    for f in rsp.get("flavors", []):
        if str(f.get("id")) == flavor_id:
            try:
                return int(f.get("vcpus")), int(f.get("ram"))
            except Exception:
                break
    return parse_vcpus_ram_from_flavor_id(flavor_id)


def choose_target_flavors(
    client: HcApiClient,
    target_region: str,
    target_project_id: str,
    preferred_flavor_id: str,
    src_vcpus: int,
    src_ram_mb: int,
) -> List[str]:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/flavors",
    )
    flavors = rsp.get("flavors", [])
    if not flavors:
        raise RuntimeError(f"No available ECS flavors in {target_region}")

    result: List[str] = []
    want_vcpus = src_vcpus if src_vcpus > 0 else 1
    want_ram_mb = src_ram_mb if src_ram_mb > 0 else 1024

    # Prefer exact same flavor if it exists and is enabled, but still keep fallbacks.
    if preferred_flavor_id:
        for f in flavors:
            if (
                str(f.get("id")) == preferred_flavor_id
                and not bool(f.get("OS-FLV-DISABLED:disabled", False))
            ):
                result.append(preferred_flavor_id)
                break

    candidates = []
    for f in flavors:
        if bool(f.get("OS-FLV-DISABLED:disabled", False)):
            continue
        try:
            vcpus = int(f.get("vcpus"))
            ram_mb = int(f.get("ram"))
        except Exception:
            continue
        # score: nearest CPU first, then nearest RAM, then prefer RAM >= source.
        score = (
            abs(vcpus - want_vcpus),
            abs(ram_mb - want_ram_mb),
            0 if ram_mb >= want_ram_mb else 1,
        )
        candidates.append((score, str(f.get("id")), vcpus, ram_mb))

    if not candidates:
        raise RuntimeError(f"No enabled ECS flavor candidates in {target_region}")

    candidates.sort(key=lambda x: x[0])
    for _, flavor_id, _, _ in candidates:
        if flavor_id not in result:
            result.append(flavor_id)
    return result


def extract_data_disks_from_source(source_server: dict, data_volume_type: str) -> List[dict]:
    disks = (((source_server.get("init_target_server") or {}).get("disks")) or [])
    result = []
    for d in disks:
        if str(d.get("device_use", "")).upper() == "BOOT":
            continue
        size_bytes = int(d.get("size", 0))
        if size_bytes <= 0:
            continue
        size_gb = max(1, math.ceil(size_bytes / (1024 ** 3)))
        result.append({"volumetype": data_volume_type, "size": size_gb})
    return result


def extract_boot_disk_size_gb_from_source(source_server: dict) -> int:
    disks = (
        ((source_server.get("init_target_server") or {}).get("disks"))
        or source_server.get("disks")
        or []
    )
    for d in disks:
        is_boot = str(d.get("device_use") or "").upper() == "BOOT" or bool(d.get("os_disk"))
        if not is_boot:
            continue
        size_bytes = int(d.get("size") or 0)
        if size_bytes <= 0:
            continue
        return max(1, math.ceil(size_bytes / (1024 ** 3)))
    return 0


def parse_required_root_volume_size_from_error(err_text: str) -> int:
    text = str(err_text or "")
    if not text:
        return 0
    # Example:
    # root volume size is [8], must over image mindisk [40]
    m = re.search(
        r"root\s+volume\s+size\s+is\s*\[(\d+)\]\s*,\s*must\s+over\s+image\s+mindisk\s*\[(\d+)\]",
        text,
        re.IGNORECASE,
    )
    if m:
        return int(m.group(2))
    m = re.search(r"mindisk\s*\[(\d+)\]", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def build_linux_ssh_user_data_b64(vpn_client_ovpn: str = "", admin_password: str = "") -> str:
    # Ensure SSH service is up and optionally bootstrap OpenVPN client on target ECS.
    lines = [
        "#cloud-config",
        "runcmd:",
        '  - [sh, -c, "sed -ri \'s/^#?PasswordAuthentication[[:space:]]+.*/PasswordAuthentication yes/\' /etc/ssh/sshd_config || true"]',
        '  - [sh, -c, "grep -Eq \'^PasswordAuthentication[[:space:]]+yes\' /etc/ssh/sshd_config || echo \'PasswordAuthentication yes\' >> /etc/ssh/sshd_config"]',
        '  - [sh, -c, "sed -ri \'s/^#?PermitRootLogin[[:space:]]+.*/PermitRootLogin yes/\' /etc/ssh/sshd_config || true"]',
        '  - [sh, -c, "grep -Eq \'^PermitRootLogin[[:space:]]+yes\' /etc/ssh/sshd_config || echo \'PermitRootLogin yes\' >> /etc/ssh/sshd_config"]',
        '  - [sh, -c, "systemctl enable sshd || true"]',
        '  - [sh, -c, "systemctl enable ssh || true"]',
        '  - [sh, -c, "systemctl restart sshd || systemctl restart ssh || true"]',
        '  - [sh, -c, "firewall-cmd --permanent --add-service=ssh >/dev/null 2>&1 || true"]',
        '  - [sh, -c, "firewall-cmd --permanent --add-port=22/tcp >/dev/null 2>&1 || true"]',
        '  - [sh, -c, "firewall-cmd --reload >/dev/null 2>&1 || true"]',
        '  - [sh, -c, "iptables -C INPUT -p tcp --dport 22 -j ACCEPT >/dev/null 2>&1 || iptables -I INPUT -p tcp --dport 22 -j ACCEPT >/dev/null 2>&1 || true"]',
    ]
    if admin_password:
        pw_b64 = base64.b64encode(admin_password.encode("utf-8")).decode("ascii")
        lines.insert(
            2,
            '  - [sh, -c, "echo root:$(echo %s | base64 -d) | chpasswd || true"]' % pw_b64,
        )
    if vpn_client_ovpn:
        ovpn_b64 = base64.b64encode(vpn_client_ovpn.encode("utf-8")).decode("ascii")
        lines.extend([
            '  - [sh, -c, "mkdir -p /etc/openvpn/client /etc/openvpn"]',
            '  - [sh, -c, "echo %s | base64 -d > /etc/openvpn/client/mgc-target.conf"]' % ovpn_b64,
            '  - [sh, -c, "chmod 600 /etc/openvpn/client/mgc-target.conf"]',
            '  - [sh, -c, "(dnf -y install openvpn || yum -y install openvpn || (apt-get update -y && apt-get install -y openvpn)) >/tmp/mgc-openvpn-install.log 2>&1 || true"]',
            '  - [sh, -c, "systemctl enable --now openvpn-client@mgc-target >/tmp/mgc-openvpn-start.log 2>&1 || systemctl enable --now openvpn@mgc-target >/tmp/mgc-openvpn-start.log 2>&1 || (pkill -f \'openvpn --config /etc/openvpn/client/mgc-target.conf\' >/dev/null 2>&1 || true; nohup openvpn --config /etc/openvpn/client/mgc-target.conf --daemon >/tmp/mgc-openvpn-start.log 2>&1)"]',
        ])
    cloud_init = "\n".join(lines) + "\n"
    return base64.b64encode(cloud_init.encode("utf-8")).decode("ascii")


def build_server_create_body(
    az: str,
    name: str,
    image_id: str,
    flavor_id: str,
    admin_password: str,
    vpc_id: str,
    subnet_id: str,
    root_volume_type: str,
    root_volume_size_gb: int,
    data_disks: List[dict],
    eip_bandwidth_mbps: int,
    eip_iptype: str,
    enterprise_project_id: str,
    user_data_b64: str,
) -> dict:
    root_volume = {"volumetype": root_volume_type}
    if int(root_volume_size_gb) > 0:
        root_volume["size"] = int(root_volume_size_gb)

    server = {
        "availability_zone": az,
        "name": name,
        "imageRef": image_id,
        "flavorRef": flavor_id,
        "adminPass": admin_password,
        "vpcid": vpc_id,
        "nics": [{"subnet_id": subnet_id}],
        "root_volume": root_volume,
        "publicip": {
            "eip": {
                "iptype": eip_iptype,
                "bandwidth": {
                    "size": int(eip_bandwidth_mbps),
                    "sharetype": "PER",
                },
            }
        },
        "user_data": user_data_b64,
    }

    if data_disks:
        server["data_volumes"] = data_disks

    extendparam: Dict[str, object] = {"chargingMode": "postPaid"}
    ep_id = str(enterprise_project_id or "").strip()
    if ep_id:
        extendparam["enterprise_project_id"] = ep_id
    server["extendparam"] = extendparam

    return {"server": server}


def wait_ecs_job_success(client: HcApiClient, target_region: str, target_project_id: str, job_id: str, timeout_sec: int = 1200) -> dict:
    start = time.time()
    while True:
        rsp = client.request_json(
            "GET",
            f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/jobs/{job_id}",
        )
        status = str(rsp.get("status", "")).upper()
        if status == "SUCCESS":
            return rsp
        if status == "FAIL":
            raise RuntimeError(f"ECS async job failed: {json.dumps(rsp, ensure_ascii=False)}")
        if time.time() - start > timeout_sec:
            raise RuntimeError(f"Timeout waiting ECS job: {job_id}")
        time.sleep(10)


def extract_server_id_from_ecs_job(job_rsp: dict) -> str:
    uuid_pat = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
    )
    candidates: List[str] = []

    def walk(node: object, key: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                lk = str(k).lower()
                if isinstance(v, str) and uuid_pat.match(v):
                    if "server" in lk or lk in {"server_id", "serverid"}:
                        candidates.append(v)
                walk(v, lk)
        elif isinstance(node, list):
            for item in node:
                walk(item, key)

    walk(job_rsp.get("entities") or job_rsp)
    return candidates[0] if candidates else ""


def find_server_id_by_name(client: HcApiClient, target_region: str, target_project_id: str, server_name: str) -> str:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/detail",
        params={"name": server_name, "limit": "100"},
    )
    servers = rsp.get("servers", [])
    if not servers:
        raise RuntimeError(f"Cannot find target ECS by name: {server_name}")
    servers = [s for s in servers if str(s.get("name") or "") == server_name] or servers
    servers.sort(key=lambda x: x.get("created", ""), reverse=True)
    return servers[0]["id"]


def ensure_server_exists(client: HcApiClient, target_region: str, target_project_id: str, server_id: str) -> bool:
    try:
        client.request_json(
            "GET",
            f"https://ecs.{target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/{server_id}",
        )
        return True
    except Exception:
        return False


def get_server_fixed_and_floating_ip(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
) -> Tuple[str, str]:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
    )
    server = rsp.get("server", {})
    return get_server_primary_fixed_ip(server), get_server_primary_floating_ip(server)


def get_server_image_and_flavor(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
) -> Tuple[str, str]:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
    )
    server = rsp.get("server", {})
    image_id = str((server.get("image") or {}).get("id") or "").strip()
    flavor_id = str((server.get("flavor") or {}).get("id") or "").strip()
    return image_id, flavor_id


def get_server_status(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
) -> str:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
    )
    server = rsp.get("server", {})
    return str(server.get("status") or "").upper()


def wait_server_status(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    expected_status: str = "ACTIVE",
    timeout_sec: int = 900,
    interval_sec: int = 10,
) -> str:
    expect = str(expected_status or "").upper() or "ACTIVE"
    started = time.time()
    while True:
        status = get_server_status(client, region, project_id, server_id)
        if status == expect:
            return status
        if time.time() - started > timeout_sec:
            raise RuntimeError(
                "Timeout waiting server '%s' status '%s' (current=%s)"
                % (server_id, expect, status)
            )
        time.sleep(max(2, int(interval_sec)))


def get_server_attached_disks(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
) -> List[dict]:
    rsp = client.request_json(
        "GET",
        f"https://ecs.{region}.myhuaweicloud.com/v1/{project_id}/cloudservers/{server_id}",
    )
    server = rsp.get("server", {})
    out = []
    for v in server.get("os-extended-volumes:volumes_attached", []) or []:
        out.append({
            "id": str(v.get("id") or ""),
            "device": str(v.get("device") or ""),
            "boot_index": str(v.get("bootIndex") or ""),
        })
    return out


def get_candidate_eip_types(client: HcApiClient, target_region: str, target_project_id: str) -> List[str]:
    candidates: List[str] = []

    def add(v: str) -> None:
        vv = str(v or "").strip()
        if vv and vv not in candidates:
            candidates.append(vv)

    # Legacy publicips API often returns `type` like "5_bgp".
    try:
        rsp = client.request_json(
            "GET",
            f"https://vpc.{target_region}.myhuaweicloud.com/v1/{target_project_id}/publicips",
        )
        for p in rsp.get("publicips", []):
            add(p.get("type"))
    except Exception:
        pass

    # V3 EIP API may expose `publicip_pool_name`.
    try:
        rsp = client.request_json(
            "GET",
            f"https://vpc.{target_region}.myhuaweicloud.com/v3/{target_project_id}/eip/publicips",
        )
        for p in rsp.get("publicips", []):
            add(p.get("publicip_pool_name"))
    except Exception:
        pass

    # Common fallbacks.
    add("5_bgp")
    add("5_sbgp")
    return candidates


def find_reusable_target_server_id(
    client: HcApiClient,
    cfg: Config,
    target_project_id: str,
    target_vpc_id: str,
) -> str:
    # Avoid creating extra ECS/EIP when a previous retry already prepared a target server.
    # Exclude servers that are still referenced by existing SMS tasks.
    blocked_vm_ids = set()
    try:
        tasks = list_sms_tasks(client, cfg.sms_endpoint)
        for t in tasks:
            vm_id = str((t.get("target_server") or {}).get("vm_id") or "").strip()
            if vm_id:
                blocked_vm_ids.add(vm_id)
    except Exception:
        pass

    rsp = client.request_json(
        "GET",
        f"https://ecs.{cfg.target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/detail",
        params={"limit": "200"},
    )
    servers = rsp.get("servers", [])
    if not servers:
        return ""

    base_name = str(cfg.target_server_name or "").strip()
    servers = [
        s for s in servers
        if str(s.get("name") or "").strip() == base_name
        or str(s.get("name") or "").strip().startswith(base_name + "-")
    ]
    servers.sort(key=lambda x: str(x.get("created") or ""), reverse=True)

    for s in servers:
        sid = str(s.get("id") or "").strip()
        if not sid or sid in blocked_vm_ids:
            continue
        status = str(s.get("status") or "").upper()
        if status not in {"ACTIVE", "SHUTOFF"}:
            continue
        vpc_id = get_server_vpc_id(s)
        if target_vpc_id and vpc_id and vpc_id != target_vpc_id:
            continue
        fixed_ip = get_server_primary_fixed_ip(s)
        floating_ip = get_server_primary_floating_ip(s)
        if fixed_ip and floating_ip:
            return sid
    return ""


def create_target_server(
    client: HcApiClient,
    cfg: Config,
    source_project_id: str,
    target_project_id: str,
    source_server: dict,
    vpc_id: str,
    subnet_id: str,
    allow_reuse: bool = True,
) -> str:
    source_ecs = {}
    source_flavor = ""
    src_vcpus = 0
    src_ram_mb = 0

    try:
        source_ecs_rsp = client.request_json(
            "GET",
            f"https://ecs.{cfg.source_region}.myhuaweicloud.com/v1/{source_project_id}/cloudservers/{cfg.source_server_id}",
        )
        source_ecs = source_ecs_rsp.get("server") or {}
        source_flavor = str((source_ecs.get("flavor") or {}).get("id") or "").strip()
    except Exception:
        # For non-ECS source servers (for example, on-prem VMware), flavor info is not available.
        source_ecs = {}
        source_flavor = ""

    if allow_reuse:
        reusable_id = find_reusable_target_server_id(client, cfg, target_project_id, vpc_id)
        if reusable_id:
            print_step(f"Reusing existing target ECS '{reusable_id}' with bound EIP")
            return reusable_id

    if source_flavor:
        src_vcpus, src_ram_mb = get_flavor_vcpus_ram(
            client=client,
            region=cfg.source_region,
            project_id=source_project_id,
            flavor_id=source_flavor,
        )
    if src_vcpus <= 0:
        src_vcpus = int(source_server.get("cpu_quantity") or 0)
    if src_ram_mb <= 0:
        src_ram_mb = int(int(source_server.get("memory") or 0) / (1024 * 1024))

    preferred_flavor = str(cfg.target_flavor_id or "").strip() or source_flavor
    target_flavors = choose_target_flavors(
        client=client,
        target_region=cfg.target_region,
        target_project_id=target_project_id,
        preferred_flavor_id=preferred_flavor,
        src_vcpus=src_vcpus,
        src_ram_mb=src_ram_mb,
    )
    target_flavor = target_flavors[0]
    if source_flavor and target_flavor != source_flavor:
        print_step(
            f"Source flavor '{source_flavor}' not available in {cfg.target_region}, "
            f"using compatible flavor '{target_flavor}'"
        )
    elif not source_flavor:
        print_step(
            "Source is not an ECS flavor-based source, selected target flavor "
            f"'{target_flavor}' by source CPU/RAM ({src_vcpus} vCPU/{src_ram_mb} MB)"
        )
    elif cfg.target_flavor_id and target_flavor == cfg.target_flavor_id:
        print_step(f"Using user-specified target flavor '{cfg.target_flavor_id}'")

    az = get_first_available_az(client, cfg.target_region, target_project_id)
    create_server_name = f"{cfg.target_server_name}-{int(time.time())}"
    root_volume_size_gb = extract_boot_disk_size_gb_from_source(source_server)
    if root_volume_size_gb > 0:
        print_step(f"Using source boot disk size {root_volume_size_gb}GB for target root volume")
    data_disks = extract_data_disks_from_source(source_server, cfg.data_volume_type)
    vpn_client_ovpn, _ = ensure_target_vpn_client_bundle(cfg)
    user_data_b64 = build_linux_ssh_user_data_b64(
        vpn_client_ovpn=vpn_client_ovpn,
        admin_password=cfg.target_admin_password,
    )
    source_ep_id = str(source_server.get("enterprise_project_id") or "").strip()
    if source_ep_id.lower() == "default":
        source_ep_id = "0"
    enterprise_project_candidates = []
    for ep_id in (source_ep_id, "0", ""):
        if ep_id not in enterprise_project_candidates:
            enterprise_project_candidates.append(ep_id)
    eip_types = get_candidate_eip_types(client, cfg.target_region, target_project_id)
    last_err = None
    for enterprise_project_id in enterprise_project_candidates:
        if enterprise_project_id != source_ep_id:
            label = enterprise_project_id or "omitted"
            print_step(
                "Retrying target ECS create with enterprise_project_id='%s'"
                % label
            )
        budget_blocked = False
        for flavor_id in target_flavors:
            if flavor_id != target_flavor:
                print_step(f"Retrying target ECS create with fallback flavor '{flavor_id}'")
            for eip_type in eip_types:
                print_step(f"Creating target ECS with flavor '{flavor_id}' and EIP pool '{eip_type}'")
                body = build_server_create_body(
                    az=az,
                    name=create_server_name,
                    image_id=cfg.target_image_id,
                    flavor_id=flavor_id,
                    admin_password=cfg.target_admin_password,
                    vpc_id=vpc_id,
                    subnet_id=subnet_id,
                    root_volume_type=cfg.root_volume_type,
                    root_volume_size_gb=root_volume_size_gb,
                    data_disks=data_disks,
                    eip_bandwidth_mbps=cfg.eip_bandwidth_mbps,
                    eip_iptype=eip_type,
                    enterprise_project_id=enterprise_project_id,
                    user_data_b64=user_data_b64,
                )

                try:
                    rsp = client.request_json(
                        "POST",
                        f"https://ecs.{cfg.target_region}.myhuaweicloud.com/v1.1/{target_project_id}/cloudservers",
                        body=body,
                    )
                except Exception as exc:
                    last_err = exc
                    err = str(exc)
                    required_root_size = parse_required_root_volume_size_from_error(err)
                    if "Ecs.0005" in err and required_root_size > int(root_volume_size_gb):
                        print_step(
                            "Target image requires root volume >= %dGB, retrying with adjusted root volume size"
                            % required_root_size
                        )
                        root_volume_size_gb = required_root_size
                        retry_body = build_server_create_body(
                            az=az,
                            name=create_server_name,
                            image_id=cfg.target_image_id,
                            flavor_id=flavor_id,
                            admin_password=cfg.target_admin_password,
                            vpc_id=vpc_id,
                            subnet_id=subnet_id,
                            root_volume_type=cfg.root_volume_type,
                            root_volume_size_gb=root_volume_size_gb,
                            data_disks=data_disks,
                            eip_bandwidth_mbps=cfg.eip_bandwidth_mbps,
                            eip_iptype=eip_type,
                            enterprise_project_id=enterprise_project_id,
                            user_data_b64=user_data_b64,
                        )
                        try:
                            rsp = client.request_json(
                                "POST",
                                f"https://ecs.{cfg.target_region}.myhuaweicloud.com/v1.1/{target_project_id}/cloudservers",
                                body=retry_body,
                            )
                            err = ""
                        except Exception as retry_exc:
                            last_err = retry_exc
                            err = str(retry_exc)
                    if "Ecs.0070" in err:
                        print_step(
                            "Enterprise project budget is insufficient for target ECS create, "
                            "trying next enterprise project candidate"
                        )
                        budget_blocked = True
                        break
                    if "EIP.7904" in err:
                        print_step(f"EIP pool '{eip_type}' not available, trying next candidate")
                        continue
                    if "Ecs.0005" in err:
                        print_step(
                            "Flavor '%s' cannot satisfy image root-disk constraints, trying fallback flavor"
                            % flavor_id
                        )
                        break
                    if "Ecs.0018" in err or "sold out" in err.lower():
                        print_step(f"Flavor '{flavor_id}' is sold out, trying fallback flavor")
                        break
                    raise

                job_id = rsp.get("job_id")
                if job_id:
                    try:
                        job_rsp = wait_ecs_job_success(client, cfg.target_region, target_project_id, job_id)
                    except Exception as exc:
                        last_err = exc
                        err = str(exc)
                        if "Ecs.0070" in err:
                            print_step(
                                "Enterprise project budget failed during create job, "
                                "trying next enterprise project candidate"
                            )
                            budget_blocked = True
                            break
                        if "EIP.7904" in err:
                            print_step(f"EIP pool '{eip_type}' failed during create job, trying next candidate")
                            continue
                        if "Ecs.0018" in err or "sold out" in err.lower():
                            print_step(f"Flavor '{flavor_id}' sold out during create job, trying fallback flavor")
                            break
                        raise
                    server_ids = rsp.get("serverIds") or rsp.get("server_ids") or []
                    if isinstance(server_ids, list):
                        for sid in server_ids:
                            if sid and ensure_server_exists(client, cfg.target_region, target_project_id, sid):
                                return sid

                    sid = extract_server_id_from_ecs_job(job_rsp)
                    if sid and ensure_server_exists(client, cfg.target_region, target_project_id, sid):
                        return sid

                    return find_server_id_by_name(client, cfg.target_region, target_project_id, create_server_name)

                server_ids = rsp.get("serverIds") or rsp.get("server_ids")
                if isinstance(server_ids, list) and server_ids:
                    sid = server_ids[0]
                    if ensure_server_exists(client, cfg.target_region, target_project_id, sid):
                        return sid
                    # Fallback for APIs that return reserved IDs before instance is fully available.
                    time.sleep(5)
                    if ensure_server_exists(client, cfg.target_region, target_project_id, sid):
                        return sid
                    return find_server_id_by_name(client, cfg.target_region, target_project_id, create_server_name)

                raise RuntimeError(f"Unexpected ECS create response: {json.dumps(rsp, ensure_ascii=False)}")
            if budget_blocked:
                break

    if last_err:
        raise last_err
    raise RuntimeError("No available EIP pool type found for target ECS creation")


def create_sms_migproject(client: HcApiClient, cfg: Config) -> str:
    raw_name = "mgc%s%s%d" % (
        cfg.source_server_id[:8],
        cfg.target_region.replace("-", ""),
        int(time.time()),
    )
    name = sanitize_name(raw_name, 20)
    body = {
        "name": name,
        "description": f"Cross-region migration {cfg.source_region} -> {cfg.target_region}",
        "region": cfg.target_region_name,
        "start_target_server": True,
        "speed_limit": 0,
        "use_public_ip": True,
        "exist_server": True,
        "isdefault": False,
        "type": "MIGRATE_BLOCK",
        "syncing": False,
        "enterprise_project": "default",
    }
    rsp = client.request_json("POST", f"{cfg.sms_endpoint}/v3/migprojects", body=body)
    project_id = rsp.get("id")
    if not project_id:
        raise RuntimeError(f"Unexpected CreateMigproject response: {json.dumps(rsp, ensure_ascii=False)}")
    return project_id


def create_sms_task(
    client: HcApiClient,
    cfg: Config,
    source_sms_id: str,
    source_server: dict,
    target_vm_id: str,
    target_project_id: str,
    target_project_name: str,
) -> str:
    os_type = str(source_server.get("os_type") or "LINUX").upper()
    if os_type not in {"LINUX", "WINDOWS"}:
        os_type = "LINUX"

    raw_name = "task%s%s%d" % (
        cfg.source_server_id[:8],
        cfg.target_region.replace("-", ""),
        int(time.time()),
    )
    base_task_name = sanitize_name(raw_name, 20)
    task_target_name = "%s%s" % (
        sanitize_name(cfg.target_server_name, 12),
        str(int(time.time()))[-8:],
    )
    target_disks = (
        ((source_server.get("init_target_server") or {}).get("disks"))
        or source_server.get("disks")
        or []
    )
    target_volume_groups = (
        ((source_server.get("init_target_server") or {}).get("volume_groups"))
        or source_server.get("volume_groups")
        or []
    )
    target_btrfs = source_server.get("btrfs_list") or []
    target_disks = deepcopy(target_disks)

    # Fill required diskId for existing target server disks.
    attached = get_server_attached_disks(
        client=client,
        region=cfg.target_region,
        project_id=target_project_id,
        server_id=target_vm_id,
    )
    by_device = {}
    boot_disk_id = ""
    # Track attached disks in order for index-based fallback mapping.
    attached_ordered_ids: List[str] = []
    for a in attached:
        dev = str(a.get("device") or "").strip()
        did = str(a.get("id") or "").strip()
        if dev and did:
            by_device[dev] = did
        if str(a.get("boot_index", "")) == "0" and did:
            boot_disk_id = did
        if did:
            attached_ordered_ids.append(did)

    def normalize_device_name(dev: str) -> str:
        """Map source device naming (sd*/nvme*) to Huawei target naming (vd*)."""
        if not dev:
            return dev
        # /dev/sda -> /dev/vda, /dev/sdb -> /dev/vdb, etc.
        m = re.match(r"^/dev/(sd|nvme[n0-9]*n)([a-z]+)$", dev)
        if m:
            return f"/dev/vd{m.group(2)}"
        return dev

    for d in target_disks:
        dev = str(d.get("name") or "").strip()
        did = by_device.get(dev, "")
        if not did:
            # Try normalized device name (e.g. /dev/sda -> /dev/vda)
            did = by_device.get(normalize_device_name(dev), "")
        if not did and str(d.get("device_use") or "").upper() == "BOOT":
            did = boot_disk_id
        if did:
            d["disk_id"] = did
    # Some regions/devices return different device names; if there is only one
    # source disk and one attached target disk, bind them directly.
    if len(target_disks) == 1 and len(attached) == 1 and not str(target_disks[0].get("disk_id") or "").strip():
        target_disks[0]["disk_id"] = str(attached[0].get("id") or "").strip()
    # Fallback: if some source disks still lack disk_id and we have enough
    # attached target disks, map by index order (boot first, then data disks).
    unmapped_indices = [
        i for i, d in enumerate(target_disks)
        if not str(d.get("disk_id") or "").strip()
    ]
    if unmapped_indices and len(attached_ordered_ids) >= len(target_disks):
        # Build ordered source disk indices: BOOT first, then NORMAL by order.
        source_order = sorted(
            range(len(target_disks)),
            key=lambda i: (
                0 if str(target_disks[i].get("device_use") or "").upper() == "BOOT" else 1,
                i,
            ),
        )
        # Build ordered target ids: boot_index=0 first, then by device name.
        target_order = sorted(
            range(len(attached)),
            key=lambda j: (
                0 if str(attached[j].get("boot_index", "")) == "0" else 1,
                str(attached[j].get("device") or ""),
            ),
        )
        for s_idx, t_idx in zip(source_order, target_order):
            if not str(target_disks[s_idx].get("disk_id") or "").strip():
                target_disks[s_idx]["disk_id"] = str(attached[t_idx].get("id") or "").strip()

    def normalize_pvs(pvs: List[dict]) -> List[dict]:
        out: List[dict] = []
        for pv in pvs or []:
            item: Dict[str, object] = {}
            for k in ("uuid", "index", "name", "device_use", "file_system", "mount_point", "size", "used_size"):
                if pv.get(k) is not None:
                    item[k] = pv.get(k)
            if item:
                out.append(item)
        return out

    def normalize_target_disks(disks: List[dict]) -> List[dict]:
        out: List[dict] = []
        for d in disks or []:
            did = str(d.get("disk_id") or "").strip()
            name = str(d.get("name") or "").strip()
            if not did:
                raise RuntimeError(f"Target disk mapping missing disk_id for source disk '{name}'")
            item: Dict[str, object] = {
                "name": name,
                "disk_id": did,
                "device_use": str(d.get("device_use") or "NORMAL"),
            }
            if d.get("size") is not None:
                item["size"] = int(d.get("size"))
            if d.get("used_size") is not None:
                item["used_size"] = int(d.get("used_size"))
            pvs = normalize_pvs(d.get("physical_volumes") or [])
            if pvs:
                item["physical_volumes"] = pvs
            out.append(item)
        return out

    target_disks_payload_cache = None

    def get_target_disks_payload() -> List[dict]:
        nonlocal target_disks_payload_cache
        if target_disks_payload_cache is None:
            target_disks_payload_cache = normalize_target_disks(target_disks)
        return target_disks_payload_cache

    def do_create(
        task_type: str,
        task_name: str,
        consistency: bool,
        use_public_ip: bool,
        include_target_disks: bool,
    ) -> str:
        fixed_ip, floating_ip = get_server_fixed_and_floating_ip(
            client=client,
            region=cfg.target_region,
            project_id=target_project_id,
            server_id=target_vm_id,
        )
        migration_ip = floating_ip if use_public_ip else fixed_ip
        if not migration_ip:
            raise RuntimeError(
                "Cannot determine target migration IP. "
                f"use_public_ip={str(use_public_ip).lower()}, fixed_ip='{fixed_ip}', floating_ip='{floating_ip}'"
            )
        body = {
            "name": task_name,
            "type": task_type,
            "os_type": os_type,
            "start_target_server": True,
            "syncing": False,
            "use_public_ip": use_public_ip,
            "region_name": cfg.target_region_name,
            "region_id": cfg.target_region,
            "project_name": target_project_name,
            "project_id": target_project_id,
            "source_server": {"id": source_sms_id},
            "target_server": {
                "vm_id": target_vm_id,
                "name": task_target_name,
                "ip": migration_ip,
                "volume_groups": target_volume_groups if target_volume_groups is not None else [],
                "btrfs_list": target_btrfs if target_btrfs is not None else [],
            },
            "migration_ip": migration_ip,
            "exist_server": True,
            "is_need_consistency_check": consistency,
        }
        if include_target_disks:
            # Some SMS backends reject attached disk_id during runtime start
            # (SMS.1404: expected available, current IN-USE). Keep this optional.
            target_disks_payload = get_target_disks_payload()
            if target_disks_payload:
                body["target_server"]["disks"] = target_disks_payload
        print_step(
            "CreateTask request names: task_name='%s', target_server_name='%s', type=%s, use_public_ip=%s, include_disks=%s, migration_ip=%s"
            % (
                task_name,
                task_target_name,
                task_type,
                str(use_public_ip).lower(),
                str(include_target_disks).lower(),
                migration_ip,
            )
        )
        rsp = client.request_json("POST", f"{cfg.sms_endpoint}/v3/tasks", body=body)
        task_id = rsp.get("id")
        if not task_id:
            raise RuntimeError(f"Unexpected CreateTask response: {json.dumps(rsp, ensure_ascii=False)}")
        return task_id

    def create_with_public_ip_fallback(
        task_type: str,
        task_name: str,
        consistency: bool,
        include_target_disks: bool,
    ) -> str:
        try:
            return do_create(task_type, task_name, consistency, True, include_target_disks)
        except Exception as exc:
            err = str(exc)
            if include_target_disks and "SMS.1404" in err and "IN-USE" in err and "available" in err:
                print_step(
                    "Task creation got SMS.1404(volume IN-USE), retrying without target_server.disks mapping"
                )
                return do_create(task_type, task_name, consistency, True, False)
            if "SMS.7605" in err:
                deleted = cleanup_failed_tasks_for_source(client, cfg.sms_endpoint, source_sms_id)
                if deleted > 0:
                    print_step(f"Task creation got SMS.7605, cleaned {deleted} failed task(s), retrying")
                    return do_create(task_type, task_name, consistency, True, include_target_disks)
            if "SMS.6602" in err:
                print_step("Task creation got SMS.6602, retrying with use_public_ip=false")
                return do_create(task_type, task_name, consistency, False, include_target_disks)
            raise

    # Prefer file migration first to avoid known 6617->7605 chaining in some regions/accounts.
    fallback_name = sanitize_name("file" + base_task_name, 20)
    try:
        return create_with_public_ip_fallback("MIGRATE_FILE", fallback_name, False, True)
    except Exception as file_exc:
        file_err = str(file_exc)
        if "SMS.6603" in file_err:
            raise RuntimeError(
                "Source server is not connected to SMS (SMS.6603). "
                "Install and start SMS-Agent on source server, then retry."
            )
        if "SMS.7605" in file_err:
            # Let caller decide whether to recreate target ECS and retry.
            raise
        print_step(f"MIGRATE_FILE task creation failed: {file_err}")
        print_step("Retrying with MIGRATE_BLOCK")

    try:
        return create_with_public_ip_fallback("MIGRATE_BLOCK", base_task_name, True, True)
    except Exception as block_exc:
        err = str(block_exc)
        if "SMS.6617" in err:
            raise RuntimeError(
                "Source kernel does not support block migration (SMS.6617), "
                "and MIGRATE_FILE task creation also failed."
            )
        if "SMS.6603" in err:
            raise RuntimeError(
                "Source server is not connected to SMS (SMS.6603). "
                "Install and start SMS-Agent on source server, then retry."
            )
        raise


def start_sms_task(client: HcApiClient, sms_endpoint: str, task_id: str) -> None:
    client.request_json(
        "POST",
        f"{sms_endpoint}/v3/tasks/{task_id}/action",
        body={"operation": "start"},
    )


def get_sms_task_state(client: HcApiClient, sms_endpoint: str, task_id: str) -> str:
    rsp = client.request_json("GET", f"{sms_endpoint}/v3/tasks/{task_id}")
    return str(rsp.get("state") or "")


def get_source_precheck_issues(source_server: dict) -> List[dict]:
    issues: List[dict] = []
    checks = source_server.get("checks") or []
    for item in checks:
        name = str(item.get("name") or "").strip().upper()
        result = str(item.get("result") or "").strip().upper()
        code = str(item.get("error_code") or "").strip().upper()
        if result == "ERROR":
            issues.append({
                "name": name,
                "result": result,
                "error_code": code,
            })
    return issues


def detect_sms_incompatible_reason(source_server: dict) -> str:
    issues = get_source_precheck_issues(source_server)
    for issue in issues:
        code = issue.get("error_code", "")
        name = issue.get("name", "")
        if code in {"SMS.6504", "SMS.6617"}:
            return f"{name}:{code}"
        if name in {"OS_VERSION", "KERNEL_VERSION"}:
            return f"{name}:{code or 'ERROR'}"
    return ""


def should_use_rsync_on_sms_error(err: str) -> bool:
    text = str(err or "").upper()
    markers = [
        "SMS.6504",
        "SMS.6617",
        "SMS.6603",
        "NOT SUPPORT",
        "UNSUPPORTED",
        "INCOMPATIBLE",
    ]
    for marker in markers:
        if marker in text:
            return True
    return False


def collect_target_peer_ips(
    cfg: Config,
    source_fixed_ip: str,
    source_floating_ip: str,
) -> List[str]:
    candidates = [
        source_fixed_ip,
        source_floating_ip,
        cfg.source_private_ip,
        cfg.rsync_source_host,
    ] + list(cfg.extra_peer_ips)
    out = []
    for ip in unique_nonempty(candidates):
        if is_ipv4_prefix(ip):
            out.append(ip)
    return out


def run_cmd_with_optional_password(
    cmd: List[str],
    password: object,
    timeout_sec: int,
) -> Tuple[int, str]:
    if isinstance(password, list) and password:
        return run_interactive_command_with_password(cmd, password, timeout_sec)
    if isinstance(password, str) and password.strip():
        return run_interactive_command_with_password(cmd, password, timeout_sec)
    return run_local_command(cmd, timeout_sec)


def maybe_tail(text: str, max_chars: int = 2000) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


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
    return "%s@%s" % (user, host)


def run_remote_ssh_command(
    host: str,
    port: int,
    user: str,
    password: str,
    remote_cmd: str,
    timeout_sec: int,
    step_name: str,
) -> Dict[str, object]:
    cmd = ssh_base_args(port) + [build_ssh_target(user, host), remote_cmd]
    started = time.time()
    rc, output = run_cmd_with_optional_password(cmd, password, timeout_sec)
    elapsed = int(time.time() - started)
    result = {
        "step": step_name,
        "command": " ".join([shlex.quote(x) for x in cmd[:-1]]) + " <remote-cmd>",
        "duration_sec": elapsed,
        "return_code": rc,
        "output_tail": maybe_tail(output),
    }
    if rc != 0:
        raise RuntimeError(
            "Remote command failed (%s): rc=%d\n%s"
            % (step_name, rc, result["output_tail"])
        )
    return result


def build_rsync_ssh_cmd(port: int) -> str:
    ssh_parts = ssh_base_args(port)
    return " ".join([shlex.quote(x) for x in ssh_parts])


def ensure_local_tools_for_rsync() -> None:
    for binary in ("ssh", "rsync"):
        rc, _ = run_local_command(["bash", "-lc", "command -v %s >/dev/null 2>&1" % binary], 30)
        if rc != 0:
            raise RuntimeError("Required local command not found: %s" % binary)


def ensure_remote_rsync_ready(
    host: str,
    port: int,
    user: str,
    password: str,
    timeout_sec: int,
    role: str,
) -> Dict[str, object]:
    install_cmd = (
        "if ! command -v rsync >/dev/null 2>&1; then "
        "(dnf -y install rsync || yum -y install rsync || "
        "(apt-get update -y && apt-get install -y rsync)); "
        "fi; command -v rsync >/dev/null 2>&1 && rsync --version | head -n 1"
    )
    return run_remote_ssh_command(
        host=host,
        port=port,
        user=user,
        password=password,
        remote_cmd=install_cmd,
        timeout_sec=timeout_sec,
        step_name="ensure_%s_rsync" % role,
    )


def source_path_to_stage_subdir(base_dir: str, source_path: str) -> str:
    raw = str(source_path or "").strip()
    if raw in {"", "/"}:
        return os.path.join(base_dir, "_root_")
    clean = raw.strip("/")
    clean = re.sub(r"[^A-Za-z0-9._/-]", "_", clean)
    clean = clean.replace("/", "__")
    if not clean:
        clean = "_root_"
    return os.path.join(base_dir, clean)


def normalize_rsync_source_path(path: str) -> str:
    value = str(path or "").strip()
    if not value:
        return "/"
    if not value.startswith("/"):
        value = "/" + value
    if not value.endswith("/"):
        value = value + "/"
    return value


def normalize_rsync_target_path(path: str) -> str:
    value = str(path or "").strip()
    if value in {"", "/"}:
        return "/"
    if not value.startswith("/"):
        value = "/" + value
    if not value.endswith("/"):
        value = value + "/"
    return value


def build_rsync_exclude_args(excludes: List[str]) -> List[str]:
    args: List[str] = []
    for item in excludes:
        value = str(item or "").strip()
        if value:
            args.extend(["--exclude", value])
    return args


def run_rsync_transfer_step(
    name: str,
    cmd: List[str],
    password: object,
    timeout_sec: int,
) -> Dict[str, object]:
    started = time.time()
    rc, output = run_cmd_with_optional_password(cmd, password, timeout_sec)
    elapsed = int(time.time() - started)
    result = {
        "step": name,
        "command": " ".join([shlex.quote(x) for x in cmd]),
        "return_code": rc,
        "duration_sec": elapsed,
        "output_tail": maybe_tail(output, 4000),
    }
    if rc in {23, 24}:
        # Live filesystem sync can return partial-transfer/vanished-file codes.
        # Keep these as warnings so incremental/cutover phases can complete.
        result["warning"] = (
            "rsync returned non-fatal code %d (partial/vanished files), continuing" % rc
        )
        return result
    if rc != 0:
        raise RuntimeError(
            "Rsync command failed (%s): rc=%d\n%s"
            % (name, rc, result["output_tail"])
        )
    return result


def run_rsync_phase(
    cfg: Config,
    phase_name: str,
    source_host: str,
    target_host: str,
    source_password: str,
    target_password: str,
    target_ssh_key_path: str,
    delete_mode: bool,
) -> Dict[str, object]:
    phase_started = int(time.time())

    common_args = ["-aHAXx"]
    if delete_mode:
        common_args.append("--delete")
    common_args.extend(shlex_split_extra_args(cfg.rsync_common_args))
    common_args.extend(build_rsync_exclude_args(cfg.rsync_excludes))

    path_results: List[dict] = []
    for raw_source_path in cfg.rsync_source_paths:
        source_path = normalize_rsync_source_path(raw_source_path)
        target_path = normalize_rsync_target_path(raw_source_path)

        # Run rsync on source host directly so this local orchestrator only needs
        # source SSH connectivity (useful when local->target:22 is restricted).
        key_path = str(target_ssh_key_path or "").strip()
        auth_attempts: List[Tuple[List[str], object, str]] = []
        if key_path:
            key_ssh_args = ssh_base_args(cfg.rsync_target_port)
            key_ssh_args.extend(["-i", key_path, "-o", "BatchMode=yes"])
            auth_attempts.append((key_ssh_args, source_password, "ssh_key"))
        password_ssh_args = ssh_base_args(cfg.rsync_target_port)
        auth_attempts.append((password_ssh_args, [source_password, target_password], "password"))

        sync_result: Optional[Dict[str, object]] = None
        last_err: Optional[Exception] = None
        for target_ssh_args, source_cmd_password, auth_mode in auth_attempts:
            remote_rsync_cmd = [
                "rsync",
            ] + common_args + [
                "-e",
                " ".join([shlex.quote(x) for x in target_ssh_args]),
                source_path,
                "%s:%s" % (build_ssh_target(cfg.rsync_target_user, target_host), target_path),
            ]
            source_cmd = ssh_base_args(cfg.rsync_source_port) + [
                build_ssh_target(cfg.rsync_source_user, source_host),
                " ".join([shlex.quote(x) for x in remote_rsync_cmd]),
            ]
            try:
                sync_result = run_rsync_transfer_step(
                    name="%s_sync_%s" % (phase_name, target_path),
                    cmd=source_cmd,
                    password=source_cmd_password,
                    timeout_sec=cfg.rsync_timeout_sec,
                )
                sync_result["auth_mode"] = auth_mode
                break
            except Exception as exc:
                last_err = exc
                err_text = str(exc).lower()
                if auth_mode == "ssh_key" and (
                    "permission denied" in err_text or "publickey" in err_text
                ):
                    print_step(
                        "Rsync key authentication failed for target host, retrying with password auth"
                    )
                    continue
                raise

        if sync_result is None:
            if last_err:
                raise last_err
            raise RuntimeError("Rsync sync step failed without detailed error")

        path_results.append({
            "source_path": source_path,
            "target_path": target_path,
            "sync": sync_result,
        })

    phase_finished = int(time.time())
    return {
        "phase": phase_name,
        "started_at": phase_started,
        "finished_at": phase_finished,
        "duration_sec": phase_finished - phase_started,
        "delete_mode": delete_mode,
        "paths": path_results,
    }


def run_command_on_target_via_source(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_host: str,
    target_password: str,
    target_cmd: str,
    timeout_sec: int,
    step_name: str,
    target_ssh_key_path: str = "",
) -> Dict[str, object]:
    nested = ssh_base_args(cfg.rsync_target_port)
    key_path = str(target_ssh_key_path or "").strip()
    if key_path:
        nested.extend(["-i", key_path, "-o", "BatchMode=yes"])
    nested.extend([
        build_ssh_target(cfg.rsync_target_user, target_host),
        target_cmd,
    ])
    cmd = ssh_base_args(cfg.rsync_source_port) + [
        build_ssh_target(cfg.rsync_source_user, source_host),
        " ".join([shlex.quote(x) for x in nested]),
    ]
    started = time.time()
    cmd_password: object = [source_password, target_password]
    if key_path:
        cmd_password = source_password
    rc, output = run_cmd_with_optional_password(cmd, cmd_password, timeout_sec)
    elapsed = int(time.time() - started)
    result = {
        "step": step_name,
        "command": " ".join([shlex.quote(x) for x in cmd[:-1]]) + " <target-cmd-via-source>",
        "duration_sec": elapsed,
        "return_code": rc,
        "output_tail": maybe_tail(output, 4000),
    }
    if rc != 0:
        raise RuntimeError(
            "Remote command via source failed (%s): rc=%d\n%s"
            % (step_name, rc, result["output_tail"])
        )
    return result


def run_command_on_target_via_source_with_retry(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_host: str,
    target_password: str,
    target_cmd: str,
    timeout_sec: int,
    step_name: str,
    retry_timeout_sec: int,
    retry_interval_sec: int = 8,
    target_ssh_key_path: str = "",
) -> Dict[str, object]:
    started = time.time()
    attempts = 0
    last_err = ""
    while True:
        attempts += 1
        try:
            result = run_command_on_target_via_source(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_password=target_password,
                target_cmd=target_cmd,
                timeout_sec=timeout_sec,
                step_name=step_name,
                target_ssh_key_path=target_ssh_key_path,
            )
            result["attempts"] = attempts
            return result
        except Exception as exc:
            last_err = str(exc)
            err = last_err.lower()
            transient = (
                "connection reset" in err
                or "connection refused" in err
                or "timed out" in err
                or "no route to host" in err
                or "network is unreachable" in err
                or "permission denied" in err
            )
            elapsed = time.time() - started
            if transient and elapsed < max(30, int(retry_timeout_sec)):
                time.sleep(max(2, int(retry_interval_sec)))
                continue
            raise RuntimeError(
                "Remote command via source failed after %d attempt(s) (%s):\n%s"
                % (attempts, step_name, maybe_tail(last_err, 2000))
            )


def run_command_on_target_via_source_tty_password(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_host: str,
    target_password: str,
    target_cmd: str,
    timeout_sec: int,
    step_name: str,
) -> Dict[str, object]:
    nested = [
        "ssh",
        "-tt",
        "-p",
        str(cfg.rsync_target_port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ServerAliveInterval=20",
        "-o",
        "ServerAliveCountMax=6",
        build_ssh_target(cfg.rsync_target_user, target_host),
        target_cmd,
    ]
    cmd = [
        "ssh",
        "-tt",
        "-p",
        str(cfg.rsync_source_port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ServerAliveInterval=20",
        "-o",
        "ServerAliveCountMax=6",
        build_ssh_target(cfg.rsync_source_user, source_host),
        " ".join([shlex.quote(x) for x in nested]),
    ]
    started = time.time()
    rc, output = run_cmd_with_optional_password(cmd, [source_password, target_password], timeout_sec)
    elapsed = int(time.time() - started)
    result = {
        "step": step_name,
        "command": "ssh -tt <source> \"ssh -tt <target> <cmd>\"",
        "duration_sec": elapsed,
        "return_code": rc,
        "output_tail": maybe_tail(output, 4000),
    }
    if rc != 0:
        raise RuntimeError(
            "Remote tty command via source failed (%s): rc=%d\n%s"
            % (step_name, rc, result["output_tail"])
        )
    return result


def prepare_source_to_target_ssh_key(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_bootstrap_host: str,
    target_private_host: str,
    target_password: str,
    timeout_sec: int,
) -> Dict[str, object]:
    if not env_default_bool("CONFIRM_TARGET_SSH_BOOTSTRAP", False):
        raise RuntimeError(
            "Target password-based SSH auth failed and recovery requires temporarily "
            "injecting a migration-only SSH key into the target and enabling "
            "PasswordAuthentication/PermitRootLogin on it. This is destructive enough to "
            "need an explicit opt-in: set CONFIRM_TARGET_SSH_BOOTSTRAP=yes to proceed. "
            "The change is reverted automatically (key removed, sshd_config restored) once "
            "the migration finishes; see cleanup_target_ssh_bootstrap()."
        )

    key_path = "/root/.ssh/mgc_target_rsync_key"
    source_key_cmd = (
        "set -e; "
        "mkdir -p /root/.ssh; chmod 700 /root/.ssh; "
        "if [ ! -f {key} ]; then "
        "ssh-keygen -t rsa -b 2048 -N '' -f {key} >/dev/null 2>&1; "
        "fi; "
        "chmod 600 {key}; chmod 644 {key}.pub; "
        "cat {key}.pub"
    ).format(key=shlex.quote(key_path))
    source_rsp = run_remote_ssh_command(
        host=source_host,
        port=cfg.rsync_source_port,
        user=cfg.rsync_source_user,
        password=source_password,
        remote_cmd=source_key_cmd,
        timeout_sec=timeout_sec,
        step_name="prepare_source_target_ssh_keypair",
    )

    source_pubkey = ""
    for line in str(source_rsp.get("output_tail") or "").splitlines():
        val = line.strip()
        if val.startswith("ssh-rsa ") or val.startswith("ssh-ed25519 "):
            source_pubkey = val
    if not source_pubkey:
        raise RuntimeError("Failed to read source public key for target key bootstrap")

    # Snapshot the target's current PasswordAuthentication/PermitRootLogin lines (and
    # whether the migration key is already present) before loosening sshd_config, so
    # cleanup_target_ssh_bootstrap() can restore the original state after migration.
    inject_key_cmd = (
        "set -e; "
        "mkdir -p /root/.ssh; chmod 700 /root/.ssh; "
        "touch /root/.ssh/authorized_keys; chmod 600 /root/.ssh/authorized_keys; "
        "KEY={pub}; "
        "ALREADY=0; grep -qxF \"$KEY\" /root/.ssh/authorized_keys && ALREADY=1; "
        "grep -qxF \"$KEY\" /root/.ssh/authorized_keys || echo \"$KEY\" >> /root/.ssh/authorized_keys; "
        "ORIG_PWAUTH=$(grep -i '^PasswordAuthentication[[:space:]]' /etc/ssh/sshd_config | tail -n1); "
        "ORIG_ROOTLOGIN=$(grep -i '^PermitRootLogin[[:space:]]' /etc/ssh/sshd_config | tail -n1); "
        "sed -ri 's/^#?PasswordAuthentication\\s+.*/PasswordAuthentication yes/' /etc/ssh/sshd_config || true; "
        "grep -q '^PasswordAuthentication\\s\\+yes' /etc/ssh/sshd_config || echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config; "
        "sed -ri 's/^#?PermitRootLogin\\s+.*/PermitRootLogin yes/' /etc/ssh/sshd_config || true; "
        "grep -q '^PermitRootLogin\\s\\+yes' /etc/ssh/sshd_config || echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config; "
        "systemctl restart sshd >/dev/null 2>&1 || systemctl restart ssh >/dev/null 2>&1 || true; "
        "echo \"MGC_BOOTSTRAP_STATE $ALREADY|$ORIG_PWAUTH|$ORIG_ROOTLOGIN\""
    ).format(pub=shlex.quote(source_pubkey))
    target_rsp = {}
    inject_mode = "direct"
    try:
        target_rsp = run_remote_ssh_command(
            host=target_bootstrap_host,
            port=cfg.rsync_target_port,
            user=cfg.rsync_target_user,
            password=target_password,
            remote_cmd=inject_key_cmd,
            timeout_sec=timeout_sec,
            step_name="inject_source_pubkey_to_target",
        )
    except Exception as direct_exc:
        if not str(target_private_host or "").strip():
            raise
        inject_mode = "via_source_tty"
        target_rsp = run_command_on_target_via_source_tty_password(
            cfg=cfg,
            source_host=source_host,
            source_password=source_password,
            target_host=target_private_host,
            target_password=target_password,
            target_cmd=inject_key_cmd,
            timeout_sec=timeout_sec,
            step_name="inject_source_pubkey_to_target_via_source_tty",
        )
        target_rsp["direct_inject_error"] = str(direct_exc)

    already_present = False
    orig_password_authentication = ""
    orig_permit_root_login = ""
    for line in str(target_rsp.get("output_tail") or "").splitlines():
        if line.strip().startswith("MGC_BOOTSTRAP_STATE "):
            payload = line.strip()[len("MGC_BOOTSTRAP_STATE "):]
            parts = payload.split("|", 2)
            if len(parts) == 3:
                already_present = parts[0].strip() == "1"
                orig_password_authentication = parts[1].strip()
                orig_permit_root_login = parts[2].strip()

    return {
        "source_key_prepare": source_rsp,
        "target_key_inject": target_rsp,
        "target_ssh_key_path": key_path,
        "target_bootstrap_host": target_bootstrap_host,
        "target_private_host": target_private_host,
        "inject_mode": inject_mode,
        "source_pubkey": source_pubkey,
        "authorized_key_already_present": already_present,
        "orig_password_authentication": orig_password_authentication,
        "orig_permit_root_login": orig_permit_root_login,
    }


def cleanup_target_ssh_bootstrap(
    cfg: Config,
    bootstrap_info: Dict[str, object],
    target_password: str,
    timeout_sec: int,
) -> Dict[str, object]:
    """Best-effort revert of prepare_source_to_target_ssh_key(): remove the
    migration-only key this run added (if it wasn't already present) and restore the
    target's original PasswordAuthentication/PermitRootLogin lines. Never raises -
    migration success must not depend on cleanup succeeding, but we always try so the
    target isn't left in a more permissive state than before the migration."""
    if env_default_bool("SKIP_TARGET_SSH_BOOTSTRAP_CLEANUP", False):
        return {"skipped": True, "reason": "SKIP_TARGET_SSH_BOOTSTRAP_CLEANUP=yes"}

    source_pubkey = str(bootstrap_info.get("source_pubkey") or "").strip()
    target_bootstrap_host = str(bootstrap_info.get("target_bootstrap_host") or "").strip()
    if not source_pubkey or not target_bootstrap_host:
        return {"skipped": True, "reason": "no bootstrap record to revert"}

    already_present = bool(bootstrap_info.get("authorized_key_already_present"))
    orig_pwauth = str(bootstrap_info.get("orig_password_authentication") or "").strip()
    orig_rootlogin = str(bootstrap_info.get("orig_permit_root_login") or "").strip()

    remove_key_part = ""
    if not already_present:
        remove_key_part = (
            "KEY={pub}; "
            "grep -vxF \"$KEY\" /root/.ssh/authorized_keys > /root/.ssh/authorized_keys.mgc_tmp 2>/dev/null "
            "&& mv /root/.ssh/authorized_keys.mgc_tmp /root/.ssh/authorized_keys || true; "
        ).format(pub=shlex.quote(source_pubkey))

    restore_pwauth = "sed -ri '/^PasswordAuthentication[[:space:]]/d' /etc/ssh/sshd_config; "
    if orig_pwauth:
        restore_pwauth += "echo {line} >> /etc/ssh/sshd_config; ".format(line=shlex.quote(orig_pwauth))
    restore_rootlogin = "sed -ri '/^PermitRootLogin[[:space:]]/d' /etc/ssh/sshd_config; "
    if orig_rootlogin:
        restore_rootlogin += "echo {line} >> /etc/ssh/sshd_config; ".format(line=shlex.quote(orig_rootlogin))

    cleanup_cmd = (
        "set +e; "
        + remove_key_part
        + restore_pwauth
        + restore_rootlogin
        + "systemctl restart sshd >/dev/null 2>&1 || systemctl restart ssh >/dev/null 2>&1 || true; "
        "true"
    )
    try:
        return run_remote_ssh_command(
            host=target_bootstrap_host,
            port=cfg.rsync_target_port,
            user=cfg.rsync_target_user,
            password=target_password,
            remote_cmd=cleanup_cmd,
            timeout_sec=timeout_sec,
            step_name="cleanup_target_ssh_bootstrap",
        )
    except Exception as cleanup_exc:
        return {"error": str(cleanup_exc)}


def wait_for_target_port_via_source(
    cfg: Config,
    source_host: str,
    source_password: str,
    target_host: str,
    target_port: int,
    timeout_sec: int,
    interval_sec: int = 8,
) -> Dict[str, object]:
    probe_cmd = (
        "timeout 6 bash -lc '</dev/tcp/%s/%d' >/dev/null 2>&1"
        % (target_host, int(target_port))
    )
    started = time.time()
    last_output = ""
    attempts = 0
    while True:
        attempts += 1
        cmd = ssh_base_args(cfg.rsync_source_port) + [
            build_ssh_target(cfg.rsync_source_user, source_host),
            probe_cmd,
        ]
        rc, output = run_cmd_with_optional_password(cmd, source_password, max(20, interval_sec + 10))
        last_output = output
        if rc == 0:
            return {
                "step": "wait_target_ssh_via_source",
                "target_host": target_host,
                "target_port": int(target_port),
                "attempts": attempts,
                "duration_sec": int(time.time() - started),
                "ready": True,
            }
        if time.time() - started > timeout_sec:
            raise RuntimeError(
                "Target port not ready via source after %ds (host=%s port=%d)\n%s"
                % (timeout_sec, target_host, int(target_port), maybe_tail(last_output, 2000))
            )
        time.sleep(max(2, int(interval_sec)))


def run_rsync_migration(
    client: HcApiClient,
    cfg: Config,
    target_project_id: str,
    target_server_id: str,
    target_vpc_id: str,
    target_fixed_ip: str,
    target_floating_ip: str,
) -> Dict[str, object]:
    bootstrap_state: Dict[str, object] = {}
    result = None
    try:
        result = _run_rsync_migration_inner(
            client=client,
            cfg=cfg,
            target_project_id=target_project_id,
            target_server_id=target_server_id,
            target_vpc_id=target_vpc_id,
            target_fixed_ip=target_fixed_ip,
            target_floating_ip=target_floating_ip,
            bootstrap_state=bootstrap_state,
        )
        return result
    finally:
        if bootstrap_state.get("bootstrap_info"):
            cleanup_result = cleanup_target_ssh_bootstrap(
                cfg=cfg,
                bootstrap_info=bootstrap_state["bootstrap_info"],
                target_password=str(bootstrap_state.get("target_password") or cfg.target_admin_password),
                timeout_sec=min(300, cfg.rsync_timeout_sec),
            )
            if isinstance(result, dict):
                result["ssh_bootstrap_cleanup"] = cleanup_result


def _run_rsync_migration_inner(
    client: HcApiClient,
    cfg: Config,
    target_project_id: str,
    target_server_id: str,
    target_vpc_id: str,
    target_fixed_ip: str,
    target_floating_ip: str,
    bootstrap_state: Dict[str, object],
) -> Dict[str, object]:
    ensure_local_tools_for_rsync()

    source_host = str(cfg.rsync_source_host or "").strip()
    if not source_host:
        raise RuntimeError("RSYNC_SOURCE_HOST is required for rsync fallback")

    target_host = str(cfg.rsync_target_host or "").strip()
    target_host_source = "rsync_target_host"
    vpn_ready_ip = ""
    source_password = str(cfg.rsync_source_password or "").strip()
    target_password = str(cfg.rsync_target_password or "").strip()
    if not target_password:
        target_password = cfg.target_admin_password
    target_ssh_key_path = ""

    vpn_bridge = {}
    if cfg.enable_vpn_bridge:
        print_step("Ensuring VPN bridge connectivity (source <-> codex <-> target VPC)")
        vpn_bridge = ensure_vpn_bridge_connectivity(
            client=client,
            cfg=cfg,
            target_project_id=target_project_id,
            target_vpc_id=target_vpc_id,
            source_host=source_host,
            source_password=source_password,
        )

    if cfg.enable_target_vpn_client:
        wait_timeout = min(900, max(120, int(cfg.rsync_timeout_sec / 4)))
        print_step(
            "Waiting target OpenVPN client '%s' to connect (timeout=%ss)"
            % (cfg.vpn_client_common_name, wait_timeout)
        )
        vpn_ready_ip = wait_for_openvpn_client_virtual_ip(cfg.vpn_client_common_name, timeout_sec=wait_timeout)
        if vpn_ready_ip:
            print_step(f"Target OpenVPN client is online: {vpn_ready_ip}")
        else:
            raise RuntimeError(
                "Target OpenVPN client '%s' did not connect in time. "
                "Check cloud-init and OpenVPN server log."
                % cfg.vpn_client_common_name
            )

    if not target_host:
        if vpn_ready_ip:
            target_host = vpn_ready_ip
            target_host_source = "vpn_client_ip"
        elif cfg.enable_vpn_bridge and target_fixed_ip:
            target_host = str(target_fixed_ip).strip()
            target_host_source = "target_fixed_ip_vpn_bridge"
        else:
            target_host = str(target_floating_ip or "").strip() or str(target_fixed_ip or "").strip()
            target_host_source = "target_floating_or_fixed_ip"
    if not target_host:
        raise RuntimeError("Cannot determine target SSH host for rsync fallback")

    artifact = {
        "method": "rsync",
        "execution_mode": "source_to_target",
        "source_host": source_host,
        "source_port": cfg.rsync_source_port,
        "target_host": target_host,
        "target_host_source": target_host_source,
        "target_vpn_ip_detected": vpn_ready_ip,
        "vpn_bridge": vpn_bridge,
        "target_port": cfg.rsync_target_port,
        "incremental_rounds": cfg.rsync_incremental_rounds,
        "phases": [],
    }

    artifact["source_rsync_check"] = ensure_remote_rsync_ready(
        host=source_host,
        port=cfg.rsync_source_port,
        user=cfg.rsync_source_user,
        password=source_password,
        timeout_sec=cfg.rsync_timeout_sec,
        role="source",
    )
    probe_timeout = min(900, max(120, int(cfg.rsync_timeout_sec / 12)))
    artifact["target_ssh_probe_via_source"] = wait_for_target_port_via_source(
        cfg=cfg,
        source_host=source_host,
        source_password=source_password,
        target_host=target_host,
        target_port=cfg.rsync_target_port,
        timeout_sec=probe_timeout,
    )
    install_cmd = (
        "if ! command -v rsync >/dev/null 2>&1; then "
        "printf 'nameserver 8.8.8.8\\nnameserver 1.1.1.1\\n' >/etc/resolv.conf 2>/dev/null || true; "
        "(dnf --disablerepo='epel*' -y install rsync || yum -y install rsync || "
        "(apt-get update -y && apt-get install -y rsync)); "
        "fi; command -v rsync >/dev/null 2>&1 && rsync --version | head -n 1"
    )
    try:
        artifact["target_rsync_check"] = run_command_on_target_via_source(
            cfg=cfg,
            source_host=source_host,
            source_password=source_password,
            target_host=target_host,
            target_password=target_password,
            target_cmd=install_cmd,
            timeout_sec=cfg.rsync_timeout_sec,
            step_name="ensure_target_rsync_via_source",
        )
    except Exception as exc:
        err = str(exc).lower()
        recovered_without_reset = False
        transient_ssh_errors = (
            "connection reset",
            "kex_exchange_identification",
            "ssh_exchange_identification",
            "connection closed",
            "broken pipe",
        )
        if any(token in err for token in transient_ssh_errors):
            artifact["target_ssh_probe_via_source_after_transient"] = wait_for_target_port_via_source(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_port=cfg.rsync_target_port,
                timeout_sec=probe_timeout,
            )
            artifact["target_rsync_check"] = run_command_on_target_via_source_with_retry(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_password=target_password,
                target_cmd=install_cmd,
                timeout_sec=cfg.rsync_timeout_sec,
                step_name="ensure_target_rsync_via_source_transient_retry",
                retry_timeout_sec=min(1200, max(180, int(cfg.rsync_timeout_sec / 6))),
                retry_interval_sec=10,
                target_ssh_key_path=target_ssh_key_path,
            )
            err = ""
        if "permission denied" in err:
            print_step(
                "Target SSH authentication denied, waiting for cloud-init and retrying before password reset"
            )
            try:
                artifact["target_rsync_check_after_auth_wait"] = run_command_on_target_via_source_with_retry(
                    cfg=cfg,
                    source_host=source_host,
                    source_password=source_password,
                    target_host=target_host,
                    target_password=target_password,
                    target_cmd=install_cmd,
                    timeout_sec=cfg.rsync_timeout_sec,
                    step_name="ensure_target_rsync_via_source_auth_wait_retry",
                    retry_timeout_sec=min(1200, max(240, int(cfg.rsync_timeout_sec / 6))),
                    retry_interval_sec=10,
                    target_ssh_key_path=target_ssh_key_path,
                )
                artifact["target_rsync_check"] = artifact["target_rsync_check_after_auth_wait"]
                err = ""
                recovered_without_reset = True
            except Exception as auth_wait_exc:
                err = str(auth_wait_exc).lower()

        if recovered_without_reset:
            pass
        elif "permission denied" not in err:
            raise
        else:
            if not target_server_id:
                raise
            print_step(
                "Target SSH authentication failed, resetting target password and rebooting target ECS"
            )
            client.request_json(
                "PUT",
                f"https://ecs.{cfg.target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/{target_server_id}/os-reset-password",
                body={"reset-password": {"new_password": target_password}},
            )
            try:
                reboot_rsp = client.request_json(
                    "POST",
                    f"https://ecs.{cfg.target_region}.myhuaweicloud.com/v1/{target_project_id}/cloudservers/action",
                    body={"reboot": {"type": "HARD", "servers": [{"id": target_server_id}]}},
                )
            except Exception as reboot_exc:
                reboot_err = str(reboot_exc).lower()
                if "ecs.0018" not in reboot_err and "status" not in reboot_err:
                    raise
                reboot_rsp = {"warning": str(reboot_exc)}

            wait_server_status(
                cfg=cfg,
                region=cfg.target_region,
                project_id=target_project_id,
                server_id=target_server_id,
                expected_status="ACTIVE",
                timeout_sec=min(1800, max(300, int(cfg.rsync_timeout_sec / 2))),
                interval_sec=10,
            )
            artifact["target_auth_recovery"] = {
                "reset_password": True,
                "reboot_response": reboot_rsp,
            }
            artifact["target_ssh_probe_via_source_before_key_bootstrap"] = wait_for_target_port_via_source(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_port=cfg.rsync_target_port,
                timeout_sec=probe_timeout,
            )
            target_bootstrap_host = str(target_floating_ip or "").strip() or str(target_host or "").strip()
            if not target_bootstrap_host:
                raise RuntimeError("Cannot determine target bootstrap host for SSH key injection")
            try:
                artifact["target_key_bootstrap"] = prepare_source_to_target_ssh_key(
                    cfg=cfg,
                    source_host=source_host,
                    source_password=source_password,
                    target_bootstrap_host=target_bootstrap_host,
                    target_private_host=target_host,
                    target_password=target_password,
                    timeout_sec=min(300, cfg.rsync_timeout_sec),
                )
            except Exception as key_exc:
                key_err = str(key_exc).lower()
                transient_key_err = (
                    "connection refused" in key_err
                    or "timed out" in key_err
                    or "connection reset" in key_err
                    or "no route to host" in key_err
                    or "network is unreachable" in key_err
                )
                if not transient_key_err:
                    raise
                artifact["target_ssh_probe_via_source_before_key_bootstrap_retry"] = wait_for_target_port_via_source(
                    cfg=cfg,
                    source_host=source_host,
                    source_password=source_password,
                    target_host=target_host,
                    target_port=cfg.rsync_target_port,
                    timeout_sec=probe_timeout,
                )
                artifact["target_key_bootstrap"] = prepare_source_to_target_ssh_key(
                    cfg=cfg,
                    source_host=source_host,
                    source_password=source_password,
                    target_bootstrap_host=target_bootstrap_host,
                    target_private_host=target_host,
                    target_password=target_password,
                    timeout_sec=min(300, cfg.rsync_timeout_sec),
                )
            target_ssh_key_path = str(artifact["target_key_bootstrap"].get("target_ssh_key_path") or "").strip()
            bootstrap_state["bootstrap_info"] = artifact["target_key_bootstrap"]
            bootstrap_state["target_password"] = target_password
            artifact["target_ssh_probe_via_source_after_recovery"] = wait_for_target_port_via_source(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_port=cfg.rsync_target_port,
                timeout_sec=probe_timeout,
            )
            artifact["target_rsync_check"] = run_command_on_target_via_source_with_retry(
                cfg=cfg,
                source_host=source_host,
                source_password=source_password,
                target_host=target_host,
                target_password=target_password,
                target_cmd=install_cmd,
                timeout_sec=cfg.rsync_timeout_sec,
                step_name="ensure_target_rsync_via_source_after_auth_recovery",
                retry_timeout_sec=min(1200, max(180, int(cfg.rsync_timeout_sec / 6))),
                retry_interval_sec=10,
                target_ssh_key_path=target_ssh_key_path,
            )

    artifact["phases"].append(
        run_rsync_phase(
            cfg=cfg,
            phase_name="full_sync",
            source_host=source_host,
            target_host=target_host,
            source_password=source_password,
            target_password=target_password,
            target_ssh_key_path=target_ssh_key_path,
            delete_mode=True,
        )
    )

    rounds = max(0, int(cfg.rsync_incremental_rounds))
    if rounds == 0:
        artifact["state"] = "FULL_SYNCED"
        return artifact
    for idx in range(rounds):
        artifact["phases"].append(
            run_rsync_phase(
                cfg=cfg,
                phase_name="incremental_sync_%d" % (idx + 1),
                source_host=source_host,
                target_host=target_host,
                source_password=source_password,
                target_password=target_password,
                target_ssh_key_path=target_ssh_key_path,
                delete_mode=True,
            )
        )

    if cfg.rsync_cutover_stop_cmd:
        artifact["cutover_stop"] = run_remote_ssh_command(
            host=source_host,
            port=cfg.rsync_source_port,
            user=cfg.rsync_source_user,
            password=source_password,
            remote_cmd=cfg.rsync_cutover_stop_cmd,
            timeout_sec=cfg.rsync_timeout_sec,
            step_name="cutover_stop_source",
        )

    artifact["phases"].append(
        run_rsync_phase(
            cfg=cfg,
            phase_name="cutover_sync",
            source_host=source_host,
            target_host=target_host,
            source_password=source_password,
            target_password=target_password,
            target_ssh_key_path=target_ssh_key_path,
            delete_mode=True,
        )
    )

    if cfg.rsync_cutover_start_cmd:
        artifact["cutover_start"] = run_remote_ssh_command(
            host=source_host,
            port=cfg.rsync_source_port,
            user=cfg.rsync_source_user,
            password=source_password,
            remote_cmd=cfg.rsync_cutover_start_cmd,
            timeout_sec=cfg.rsync_timeout_sec,
            step_name="cutover_start_source",
        )

    if cfg.rsync_target_finalize_cmd:
        artifact["target_finalize"] = run_command_on_target_via_source(
            cfg=cfg,
            source_host=source_host,
            source_password=source_password,
            target_host=target_host,
            target_password=target_password,
            target_cmd=cfg.rsync_target_finalize_cmd,
            timeout_sec=cfg.rsync_timeout_sec,
            step_name="target_finalize",
        )

    artifact["state"] = "CUTOVER_SYNCED"
    return artifact


def load_config() -> Config:
    return Config(
        ak=env_required("HC_AK"),
        sk=env_required("HC_SK"),
        source_server_id=env_required("SOURCE_SERVER_ID"),
        source_region=env_default("SOURCE_REGION", "la-north-2"),
        target_region=env_default("TARGET_REGION", "la-south-2"),
        target_region_name=env_default("TARGET_REGION_NAME", "LA-Santiago"),
        target_vpc_name=env_default("TARGET_VPC_NAME", "vpc-migration"),
        target_vpc_cidr=env_default("TARGET_VPC_CIDR", "10.250.0.0/16"),
        target_subnet_cidr=env_default("TARGET_SUBNET_CIDR", "10.250.1.0/24"),
        target_image_id=env_required("TARGET_IMAGE_ID"),
        target_server_name=env_default("TARGET_SERVER_NAME", "mx2-to-santiago-migrated"),
        target_flavor_id=env_default("TARGET_FLAVOR_ID", ""),
        target_admin_password=env_required("TARGET_ADMIN_PASSWORD"),
        eip_bandwidth_mbps=int(env_default("EIP_BANDWIDTH_MBPS", "5")),
        root_volume_type=env_default("ROOT_VOLUME_TYPE", "SSD"),
        data_volume_type=env_default("DATA_VOLUME_TYPE", "SSD"),
        sms_endpoint=env_default("SMS_ENDPOINT", "https://sms.ap-southeast-3.myhuaweicloud.com").rstrip("/"),
        preferred_migration_method=normalize_migration_method(env_default("PREFERRED_MIGRATION_METHOD", "sms")),
        enable_rsync_fallback=env_default_bool("ENABLE_RSYNC_FALLBACK", True),
        source_private_ip=env_default("SOURCE_PRIVATE_IP", ""),
        source_network_cidr=env_default("SOURCE_NETWORK_CIDR", ""),
        extra_peer_ips=env_csv_list("EXTRA_PEER_IPS", []),
        rsync_source_host=env_default("RSYNC_SOURCE_HOST", "10.8.0.2"),
        rsync_source_port=env_default_int("RSYNC_SOURCE_PORT", 2222),
        rsync_source_user=env_default("RSYNC_SOURCE_USER", "root"),
        rsync_source_password=env_default("RSYNC_SOURCE_PASSWORD", ""),
        rsync_target_host=env_default("RSYNC_TARGET_HOST", ""),
        rsync_target_port=env_default_int("RSYNC_TARGET_PORT", 22),
        rsync_target_user=env_default("RSYNC_TARGET_USER", "root"),
        rsync_target_password=env_default("RSYNC_TARGET_PASSWORD", ""),
        rsync_source_paths=env_csv_list("RSYNC_SOURCE_PATHS", ["/"]),
        rsync_staging_dir=env_default("RSYNC_STAGING_DIR", "/tmp/mgc-rsync-stage"),
        rsync_incremental_rounds=env_default_int("RSYNC_INCREMENTAL_ROUNDS", 1),
        rsync_timeout_sec=env_default_int("RSYNC_TIMEOUT_SEC", 7200),
        rsync_common_args=env_default("RSYNC_COMMON_ARGS", "--numeric-ids --info=stats2,progress2 --partial"),
        rsync_excludes=env_csv_list(
            "RSYNC_EXCLUDES",
            [
                "/dev/*",
                "/proc/*",
                "/sys/*",
                "/tmp/*",
                "/run/*",
                "/mnt/*",
                "/media/*",
                "/lost+found",
                "/swapfile",
                "/var/tmp/*",
                "/var/run/*",
                "/boot/efi/*",
                "/etc/fstab",
            ],
        ),
        rsync_cutover_stop_cmd=env_default("RSYNC_CUTOVER_STOP_CMD", ""),
        rsync_cutover_start_cmd=env_default("RSYNC_CUTOVER_START_CMD", ""),
        rsync_target_finalize_cmd=env_default("RSYNC_TARGET_FINALIZE_CMD", ""),
        enable_vpn_bridge=env_default_bool("ENABLE_VPN_BRIDGE", True),
        local_vpc_id=env_default("LOCAL_VPC_ID", ""),
        enable_target_vpn_client=env_default_bool("ENABLE_TARGET_VPN_CLIENT", True),
        vpn_server_public_ip=env_default("VPN_SERVER_PUBLIC_IP", ""),
        vpn_server_port=env_default_int("VPN_SERVER_PORT", 1194),
        vpn_client_common_name=env_default("VPN_CLIENT_COMMON_NAME", "site-mx2-target"),
        vpn_client_static_ip=env_default("VPN_CLIENT_STATIC_IP", "10.8.0.10"),
        result_path=env_default("RESULT_PATH", "./out/migration_result.json"),
    )


def main() -> int:
    cfg = load_config()
    client = HcApiClient(cfg.ak, cfg.sk)

    print_step("Resolving project IDs by region")
    source_project_id, source_project_name = get_region_project(client, cfg.source_region)
    target_project_id, target_project_name = get_region_project(client, cfg.target_region)

    source_ecs = get_source_ecs_detail(client, cfg.source_region, source_project_id, cfg.source_server_id)
    source_ecs_name = str((source_ecs or {}).get("name") or "")
    source_ecs_fixed_ip = get_server_primary_fixed_ip(source_ecs)
    source_ecs_floating_ip = get_server_primary_floating_ip(source_ecs)
    aws_source_profile = fetch_aws_source_security_profile(
        source_server_id=cfg.source_server_id,
        access_key=env_default("AWS_SOURCE_ACCESS_KEY", ""),
        secret_key=env_default("AWS_SOURCE_SECRET_KEY", ""),
        region_hint=env_default("AWS_SOURCE_REGION", ""),
        session_token=env_default("AWS_SOURCE_SESSION_TOKEN", ""),
    )
    if aws_source_profile:
        print_step(
            "Loaded AWS source instance profile: "
            f"instance={aws_source_profile.get('instance_id')} "
            f"region={aws_source_profile.get('region')} "
            f"sg_count={len(aws_source_profile.get('security_group_ids') or [])} "
            f"rule_count={int(aws_source_profile.get('rules_total') or 0)}"
        )
        if not source_ecs_fixed_ip:
            source_ecs_fixed_ip = str(aws_source_profile.get("private_ip") or "").strip()
        if not source_ecs_floating_ip:
            source_ecs_floating_ip = str(aws_source_profile.get("public_ip") or "").strip()

    print_step("Accepting SMS privacy agreements")
    client.request_json("POST", f"{cfg.sms_endpoint}/v3/privacy-agreements", body={})

    source_lookup_ip = source_ecs_fixed_ip or cfg.source_private_ip

    print_step("Querying source server from SMS")
    source_server = get_sms_source_server(
        client,
        cfg.sms_endpoint,
        cfg.source_server_id,
        fallback_name=source_ecs_name,
        fallback_ip=source_lookup_ip,
    )
    source_sms_id = source_server.get("id")
    if not source_sms_id:
        raise RuntimeError("SMS source object does not include 'id'.")
    source_server = get_sms_source_detail(client, cfg.sms_endpoint, source_sms_id)
    if not source_ecs_fixed_ip:
        source_ecs_fixed_ip = str(source_server.get("ip") or "").strip() or source_lookup_ip
    if not source_ecs_fixed_ip and cfg.source_private_ip:
        source_ecs_fixed_ip = cfg.source_private_ip

    source_precheck_issues = get_source_precheck_issues(source_server)
    sms_incompatible_reason = detect_sms_incompatible_reason(source_server)
    precheck_path = build_out_path(cfg.result_path, "precheck_source_checks.json")
    write_json_file(
        precheck_path,
        {
            "source_sms_server_id": source_sms_id,
            "source_server_id_input": cfg.source_server_id,
            "sms_incompatible_reason": sms_incompatible_reason,
            "issues": source_precheck_issues,
            "generated_at": int(time.time()),
        },
    )

    print_step("Prechecking and cleaning historical source-bound SMS tasks")
    precheck_task_cleanup_path = build_out_path(cfg.result_path, "precheck_task_cleanup.json")
    task_cleanup_result = cleanup_terminal_tasks_for_source(client, cfg.sms_endpoint, source_sms_id)
    write_json_file(precheck_task_cleanup_path, task_cleanup_result)
    active_tasks = task_cleanup_result.get("active_tasks") or []
    if active_tasks:
        raise RuntimeError(
            "Existing non-terminal SMS task(s) still bind this source server: "
            f"{json.dumps(active_tasks, ensure_ascii=False)}"
        )
    deleted_count = int(task_cleanup_result.get("deleted_count") or 0)
    if deleted_count > 0:
        print_step(f"Deleted {deleted_count} historical terminal SMS task(s) for this source")

    planned_migration_method = cfg.preferred_migration_method
    planned_fallback_reason = ""
    if planned_migration_method == "sms" and sms_incompatible_reason and cfg.enable_rsync_fallback:
        planned_migration_method = "rsync"
        planned_fallback_reason = "sms_precheck_incompatible:%s" % sms_incompatible_reason

    print_step("Finding target VPC/subnet")
    target_vpc_id, target_subnet_id = get_target_vpc_and_subnet(
        client,
        cfg.target_region,
        target_project_id,
        cfg.target_vpc_name,
        cfg.target_vpc_cidr,
        cfg.target_subnet_cidr,
    )

    print_step("Creating target ECS in target region with EIP")
    target_vm_id = create_target_server(
        client=client,
        cfg=cfg,
        source_project_id=source_project_id,
        target_project_id=target_project_id,
        source_server=source_server,
        vpc_id=target_vpc_id,
        subnet_id=target_subnet_id,
        allow_reuse=True,
    )

    print_step("Ensuring security groups allow source/target connectivity")
    target_peer_ips = collect_target_peer_ips(cfg, source_ecs_fixed_ip, source_ecs_floating_ip)
    sg_result = ensure_source_target_security_groups(
        client=client,
        source_region=cfg.source_region,
        source_project_id=source_project_id,
        source_server=source_ecs,
        target_region=cfg.target_region,
        target_project_id=target_project_id,
        target_vpc_id=target_vpc_id,
        target_vm_id=target_vm_id,
        source_fixed_ip=source_ecs_fixed_ip,
        source_floating_ip=source_ecs_floating_ip,
        additional_target_peer_ips=target_peer_ips,
        aws_source_profile=aws_source_profile,
    )
    recreate_cfg = cfg
    recreate_image_id = ""
    recreate_flavor_id = ""
    try:
        recreate_image_id, recreate_flavor_id = get_server_image_and_flavor(
            client=client,
            region=cfg.target_region,
            project_id=target_project_id,
            server_id=target_vm_id,
        )
        if recreate_image_id:
            recreate_cfg = recreate_cfg._replace(target_image_id=recreate_image_id)
        if recreate_image_id or recreate_flavor_id:
            print_step(
                "Preserving target OS baseline for recreate: image_id='%s', flavor_id='%s'"
                % (recreate_image_id or cfg.target_image_id, recreate_flavor_id or cfg.target_flavor_id)
            )
    except Exception as exc:
        print_step(
            "Cannot read current target image/flavor for recreate baseline, using configured values: %s"
            % str(exc)[:160]
        )

    migration_method = planned_migration_method
    migration_fallback_reason = planned_fallback_reason

    if cfg.preferred_migration_method == "sms" and sms_incompatible_reason and cfg.enable_rsync_fallback:
        print_step(
            "SMS precheck indicates incompatibility (%s), fallback to rsync"
            % sms_incompatible_reason
        )
    elif cfg.preferred_migration_method == "sms" and sms_incompatible_reason:
        print_step(
            "SMS precheck indicates incompatibility (%s), but rsync fallback is disabled"
            % sms_incompatible_reason
        )

    migproject_id = ""
    task_id = ""
    task_state = ""
    rsync_result: Optional[Dict[str, object]] = None
    rsync_result_file = ""

    if migration_method == "sms":
        print_step("Creating SMS migration project")
        migproject_id = create_sms_migproject(client, cfg)

        print_step("Creating SMS migration task")
        try:
            task_id = create_sms_task(
                client=client,
                cfg=cfg,
                source_sms_id=source_sms_id,
                source_server=source_server,
                target_vm_id=target_vm_id,
                target_project_id=target_project_id,
                target_project_name=target_project_name,
            )
        except Exception as exc:
            if "SMS.7605" not in str(exc):
                raise
            print_step(
                "Task creation got SMS.7605, creating a fresh target ECS with EIP and retrying once"
            )
            target_vm_id = create_target_server(
                client=client,
                cfg=recreate_cfg,
                source_project_id=source_project_id,
                target_project_id=target_project_id,
                source_server=source_server,
                vpc_id=target_vpc_id,
                subnet_id=target_subnet_id,
                allow_reuse=False,
            )
            print_step("Re-checking security groups for the fresh target ECS")
            sg_result = ensure_source_target_security_groups(
                client=client,
                source_region=cfg.source_region,
                source_project_id=source_project_id,
                source_server=source_ecs,
                target_region=cfg.target_region,
                target_project_id=target_project_id,
                target_vpc_id=target_vpc_id,
                target_vm_id=target_vm_id,
                source_fixed_ip=source_ecs_fixed_ip,
                source_floating_ip=source_ecs_floating_ip,
                additional_target_peer_ips=target_peer_ips,
                aws_source_profile=aws_source_profile,
            )
            task_id = create_sms_task(
                client=client,
                cfg=cfg,
                source_sms_id=source_sms_id,
                source_server=source_server,
                target_vm_id=target_vm_id,
                target_project_id=target_project_id,
                target_project_name=target_project_name,
            )

        try:
            print_step("Starting SMS migration task")
            start_sms_task(client, cfg.sms_endpoint, task_id)
            task_state = get_sms_task_state(client, cfg.sms_endpoint, task_id)
        except Exception as exc:
            if cfg.enable_rsync_fallback and should_use_rsync_on_sms_error(str(exc)):
                migration_method = "rsync"
                migration_fallback_reason = "sms_runtime_failure:%s" % str(exc)[:240]
                print_step(
                    "SMS execution failed with incompatible error, fallback to rsync: %s"
                    % str(exc)[:160]
                )
            else:
                raise

    if migration_method == "rsync":
        print_step("Executing rsync migration phases: full -> incremental -> cutover")
        try:
            rsync_result = run_rsync_migration(
                client=client,
                cfg=cfg,
                target_project_id=target_project_id,
                target_server_id=target_vm_id,
                target_vpc_id=target_vpc_id,
                target_fixed_ip=str(sg_result.get("target_fixed_ip") or ""),
                target_floating_ip=str(sg_result.get("target_floating_ip") or ""),
            )
        except Exception as exc:
            err = str(exc).lower()
            if (
                "connect to host" not in err
                and "timed out" not in err
                and "connection refused" not in err
                and "no route to host" not in err
                and "network is unreachable" not in err
            ):
                raise
            print_step(
                "Rsync target SSH is unreachable, creating fresh target ECS and retrying once"
            )
            target_vm_id = create_target_server(
                client=client,
                cfg=recreate_cfg,
                source_project_id=source_project_id,
                target_project_id=target_project_id,
                source_server=source_server,
                vpc_id=target_vpc_id,
                subnet_id=target_subnet_id,
                allow_reuse=False,
            )
            sg_result = ensure_source_target_security_groups(
                client=client,
                source_region=cfg.source_region,
                source_project_id=source_project_id,
                source_server=source_ecs,
                target_region=cfg.target_region,
                target_project_id=target_project_id,
                target_vpc_id=target_vpc_id,
                target_vm_id=target_vm_id,
                source_fixed_ip=source_ecs_fixed_ip,
                source_floating_ip=source_ecs_floating_ip,
                additional_target_peer_ips=target_peer_ips,
                aws_source_profile=aws_source_profile,
            )
            rsync_result = run_rsync_migration(
                client=client,
                cfg=cfg,
                target_project_id=target_project_id,
                target_server_id=target_vm_id,
                target_vpc_id=target_vpc_id,
                target_fixed_ip=str(sg_result.get("target_fixed_ip") or ""),
                target_floating_ip=str(sg_result.get("target_floating_ip") or ""),
            )
        task_state = str(rsync_result.get("state") or "CUTOVER_SYNCED")
        rsync_result_file = build_out_path(cfg.result_path, "rsync_execution.json")
        write_json_file(rsync_result_file, rsync_result)

    result = {
        "source_region": cfg.source_region,
        "target_region": cfg.target_region,
        "source_project_id": source_project_id,
        "source_project_name": source_project_name,
        "target_project_id": target_project_id,
        "target_project_name": target_project_name,
        "input_source_server_id": cfg.source_server_id,
        "source_sms_server_id": source_sms_id,
        "migration_method": migration_method,
        "preferred_migration_method": cfg.preferred_migration_method,
        "enable_rsync_fallback": cfg.enable_rsync_fallback,
        "enable_vpn_bridge": cfg.enable_vpn_bridge,
        "enable_target_vpn_client": cfg.enable_target_vpn_client,
        "vpn_server_public_ip": cfg.vpn_server_public_ip,
        "vpn_server_port": cfg.vpn_server_port,
        "vpn_client_common_name": cfg.vpn_client_common_name,
        "vpn_client_static_ip": cfg.vpn_client_static_ip,
        "migration_fallback_reason": migration_fallback_reason,
        "sms_incompatible_reason": sms_incompatible_reason,
        "source_precheck_issues": source_precheck_issues,
        "precheck_source_checks_file": precheck_path,
        "precheck_task_cleanup_file": precheck_task_cleanup_path,
        "precheck_task_cleanup": task_cleanup_result,
        "target_server_id": target_vm_id,
        "target_recreate_image_id": recreate_image_id,
        "target_recreate_flavor_id": recreate_flavor_id,
        "migproject_id": migproject_id,
        "task_id": task_id,
        "task_state": task_state,
        "vpc_id": target_vpc_id,
        "subnet_id": target_subnet_id,
        "source_fixed_ip": sg_result.get("source_fixed_ip", ""),
        "source_floating_ip": sg_result.get("source_floating_ip", ""),
        "target_fixed_ip": sg_result.get("target_fixed_ip", ""),
        "target_floating_ip": sg_result.get("target_floating_ip", ""),
        "source_security_group_ids": sg_result.get("source_security_group_ids", []),
        "target_security_group_ids": sg_result.get("target_security_group_ids", []),
        "aws_source_instance_id": sg_result.get("aws_source_instance_id", ""),
        "aws_source_region": sg_result.get("aws_source_region", ""),
        "aws_source_security_group_ids": sg_result.get("aws_source_security_group_ids", []),
        "aws_source_security_group_rules_total": sg_result.get("aws_source_security_group_rules_total", 0),
        "aws_source_security_group_rules_copied": sg_result.get("aws_source_security_group_rules_copied", 0),
        "aws_source_security_group_rules_existing": sg_result.get("aws_source_security_group_rules_existing", 0),
        "aws_source_security_group_rules_skipped_unsupported": sg_result.get(
            "aws_source_security_group_rules_skipped_unsupported", 0
        ),
        "aws_source_security_group_rules_skipped_ipv6": sg_result.get(
            "aws_source_security_group_rules_skipped_ipv6", 0
        ),
        "aws_source_security_group_rules_skipped_group_reference": sg_result.get(
            "aws_source_security_group_rules_skipped_group_reference", 0
        ),
        "aws_source_security_group_rules_skipped_non_cidr": sg_result.get(
            "aws_source_security_group_rules_skipped_non_cidr", 0
        ),
        "aws_source_unsupported_protocols": sg_result.get("aws_source_unsupported_protocols", []),
        "target_peer_ips": sg_result.get("target_peer_ips", []),
        "target_vpc_default_security_group_id": sg_result.get("target_vpc_default_security_group_id", ""),
        "source_security_group_rules_created": sg_result.get("source_security_group_rules_created", 0),
        "target_security_group_rules_created": sg_result.get("target_security_group_rules_created", 0),
        "rsync_result_file": rsync_result_file,
    }

    write_json_file(cfg.result_path, result)

    print_step(f"Completed. Result written to {cfg.result_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[MGC-MIGRATE][ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
