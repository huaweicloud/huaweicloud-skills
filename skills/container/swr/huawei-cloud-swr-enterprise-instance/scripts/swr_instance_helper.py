"""SWR Enterprise Instance Helper - Python SDK wrapper for CreateInstance.

This script bypasses the hcloud CLI duplicate --project_id parameter bug
by using the Huawei Cloud Python SDK directly to create SWR enterprise instances.

Usage:
    python swr_instance_helper.py create --name=<name> --spec=<spec> \
        --vpc_id=<vpc-id> --subnet_id=<subnet-id> \
        [--region=cn-north-4] [--description=...] [--enterprise_project_id=0]

Environment variables (required):
    HUAWEI_CLOUD_AK   or HUAWEI_AK   or HUAWEICLOUD_SDK_AK
    HUAWEI_CLOUD_SK   or HUAWEI_SK   or HUAWEICLOUD_SDK_SK
    HUAWEI_CLOUD_REGION (optional, default cn-north-4)

Requirements:
    pip install huaweicloudsdkcore huaweicloudsdkswr
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time


def get_credentials():
    ak = os.environ.get("HUAWEI_CLOUD_AK") or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK") or os.environ.get("HW_ACCESS_KEY")
    sk = os.environ.get("HUAWEI_CLOUD_SK") or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK") or os.environ.get("HW_SECRET_KEY")
    region = os.environ.get("HUAWEI_CLOUD_REGION") or os.environ.get("HUAWEI_REGION") or os.environ.get("HW_REGION_NAME") or "cn-north-4"
    if not ak or not sk:
        print("ERROR: Missing credentials. Set HUAWEI_CLOUD_AK and HUAWEI_CLOUD_SK environment variables.", file=sys.stderr)
        sys.exit(1)
    return ak, sk, region


def create_swr_client(ak, sk, region, project_id=None):
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkswr.v2 import SwrClient
    from huaweicloudsdkswr.v2.region.swr_region import SwrRegion

    if project_id:
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
    else:
        credentials = BasicCredentials(ak=ak, sk=sk)

    swr_region = SwrRegion.value_of(region)

    return SwrClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(swr_region) \
        .build()


def create_instance(args):
    ak, sk, default_region = get_credentials()
    region = args.region or default_region

    project_id = args.project_id
    if not project_id:
        try:
            from scripts.huawei_cloud.common import get_project_id_for_region
            project_id = get_project_id_for_region(region, ak, sk)
        except Exception:
            pass
        if not project_id:
            try:
                from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
                from huaweicloudsdkcore.auth.credentials import GlobalCredentials
                iam_client = IamClient.new_builder() \
                    .with_credentials(GlobalCredentials(ak=ak, sk=sk)) \
                    .with_endpoint("iam.myhuaweicloud.com") \
                    .build()
                req = KeystoneListProjectsRequest()
                req.name = region
                resp = iam_client.keystone_list_projects(req)
                for proj in resp.projects:
                    if proj.name == region:
                        project_id = proj.id
                        break
            except Exception as e:
                print(f"WARNING: Could not auto-fetch project_id for region {region}: {e}", file=sys.stderr)

    if not project_id:
        print(f"ERROR: project_id is required and could not be auto-fetched for region {region}.", file=sys.stderr)
        print("Set HUAWEI_CLOUD_PROJECT_ID or pass --project_id explicitly.", file=sys.stderr)
        sys.exit(1)

    client = create_swr_client(ak, sk, region, project_id)

    from huaweicloudsdkswr.v2 import CreateInstanceRequest, CreateInstanceRequestBody

    body = CreateInstanceRequestBody(
        name=args.name,
        spec=args.spec,
        charge_mode=args.charge_mode or "postPaid",
        vpc_id=args.vpc_id,
        subnet_id=args.subnet_id,
        project_id=project_id,
        enterprise_project_id=args.enterprise_project_id or "0",
        description=args.description or None,
        enable_intranet_access=args.enable_intranet_access if args.enable_intranet_access is not None else True,
        obs_encrypt=args.obs_encrypt if args.obs_encrypt else None,
        encrypt_type=args.encrypt_type or None,
        obs_bucket_name=args.obs_bucket_name or None,
        obs_enc_kms_key_id=args.obs_enc_kms_key_id or None,
    )

    request = CreateInstanceRequest(body=body)

    try:
        response = client.create_instance(request)
        result = response.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    except Exception as e:
        print(f"ERROR: CreateInstance failed: {e}", file=sys.stderr)
        sys.exit(1)


def list_instances(args):
    ak, sk, default_region = get_credentials()
    region = args.region or default_region

    project_id = args.project_id
    if not project_id:
        try:
            from scripts.huawei_cloud.common import get_project_id_for_region
            project_id = get_project_id_for_region(region, ak, sk)
        except Exception:
            pass

    if not project_id:
        try:
            from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
            from huaweicloudsdkcore.auth.credentials import GlobalCredentials
            iam_client = IamClient.new_builder() \
                .with_credentials(GlobalCredentials(ak=ak, sk=sk)) \
                .with_endpoint("iam.myhuaweicloud.com") \
                .build()
            req = KeystoneListProjectsRequest()
            req.name = region
            resp = iam_client.keystone_list_projects(req)
            for proj in resp.projects:
                if proj.name == region:
                    project_id = proj.id
                    break
        except Exception:
            pass

    if not project_id:
        print(f"ERROR: project_id required for region {region}.", file=sys.stderr)
        sys.exit(1)

    client = create_swr_client(ak, sk, region, project_id)

    from huaweicloudsdkswr.v2 import ListInstanceRequest

    request = ListInstanceRequest()

    if args.status:
        request.status = args.status
    if args.limit:
        request.limit = args.limit
    if args.offset:
        request.offset = args.offset

    try:
        response = client.list_instance(request)
        result = response.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    except Exception as e:
        print(f"ERROR: ListInstance failed: {e}", file=sys.stderr)
        sys.exit(1)


def show_instance(args):
    ak, sk, default_region = get_credentials()
    region = args.region or default_region

    project_id = args.project_id
    if not project_id:
        try:
            from scripts.huawei_cloud.common import get_project_id_for_region
            project_id = get_project_id_for_region(region, ak, sk)
        except Exception:
            pass

    if not project_id:
        try:
            from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
            from huaweicloudsdkcore.auth.credentials import GlobalCredentials
            iam_client = IamClient.new_builder() \
                .with_credentials(GlobalCredentials(ak=ak, sk=sk)) \
                .with_endpoint("iam.myhuaweicloud.com") \
                .build()
            req = KeystoneListProjectsRequest()
            req.name = region
            resp = iam_client.keystone_list_projects(req)
            for proj in resp.projects:
                if proj.name == region:
                    project_id = proj.id
                    break
        except Exception:
            pass

    if not project_id:
        print(f"ERROR: project_id required for region {region}.", file=sys.stderr)
        sys.exit(1)

    client = create_swr_client(ak, sk, region, project_id)

    from huaweicloudsdkswr.v2 import ShowInstanceRequest

    request = ShowInstanceRequest(instance_id=args.instance_id)

    try:
        response = client.show_instance(request)
        result = response.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    except Exception as e:
        print(f"ERROR: ShowInstance failed: {e}", file=sys.stderr)
        sys.exit(1)


def delete_instance(args):
    ak, sk, default_region = get_credentials()
    region = args.region or default_region

    project_id = args.project_id
    if not project_id:
        try:
            from scripts.huawei_cloud.common import get_project_id_for_region
            project_id = get_project_id_for_region(region, ak, sk)
        except Exception:
            pass

    if not project_id:
        try:
            from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
            from huaweicloudsdkcore.auth.credentials import GlobalCredentials
            iam_client = IamClient.new_builder() \
                .with_credentials(GlobalCredentials(ak=ak, sk=sk)) \
                .with_endpoint("iam.myhuaweicloud.com") \
                .build()
            req = KeystoneListProjectsRequest()
            req.name = region
            resp = iam_client.keystone_list_projects(req)
            for proj in resp.projects:
                if proj.name == region:
                    project_id = proj.id
                    break
        except Exception:
            pass

    if not project_id:
        print(f"ERROR: project_id required for region {region}.", file=sys.stderr)
        sys.exit(1)

    client = create_swr_client(ak, sk, region, project_id)

    from huaweicloudsdkswr.v2 import DeleteInstanceRequest

    request = DeleteInstanceRequest(instance_id=args.instance_id)

    if args.delete_obs:
        request.delete_obs = args.delete_obs
    if args.delete_dns:
        request.delete_dns = args.delete_dns

    try:
        response = client.delete_instance(request)
        result = response.to_dict()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result
    except Exception as e:
        print(f"ERROR: DeleteInstance failed: {e}", file=sys.stderr)
        sys.exit(1)


def wait_instance_running(args):
    ak, sk, default_region = get_credentials()
    region = args.region or default_region

    project_id = args.project_id
    if not project_id:
        try:
            from scripts.huawei_cloud.common import get_project_id_for_region
            project_id = get_project_id_for_region(region, ak, sk)
        except Exception:
            pass

    if not project_id:
        try:
            from huaweicloudsdkiam.v3 import IamClient, KeystoneListProjectsRequest
            from huaweicloudsdkcore.auth.credentials import GlobalCredentials
            iam_client = IamClient.new_builder() \
                .with_credentials(GlobalCredentials(ak=ak, sk=sk)) \
                .with_endpoint("iam.myhuaweicloud.com") \
                .build()
            req = KeystoneListProjectsRequest()
            req.name = region
            resp = iam_client.keystone_list_projects(req)
            for proj in resp.projects:
                if proj.name == region:
                    project_id = proj.id
                    break
        except Exception:
            pass

    if not project_id:
        print(f"ERROR: project_id required for region {region}.", file=sys.stderr)
        sys.exit(1)

    client = create_swr_client(ak, sk, region, project_id)

    from huaweicloudsdkswr.v2 import ShowInstanceRequest

    timeout = args.timeout or 600
    interval = args.interval or 30
    elapsed = 0

    while elapsed < timeout:
        request = ShowInstanceRequest(instance_id=args.instance_id)
        try:
            response = client.show_instance(request)
            instance = response.to_dict()
            status = instance.get("status", "Unknown")
            print(f"Instance {args.instance_id} status: {status} (elapsed: {elapsed}s)")
            if status == "Running":
                print(json.dumps(instance, indent=2, ensure_ascii=False))
                return instance
            if status == "Unavailable":
                print(f"ERROR: Instance creation failed, status is Unavailable.", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"WARNING: ShowInstance check failed: {e}", file=sys.stderr)

        time.sleep(interval)
        elapsed += interval

    print(f"ERROR: Timeout waiting for instance to reach Running status ({timeout}s).", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SWR Enterprise Instance Helper - Python SDK wrapper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create
    create_parser = subparsers.add_parser("create", help="Create an SWR enterprise instance")
    create_parser.add_argument("--name", required=True, help="Instance name (3-48 chars, lowercase start)")
    create_parser.add_argument("--spec", required=True, choices=["swr.ee.basic", "swr.ee.professional"], help="Instance spec")
    create_parser.add_argument("--vpc_id", required=True, help="VPC ID")
    create_parser.add_argument("--subnet_id", required=True, help="Subnet ID")
    create_parser.add_argument("--charge_mode", default="postPaid", help="Charge mode (default: postPaid)")
    create_parser.add_argument("--enterprise_project_id", default="0", help="Enterprise project ID (default: 0)")
    create_parser.add_argument("--project_id", default=None, help="Project ID (auto-fetched if not provided)")
    create_parser.add_argument("--region", default=None, help="Region (default from env or cn-north-4)")
    create_parser.add_argument("--description", default=None, help="Instance description")
    create_parser.add_argument("--enable_intranet_access", type=bool, default=None, help="Create intranet access (default: True)")
    create_parser.add_argument("--obs_encrypt", type=bool, default=None, help="Enable OBS encryption")
    create_parser.add_argument("--encrypt_type", default=None, choices=["gm"], help="OBS encryption algorithm")
    create_parser.add_argument("--obs_bucket_name", default=None, help="Custom OBS bucket name")
    create_parser.add_argument("--obs_enc_kms_key_id", default=None, help="KMS key ID for OBS encryption")

    # list
    list_parser = subparsers.add_parser("list", help="List SWR enterprise instances")
    list_parser.add_argument("--region", default=None, help="Region")
    list_parser.add_argument("--project_id", default=None, help="Project ID")
    list_parser.add_argument("--status", default=None, help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=None, help="Page size")
    list_parser.add_argument("--offset", type=int, default=None, help="Page offset")

    # show
    show_parser = subparsers.add_parser("show", help="Show SWR enterprise instance details")
    show_parser.add_argument("--instance_id", required=True, help="Instance ID")
    show_parser.add_argument("--region", default=None, help="Region")
    show_parser.add_argument("--project_id", default=None, help="Project ID")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete an SWR enterprise instance")
    delete_parser.add_argument("--instance_id", required=True, help="Instance ID")
    delete_parser.add_argument("--region", default=None, help="Region")
    delete_parser.add_argument("--project_id", default=None, help="Project ID")
    delete_parser.add_argument("--delete_obs", type=bool, default=None, help="Also delete OBS bucket")
    delete_parser.add_argument("--delete_dns", type=bool, default=None, help="Also delete DNS records")

    # wait
    wait_parser = subparsers.add_parser("wait", help="Wait for instance to reach Running status")
    wait_parser.add_argument("--instance_id", required=True, help="Instance ID")
    wait_parser.add_argument("--region", default=None, help="Region")
    wait_parser.add_argument("--project_id", default=None, help="Project ID")
    wait_parser.add_argument("--timeout", type=int, default=600, help="Max wait time in seconds (default: 600)")
    wait_parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "create": create_instance,
        "list": list_instances,
        "show": show_instance,
        "delete": delete_instance,
        "wait": wait_instance_running,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()