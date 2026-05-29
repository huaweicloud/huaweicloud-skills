#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Password Reset Tool (Unified Version)
Supports batch reset of Flexus L instance passwords
Only supports AK/SK authentication (using Huawei Cloud SDK)
"""

import os
import sys
from typing import Dict, List, Optional


class HuaweiFlexusLAPI:
    """Huawei Cloud Flexus L API Client - AK/SK authentication only"""
    
    def __init__(self, ak: str, sk: str, region: str = "cn-north-4"):
        """
        Initialize Huawei Cloud Flexus L API client
        
        Args:
            ak: Access Key ID (AK/SK authentication)
            sk: Secret Access Key (AK/SK authentication)
            region: Region, default cn-north-4
        """
        if not ak or not sk:
            raise ValueError("AK and SK credentials must be provided")
        
        self.ak = ak
        self.sk = sk
        self.region = region
        
        # Check if Huawei Cloud SDK is installed
        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
            from huaweicloudsdkecs.v2 import EcsClient
            self.has_sdk = True
        except ImportError:
            self.has_sdk = False
            print("❌ Huawei Cloud SDK not installed")
            print("Please install Huawei Cloud SDK with the following command:")
            print("   pip install -i https://mirrors.huaweicloud.com/repository/pypi/simple huaweicloudsdkcore huaweicloudsdkecs")
            raise
        
        print(f"✅ Using Huawei Cloud SDK (AK/SK authentication)")
        print(f"   Region: {region}")
    
    def _get_client(self):
        """Get Huawei Cloud SDK client"""
        if not self.has_sdk:
            raise ImportError("Huawei Cloud SDK not installed, please install dependencies first")
        
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
        from huaweicloudsdkecs.v2 import EcsClient
        
        credentials = BasicCredentials(self.ak, self.sk)
        client = EcsClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(EcsRegion.value_of(self.region)) \
            .build()
        
        return client
    
    def list_flexusl_servers(self, limit: int = 100, status: str = None) -> Dict:
        """Get Flexus L server list"""
        if not self.has_sdk:
            raise ImportError("Huawei Cloud SDK not installed, please install dependencies first")
        
        from huaweicloudsdkecs.v2 import ListServersDetailsRequest
        
        client = self._get_client()
        
        try:
            request = ListServersDetailsRequest()
            request.limit = limit
            if status:
                request.status = status
            
            response = client.list_servers_details(request)
            return response.to_dict()
        except Exception as e:
            raise Exception(f"Failed to get server list: {e}")
    
    def get_flexusl_server_detail(self, server_id: str) -> Dict:
        """Get Flexus L server details"""
        if not self.has_sdk:
            raise ImportError("Huawei Cloud SDK not installed, please install dependencies first")
        
        from huaweicloudsdkecs.v2 import ShowServerRequest
        
        client = self._get_client()
        
        try:
            request = ShowServerRequest()
            request.server_id = server_id
            
            response = client.show_server(request)
            return response.to_dict()
        except Exception as e:
            print(f"⚠️  Failed to get server details: {e}")
            return {}
    
    def reset_flexusl_password(self, server_ids: List[str], new_password: str) -> bool:
        """Reset Flexus L server password"""
        if not self.has_sdk:
            raise ImportError("Huawei Cloud SDK not installed, please install dependencies first")
        
        from huaweicloudsdkecs.v2 import BatchResetServersPasswordRequest, ServerId, BatchResetServersPasswordRequestBody
        
        client = self._get_client()
        
        try:
            # Build server ID list
            list_servers_body = [ServerId(id=server_id) for server_id in server_ids]
            
            request = BatchResetServersPasswordRequest()
            request.body = BatchResetServersPasswordRequestBody(
                servers=list_servers_body,
                new_password=new_password
            )
            
            print(f"Resetting password for {len(server_ids)} server(s)...")
            response = client.batch_reset_servers_password(request)
            
            # Check response
            if response:
                print(f"✅ Password reset request submitted")
                
                # Try to get job ID
                try:
                    response_dict = response.to_dict()
                    if 'job_id' in response_dict:
                        print(f"   Job ID: {response_dict['job_id']}")
                    elif 'response' in response_dict:
                        print(f"   Response: Operation successful")
                except Exception as e:
                    print(f"   Response parsed successfully, but unable to get job ID: {e}")
                
                return True
            else:
                print("⚠️  Password reset request sent, but no valid response received")
                return False
                
        except Exception as e:
            error_msg = str(e)
            if "Invalid AK/SK" in error_msg or "authentication" in error_msg.lower():
                raise Exception(f"Authentication failed: {error_msg}\nPlease check if AK/SK is correct and if the account has Flexus L operation permissions")
            elif "not active" in error_msg.lower():
                raise Exception(f"Server status incorrect: {error_msg}\nOnly ACTIVE status servers can reset password")
            elif "complexity" in error_msg.lower() or "password" in error_msg.lower():
                raise Exception(f"Password does not meet Huawei Cloud complexity requirements: {error_msg}")
            else:
                raise Exception(f"Password reset failed: {error_msg}")


def validate_password_complexity(password: str) -> bool:
    """
    Validate password complexity
    
    Huawei Cloud password requirements:
    1. Length 8-26 characters
    2. Must contain at least 3 of: uppercase letters, lowercase letters, numbers, special characters
    3. Cannot contain username or reversed username
    4. Cannot contain 3 or more consecutive identical characters
    """
    # Check length
    if len(password) < 8 or len(password) > 26:
        print(f"❌ Password length must be between 8-26 characters (current: {len(password)})")
        return False
    
    # Check character types
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    # Must contain at least 3 character types
    char_types = sum([has_upper, has_lower, has_digit, has_special])
    if char_types < 3:
        print(f"❌ Password must contain at least 3 of: uppercase letters, lowercase letters, numbers, special characters")
        print(f"   Current contains: {'uppercase ' if has_upper else ''}{'lowercase ' if has_lower else ''}{'numbers ' if has_digit else ''}{'special characters ' if has_special else ''}")
        print(f"   Suggested format: 8-26 chars, 3+ types (upper/lower/digit/special)")
        return False
    
    # Check consecutive identical characters
    for i in range(len(password) - 2):
        if password[i] == password[i+1] == password[i+2]:
            print(f"❌ Password cannot contain 3 or more consecutive identical characters")
            return False
    
    # Check if contains common usernames (simplified check)
    common_usernames = ["admin", "root", "user", "test", "password"]
    for username in common_usernames:
        if username in password.lower() or username[::-1] in password.lower():
            print(f"❌ Password cannot contain common username: {username}")
            return False
    
    # Check if contains simple patterns
    if password.lower() in ["password", "12345678", "qwertyui", "abcdefgh"]:
        print(f"❌ Password cannot use common weak passwords")
        return False
    
    return True


def main():
    """Command line entry point"""
    if len(sys.argv) < 2:
        print("Usage: python password_unified.py <command> [args]")
        print("\nCommands:")
        print("  test                           - Test connection")
        print("  list                           - List Flexus L servers")
        print("  reset <server_id> <password>   - Reset server password")
        print("\nExamples:")
        print("  python password_unified.py test")
        print("  python password_unified.py list")
        print("  python password_unified.py reset 1d8c397c-xxx '<YOUR_PASSWORD>'")
        print("\nEnvironment variables:")
        print("  CLOUD_SDK_AK or HUAWEICLOUD_SDK_AK  - Access Key")
        print("  CLOUD_SDK_SK or HUAWEICLOUD_SDK_SK  - Secret Key")
        print("  CLOUD_SDK_REGION or HUAWEICLOUD_SDK_REGION - Region (default: cn-north-4)")
        sys.exit(1)
    
    # Get credentials from environment variables
    ak = os.environ.get("CLOUD_SDK_AK") or os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("CLOUD_SDK_SK") or os.environ.get("HUAWEICLOUD_SDK_SK")
    region = os.environ.get("CLOUD_SDK_REGION") or os.environ.get("HUAWEICLOUD_SDK_REGION") or "cn-north-4"
    
    if not ak or not sk:
        print("❌ Please set environment variables CLOUD_SDK_AK and CLOUD_SDK_SK")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        # Create API client
        api = HuaweiFlexusLAPI(ak=ak, sk=sk, region=region)
        
        if command == "test":
            # Test connection
            print("\n🔍 Testing connection...")
            servers = api.list_flexusl_servers(limit=1)
            print("✅ Connection successful!")
            
        elif command == "list":
            # List servers
            print("\n📋 Listing Flexus L servers...")
            servers = api.list_flexusl_servers(limit=100)
            
            if servers and 'servers' in servers:
                server_list = servers['servers']
                print(f"\nFound {len(server_list)} servers:\n")
                print(f"{'No.':<6} {'Name':<30} {'ID':<40} {'Status':<15}")
                print("-" * 91)
                
                for i, server in enumerate(server_list, 1):
                    name = server.get('name', 'N/A')
                    server_id = server.get('id', 'N/A')
                    status = server.get('status', 'N/A')
                    print(f"{i:<6} {name:<30} {server_id:<40} {status:<15}")
            else:
                print("No servers found")
                
        elif command == "reset":
            # Reset password
            if len(sys.argv) < 4:
                print("❌ Usage: python password_unified.py reset <server_id> <password>")
                sys.exit(1)
            
            server_id = sys.argv[2]
            new_password = sys.argv[3]
            
            # Validate password complexity
            print("\n🔍 Validating password complexity...")
            if not validate_password_complexity(new_password):
                sys.exit(1)
            
            print("✅ Password complexity validation passed")
            
            # Get server detail
            print(f"\n🔍 Getting server detail: {server_id}")
            server_detail = api.get_flexusl_server_detail(server_id)
            
            if server_detail and 'server' in server_detail:
                server = server_detail['server']
                server_name = server.get('name', 'N/A')
                server_status = server.get('status', 'N/A')
                print(f"   Name: {server_name}")
                print(f"   Status: {server_status}")
                
                if server_status != 'ACTIVE':
                    print(f"\n⚠️  Warning: Server status is {server_status}, not ACTIVE")
                    print("   Password reset may fail for non-ACTIVE servers")
            
            # Reset password
            print(f"\n🔑 Resetting password...")
            success = api.reset_flexusl_password([server_id], new_password)
            
            if success:
                print("\n" + "=" * 50)
                print("✅ Password reset successful!")
                print("=" * 50)
                print(f"Server ID: {server_id}")
                print(f"New password: {new_password}")
                print("\n⚠️  Please save the new password securely!")
            else:
                print("\n❌ Password reset failed")
                sys.exit(1)
                
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
