#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified authentication module - All scripts get credentials and clients through AuthManager

Environment variables:
- HW_ACCESS_KEY      (AK)
- HW_SECRET_KEY      (SK)
- HW_SECURITY_TOKEN  (Security Token, optional)
"""

import os
from typing import Optional, Tuple

from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkecs.v2 import EcsClient, ListServersDetailsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.region.bss_region import BssRegion
from huaweicloudsdkconfig.v1 import ConfigClient
from huaweicloudsdkconfig.v1.region.config_region import ConfigRegion


class AuthManager:
    """AK/SK Authentication Manager"""
    
    ENV_AK = "HW_ACCESS_KEY"
    ENV_SK = "HW_SECRET_KEY"
    ENV_TOKEN = "HW_SECURITY_TOKEN"
    
    def __init__(self, ak: Optional[str] = None, sk: Optional[str] = None, security_token: Optional[str] = None, project_id: Optional[str] = None):
        """Initialize authentication manager, supports long-term and temporary credentials"""
        self.ak = ak or os.environ.get(self.ENV_AK)
        self.sk = sk or os.environ.get(self.ENV_SK)
        self.security_token = security_token or os.environ.get(self.ENV_TOKEN)
        self.project_id = project_id

        # If Security Token exists, AK/SK are also temporary
        self.is_temporary = bool(self.security_token)

    def get_basic_credentials(self):
        """Get regional service credentials (ECS, Flexus L, etc.)"""
        try:
            if self.security_token:
                # Temporary credentials: AK/SK + Security Token
                credentials = BasicCredentials(self.ak, self.sk, self.project_id).with_security_token(self.security_token)
            else:
                # Long-term credentials: permanent AK/SK
                credentials = BasicCredentials(self.ak, self.sk, self.project_id)
            return credentials
        except Exception as e:
            raise ValueError(f"Failed to create BasicCredentials: {e}")
    
    def get_global_credentials(self):
        """Get global service credentials (BSS, Config, IAM, etc.)"""
        try:
            if self.security_token:
                # Temporary credentials
                credentials = GlobalCredentials(self.ak, self.sk).with_security_token(self.security_token)
            else:
                # Long-term credentials
                credentials = GlobalCredentials(self.ak, self.sk)
            return credentials
        except Exception as e:
            raise ValueError(f"Failed to create GlobalCredentials: {e}")

    def get_ecs_client(self, region: str):
        """Get ECS client (for Flexus L instance operations)"""
        return EcsClient.new_builder() \
            .with_credentials(self.get_basic_credentials()) \
            .with_region(EcsRegion.value_of(region)) \
            .build()
    
    def get_bss_client(self, region: str = "cn-north-1"):
        """Get BSS client (for traffic package queries)"""
        return BssClient.new_builder() \
            .with_credentials(self.get_global_credentials()) \
            .with_region(BssRegion.value_of(region)) \
            .build()
    
    def get_config_client(self, region: str = "cn-north-4"):
        """Get Config client (for resource configuration queries)"""
        config = HttpConfig.get_default_config()
        config.ignore_ssl_verification = True
        return ConfigClient.new_builder() \
            .with_http_config(config) \
            .with_credentials(self.get_global_credentials()) \
            .with_region(ConfigRegion.value_of(region)) \
            .build()

    def get_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get current credential tuple (AK, SK, SecurityToken)"""
        return (self.ak, self.sk, self.security_token)
    
    def is_configured(self) -> bool:
        """Check if AK/SK is configured"""
        return bool(self.ak and self.sk)
    
    def has_security_token(self) -> bool:
        """Check if Security Token exists (indicates temporary credentials)"""
        return bool(self.security_token)
    
    def is_temporary_credentials(self) -> bool:
        """Check if using temporary credentials (AK/SK + Security Token)"""
        return self.is_temporary
    
    def validate(self) -> Tuple[bool, str]:
        """Validate credentials"""
        if not self.is_configured():
            return (False, "ERROR: AK/SK environment variables not detected")
        try:
            client = self.get_ecs_client("cn-north-4")
            client.list_servers_details(ListServersDetailsRequest(limit=1))
            auth_type = "AK/SK/Security Token" if self.security_token else "AK/SK"
            return (True, f"SUCCESS: Credentials validated ({auth_type})")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                return (False, "ERROR: Credentials invalid or expired")
            elif "403" in error_msg:
                return (False, "ERROR: Insufficient permissions")
            return (False, f"ERROR: Validation failed: {error_msg}")
