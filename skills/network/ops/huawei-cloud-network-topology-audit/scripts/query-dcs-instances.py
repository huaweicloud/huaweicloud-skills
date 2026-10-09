#!/usr/bin/env python3
"""
Query DCS (Distributed Cache Service) instances via Huawei Cloud SDK.

Path B script for DCS resource collection in the network topology audit.
Based on huaweicloudsdkdcs.v2 official SDK.

Usage:
    python3 query-dcs-instances.py --region=cn-north-4 [--limit=50]

Requirements:
    pip install huaweicloudsdkdcs
"""

import argparse
import json
import os
import sys

try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkdcs.v2 import DcsClient, ListInstancesRequest
    from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion
except ImportError:
    print("ERROR: huaweicloudsdkdcs not installed. Run: pip install huaweicloudsdkdcs")
    sys.exit(1)


def get_credentials():
    """Get Huawei Cloud credentials from environment variables."""
    ak = (os.environ.get("HUAWEICLOUD_SDK_AK") or
          os.environ.get("HW_ACCESS_KEY") or
          os.environ.get("HWC_AK") or "")
    sk = (os.environ.get("HUAWEICLOUD_SDK_SK") or
          os.environ.get("HW_SECRET_KEY") or
          os.environ.get("HWC_SK") or "")

    if not ak or not sk:
        print("ERROR: No credentials found. Set HUAWEICLOUD_SDK_AK/SK or HW_ACCESS_KEY/SECRET_KEY")
        sys.exit(1)

    return ak, sk


def query_dcs_instances(region, limit=50, name=None):
    """List DCS instances in the given region."""
    ak, sk = get_credentials()
    creds = BasicCredentials(ak, sk)

    client = DcsClient.new_builder() \
        .with_credentials(creds) \
        .with_region(DcsRegion.value_of(region)) \
        .build()

    request = ListInstancesRequest(limit=min(limit, 100))

    if name:
        request.name = name

    try:
        response = client.list_instances(request)
        instances = response.instances or []
        return instances
    except Exception as e:
        print(f"ERROR querying DCS instances: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Query DCS instances")
    parser.add_argument("--region", default="cn-north-4", help="Huawei Cloud region")
    parser.add_argument("--limit", type=int, default=50, help="Max instances to return")
    parser.add_argument("--name", help="Filter by instance name")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    instances = query_dcs_instances(args.region, args.limit, args.name)

    if args.json:
        output = []
        for inst in instances:
            output.append({
                "id": inst.id,
                "name": inst.name,
                "engine": inst.engine,
                "engine_version": inst.engine_version,
                "status": inst.status,
                "type": inst.specification_type or inst.spec_code,
                "capacity": inst.capacity,
                "vpc_id": inst.vpc_id,
                "subnet_id": inst.subnet_id,
                "security_group_id": inst.security_group_id,
                "port": inst.port if hasattr(inst, 'port') else None,
                "enable_publicip": inst.enable_publicip if hasattr(inst, 'enable_publicip') else None,
                "created_at": str(inst.created_at) if hasattr(inst, 'created_at') else None,
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"DCS instances in {args.region}:")
        if not instances:
            print("  (none found)")
        for inst in instances:
            pub = "PUBLIC" if getattr(inst, 'enable_publicip', False) else "VPC"
            print(f"  - {inst.name} ({inst.id}): {inst.engine} {inst.engine_version}, "
                  f"{inst.status}, {pub}, SG={inst.security_group_id}")


if __name__ == "__main__":
    main()