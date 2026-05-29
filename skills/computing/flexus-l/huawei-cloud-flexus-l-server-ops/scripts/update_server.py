#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Server Information Update Script

Before using, set environment variables:
- CLOUD_SDK_AK: Huawei Cloud Access Key
- CLOUD_SDK_SK: Huawei Cloud Secret Key
"""

import os
import sys
import re
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkecs.v2 import *


def validate_name(name: str) -> tuple[bool, str]:
    """
    Validate cloud server name
    
    Rule: Can only contain Chinese characters, English letters, numbers, and "_", "-", ".", length [1-64] characters
    
    Returns:
        (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"
    
    if len(name) < 1 or len(name) > 64:
        return False, f"Name length must be between 1-64 characters, current length: {len(name)}"
    
    # Check if only allowed characters
    pattern = r'^[\u4e00-\u9fa5a-zA-Z0-9_\-\.]+$'
    if not re.match(pattern, name):
        return False, "Name can only contain Chinese characters, English letters, numbers, and _, -, ."
    
    return True, ""


def validate_description(description: str) -> tuple[bool, str]:
    """
    Validate cloud server description
    
    Rule: Cannot contain "<", ">", length [0-85] characters
    
    Returns:
        (is_valid, error_message)
    """
    if len(description) > 85:
        return False, f"Description length cannot exceed 85 characters, current length: {len(description)}"
    
    if '<' in description or '>' in description:
        return False, "Description cannot contain < or >"
    
    return True, ""


def validate_hostname(hostname: str) -> tuple[bool, str]:
    """
    Validate cloud server hostname
    
    Rules:
    - Length [1-64] characters
    - Allow using dot (.) to separate characters into multiple segments
    - Each segment allows uppercase letters, lowercase letters, numbers, or hyphen (-)
    - Cannot use dot (.) or hyphen (-) consecutively
    - Cannot start or end with dot (.) or hyphen (-)
    - Cannot appear (. -) and (- .)
    
    Returns:
        (is_valid, error_message)
    """
    if not hostname:
        return False, "Hostname cannot be empty"
    
    if len(hostname) < 1 or len(hostname) > 64:
        return False, f"Hostname length must be between 1-64 characters, current length: {len(hostname)}"
    
    # Cannot start or end with dot or hyphen
    if hostname.startswith('.') or hostname.startswith('-'):
        return False, "Hostname cannot start with dot (.) or hyphen (-)"
    
    if hostname.endswith('.') or hostname.endswith('-'):
        return False, "Hostname cannot end with dot (.) or hyphen (-)"
    
    # Cannot use dot or hyphen consecutively
    if '..' in hostname or '--' in hostname:
        return False, "Hostname cannot use dot (.) or hyphen (-) consecutively"
    
    # Cannot appear (. -) and (- .)
    if '.-' in hostname or '-.' in hostname:
        return False, "Hostname cannot appear (. -) or (- .)"
    
    # Check each segment for allowed characters only
    segments = hostname.split('.')
    for segment in segments:
        if not segment:
            return False, "Hostname format error: empty segment exists"
        
        # Each segment can only contain uppercase letters, lowercase letters, numbers, or hyphen
        pattern = r'^[a-zA-Z0-9\-]+$'
        if not re.match(pattern, segment):
            return False, f"Hostname segment '{segment}' can only contain uppercase letters, lowercase letters, numbers, or hyphen (-)"
    
    return True, ""


def update_server(
    server_id: str,
    region: str = "cn-north-4",
    name: str = None,
    description: str = None,
    hostname: str = None
) -> dict:
    """
    Update Flexus L server information
    
    Args:
        server_id: Server ID
        region: Huawei Cloud region, default cn-north-4
        name: New cloud server name (optional)
        description: New cloud server description (optional)
        hostname: New cloud server hostname (optional)
    
    Returns:
        dict: Operation result
    """
    # Get credentials from environment variables
    ak = os.environ.get("CLOUD_SDK_AK") or os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("CLOUD_SDK_SK") or os.environ.get("HUAWEICLOUD_SDK_SK")

    if not ak or not sk:
        raise ValueError("Please set environment variables CLOUD_SDK_AK and CLOUD_SDK_SK")
    
    # Validate at least one modification parameter provided
    if not name and description is None and not hostname:
        raise ValueError("Please provide at least one modification parameter (name, description, or hostname)")
    
    # Validate parameters
    if name:
        is_valid, error = validate_name(name)
        if not is_valid:
            raise ValueError(f"Name validation failed: {error}")
    
    if description is not None:
        is_valid, error = validate_description(description)
        if not is_valid:
            raise ValueError(f"Description validation failed: {error}")
    
    if hostname:
        is_valid, error = validate_hostname(hostname)
        if not is_valid:
            raise ValueError(f"Hostname validation failed: {error}")
    
    # Create credentials and client
    credentials = BasicCredentials(ak, sk)
    
    client = EcsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(EcsRegion.value_of(region)) \
        .build()
    
    try:
        # Build request
        request = UpdateServerRequest()
        request.server_id = server_id
        
        # Build modification parameters (only include user-specified parameters)
        update_kwargs = {}
        if name:
            update_kwargs['name'] = name
        if description is not None:
            update_kwargs['description'] = description
        if hostname:
            update_kwargs['hostname'] = hostname
        
        serverbody = UpdateServerOption(**update_kwargs)
        request.body = UpdateServerRequestBody(server=serverbody)
        
        # Execute update operation
        response = client.update_server(request)
        
        return {
            "success": True,
            "response": str(response),
            "server_id": server_id,
            "region": region,
            "updated_fields": {
                "name": name,
                "description": description,
                "hostname": hostname
            }
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
            "server_id": server_id,
            "region": region
        }


def main():
    """Command line entry point"""
    if len(sys.argv) < 2:
        print("Usage: python update_server.py <server_id> [--name <name>] [--description <description>] [--hostname <hostname>] [--region <region>]")
        print("")
        print("Modifiable parameters:")
        print("  --name        Cloud server name (can only contain Chinese characters, English letters, numbers, and _, -, ., length 1-64)")
        print("  --description Cloud server description (cannot contain <, >, length 0-85)")
        print("  --hostname    Cloud server hostname (length 1-64, has specific naming rules)")
        print("")
        print("Examples:")
        print("  python update_server.py 28f0xxx --name 'web-server-01'")
        print("  python update_server.py 28f0xxx --name 'web-01' --description 'Production server'")
        print("  python update_server.py 28f0xxx --hostname 'web-01' --region cn-south-1")
        sys.exit(1)
    
    # Parse arguments
    server_id = None
    region = "cn-north-4"  # Default region
    name = None
    description = None
    hostname = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--region" and i + 1 < len(sys.argv):
            region = sys.argv[i + 1]
            i += 2
        elif arg == "--name" and i + 1 < len(sys.argv):
            name = sys.argv[i + 1]
            i += 2
        elif arg == "--description" and i + 1 < len(sys.argv):
            description = sys.argv[i + 1]
            i += 2
        elif arg == "--hostname" and i + 1 < len(sys.argv):
            hostname = sys.argv[i + 1]
            i += 2
        elif not arg.startswith("--"):
            server_id = arg
            i += 1
        else:
            i += 1
    
    if not server_id:
        print("Error: Please provide server ID")
        sys.exit(1)
    
    if not name and description is None and not hostname:
        print("Error: Please provide at least one modification parameter (--name, --description, or --hostname)")
        sys.exit(1)
    
    print(f"Updating server information...")
    print(f"Server ID: {server_id}")
    print(f"Region: {region}")
    print(f"Modification parameters:")
    if name:
        print(f"  - Name: {name}")
    if description is not None:
        print(f"  - Description: {description}")
    if hostname:
        print(f"  - Hostname: {hostname}")
    print()
    
    result = update_server(server_id, region, name, description, hostname)
    
    if result["success"]:
        print("✅ Update successful")
        print(f"Response: {result['response']}")
    else:
        print("❌ Update failed")
        error = result["error"]
        print(f"Status code: {error['status_code']}")
        print(f"Request ID: {error['request_id']}")
        print(f"Error code: {error['error_code']}")
        print(f"Error message: {error['error_msg']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
