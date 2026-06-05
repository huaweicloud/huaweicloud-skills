#!/usr/bin/env python3
# coding: utf-8
"""Flexus L instance password reset tool"""

import os
import sys

from huaweicloudsdkecs.v2 import (
    ListServersDetailsRequest, ShowServerRequest,
    BatchResetServersPasswordRequest, BatchResetServersPasswordRequestBody, ServerId
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import AuthManager


class FlexusLClient:
    """Flexus L instance client"""
    
    def __init__(self, auth: AuthManager = None, region: str = "cn-north-4"):
        """Initialize client"""
        self.auth = auth or AuthManager()
        if not self.auth.is_configured():
            raise ValueError("Please provide AK/SK/Security_Token")
        self.region = region
    
    def list_servers(self, limit: int = 100):
        """List servers"""
        client = self.auth.get_ecs_client(self.region)
        return client.list_servers_details(ListServersDetailsRequest(limit=limit)).to_dict()
    
    def get_server(self, server_id: str):
        """Get server details"""
        client = self.auth.get_ecs_client(self.region)
        return client.show_server(ShowServerRequest(server_id=server_id)).to_dict()
    
    def reset_password(self, server_ids: list, new_password: str):
        """Reset instance login password"""
        client = self.auth.get_ecs_client(self.region)
        request = BatchResetServersPasswordRequest(body=BatchResetServersPasswordRequestBody(
            servers=[ServerId(id=sid) for sid in server_ids], new_password=new_password))
        response = client.batch_reset_servers_password(request)
        return True


def validate_password(password: str) -> bool:
    """Validate password complexity (8-26 chars, at least 3 character types, no weak passwords)"""
    if not 8 <= len(password) <= 26:
        print(f"ERROR: Password length must be 8-26 characters (current: {len(password)})")
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    if sum([has_upper, has_lower, has_digit, has_special]) < 3:
        print("ERROR: Password must contain at least 3 character types (upper/lower/digit/special)")
        return False
    
    for i in range(len(password) - 2):
        if password[i] == password[i+1] == password[i+2]:
            print("ERROR: Password cannot contain 3 consecutive identical characters")
            return False
    
    common_usernames = ["admin", "root", "user", "test", "password"]
    for username in common_usernames:
        if username in password.lower() or username[::-1] in password.lower():
            print(f"ERROR: Password cannot contain common username: {username}")
            return False
    
    if password.lower() in ["password", "12345678", "qwertyui", "abcdefgh"]:
        print("ERROR: Cannot use common weak passwords")
        return False
    
    return True


def main():
    """Command line entry: parse arguments and execute password operations"""
    if len(sys.argv) < 2:
        print("Usage: python password_unified.py <command> [args] [--ak <AK>] [--sk <SK>] [--security-token <TOKEN>]")
        print("Commands: test (test connection) / list (list servers) / reset --instance-id <ID> --password <PWD> (reset password)")
        sys.exit(1)
    
    region = os.environ.get("CLOUD_SDK_REGION") or os.environ.get("HUAWEICLOUD_SDK_REGION") or "cn-north-4"
    ak, sk, security_token = None, None, None
    cmd = None
    i = 1
    
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--ak" and i + 1 < len(sys.argv):
            ak, i = sys.argv[i + 1], i + 2
        elif arg == "--sk" and i + 1 < len(sys.argv):
            sk, i = sys.argv[i + 1], i + 2
        elif arg == "--security-token" and i + 1 < len(sys.argv):
            security_token, i = sys.argv[i + 1], i + 2
        elif arg == "--region" and i + 1 < len(sys.argv):
            region, i = sys.argv[i + 1], i + 2
        elif not arg.startswith("--"):
            if cmd is None:
                cmd = arg.lower()
            i += 1
        else:
            i += 1
    
    if cmd is None:
        print("ERROR: No command specified")
        sys.exit(1)
    
    auth = AuthManager(ak=ak, sk=sk, security_token=security_token)
    client = FlexusLClient(auth=auth, region=region)
    
    try:
        if cmd == "test":
            client.list_servers(limit=1)
            print("SUCCESS: Connection successful")
        elif cmd == "list":
            servers = client.list_servers().get('servers', [])
            print(f"\nFound {len(servers)} server(s):\n")
            for i, s in enumerate(servers, 1):
                print(f"{i}. {s.get('name', 'N/A'):<30} {s.get('id', 'N/A'):<40} {s.get('status', 'N/A')}")
        elif cmd == "reset":
            # Get --instance-id and --password from args
            server_id, password = None, None
            j = 1
            while j < len(sys.argv):
                if sys.argv[j] == "--instance-id" and j + 1 < len(sys.argv):
                    server_id = sys.argv[j + 1]
                    j += 2
                elif sys.argv[j] == "--password" and j + 1 < len(sys.argv):
                    password = sys.argv[j + 1]
                    j += 2
                else:
                    j += 1
            if not server_id or not password:
                print("ERROR: Usage: python password_unified.py reset --instance-id <ID> --password <PWD>")
                sys.exit(1)
            if not validate_password(password):
                sys.exit(1)
            print(f"Resetting password for: {server_id}")
            client.reset_password([server_id], password)
            print(f"SUCCESS: Password reset successful")
        else:
            print(f"ERROR: Unknown command: {cmd}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
