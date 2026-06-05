#!/usr/bin/env python3
# coding: utf-8
"""Flexus L instance information update tool"""

import os
import sys
import re

from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkecs.v2 import (
    UpdateServerRequest, UpdateServerRequestBody, UpdateServerOption
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import AuthManager


def validate_name(name: str) -> tuple:
    """Validate name (1-64 characters, supports Chinese/letters/numbers/_-.)"""
    if not name or len(name) > 64:
        return False, "Name length must be 1-64 characters"
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_\-\.]+$', name):
        return False, "Name can only contain Chinese, letters, numbers, _, -, ."
    return True, ""


def validate_description(desc: str) -> tuple:
    """Validate description (0-85 characters, cannot contain <>)"""
    if len(desc) > 85:
        return False, "Description length cannot exceed 85 characters"
    if '<' in desc or '>' in desc:
        return False, "Description cannot contain < or >"
    return True, ""


def validate_hostname(hostname: str) -> tuple:
    """Validate hostname (1-64 characters, DNS compliant)"""
    if not hostname or len(hostname) > 64:
        return False, "Hostname length must be 1-64 characters"
    if hostname.startswith('.') or hostname.startswith('-') or hostname.endswith('.') or hostname.endswith('-'):
        return False, "Hostname cannot start or end with . or -"
    if '..' in hostname or '--' in hostname or '.-' in hostname or '-.' in hostname:
        return False, "Invalid hostname format"
    for seg in hostname.split('.'):
        if not seg or not re.match(r'^[a-zA-Z0-9\-]+$', seg):
            return False, f"Invalid hostname segment: '{seg}'"
    return True, ""


def update_server(server_id: str, region: str = "cn-north-4", name: str = None, 
                  description: str = None, hostname: str = None, auth: AuthManager = None):
    """Update server information (name/description/hostname)"""
    auth = auth or AuthManager()
    if not auth.is_configured():
        raise ValueError("Please set environment variables HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN or provide --ak --sk parameters")
    
    if not any([name, description is not None, hostname]):
        raise ValueError("Please provide at least one modification parameter")
    
    for val, fn in [(name, validate_name), (description, validate_description), (hostname, validate_hostname)]:
        if val is not None:
            ok, err = fn(val)
            if not ok:
                raise ValueError(err)
    
    client = auth.get_ecs_client(region)
    kwargs = {k: v for k, v in [('name', name), ('description', description), ('hostname', hostname)] if v is not None}
    
    try:
        request = UpdateServerRequest(server_id=server_id, body=UpdateServerRequestBody(server=UpdateServerOption(**kwargs)))
        response = client.update_server(request)
        return {"success": True, "response": str(response)}
    except exceptions.ClientRequestException as e:
        return {"success": False, "error": {"status_code": e.status_code, "error_msg": e.error_msg}}


def main():
    """Command line entry: parse arguments and execute update operations"""
    if len(sys.argv) < 2:
        print("Usage: python update_server.py --instance-id <ID> [--name <name>] [--description <desc>] [--hostname <hostname>] [--region <region>] [--ak <AK>] [--sk <SK>] [--security-token <TOKEN>]")
        sys.exit(1)
    
    server_id, region, name, desc, hostname = None, "cn-north-4", None, None, None
    ak, sk, security_token = None, None, None
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--instance-id" and i + 1 < len(sys.argv):
            server_id, i = sys.argv[i + 1], i + 2
        elif arg == "--region" and i + 1 < len(sys.argv):
            region, i = sys.argv[i + 1], i + 2
        elif arg == "--name" and i + 1 < len(sys.argv):
            name, i = sys.argv[i + 1], i + 2
        elif arg == "--description" and i + 1 < len(sys.argv):
            desc, i = sys.argv[i + 1], i + 2
        elif arg == "--hostname" and i + 1 < len(sys.argv):
            hostname, i = sys.argv[i + 1], i + 2
        elif arg == "--ak" and i + 1 < len(sys.argv):
            ak, i = sys.argv[i + 1], i + 2
        elif arg == "--sk" and i + 1 < len(sys.argv):
            sk, i = sys.argv[i + 1], i + 2
        elif arg == "--security-token" and i + 1 < len(sys.argv):
            security_token, i = sys.argv[i + 1], i + 2
        else:
            i += 1
    
    if not server_id:
        print("ERROR: Please provide --instance-id")
        sys.exit(1)
    
    auth = AuthManager(ak=ak, sk=sk, security_token=security_token)
    print(f"Updating server: {server_id}")
    result = update_server(server_id, region, name, desc, hostname, auth)
    
    if result["success"]:
        print("SUCCESS: Update successful")
    else:
        print(f"ERROR: Update failed: {result['error']['error_msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
