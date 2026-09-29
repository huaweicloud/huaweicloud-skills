#!/usr/bin/env python3
"""list_iam_agencies.py — 列出账号下可用的 IAM 委托 (v5)

huawei_list_iam_agencies
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig, list_agencies


def main():
    parser = argparse.ArgumentParser(description="列出账号下 IAM 委托 (v5)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    args = parser.parse_args()

    cfg = IamConfig(region=args.region)
    agencies = list_agencies(cfg)
    if not agencies:
        print("账号下没有委托。")
        return 0
    print(f"agency_count    {len(agencies)}")
    for a in agencies:
        print(f"{a['agency_id']}\t{a['agency_name']}\t{a.get('trust_domain_name','')}\t{a.get('description','')}")
    return 0


if __name__ == "__main__":
    main()