#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Security Group Rule Configuration Module
"""

import os
import sys
import time, argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lib import create_ingress_rule, get_security_group_id_by_name


def do_set_security_group_rule(
        ak: str,
        sk: str,
        region: str,
        security_token: str = None,
        group_name: str = "sg-default-smb",
):
    """Configure security group inbound port 80"""
    print("=" * 60)
    print("        Configure Security Group to Allow Port 80")
    print("=" * 60)
    print(f"  Region: {region}")

    print("\nSetting up security group inbound rule...")
    for i in range(10):
        resp_id = get_security_group_id_by_name(ak, sk, region, group_name, security_token)
        if resp_id.get("result"):
            resp_rule = create_ingress_rule(ak, sk, region, resp_id.get("result"), security_token=security_token)
            if resp_rule.get("ok"):
                print("\nPort 80 has been allowed")
            else:
                print(resp_rule.get("text"))
                print(resp_rule.get("error").get("message"))
            break
        else:
            time.sleep(10)
    else:
        print("\nFailed to get security group ID by name")
