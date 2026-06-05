#!/usr/bin/env python3
# coding: utf-8
"""Flexus L instance lifecycle management (start/stop/reboot)"""

import os
import sys

from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkecs.v2 import (
    BatchStartServersRequest, BatchStartServersRequestBody, BatchStartServersOption,
    BatchStopServersRequest, BatchStopServersRequestBody, BatchStopServersOption,
    BatchRebootServersRequest, BatchRebootServersRequestBody, BatchRebootSeversOption,
    ServerId
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import AuthManager


def manage_servers(action: str, server_ids: list, region: str = "cn-north-4", reboot_type: str = "SOFT", auth: AuthManager = None):
    """Manage Flexus L instance lifecycle (start/stop/reboot)"""
    action = action.lower()
    if action not in ["start", "stop", "reboot"]:
        raise ValueError(f"Invalid action: {action}, must be start/stop/reboot")
    
    auth = auth or AuthManager()
    if not auth.is_configured():
        raise ValueError("Please set environment variables HW_ACCESS_KEY, HW_SECRET_KEY, HW_SECURITY_TOKEN or provide --ak --sk parameters")
    
    client = auth.get_ecs_client(region)
    server_id_list = [ServerId(id=sid) for sid in server_ids]
    
    try:
        if action == "start":
            request = BatchStartServersRequest(body=BatchStartServersRequestBody(
                os_start=BatchStartServersOption(servers=server_id_list)))
            response = client.batch_start_servers(request)
        elif action == "stop":
            request = BatchStopServersRequest(body=BatchStopServersRequestBody(
                os_stop=BatchStopServersOption(servers=server_id_list)))
            response = client.batch_stop_servers(request)
        else:  # reboot
            request = BatchRebootServersRequest(body=BatchRebootServersRequestBody(
                reboot=BatchRebootSeversOption(servers=server_id_list, type=reboot_type)))
            response = client.batch_reboot_servers(request)
        
        return {"success": True, "response": str(response), "action": action, "server_ids": server_ids}
    except exceptions.ClientRequestException as e:
        return {"success": False, "error": {"status_code": e.status_code, "request_id": e.request_id, 
                                            "error_code": e.error_code, "error_msg": e.error_msg}}


def main():
    """Command line entry: parse arguments and execute lifecycle operations"""
    if len(sys.argv) < 2:
        print("Usage: python lifecycle.py <action> --instance-id <ID> [--instance-id <ID2>...] [--region <region>] [--type SOFT|HARD] [--ak <AK>] [--sk <SK>] [--security-token <TOKEN>]")
        print("Actions: start / stop / reboot")
        sys.exit(1)
    
    action, server_ids, region, reboot_type = sys.argv[1].lower(), [], "cn-north-4", "SOFT"
    ak, sk, security_token = None, None, None
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--instance-id" and i + 1 < len(sys.argv):
            server_ids.append(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--region" and i + 1 < len(sys.argv):
            region, i = sys.argv[i + 1], i + 2
        elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            reboot_type, i = sys.argv[i + 1].upper(), i + 2
        elif sys.argv[i] == "--ak" and i + 1 < len(sys.argv):
            ak, i = sys.argv[i + 1], i + 2
        elif sys.argv[i] == "--sk" and i + 1 < len(sys.argv):
            sk, i = sys.argv[i + 1], i + 2
        elif sys.argv[i] == "--security-token" and i + 1 < len(sys.argv):
            security_token, i = sys.argv[i + 1], i + 2
        else:
            i += 1
    
    if not server_ids or action not in ["start", "stop", "reboot"]:
        print("ERROR: Invalid parameters. Please provide --instance-id")
        sys.exit(1)
    
    auth = AuthManager(ak=ak, sk=sk, security_token=security_token)
    action_name = "Starting" if action == "start" else "Stopping" if action == "stop" else "Rebooting"
    print(f"{action_name} {len(server_ids)} server(s)...")
    result = manage_servers(action, server_ids, region, reboot_type, auth)
    
    if result["success"]:
        print(f"SUCCESS: {action.upper()} operation submitted")
    else:
        print(f"ERROR: Operation failed: {result['error']['error_msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
