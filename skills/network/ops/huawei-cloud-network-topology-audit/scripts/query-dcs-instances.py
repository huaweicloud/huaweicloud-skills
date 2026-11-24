#!/usr/bin/env python3
"""
Query DCS (Distributed Cache Service) instances via Huawei Cloud SDK.

Path B script for DCS resource collection in the network topology audit.
Based on huaweicloudsdkdcs.v2 official SDK.

Usage:
    python3 query-dcs-instances.py --region=cn-north-4 [--limit=50] [--json]

Requirements:
    Python 3.8+ and huaweicloudsdkdcs (``pip install huaweicloudsdkdcs``).

Credentials (first match wins, same order as scripts/precheck.sh):
    HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK
    HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY
    HW_ACCESS_KEY / HW_SECRET_KEY
    HWC_AK / HWC_SK
    HWC_ACCESS_KEY / HWC_SECRET_KEY
    hcloud CLI profile (``hcloud configure set``)

Exit codes:
    0  query succeeded
    2  missing or incomplete credentials
    3  SDK dependency not installed
    1  API / runtime failure
"""

import argparse
import json
import os
import sys

CREDENTIAL_VARS = [
    ("HUAWEICLOUD_SDK_AK", "HUAWEICLOUD_SDK_SK"),
    ("HUAWEI_ACCESS_KEY", "HUAWEI_SECRET_KEY"),
    ("HW_ACCESS_KEY", "HW_SECRET_KEY"),
    ("HWC_AK", "HWC_SK"),
    ("HWC_ACCESS_KEY", "HWC_SECRET_KEY"),
]


def get_credentials():
    """Return (ak, sk) from the first complete environment pair, else exit 2."""
    for ak_var, sk_var in CREDENTIAL_VARS:
        ak = os.environ.get(ak_var, "")
        sk = os.environ.get(sk_var, "")
        if ak and sk:
            return ak, sk

    print(
        "ERROR: No Huawei Cloud credentials found.\n"
        "Set one complete AK/SK pair, for example:\n"
        "  export HUAWEICLOUD_SDK_AK=<your-ak>\n"
        "  export HUAWEICLOUD_SDK_SK=<your-sk>\n"
        "Supported pairs (checked in this order):\n"
        "  - HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK\n"
        "  - HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY\n"
        "  - HW_ACCESS_KEY / HW_SECRET_KEY\n"
        "  - HWC_AK / HWC_SK\n"
        "  - HWC_ACCESS_KEY / HWC_SECRET_KEY\n"
        "Alternatively configure a profile with: hcloud configure set --cli-region=<region>",
        file=sys.stderr,
    )
    sys.exit(2)


def load_sdk():
    """Import the DCS SDK lazily and fail with a readable message + exit 3."""
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkdcs.v2 import DcsClient, ListInstancesRequest
        from huaweicloudsdkdcs.v2.region.dcs_region import DcsRegion
    except ImportError as exc:
        print(
            f"ERROR: huaweicloudsdkdcs is required but not installed ({exc}).\n"
            "Install it with: pip install huaweicloudsdkdcs",
            file=sys.stderr,
        )
        sys.exit(3)
    return BasicCredentials, DcsClient, ListInstancesRequest, DcsRegion


def query_dcs_instances(region, limit=50, name=None):
    """List DCS instances in the given region."""
    ak, sk = get_credentials()
    BasicCredentials, DcsClient, ListInstancesRequest, DcsRegion = load_sdk()

    creds = BasicCredentials(ak, sk)

    try:
        dcs_region = DcsRegion.value_of(region)
    except Exception:
        print(
            f"ERROR: Unknown region '{region}'. Use a Huawei Cloud region such as cn-north-4.",
            file=sys.stderr,
        )
        sys.exit(2)

    client = DcsClient.new_builder() \
        .with_credentials(creds) \
        .with_region(dcs_region) \
        .build()

    request = ListInstancesRequest(limit=min(limit, 100))

    if name:
        request.name = name

    try:
        response = client.list_instances(request)
        instances = response.instances or []
        return instances
    except Exception as e:
        print(f"ERROR querying DCS instances: {e}", file=sys.stderr)
        sys.exit(1)


def _first_attr(obj, *names, default=None):
    """Return the first non-None attribute among ``names`` (missing attrs tolerated)."""
    for attr in names:
        try:
            value = getattr(obj, attr)
        except Exception:
            continue
        if value is not None:
            return value
    return default


def _serialize_instance(inst):
    """Map a DCS ``InstanceListInfo`` to a plain dict.

    ``InstanceListInfo`` exposes ``instance_id`` (not ``id``) and ``spec_code``
    (not ``specification_type``); the aliases keep the mapping tolerant of
    SDK/API variations.
    """
    created_at = _first_attr(inst, "created_at")
    data = {
        "id": _first_attr(inst, "instance_id", "id"),
        "name": _first_attr(inst, "name"),
        "engine": _first_attr(inst, "engine"),
        "engine_version": _first_attr(inst, "engine_version"),
        "status": _first_attr(inst, "status"),
        "type": _first_attr(inst, "specification_type", "spec_code"),
        "capacity": _first_attr(inst, "capacity"),
        "vpc_id": _first_attr(inst, "vpc_id"),
        "subnet_id": _first_attr(inst, "subnet_id"),
        "security_group_id": _first_attr(inst, "security_group_id"),
        "port": _first_attr(inst, "port"),
        "enable_publicip": _first_attr(inst, "enable_publicip"),
        "created_at": str(created_at) if created_at is not None else None,
    }
    if data["id"] is None and data["name"] is None:
        raise ValueError("missing both instance_id and name")
    return data


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
            try:
                output.append(_serialize_instance(inst))
            except Exception as exc:
                print(
                    f"WARNING: skipped one malformed DCS instance: {exc}",
                    file=sys.stderr,
                )
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"DCS instances in {args.region}:")
        if not instances:
            print("  (none found)")
        for inst in instances:
            try:
                data = _serialize_instance(inst)
                pub = "PUBLIC" if data["enable_publicip"] else "VPC"
                print(
                    f"  - {data['name']} ({data['id']}): "
                    f"{data['engine']} {data['engine_version']}, "
                    f"{data['status']}, {pub}, "
                    f"SG={data['security_group_id']}"
                )
            except Exception as exc:
                print(
                    f"WARNING: skipped one malformed DCS instance: {exc}",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    main()