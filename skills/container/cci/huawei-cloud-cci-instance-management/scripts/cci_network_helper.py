#!/usr/bin/env python3
"""
CCI Network Creation Helper Script

This script creates a CCI Network by directly calling the CCI OpenAPI,
bypassing hcloud CLI's limitation with annotation keys containing dots.

hcloud CLI treats dots in annotation keys as nested object delimiters,
making it impossible to pass 'network.alpha.kubernetes.io/default-security-group'
via CLI parameters or --cli-jsonInput (which also doesn't properly transmit
annotations in actual API requests, despite showing them in --dryrun).

Usage:
    python cci_network_helper.py create \
        --namespace <ns-name> \
        --name <network-name> \
        --vpc-id <vpc-id> \
        --subnet-id <neutron-subnet-id> \
        --network-id <neutron-network-id> \
        --security-group-id <sg-id> \
        --region <region>
        [--project-id <project-id>]

    python cci_network_helper.py delete \
        --namespace <ns-name> \
        --name <network-name> \
        --region <region>
        [--project-id <project-id>]

    python cci_network_helper.py status \
        --namespace <ns-name> \
        --name <network-name> \
        --region <region>
        [--project-id <project-id>]

    python cci_network_helper.py create-namespace \
        --name <ns-name> \
        --flavor <general-computing|gpu-accelerated> \
        --region <region>
        [--project-id <project-id>]

    create-namespace POSTs directly to
    https://cci.<region>.myhuaweicloud.com/api/v1/namespaces because the hcloud
    CLI cannot transmit the dotted annotation key `namespace.kubernetes.io/flavor`:
    the hyphen form `namespace-kubernetes-io/flavor` is silently ignored by CCI and
    the namespace falls back to general-computing. The command prints the flavor
    annotation returned by the API so the caller can confirm it took effect.

    --region must match [a-z0-9-]+ (e.g., cn-north-4); any other value is
    rejected with an ERROR before it can reach a subprocess argument list or the CCI API Host.
    If the project ID is already known, pass --project-id to skip the automatic
    `hcloud IAM KeystoneListProjects` detection entirely.

Required Python packages:
    pip install requests huaweicloudsdkcore

Environment variables (required):
    HW_ACCESS_KEY  - Huawei Cloud AK
    HW_SECRET_KEY  - Huawei Cloud SK

Environment variables (optional for temporary credential mode):
    HW_SECURITY_TOKEN  - Huawei Cloud SecurityToken (temporary credential mode)
                         Falls back to HUAWEI_CLOUD_SECURITY_TOKEN if HW_SECURITY_TOKEN not set.
                         When set, the script uses temporary STS credential authentication.

Environment variables (optional for hcloud CLI lookup):
    HCLOUD_PATH  - Full path to the hcloud CLI executable. Defaults to "hcloud"
                   (resolved from PATH). Set this when hcloud is not on PATH;
                   otherwise pass --project-id to skip hcloud detection entirely.

Note: subnet-id must be the neutron_subnet_id (not the VPC subnet ID).
      network-id must be the neutron_network_id (not the VPC subnet ID).
      Both can be obtained from: hcloud VPC ShowSubnet --subnet_id=<id> --cli-region=<region>
"""

import argparse
import json
import os
import re
import subprocess
import sys

import requests

try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.signer.signer import Signer
    from huaweicloudsdkcore.sdk_request import SdkRequest
except ImportError:
    print("ERROR: huaweicloudsdkcore not installed. Run: pip install huaweicloudsdkcore")
    sys.exit(1)


def get_credentials():
    ak = os.environ.get("HW_ACCESS_KEY")
    sk = os.environ.get("HW_SECRET_KEY")
    if not ak or not sk:
        print("ERROR: HW_ACCESS_KEY and HW_SECRET_KEY environment variables must be set")
        sys.exit(1)

    # Support SecurityToken for temporary credential mode
    # Check HW_SECURITY_TOKEN first, then fall back to HUAWEI_CLOUD_SECURITY_TOKEN
    security_token = os.environ.get("HW_SECURITY_TOKEN") or os.environ.get("HUAWEI_CLOUD_SECURITY_TOKEN")
    return ak, sk, security_token


# A valid region only contains lowercase letters, digits and hyphens (e.g. cn-north-4).
_REGION_PATTERN = re.compile(r"^[a-z0-9-]+$")


def _validate_region(region):
    """Validate a region against a strict whitelist; exit with ERROR on invalid values.

    The validated value is reused for both the hcloud command and the CCI API Host,
    so no raw caller-provided string is ever interpolated into a subprocess argument list or the
    CCI API Host.
    """
    if not region or not _REGION_PATTERN.match(region):
        print(f"ERROR: invalid region: {region!r}")
        print("  Region must match [a-z0-9-]+ (e.g., cn-north-4)")
        sys.exit(1)
    return region


# Flavors accepted by the CCI Namespace annotation `namespace.kubernetes.io/flavor`.
_VALID_FLAVORS = ("general-computing", "gpu-accelerated")


def _validate_flavor(flavor):
    """Validate a namespace flavor; exit with ERROR on unsupported values.

    Only the flavors documented for the CCI Namespace annotation are accepted,
    so a typo cannot silently create a namespace with an unusable flavor.
    """
    if flavor not in _VALID_FLAVORS:
        print(f"ERROR: invalid flavor: {flavor!r}")
        print("  Flavor must be one of: " + ", ".join(_VALID_FLAVORS))
        sys.exit(1)
    return flavor


def _hcloud_executable():
    """Resolve the hcloud CLI executable (HCLOUD_PATH overrides the PATH lookup)."""
    return os.environ.get("HCLOUD_PATH") or "hcloud"


def _run_hcloud(argv):
    """Run an hcloud command as an argument list, never through a shell.

    argv must be a list[str] passed directly to subprocess, so argument values
    are treated strictly as data and cannot be interpreted as shell commands.
    """
    result = subprocess.run(
        argv, capture_output=True, timeout=15,
        encoding="utf-8", errors="replace",
    )
    return result


def _truncate(text, limit=200):
    """Collapse a response body to a single short line for error reporting."""
    text = (text or "").strip().replace("\r", " ").replace("\n", " ")
    if len(text) > limit:
        return text[:limit] + "... (truncated)"
    return text


def get_project_id(region):
    hcloud = _hcloud_executable()
    try:
        result = _run_hcloud(
            [hcloud, "IAM", "KeystoneListProjects", f"--cli-region={region}", "--cli-output=json"]
        )
        if result.returncode == 0 and result.stdout.strip().startswith("{"):
            data = json.loads(result.stdout)
            for p in data.get("projects", []):
                if p.get("name") == region:
                    return p["id"]
    except Exception:
        pass
    print(f"ERROR: Cannot auto-detect project ID for region {region}")
    print(f"  hcloud executable used: {hcloud}")
    print(f"  If hcloud is not on PATH, set HCLOUD_PATH to its full path")
    print(f"  Please provide --project-id explicitly")
    print(f"  Or run: {hcloud} IAM KeystoneListProjects --cli-region={region} --cli-output=json")
    sys.exit(1)


def sign_request(method, host, resource_path, body, ak, sk, security_token, project_id):
    creds = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    if security_token:
        creds = creds.with_security_token(security_token)
    signer = Signer(creds)

    req = SdkRequest(
        method=method,
        schema="https",
        host=host,
        resource_path=resource_path,
        uri=resource_path,
        body=body,
        header_params={"Content-Type": "application/json", "Host": host},
        query_params=[],
    )

    signed_req = signer.sign(req)
    headers = signed_req.header_params
    headers["X-Project-Id"] = project_id
    return headers


def create_network(namespace, name, vpc_id, subnet_id, network_id, security_group_id, region, project_id=None):
    region = _validate_region(region)
    ak, sk, security_token = get_credentials()
    if not project_id:
        project_id = get_project_id(region)

    body_dict = {
        "apiVersion": "networking.cci.io/v1beta1",
        "kind": "Network",
        "metadata": {
            "name": name,
            "annotations": {
                "network.alpha.kubernetes.io/default-security-group": security_group_id
            },
        },
        "spec": {
            "attachedVPC": vpc_id,
            "networkID": network_id,
            "subnetID": subnet_id,
            "networkType": "underlay_neutron",
        },
    }
    body = json.dumps(body_dict)

    host = f"cci.{region}.myhuaweicloud.com"
    resource_path = (
        f"/apis/networking.cci.io/v1beta1/namespaces/{namespace}/networks"
    )
    url = f"https://{host}{resource_path}"

    headers = sign_request("POST", host, resource_path, body, ak, sk, security_token, project_id)

    resp = requests.post(url, data=body.encode("utf-8"), headers=headers)
    try:
        result = json.loads(resp.text)
    except json.JSONDecodeError:
        print(f"ERROR: Network creation failed. Status: {resp.status_code}")
        print(f"  Response was not valid JSON: {_truncate(resp.text)}")
        return resp.status_code

    if resp.status_code == 201:
        state = result.get("status", {}).get("state", "Unknown")
        print(f"SUCCESS: Network '{name}' created in namespace '{namespace}'")
        print(f"  State: {state}")
        print(f"  UID: {result.get('metadata', {}).get('uid', 'N/A')}")
    else:
        print(f"ERROR: Network creation failed. Status: {resp.status_code}")
        msg = result.get("message", resp.text)
        print(f"  Message: {msg}")

    return resp.status_code


def create_namespace(name, flavor, region, project_id=None):
    """Create a CCI Namespace with the dotted `namespace.kubernetes.io/flavor` annotation.

    hcloud CLI cannot transmit that dotted key: the hyphen form
    `namespace-kubernetes-io/flavor` is silently ignored by CCI and the namespace
    falls back to general-computing, so the request is signed and sent directly to
    the CCI OpenAPI (POST https://cci.<region>.myhuaweicloud.com/api/v1/namespaces),
    the same approach used by create_network.
    """
    region = _validate_region(region)
    flavor = _validate_flavor(flavor)
    ak, sk, security_token = get_credentials()
    if not project_id:
        project_id = get_project_id(region)

    body_dict = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": name,
            "annotations": {
                "namespace.kubernetes.io/flavor": flavor
            },
        },
    }
    body = json.dumps(body_dict)

    host = f"cci.{region}.myhuaweicloud.com"
    resource_path = "/api/v1/namespaces"
    url = f"https://{host}{resource_path}"

    headers = sign_request("POST", host, resource_path, body, ak, sk, security_token, project_id)

    resp = requests.post(url, data=body.encode("utf-8"), headers=headers)
    try:
        result = json.loads(resp.text)
    except json.JSONDecodeError:
        print(f"ERROR: Namespace creation failed. Status: {resp.status_code}")
        print(f"  Response was not valid JSON: {_truncate(resp.text)}")
        return resp.status_code

    if resp.status_code == 201:
        metadata = result.get("metadata") or {}
        annotations = metadata.get("annotations") or {}
        applied = annotations.get("namespace.kubernetes.io/flavor", "<annotation missing>")
        print(f"SUCCESS: Namespace '{name}' created (requested flavor: {flavor})")
        print(f"  UID: {metadata.get('uid', 'N/A')}")
        print(f"  Applied annotation namespace.kubernetes.io/flavor: {applied}")
        if applied != flavor:
            print("  WARNING: the flavor annotation returned by the API does not match the requested flavor")
    else:
        print(f"ERROR: Namespace creation failed. Status: {resp.status_code}")
        print(f"  Message: {result.get('message', resp.text)}")

    return resp.status_code


def delete_network(namespace, name, region, project_id=None):
    region = _validate_region(region)
    ak, sk, security_token = get_credentials()
    if not project_id:
        project_id = get_project_id(region)

    host = f"cci.{region}.myhuaweicloud.com"
    resource_path = (
        f"/apis/networking.cci.io/v1beta1/namespaces/{namespace}/networks/{name}"
    )
    url = f"https://{host}{resource_path}"

    headers = sign_request("DELETE", host, resource_path, "", ak, sk, security_token, project_id)

    resp = requests.delete(url, headers=headers)
    if resp.status_code in (200, 204):
        print(f"SUCCESS: Network '{name}' deleted from namespace '{namespace}'")
    else:
        try:
            result = json.loads(resp.text)
            print(f"ERROR: Network deletion failed. Status: {resp.status_code}")
            print(f"  Message: {result.get('message', resp.text)}")
        except json.JSONDecodeError:
            print(f"ERROR: Network deletion failed. Status: {resp.status_code}")
            print(f"  Response was not valid JSON: {_truncate(resp.text)}")

    return resp.status_code


def check_status(namespace, name, region, project_id=None):
    region = _validate_region(region)
    ak, sk, security_token = get_credentials()
    if not project_id:
        project_id = get_project_id(region)

    host = f"cci.{region}.myhuaweicloud.com"
    resource_path = (
        f"/apis/networking.cci.io/v1beta1/namespaces/{namespace}/networks/{name}"
    )
    url = f"https://{host}{resource_path}"

    headers = sign_request("GET", host, resource_path, "", ak, sk, security_token, project_id)

    resp = requests.get(url, headers=headers)
    try:
        result = json.loads(resp.text)
    except json.JSONDecodeError:
        print(f"ERROR: Failed to get network status. Status: {resp.status_code}")
        print(f"  Response was not valid JSON: {_truncate(resp.text)}")
        return resp.status_code

    if resp.status_code == 200:
        state = result.get("status", {}).get("state", "Unknown")
        cidr = result.get("spec", {}).get("cidr", "N/A")
        print(f"Network '{name}' in namespace '{namespace}'")
        print(f"  State: {state}")
        print(f"  CIDR: {cidr}")
    else:
        print(f"ERROR: Failed to get network status. Status: {resp.status_code}")
        print(f"  Message: {result.get('message', resp.text)}")

    return resp.status_code


def main():
    parser = argparse.ArgumentParser(
        description="CCI Network helper (bypasses hcloud CLI annotation key limitation)"
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    create_parser = subparsers.add_parser("create", help="Create a CCI Network")
    create_parser.add_argument("--namespace", required=True, help="CCI namespace name")
    create_parser.add_argument("--name", required=True, help="Network name")
    create_parser.add_argument("--vpc-id", required=True, help="VPC ID (attachedVPC)")
    create_parser.add_argument(
        "--subnet-id",
        required=True,
        help="Neutron subnet ID (not VPC subnet ID). Get from: hcloud VPC ShowSubnet",
    )
    create_parser.add_argument(
        "--network-id",
        required=True,
        help="Neutron network ID. Get from: hcloud VPC ShowSubnet",
    )
    create_parser.add_argument(
        "--security-group-id",
        required=True,
        help="Security group ID for the network",
    )
    create_parser.add_argument("--region", required=True, help="Region (e.g., cn-north-4); must match [a-z0-9-]+")
    create_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted; pass it to skip hcloud IAM detection)")

    delete_parser = subparsers.add_parser("delete", help="Delete a CCI Network")
    delete_parser.add_argument("--namespace", required=True, help="CCI namespace name")
    delete_parser.add_argument("--name", required=True, help="Network name")
    delete_parser.add_argument("--region", required=True, help="Region; must match [a-z0-9-]+")
    delete_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted; pass it to skip hcloud IAM detection)")

    status_parser = subparsers.add_parser("status", help="Check CCI Network status")
    status_parser.add_argument("--namespace", required=True, help="CCI namespace name")
    status_parser.add_argument("--name", required=True, help="Network name")
    status_parser.add_argument("--region", required=True, help="Region; must match [a-z0-9-]+")
    status_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted; pass it to skip hcloud IAM detection)")

    ns_parser = subparsers.add_parser(
        "create-namespace",
        help="Create a CCI Namespace with a dotted flavor annotation (bypasses hcloud CLI)",
    )
    ns_parser.add_argument("--name", required=True, help="CCI namespace name")
    ns_parser.add_argument(
        "--flavor",
        required=True,
        help="Namespace flavor: general-computing or gpu-accelerated",
    )
    ns_parser.add_argument("--region", required=True, help="Region; must match [a-z0-9-]+")
    ns_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted; pass it to skip hcloud IAM detection)")

    args = parser.parse_args()

    if args.action == "create":
        create_network(
            args.namespace,
            args.name,
            args.vpc_id,
            args.subnet_id,
            args.network_id,
            args.security_group_id,
            args.region,
            args.project_id,
        )
    elif args.action == "delete":
        delete_network(args.namespace, args.name, args.region, args.project_id)
    elif args.action == "status":
        check_status(args.namespace, args.name, args.region, args.project_id)
    elif args.action == "create-namespace":
        create_namespace(args.name, args.flavor, args.region, args.project_id)


if __name__ == "__main__":
    main()