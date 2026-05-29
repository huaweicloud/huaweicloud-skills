#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter Conversion Module
For region code, status, and other parameter conversions
"""

from typing import Dict, Optional


class RegionConverter:
    """Region code converter"""
    
    # Region mapping: Chinese name -> region code
    REGION_MAP: Dict[str, str] = {
        # North China
        "华北-北京四": "cn-north-4",
        "北京四": "cn-north-4",
        "North-China-Beijing4": "cn-north-4",
        "Beijing4": "cn-north-4",
        
        # South China
        "华南-广州": "cn-south-1",
        "广州": "cn-south-1",
        "South-China-Guangzhou": "cn-south-1",
        "Guangzhou": "cn-south-1",
        
        # East China
        "华东-上海一": "cn-east-3",
        "上海一": "cn-east-3",
        "上海": "cn-east-3",
        "East-China-Shanghai1": "cn-east-3",
        "Shanghai1": "cn-east-3",
        "Shanghai": "cn-east-3",
        
        # Southwest China
        "西南-贵阳一": "cn-southwest-2",
        "贵阳一": "cn-southwest-2",
        "贵阳": "cn-southwest-2",
        "Southwest-China-Guiyang1": "cn-southwest-2",
        "Guiyang1": "cn-southwest-2",
        "Guiyang": "cn-southwest-2",
        
        # Asia Pacific
        "中国-香港": "ap-southeast-1",
        "香港": "ap-southeast-1",
        "HongKong": "ap-southeast-1",
        "亚太-新加坡": "ap-southeast-2",
        "新加坡": "ap-southeast-2",
        "Singapore": "ap-southeast-2", 
    }
    
    # Reverse mapping: region code -> Chinese name
    REGION_NAME_MAP: Dict[str, str] = {
        # North China
        "cn-north-4": "华北-北京四",
        
        # South China
        "cn-south-1": "华南-广州",
        
        # East China
        "cn-east-3": "华东-上海一",
        
        # Southwest China
        "cn-southwest-2": "西南-贵阳一",
        
        # Asia Pacific
        "ap-southeast-1": "中国-香港",
        "ap-southeast-2": "亚太-新加坡",
    }
    
    @classmethod
    def to_code(cls, region: str) -> str:
        """
        Convert region name to region code
        
        Args:
            region: Region name or code
        
        Returns:
            Region code
        """
        # If already a region code, return directly
        if region in cls.REGION_NAME_MAP:
            return region
        
        # Try to convert from Chinese name
        region_code = cls.REGION_MAP.get(region)
        if region_code:
            return region_code
        
        # Try lowercase matching
        region_lower = region.lower()
        for name, code in cls.REGION_MAP.items():
            if name.lower() == region_lower:
                return code
        
        # No match found, return original value (let API throw error)
        return region
    
    @classmethod
    def to_name(cls, region_code: str) -> str:
        """
        Convert region code to region name
        
        Args:
            region_code: Region code
        
        Returns:
            Region name
        """
        return cls.REGION_NAME_MAP.get(region_code, region_code)
    
    @classmethod
    def list_regions(cls) -> Dict[str, str]:
        """List all regions"""
        return cls.REGION_NAME_MAP.copy()


class StatusConverter:
    """Server status converter"""
    
    STATUS_MAP: Dict[str, str] = {
        "ACTIVE": "运行中",
        "SHUTOFF": "已关机",
        "BUILD": "创建中",
        "REBUILD": "重建中",
        "ERROR": "错误",
        "HARD_REBOOT": "硬重启中",
        "REBOOT": "重启中",
        "MIGRATING": "迁移中",
        "PAUSED": "已暂停",
        "RESCUE": "救援模式",
        "RESIZED": "已调整规格",
        "SHELVED": "已搁置",
        "SHELVED_OFFLOADED": "已搁置并卸载",
        "SOFT_DELETED": "已软删除",
        "SUSPENDED": "已挂起",
        "UNKNOWN": "未知",
        "VERIFY_RESIZE": "验证调整规格中",
    }
    
    @classmethod
    def to_chinese(cls, status: str) -> str:
        """
        Convert status code to Chinese
        
        Args:
            status: Status code
        
        Returns:
            Chinese status
        """
        return cls.STATUS_MAP.get(status, status)
    
    @classmethod
    def to_code(cls, status: str) -> str:
        """
        Convert Chinese status to status code
        
        Args:
            status: Chinese status
        
        Returns:
            Status code
        """
        # Reverse mapping
        for code, name in cls.STATUS_MAP.items():
            if name == status:
                return code
        return status.upper()


def main():
    """Command line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parameter Conversion Tool")
    parser.add_argument("command", choices=["region", "status", "list-regions"], help="Operation command")
    parser.add_argument("value", nargs="?", help="Value to convert")
    
    args = parser.parse_args()
    
    if args.command == "list-regions":
        print("Supported Regions:")
        for code, name in RegionConverter.list_regions().items():
            print(f"  {code:20s} -> {name}")
        return
    
    if not args.value:
        print("❌ Please provide a value to convert")
        return
    
    if args.command == "region":
        code = RegionConverter.to_code(args.value)
        name = RegionConverter.to_name(args.value)
        print(f"Input: {args.value}")
        print(f"Region Code: {code}")
        print(f"Region Name: {name}")
    
    elif args.command == "status":
        chinese = StatusConverter.to_chinese(args.value)
        code = StatusConverter.to_code(args.value)
        print(f"Input: {args.value}")
        print(f"Status Code: {code}")
        print(f"Chinese Status: {chinese}")


if __name__ == "__main__":
    main()
