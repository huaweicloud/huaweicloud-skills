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

    python cci_network_helper.py delete \
        --namespace <ns-name> \
        --name <network-name> \
        --region <region>

    python cci_network_helper.py status \
        --namespace <ns-name> \
        --name <network-name> \
        --region <region>

Required Python packages:
    pip install requests huaweicloudsdkcore

Environment variables (required):
    HW_ACCESS_KEY  - Huawei Cloud AK
    HW_SECRET_KEY  - Huawei Cloud SK

Environment variables (optional for temporary credential mode):
    HW_SECURITY_TOKEN  - Huawei Cloud SecurityToken (temporary credential mode)
                         Falls back to HUAWEI_CLOUD_SECURITY_TOKEN if HW_SECURITY_TOKEN not set.
                         When set, the script uses temporary STS credential authentication.

Note: subnet-id must be the neutron_subnet_id (not the VPC subnet ID).
      network-id must be the neutron_network_id (not the VPC subnet ID).
      Both can be obtained from: hcloud VPC ShowSubnet --subnet_id=<id> --cli-region=<region>
"""

import argparse
import json
import os
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


def get_project_id(region):
    import subprocess
    try:
        cmd = f"hcloud IAM KeystoneListProjects --cli-region={region} --cli-output=json"
        result = subprocess.run(
            cmd, capture_output=True, timeout=15,
            encoding="utf-8", errors="replace", shell=True,
        )
        if result.returncode == 0 and result.stdout.strip().startswith("{"):
            data = json.loads(result.stdout)
            for p in data.get("projects", []):
                if p.get("name") == region:
                    return p["id"]
    except Exception:
        pass
    print(f"ERROR: Cannot auto-detect project ID for region {region}")
    print(f"  Please provide --project-id explicitly")
    print(f"  Or run: hcloud IAM KeystoneListProjects --cli-region={region} --cli-output=json")
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
    result = json.loads(resp.text)

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


def delete_network(namespace, name, region, project_id=None):
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

    return resp.status_code


def check_status(namespace, name, region, project_id=None):
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
    result = json.loads(resp.text)

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
    create_parser.add_argument("--region", required=True, help="Region (e.g., cn-north-4)")
    create_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted)")

    delete_parser = subparsers.add_parser("delete", help="Delete a CCI Network")
    delete_parser.add_argument("--namespace", required=True, help="CCI namespace name")
    delete_parser.add_argument("--name", required=True, help="Network name")
    delete_parser.add_argument("--region", required=True, help="Region")
    delete_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted)")

    status_parser = subparsers.add_parser("status", help="Check CCI Network status")
    status_parser.add_argument("--namespace", required=True, help="CCI namespace name")
    status_parser.add_argument("--name", required=True, help="Network name")
    status_parser.add_argument("--region", required=True, help="Region")
    status_parser.add_argument("--project-id", default=None, help="Project ID (auto-detected if omitted)")

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


if __name__ == "__main__":
    main()