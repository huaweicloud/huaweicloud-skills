#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parameter conversion module (region/status)"""

from typing import Dict


class RegionConverter:
    """Region code converter"""
    
    # Region name to code mapping (Chinese names supported for user input)
    REGION_MAP = {
        "华北-北京四": "cn-north-4", "北京四": "cn-north-4", "Beijing4": "cn-north-4",
        "华南-广州": "cn-south-1", "广州": "cn-south-1", "Guangzhou": "cn-south-1",
        "华东-上海一": "cn-east-3", "上海一": "cn-east-3", "上海": "cn-east-3", "Shanghai": "cn-east-3",
        "西南-贵阳一": "cn-southwest-2", "贵阳一": "cn-southwest-2", "贵阳": "cn-southwest-2",
        "中国-香港": "ap-southeast-1", "香港": "ap-southeast-1", "HongKong": "ap-southeast-1",
        "亚太-新加坡": "ap-southeast-2", "新加坡": "ap-southeast-2", "Singapore": "ap-southeast-2",
    }
    
    # Code to Chinese name mapping (for display purposes)
    REGION_NAME_MAP = {
        "cn-north-4": "华北-北京四", "cn-south-1": "华南-广州", "cn-east-3": "华东-上海一",
        "cn-southwest-2": "西南-贵阳一", "ap-southeast-1": "中国-香港", "ap-southeast-2": "亚太-新加坡",
    }
    
    @classmethod
    def to_code(cls, region: str) -> str:
        """Convert region name to region code"""
        if region in cls.REGION_NAME_MAP:
            return region
        return cls.REGION_MAP.get(region, cls.REGION_MAP.get(region.lower(), region))
    
    @classmethod
    def to_name(cls, code: str) -> str:
        """Convert region code to region name"""
        return cls.REGION_NAME_MAP.get(code, code)


class StatusConverter:
    """Server status converter"""
    
    STATUS_MAP = {
        "ACTIVE": "Running", "SHUTOFF": "Stopped", "BUILD": "Building", "ERROR": "Error",
        "REBOOT": "Rebooting", "HARD_REBOOT": "Hard Rebooting", "MIGRATING": "Migrating",
    }
    
    @classmethod
    def to_display(cls, status: str) -> str:
        """Convert status code to display name"""
        return cls.STATUS_MAP.get(status, status)
    
    @classmethod
    def to_code(cls, status: str) -> str:
        """Convert display name to status code"""
        for code, name in cls.STATUS_MAP.items():
            if name == status:
                return code
        return status.upper()
