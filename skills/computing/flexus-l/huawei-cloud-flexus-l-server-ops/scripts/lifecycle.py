#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Server Lifecycle Management Script

Supports: start, stop, reboot operations

Before using, set environment variables:
- CLOUD_SDK_AK or HUAWEICLOUD_SDK_AK: Huawei Cloud Access Key
- CLOUD_SDK_SK or HUAWEICLOUD_SDK_SK: Huawei Cloud Secret Key
"""

import os
import sys
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkecs.v2 import *


def manage_servers(action: str, server_ids: list, region: str = "cn-north-4", reboot_type: str = "SOFT"):
    """
    Manage Flexus L servers lifecycle (start/stop/reboot)
    
    Args:
        action: Action to perform (start/stop/reboot)
        server_ids: List of server IDs
        region: Huawei Cloud region, default cn-north-4
        reboot_type: Reboot type (SOFT/HARD), only for reboot action
    
    Returns:
        dict: Operation result
    """
    # Validate action
    action = action.lower()
    if action not in ["start", "stop", "reboot"]:
        raise ValueError(f"Invalid action: {action}. Must be start, stop, or reboot")
    
    # Get credentials from environment variables
    ak = os.environ.get("CLOUD_SDK_AK") or os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("CLOUD_SDK_SK") or os.environ.get("HUAWEICLOUD_SDK_SK")

    if not ak or not sk:
        raise ValueError("Please set environment variables CLOUD_SDK_AK and CLOUD_SDK_SK")
    
    # Create credentials and client
    credentials = BasicCredentials(ak, sk)
    
    client = EcsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EcsRegion.value_of(region)) \
        .build()
    
    try:
        # Build server ID list
        server_id_list = [ServerId(id=server_id) for server_id in server_ids]
        
        # Execute action
        if action == "start":
            # Start servers
            request = BatchStartServersRequest()
            osstartbody = BatchStartServersOption(servers=server_id_list)
            request.body = BatchStartServersRequestBody(os_start=osstartbody)
            response = client.batch_start_servers(request)
            
        elif action == "stop":
            # Stop servers
            request = BatchStopServersRequest()
            osstopbody = BatchStopServersOption(servers=server_id_list)
            request.body = BatchStopServersRequestBody(os_stop=osstopbody)
            response = client.batch_stop_servers(request)
            
        elif action == "reboot":
            # Reboot servers
            request = BatchRebootServersRequest()
            rebootbody = BatchRebootSeversOption(servers=server_id_list, type=reboot_type)
            request.body = BatchRebootServersRequestBody(reboot=rebootbody)
            response = client.batch_reboot_servers(request)
        
        return {
            "success": True,
            "response": str(response),
            "action": action,
            "server_ids": server_ids,
            "region": region,
            "reboot_type": reboot_type if action == "reboot" else None
        }
        
    except exceptions.ClientRequestException as e:
        return {
            "success": False,
            "error": {
                "status_code": e.status_code,
                "request_id": e.request_id,
                "error_code": e.error_code,
                "error_msg": e.error_msg
            },
            "action": action,
            "server_ids": server_ids,
            "region": region
        }


def main():
    """Command line entry point"""
    if len(sys.argv) < 3:
        print("Usage: python lifecycle.py <action> <server_id1> [server_id2] ... [--region <region>] [--type <SOFT|HARD>]")
        print("\nActions:")
        print("  start   - Start servers")
        print("  stop    - Stop servers")
        print("  reboot  - Reboot servers")
        print("\nExamples:")
        print("  python lifecycle.py start 28f0xxx 9c98xxx")
        print("  python lifecycle.py stop 28f0xxx --region cn-north-4")
        print("  python lifecycle.py reboot 28f0xxx --type HARD")
        sys.exit(1)
    
    # Parse arguments
    action = sys.argv[1].lower()
    server_ids = []
    region = "cn-north-4"  # Default region
    reboot_type = "SOFT"  # Default reboot type
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--region" and i + 1 < len(sys.argv):
            region = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            reboot_type = sys.argv[i + 1].upper()
            i += 2
        else:
            server_ids.append(sys.argv[i])
            i += 1
    
    if not server_ids:
        print("Error: Please provide at least one server ID")
        sys.exit(1)
    
    if action not in ["start", "stop", "reboot"]:
        print(f"Error: Invalid action '{action}'. Must be start, stop, or reboot")
        sys.exit(1)
    
    if action == "reboot" and reboot_type not in ["SOFT", "HARD"]:
        print("Error: Reboot type must be SOFT or HARD")
        sys.exit(1)
    
    # Action descriptions
    action_desc = {
        "start": "Starting",
        "stop": "Stopping",
        "reboot": "Rebooting"
    }
    
    print(f"{action_desc[action]} {len(server_ids)} server(s)...")
    print(f"Action: {action.upper()}")
    print(f"Server IDs: {server_ids}")
    print(f"Region: {region}")
    if action == "reboot":
        print(f"Reboot type: {reboot_type} ({'Normal reboot' if reboot_type == 'SOFT' else 'Forced reboot'})")
    
    result = manage_servers(action, server_ids, region, reboot_type)
    
    if result["success"]:
        print(f"\n✅ {action.upper()} operation submitted")
        print(f"Response: {result['response']}")
    else:
        print(f"\n❌ {action.upper()} operation failed")
        error = result["error"]
        print(f"Status code: {error['status_code']}")
        print(f"Request ID: {error['request_id']}")
        print(f"Error code: {error['error_code']}")
        print(f"Error message: {error['error_msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
