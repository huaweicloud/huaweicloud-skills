#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AK/SK Authentication Management Module
For Huawei Cloud API authentication
"""

import os
import sys
from typing import Optional, Tuple


class AuthManager:
    """AK/SK Authentication Manager"""
    
    ENV_AK = "CLOUD_SDK_AK"
    ENV_SK = "CLOUD_SDK_SK"
    
    def __init__(self, ak: Optional[str] = None, sk: Optional[str] = None):
        """
        Initialize authentication manager
        
        Args:
            ak: Access Key (optional, read from environment variables by default)
            sk: Secret Key (optional, read from environment variables by default)
        """
        self.ak = ak or os.environ.get(self.ENV_AK)
        self.sk = sk or os.environ.get(self.ENV_SK)
    
    def get_ecs_client(self, region: str):
        """
        Get Flexus L client
        
        Args:
            region: Region code
            
        Returns:
            Flexus L client instance
        """
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkecs.v2 import ecs_client
        from huaweicloudsdkcore.region.region import Region
        
        credentials = BasicCredentials(ak=self.ak, sk=self.sk)
        
        # Create region object
        region_obj = Region(region, f"https://ecs.{region}.myhuaweicloud.com")
        
        client = ecs_client.EcsClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(region_obj) \
            .build()
        
        return client
    
    def get_bss_client(self, region: str):
        """
        Get BSS client
        
        Args:
            region: Region code
            
        Returns:
            BSS client instance
        """
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkbss.v2 import bss_client
        from huaweicloudsdkcore.region.region import Region
        
        credentials = GlobalCredentials(ak=self.ak, sk=self.sk)
        
        # Create region object
        region_obj = Region(region, f"https://bss.{region}.myhuaweicloud.com")
        
        client = bss_client.BssClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(region_obj) \
            .build()
        
        return client
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get AK/SK credentials
        
        Returns:
            (ak, sk) tuple
        """
        return (self.ak, self.sk)
    
    def is_configured(self) -> bool:
        """Check if credentials are configured"""
        return bool(self.ak and self.sk)
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate credentials
        
        Returns:
            (is_valid, message) tuple
        """
        if not self.is_configured():
            return (False, "❌ No credential environment variables detected, please configure AK/SK first")
        
        # Try to connect to Huawei Cloud API to validate credentials
        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkcore.http.http_client import HttpHandler
            from huaweicloudsdkecs.v2 import ecs_client
            
            # Create credentials object
            credentials = BasicCredentials(ak=self.ak, sk=self.sk)
            
            # Create Flexus L client (using default region)
            client = ecs_client.EcsClient.new_builder() \
                .with_credentials(credentials) \
                .with_region("cn-north-4") \
                .build()
            
            # Try to list servers (only 1 record)
            request = ecs_client.ListServersDetailsRequest(limit=1)
            response = client.list_servers_details(request)
            
            return (True, "✅ Credential validation successful")
        
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                return (False, "❌ Credentials invalid or expired, please check if AK/SK is correct")
            elif "403" in error_msg or "Forbidden" in error_msg:
                return (False, "❌ Insufficient permissions, please check if account has Flexus L operation permissions")
            else:
                return (False, f"❌ Credential validation failed: {error_msg}")
    
    def set_env_credentials(self, ak: str, sk: str):
        """
        Set environment variable credentials (only valid for current process)
        
        Args:
            ak: Access Key
            sk: Secret Key
        """
        os.environ[self.ENV_AK] = ak
        os.environ[self.ENV_SK] = sk
        self.ak = ak
        self.sk = sk
    
    @staticmethod
    def print_help():
        """Print help information"""
        help_text = """
🔐 AK/SK Credential Configuration Guide

Get AK/SK:
1. Login to Huawei Cloud Management Console
2. Top right username → My Credentials → Access Keys
3. Create Access Key → Download CSV file

Configuration (temporary, only valid for current session):
  export CLOUD_SDK_AK="your_access_key"
  export CLOUD_SDK_SK="your_secret_key"

Verify configuration:
  env | grep CLOUD_SDK

⚠️ Security Reminder:
- Do not save AK/SK to configuration files
- Do not write to ~/.bashrc, ~/.profile, etc.
- Recommend clearing after use: unset CLOUD_SDK_AK CLOUD_SDK_SK
"""
        print(help_text)


def main():
    """Command line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AK/SK Authentication Management")
    parser.add_argument("command", choices=["test", "help"], help="Operation command")
    parser.add_argument("--ak", help="Access Key")
    parser.add_argument("--sk", help="Secret Key")
    
    args = parser.parse_args()
    
    if args.command == "help":
        AuthManager.print_help()
        return
    
    if args.command == "test":
        auth = AuthManager(ak=args.ak, sk=args.sk)
        
        if not auth.is_configured():
            print("❌ No credential environment variables detected")
            print("\nPlease configure AK/SK first:")
            print('  export CLOUD_SDK_AK="your_access_key"')
            print('  export CLOUD_SDK_SK="your_secret_key"')
            sys.exit(1)
        
        print("🔍 Validating credentials...")
        is_valid, message = auth.validate()
        print(message)
        
        if is_valid:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
