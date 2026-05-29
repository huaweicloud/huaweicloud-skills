#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud Flexus L Instance Query Tool
Supports querying instance list across all regions, instance details, and traffic packages
"""

import os
import sys
import argparse
from typing import Optional, List
from datetime import datetime, timezone, timedelta

# Add script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from auth import AuthManager
from params import RegionConverter, StatusConverter


def utc_to_beijing(utc_time_str: str) -> str:
    """Convert UTC time string to Beijing time (UTC+8)"""
    if not utc_time_str or utc_time_str == 'N/A':
        return 'N/A'
    try:
        # Parse UTC time (format: 2026-05-27T03:02:10Z)
        if utc_time_str.endswith('Z'):
            utc_time_str = utc_time_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(utc_time_str)
        # Convert to Beijing time
        beijing_tz = timezone(timedelta(hours=8))
        beijing_time = dt.astimezone(beijing_tz)
        return beijing_time.strftime('%Y-%m-%d %H:%M:%S (北京时间)')
    except Exception:
        return utc_time_str

# Import Config client
try:
    from config_client import HuaweiConfigClient
    CONFIG_CLIENT_AVAILABLE = True
except ImportError:
    CONFIG_CLIENT_AVAILABLE = False

# Import Huawei Cloud SDK
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkconfig.v1.region.config_region import ConfigRegion
from huaweicloudsdkconfig.v1 import ConfigClient, ListAllResourcesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion
from huaweicloudsdkbss.v2 import BssClient, ListFreeResourceUsagesRequest, ListFreeResourceUsagesReq


# Measure ID to unit mapping
MEASURE_UNITS = {
    10: "GB",  # Traffic unit
}


class InstanceQueryClient:
    """Instance query client"""
    
    def __init__(self, ak: Optional[str] = None, sk: Optional[str] = None, region: str = "cn-north-4"):
        """
        Initialize client
        
        Args:
            ak: Access Key
            sk: Secret Key
            region: Region code
        """
        self.region = RegionConverter.to_code(region)
        self.auth = AuthManager(ak=ak, sk=sk)
        
        # Initialize SDK client
        self.ecs_client = self.auth.get_ecs_client(self.region)
    
    def list_all_regions(self, resource_type="hcss.l-instance"):
        """
        Query resources across all regions using Config service
        
        Args:
            resource_type: Resource type, default hcss.l-instance
        """
        if not CONFIG_CLIENT_AVAILABLE:
            print("❌ Config client not available, please install huaweicloudsdkconfig")
            print("Install command: pip3 install huaweicloudsdkconfig")
            sys.exit(1)
        
        print(f"📋 Querying all resources using Config service (type: {resource_type})...\n")
        
        try:
            # Create Config client
            config_client = HuaweiConfigClient(ak=self.auth.ak, sk=self.auth.sk, region=self.region)
            
            # Query resources
            result = config_client.list_resources(resource_type=resource_type, limit=1000)
            
            if not result["success"]:
                print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
                sys.exit(1)
            
            resources = result["resources"]
            total = result["total"]
            
            if not resources:
                print(f"❌ No {resource_type} resources found")
                return
            
            print(f"\n{'='*120}")
            print(f"📊 Query Result: {total} {resource_type} resources")
            print(f"{'='*120}")
            print(f"{'No.':<6} {'Resource Name':<60} {'Resource ID':<42} {'Region':<15} {'Status':<10}")
            print("-" * 120)
            
            for i, resource in enumerate(resources, 1):
                name = getattr(resource, 'name', 'N/A')
                resource_id = getattr(resource, 'id', 'N/A')
                region_id = getattr(resource, 'region_id', 'N/A')
                status = getattr(resource, 'status', 'N/A')
                
                print(f"{i:<6} {name:<60} {resource_id:<42} {region_id:<15} {status:<10}")
            
            print("=" * 120)
            print(f"✅ Total: {total} resources")
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def query_instance(self, instance_id: str):
        """
        Query single instance details
        
        Args:
            instance_id: Instance ID
        """
        print(f"🔍 Querying instance details (ID: {instance_id}, Region: {RegionConverter.to_name(self.region)} [{self.region}])...")
        
        try:
            from huaweicloudsdkecs.v2.model.show_server_request import ShowServerRequest
            
            request = ShowServerRequest(server_id=instance_id)
            response = self.ecs_client.show_server(request)
            
            server = response.server
            
            print("\n" + "=" * 80)
            print("Instance Details")
            print("=" * 80)
            
            # Basic information
            print("\n[Basic Information]")
            print(f"  Instance ID:     {server.id}")
            print(f"  Instance Name:   {server.name}")
            print(f"  Status:          {StatusConverter.to_chinese(server.status)}")
            print(f"  Region:          {RegionConverter.to_name(self.region)} [{self.region}]")
            
            # Description
            if hasattr(server, 'description') and server.description:
                print(f"  Description:     {server.description}")
            
            # Flavor information
            print("\n[Flavor Information]")
            print(f"  Flavor:          {server.flavor.name if server.flavor else 'N/A'}")
            print(f"  Flavor ID:       {server.flavor.id if server.flavor else 'N/A'}")
            
            # Image information
            print("\n[Image Information]")
            if server.image:
                print(f"  Image ID:        {server.image.id if hasattr(server.image, 'id') else 'N/A'}")
            else:
                print(f"  Image:           N/A")
            
            # Network information
            print("\n[Network Information]")
            if hasattr(server, 'addresses') and server.addresses:
                for network_name, addresses in server.addresses.items():
                    print(f"  Network: {network_name}")
                    for addr in addresses:
                        version = addr.version if hasattr(addr, 'version') else 'N/A'
                        ip_addr = addr.addr if hasattr(addr, 'addr') else 'N/A'
                        print(f"    - IPv{version}: {ip_addr}")
            else:
                print(f"  Network:         N/A")
            
            # Time information
            print("\n[Time Information]")
            created_time = server.created if hasattr(server, 'created') else 'N/A'
            updated_time = server.updated if hasattr(server, 'updated') else 'N/A'
            print(f"  Created:         {utc_to_beijing(created_time)}")
            print(f"  Updated:         {utc_to_beijing(updated_time)}")
            
            # User and project information
            print("\n[User and Project Information]")
            print(f"  User ID:         {server.user_id if hasattr(server, 'user_id') else 'N/A'}")
            print(f"  Tenant ID:       {server.tenant_id if hasattr(server, 'tenant_id') else 'N/A'}")
            
            # Host information
            print("\n[Host Information]")
            if hasattr(server, 'metadata') and server.metadata:
                hostname = server.metadata.get('hostname', 'N/A')
                print(f"  Hostname:        {hostname}")
            else:
                print(f"  Hostname:        N/A")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def list_free_resources(self, resource_type: str = "hcss.l-instance"):
        """
        Query all Flexus L instance resources (including traffic package ID and Flexus L instance ID)
        
        Args:
            resource_type: Resource type, default hcss.l-instance
        """
        print(f"📋 Querying Flexus L instance resources (type: {resource_type})...\n")
        
        try:
            # Create Config client
            credentials = GlobalCredentials(self.auth.ak, self.auth.sk)
            
            client = ConfigClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(ConfigRegion.value_of(self.region)) \
                .build()
            
            # Build request
            request = ListAllResourcesRequest()
            request.type = resource_type
            
            # Execute query
            response = client.list_all_resources(request)
            
            # Parse results
            instances = []
            
            for resource in response.resources:
                # Initialize resource dict
                resources_dict = {
                    "parent_resource_id": resource.id,
                    "parent_resource_name": resource.name,
                    "cbc_logical_resource_type": None,
                    "cbc_physical_resource_id": None,  # Traffic package ID
                    "ecs_logical_resource_type": None,
                    "ecs_physical_resource_id": None   # ECS instance ID
                }
                
                properties = resource.properties
                if properties and "resources" in properties:
                    for sub_res in properties["resources"]:
                        # Get traffic package resource
                        if sub_res.get("logical_resource_type") == "huaweicloudinternal_cbc_freeresource":
                            resources_dict["cbc_logical_resource_type"] = sub_res.get("logical_resource_type")
                            resources_dict["cbc_physical_resource_id"] = sub_res.get("physical_resource_id")
                        # Get Flexus L instance
                        if sub_res.get("logical_resource_type") == "huaweicloudinternal_ecs_instance":
                            resources_dict["ecs_logical_resource_type"] = sub_res.get("logical_resource_type")
                            resources_dict["ecs_physical_resource_id"] = sub_res.get("physical_resource_id")
                
                # Only add instances with traffic packages
                if resources_dict["cbc_physical_resource_id"]:
                    instances.append(resources_dict)
            
            if not instances:
                print(f"❌ No {resource_type} resources found")
                return
            
            print(f"\n{'='*130}")
            print(f"📊 Query Result: {len(instances)} {resource_type} resources")
            print(f"{'='*130}")
            print(f"{'No.':^6} | {'Instance Name':^25} | {'Flexus L Instance ID (Server Operations)':^38} | {'Traffic Package ID (Traffic Query)':^38}")
            print("-" * 130)
            
            for i, inst in enumerate(instances, 1):
                name = inst.get("parent_resource_name", "unnamed")
                name = name[:23] + ".." if len(name) > 25 else name
                
                ecs_id = inst.get("ecs_physical_resource_id", "-") or "-"
                cbc_id = inst.get("cbc_physical_resource_id", "-")
                
                print(f"{i:^6} | {name:^25} | {ecs_id} | {cbc_id}")
            
            print("=" * 130)
            print(f"✅ Total: {len(instances)} resources")
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def query_free_resource_usage(self, free_resource_ids: List[str]):
        """
        Query traffic package remaining quota
        
        Args:
            free_resource_ids: Traffic package ID list
        """
        print(f"📊 Querying usage for {len(free_resource_ids)} traffic packages...\n")
        
        try:
            # Create BSS client (fixed to Beijing-1 region)
            credentials = GlobalCredentials(self.auth.ak, self.auth.sk)
            
            client = BssClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(BssRegion.value_of("cn-north-1")) \
                .build()
            
            # Build request
            request = ListFreeResourceUsagesRequest()
            request.body = ListFreeResourceUsagesReq(
                free_resource_ids=free_resource_ids
            )
            
            # Execute query
            response = client.list_free_resource_usages(request)
            
            # Parse results
            usages = []
            for item in response.free_resources:
                # Get unit
                measure_id = item.measure_id if hasattr(item, 'measure_id') else 10
                unit = MEASURE_UNITS.get(measure_id, "GB")
                
                # Calculate usage
                original_amount = item.original_amount if hasattr(item, 'original_amount') else 0
                amount = item.amount if hasattr(item, 'amount') else 0
                used = original_amount - amount
                usage_rate = (used / original_amount * 100) if original_amount > 0 else 0
                
                usage_info = {
                    "free_resource_id": item.free_resource_id,
                    "free_resource_type_name": item.free_resource_type_name if hasattr(item, 'free_resource_type_name') else "unknown",
                    "usage_type_name": item.usage_type_name if hasattr(item, 'usage_type_name') else "unknown",
                    "original_amount": original_amount,
                    "amount": amount,
                    "used": used,
                    "unit": unit,
                    "usage_rate": round(usage_rate, 2),
                    "start_time": item.start_time if hasattr(item, 'start_time') else None,
                    "end_time": item.end_time if hasattr(item, 'end_time') else None,
                }
                
                usages.append(usage_info)
            
            if not usages:
                print("❌ No traffic package usage records found")
                return
            
            print(f"{'='*120}")
            print(f"{'Traffic Package ID':^40} | {'Type':^20} | {'Used':^12} | {'Total':^12} | {'Remaining':^12} | {'Usage Rate':^8}")
            print("=" * 120)
            
            for usage in usages:
                free_resource_id = usage["free_resource_id"]
                type_name = usage["free_resource_type_name"][:18] if len(usage["free_resource_type_name"]) > 20 else usage["free_resource_type_name"]
                
                # Format display
                quota = f"{usage['original_amount']:.2f} {usage['unit']}"
                used = f"{usage['used']:.2f} {usage['unit']}"
                remaining = f"{usage['amount']:.2f} {usage['unit']}"
                rate = f"{usage['usage_rate']:.1f}%"
                
                print(f"{free_resource_id:^40} | {type_name:^20} | {used:^12} | {quota:^12} | {remaining:^12} | {rate:^8}")
            
            print("=" * 120)
            
            # Show detailed information
            print("\n[Validity Period]")
            for usage in usages:
                if usage["start_time"] and usage["end_time"]:
                    print(f"  Traffic Package {usage['free_resource_id'][:8]}... Valid: {usage['start_time']} ~ {usage['end_time']}")
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def query_traffic_by_region(self, target_region: str, resource_type: str = "hcss.l-instance"):
        """
        Query traffic package information by region
        
        Args:
            target_region: Target region code
            resource_type: Resource type, default hcss.l-instance
        """
        print(f"📋 Querying Flexus L instance resources in {target_region} region...\n")
        
        try:
            # Step 1: Query all Flexus L instance resources
            credentials = GlobalCredentials(self.auth.ak, self.auth.sk)
            
            client = ConfigClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(ConfigRegion.value_of(self.region)) \
                .build()
            
            request = ListAllResourcesRequest()
            request.type = resource_type
            
            response = client.list_all_resources(request)
            
            # Parse results, filter instances in specified region
            instances = []
            
            for resource in response.resources:
                # Get region information
                region_id = getattr(resource, 'region_id', None)
                
                # Filter instances in specified region
                if region_id != target_region:
                    continue
                
                # Initialize resource dict
                resources_dict = {
                    "parent_resource_id": resource.id,
                    "parent_resource_name": resource.name,
                    "region_id": region_id,
                    "cbc_physical_resource_id": None,  # Traffic package ID
                    "ecs_physical_resource_id": None   # ECS instance ID
                }
                
                properties = resource.properties
                if properties and "resources" in properties:
                    for sub_res in properties["resources"]:
                        # Get traffic package resource
                        if sub_res.get("logical_resource_type") == "huaweicloudinternal_cbc_freeresource":
                            resources_dict["cbc_physical_resource_id"] = sub_res.get("physical_resource_id")
                        # Get Flexus L instance
                        if sub_res.get("logical_resource_type") == "huaweicloudinternal_ecs_instance":
                            resources_dict["ecs_physical_resource_id"] = sub_res.get("physical_resource_id")
                
                # Only add instances with traffic packages
                if resources_dict["cbc_physical_resource_id"]:
                    instances.append(resources_dict)
            
            if not instances:
                print(f"❌ No {resource_type} resources found in {target_region} region")
                return
            
            print(f"✅ Found {len(instances)} instances, querying traffic package information...\n")
            
            # Step 2: Query traffic package usage
            free_resource_ids = [inst["cbc_physical_resource_id"] for inst in instances]
            
            # Create BSS client
            bss_client = BssClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(BssRegion.value_of("cn-north-1")) \
                .build()
            
            request = ListFreeResourceUsagesRequest()
            request.body = ListFreeResourceUsagesReq(
                free_resource_ids=free_resource_ids
            )
            
            response = bss_client.list_free_resource_usages(request)
            
            # Parse traffic package usage
            usages = {}
            for item in response.free_resources:
                measure_id = item.measure_id if hasattr(item, 'measure_id') else 10
                unit = MEASURE_UNITS.get(measure_id, "GB")
                
                original_amount = item.original_amount if hasattr(item, 'original_amount') else 0
                amount = item.amount if hasattr(item, 'amount') else 0
                used = original_amount - amount
                usage_rate = (used / original_amount * 100) if original_amount > 0 else 0
                
                usages[item.free_resource_id] = {
                    "free_resource_type_name": item.free_resource_type_name if hasattr(item, 'free_resource_type_name') else "unknown",
                    "original_amount": original_amount,
                    "amount": amount,
                    "used": used,
                    "unit": unit,
                    "usage_rate": round(usage_rate, 2),
                    "start_time": item.start_time if hasattr(item, 'start_time') else None,
                    "end_time": item.end_time if hasattr(item, 'end_time') else None,
                }
            
            # Step 3: Merge instance information and traffic package information
            print(f"{'='*150}")
            print(f"📊 {target_region} Region Traffic Query Result: {len(instances)} instances")
            print(f"{'='*150}")
            print(f"{'No.':^6} | {'Instance Name':^30} | {'Traffic Package ID':^38} | {'Used':^12} | {'Total':^12} | {'Remaining':^12} | {'Usage Rate':^8}")
            print("-" * 150)
            
            for i, inst in enumerate(instances, 1):
                name = inst.get("parent_resource_name", "unnamed")
                name = name[:28] + ".." if len(name) > 30 else name
                
                cbc_id = inst.get("cbc_physical_resource_id", "-")
                usage = usages.get(cbc_id, {})
                
                if usage:
                    used = f"{usage['used']:.2f} {usage['unit']}"
                    quota = f"{usage['original_amount']:.2f} {usage['unit']}"
                    remaining = f"{usage['amount']:.2f} {usage['unit']}"
                    rate = f"{usage['usage_rate']:.1f}%"
                else:
                    used = "N/A"
                    quota = "N/A"
                    remaining = "N/A"
                    rate = "N/A"
                
                print(f"{i:^6} | {name:^30} | {cbc_id} | {used:^12} | {quota:^12} | {remaining:^12} | {rate:^8}")
            
            print("=" * 150)
            
            # Show validity period information
            print("\n[Validity Period]")
            for inst in instances:
                cbc_id = inst.get("cbc_physical_resource_id", "-")
                usage = usages.get(cbc_id, {})
                if usage and usage.get("start_time") and usage.get("end_time"):
                    name = inst.get("parent_resource_name", "unnamed")
                    print(f"  {name[:30]:<30} Valid: {usage['start_time']} ~ {usage['end_time']}")
            
        except Exception as e:
            print(f"❌ Query failed: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Command line entry point"""
    parser = argparse.ArgumentParser(
        description="Huawei Cloud Flexus L Instance Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query instance list across all regions (using Config service)
  python3 query_instances.py list
  
  # Query instance list for specific resource type
  python3 query_instances.py list --resource-type hcss.l-instance
  
  # Query single instance details
  python3 query_instances.py detail --instance-id <ID> --region cn-north-4
  
  # Query all Flexus L instance resources (including traffic package ID and Flexus L instance ID)
  python3 query_instances.py free-resources
  
  # Query traffic package remaining quota
  python3 query_instances.py traffic <traffic_id_1> <traffic_id_2>
  
  # Query traffic package information by region (automatically query all instances in that region)
  python3 query_instances.py traffic-region --target-region cn-east-3

Region Support:
  Can use region codes (e.g., cn-north-4) or Chinese names (e.g., "北京四", "华北-北京四")
  Default region: cn-north-4 (华北-北京四)
  
  Common region codes:
  - cn-north-4: 华北-北京四
  - cn-east-3: 华东-上海二
  - cn-south-1: 华南-广州
  - cn-southwest-2: 西南-贵阳一
"""
    )
    
    parser.add_argument("--ak", help="Access Key (optional, read from environment variables by default)")
    parser.add_argument("--sk", help="Secret Key (optional, read from environment variables by default)")
    parser.add_argument("--region", "-r", default="cn-north-4", 
                       help="Region code or name (default: cn-north-4 北京四), supports Chinese like '北京四', '广州', '上海'")
    
    subparsers = parser.add_subparsers(dest="command", help="Operation command")
    
    # list command (query all resources using Config service)
    list_parser = subparsers.add_parser("list", help="Query instance list")
    list_parser.add_argument("--resource-type", "-t", default="hcss.l-instance",
                            help="Resource type (default: hcss.l-instance)")
    
    # detail command
    detail_parser = subparsers.add_parser("detail", help="Query instance details")
    detail_parser.add_argument("--instance-id", "-i", required=True, help="Instance ID")
    
    # free-resources command (query Flexus L instance resources)
    free_resources_parser = subparsers.add_parser("free-resources", help="Query Flexus L instance resources (including traffic package ID and Flexus L instance ID)")
    free_resources_parser.add_argument("--resource-type", "-t", default="hcss.l-instance",
                                       help="Resource type (default: hcss.l-instance)")
    
    # traffic command (query traffic package remaining quota)
    traffic_parser = subparsers.add_parser("traffic", help="Query traffic package remaining quota")
    traffic_parser.add_argument("traffic_ids", nargs="+", help="Traffic package ID list")
    
    # traffic-region command (query traffic package information by region)
    traffic_region_parser = subparsers.add_parser("traffic-region", help="Query traffic package information by region (automatically query all instances in that region)")
    traffic_region_parser.add_argument("--target-region", "-t", required=True, help="Target region code (e.g., cn-east-3)")
    traffic_region_parser.add_argument("--resource-type", default="hcss.l-instance", help="Resource type (default: hcss.l-instance)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Create client
    client = InstanceQueryClient(ak=args.ak, sk=args.sk, region=args.region)
    
    # Execute command
    if args.command == "list":
        resource_type = getattr(args, 'resource_type', 'hcss.l-instance')
        client.list_all_regions(resource_type=resource_type)
    
    elif args.command == "detail":
        client.query_instance(args.instance_id)
    
    elif args.command == "free-resources":
        resource_type = getattr(args, 'resource_type', 'hcss.l-instance')
        client.list_free_resources(resource_type=resource_type)
    
    elif args.command == "traffic":
        client.query_free_resource_usage(args.traffic_ids)
    
    elif args.command == "traffic-region":
        client.query_traffic_by_region(args.target_region, args.resource_type)


if __name__ == "__main__":
    main()
