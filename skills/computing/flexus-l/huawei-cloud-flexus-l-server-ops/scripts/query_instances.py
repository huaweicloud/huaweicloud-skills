#!/usr/bin/env python3
# coding: utf-8
"""Flexus L instance query tool (list/detail/traffic)"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

from huaweicloudsdkconfig.v1 import ListAllResourcesRequest
from huaweicloudsdkbss.v2 import ListFreeResourceUsagesRequest, ListFreeResourceUsagesReq
from huaweicloudsdkecs.v2 import ShowServerRequest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import AuthManager
from params import RegionConverter


MEASURE_UNITS = {10: "GB"}


def utc_to_beijing(utc_str: str) -> str:
    """Convert UTC time to Beijing time"""
    if not utc_str or utc_str == 'N/A':
        return 'N/A'
    try:
        if utc_str.endswith('Z'):
            utc_str = utc_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(utc_str)
        return dt.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return utc_str


class InstanceQueryClient:
    """Instance query client"""
    
    def __init__(self, ak=None, sk=None, security_token=None, region="cn-north-4"):
        """Initialize query client"""
        self.region = RegionConverter.to_code(region)
        self.auth = AuthManager(ak=ak, sk=sk, security_token=security_token)
    
    def _get_flexus_name_by_ecs_id(self, ecs_id: str) -> str:
        """Find Flexus L instance name by ECS ID"""
        try:
            config_client = self.auth.get_config_client(self.region)
            request = ListAllResourcesRequest(type="hcss.l-instance")
            response = config_client.list_all_resources(request)
            for r in response.resources:
                props = r.properties or {}
                for sub in props.get("resources", []):
                    if sub.get("logical_resource_type") == "huaweicloudinternal_ecs_instance":
                        if sub.get("physical_resource_id") == ecs_id:
                            return r.name
        except:
            pass
        return "N/A"
    
    def list_all_regions(self, resource_type="hcss.l-instance"):
        """List Flexus L instances across all regions"""
        print(f"Querying resources (type: {resource_type})...\n")
        config_client = self.auth.get_config_client(self.region)
        request = ListAllResourcesRequest(type=resource_type)
        response = config_client.list_all_resources(request)
        
        resources = response.resources
        if not resources:
            print(f"No {resource_type} resources found")
            return
        
        print(f"\n{'='*120}")
        print(f"Query result: {len(resources)} resource(s)")
        print(f"{'='*120}")
        print(f"{'No.':<6} {'Instance Name':<50} {'Instance ID':<42} {'Region':<15} {'Status':<10}")
        print("-" * 120)
        for i, r in enumerate(resources, 1):
            print(f"{i:<6} {getattr(r, 'name', 'N/A')[:48]:<50} {getattr(r, 'id', 'N/A'):<42} {getattr(r, 'region_id', 'N/A'):<15} {getattr(r, 'status', 'N/A'):<10}")
        print("=" * 120)
    
    def query_instance(self, instance_id: str):
        """Query single instance details"""
        print(f"Querying cloud host: {instance_id}")
        client = self.auth.get_ecs_client(self.region)
        server = client.show_server(ShowServerRequest(server_id=instance_id)).server
        
        # Find corresponding Flexus L instance name
        flexus_name = self._get_flexus_name_by_ecs_id(instance_id)
        
        print("\n" + "=" * 60)
        print(f"Instance Name:   {flexus_name}")
        print(f"Cloud Host Name: {server.name}")
        print(f"Cloud Host ID:   {server.id}")
        print(f"Status:          {server.status}")
        print(f"Region:          {self.region}")
        print(f"Created:         {utc_to_beijing(server.created)}")
        if hasattr(server, 'addresses') and server.addresses:
            print("\nNetwork Info:")
            for net, addrs in server.addresses.items():
                for a in addrs:
                    print(f"  {net}: {a.addr}")
        print("=" * 60)
    
    def list_free_resources(self, resource_type="hcss.l-instance"):
        """List Flexus L instance resources (with traffic package ID)"""
        print(f"Querying Flexus L instance resources...\n")
        config_client = self.auth.get_config_client(self.region)
        request = ListAllResourcesRequest(type=resource_type)
        response = config_client.list_all_resources(request)
        
        instances = []
        for r in response.resources:
            props = r.properties or {}
            cbc_id = ecs_id = None
            for sub in props.get("resources", []):
                if sub.get("logical_resource_type") == "huaweicloudinternal_cbc_freeresource":
                    cbc_id = sub.get("physical_resource_id")
                if sub.get("logical_resource_type") == "huaweicloudinternal_ecs_instance":
                    ecs_id = sub.get("physical_resource_id")
            if cbc_id:
                instances.append({"name": r.name, "ecs_id": ecs_id, "cbc_id": cbc_id})
        
        if not instances:
            print(f"No resources found")
            return
        
        print(f"\n{'='*130}")
        print(f"Query result: {len(instances)} instance(s)")
        print(f"{'='*130}")
        print(f"{'No.':<6} {'Instance Name':<30} {'Cloud Host ID':<40} {'Traffic Package ID':<40}")
        print("-" * 130)
        for i, inst in enumerate(instances, 1):
            print(f"{i:<6} {inst['name'][:28]:<30} {inst['ecs_id'] or '-':<40} {inst['cbc_id']:<40}")
        print("=" * 130)
    
    def query_traffic(self, traffic_ids: list):
        """Query traffic package usage"""
        print(f"Querying {len(traffic_ids)} traffic package(s)...\n")
        bss_client = self.auth.get_bss_client()
        request = ListFreeResourceUsagesRequest(body=ListFreeResourceUsagesReq(free_resource_ids=traffic_ids))
        response = bss_client.list_free_resource_usages(request)
        
        print(f"{'='*100}")
        print(f"{'Traffic Package ID':<40} {'Used':<15} {'Total':<15} {'Remaining':<15} {'Usage Rate':<10}")
        print("=" * 100)
        for item in response.free_resources:
            unit = MEASURE_UNITS.get(getattr(item, 'measure_id', 10), "GB")
            orig = getattr(item, 'original_amount', 0)
            amt = getattr(item, 'amount', 0)
            used = orig - amt
            rate = f"{(used/orig*100):.1f}%" if orig > 0 else "0%"
            print(f"{item.free_resource_id:<40} {f'{used:.2f} {unit}':<15} {f'{orig:.2f} {unit}':<15} {f'{amt:.2f} {unit}':<15} {rate:<10}")
        print("=" * 100)
    
    def query_traffic_by_region(self, target_region: str, resource_type="hcss.l-instance"):
        """Query traffic packages by region"""
        print(f"Querying traffic packages in {target_region} region...\n")
        config_client = self.auth.get_config_client(self.region)
        bss_client = self.auth.get_bss_client()
        
        request = ListAllResourcesRequest(type=resource_type)
        response = config_client.list_all_resources(request)
        
        instances = []
        for r in response.resources:
            if getattr(r, 'region_id', None) != target_region:
                continue
            props = r.properties or {}
            cbc_id = None
            for sub in props.get("resources", []):
                if sub.get("logical_resource_type") == "huaweicloudinternal_cbc_freeresource":
                    cbc_id = sub.get("physical_resource_id")
            if cbc_id:
                instances.append({"name": r.name, "cbc_id": cbc_id})
        
        if not instances:
            print(f"No resources found")
            return
        
        traffic_ids = [i["cbc_id"] for i in instances]
        request = ListFreeResourceUsagesRequest(body=ListFreeResourceUsagesReq(free_resource_ids=traffic_ids))
        usage_resp = bss_client.list_free_resource_usages(request)
        
        usages = {u.free_resource_id: u for u in usage_resp.free_resources}
        
        print(f"\n{'='*120}")
        print(f"Traffic query for {target_region}: {len(instances)} instance(s)")
        print(f"{'='*120}")
        print(f"{'No.':<6} {'Instance Name':<30} {'Used':<15} {'Total':<15} {'Remaining':<15} {'Usage Rate':<10}")
        print("-" * 120)
        for i, inst in enumerate(instances, 1):
            u = usages.get(inst["cbc_id"])
            if u:
                unit = MEASURE_UNITS.get(getattr(u, 'measure_id', 10), "GB")
                orig = getattr(u, 'original_amount', 0)
                amt = getattr(u, 'amount', 0)
                used = orig - amt
                rate = f"{(used/orig*100):.1f}%" if orig > 0 else "0%"
                print(f"{i:<6} {inst['name'][:28]:<30} {f'{used:.2f} {unit}':<15} {f'{orig:.2f} {unit}':<15} {f'{amt:.2f} {unit}':<15} {rate:<10}")
        print("=" * 120)


def main():
    """Command line entry: parse arguments and execute query operations"""
    parser = argparse.ArgumentParser(description="Flexus L instance query tool")
    parser.add_argument("--ak", help="Access Key")
    parser.add_argument("--sk", help="Secret Key")
    parser.add_argument("--security-token", help="Security Token")
    parser.add_argument("--region", "-r", default="cn-north-4", help="Region")
    subparsers = parser.add_subparsers(dest="cmd")
    
    subparsers.add_parser("list", help="List all resources")
    subparsers.add_parser("free-resources", help="List Flexus L instances and traffic package IDs")
    detail_p = subparsers.add_parser("detail", help="Query instance details")
    detail_p.add_argument("--instance-id", "-i", required=True)
    traffic_p = subparsers.add_parser("traffic", help="Query traffic package usage")
    traffic_p.add_argument("traffic_ids", nargs="+", help="Traffic package IDs")
    tr_p = subparsers.add_parser("traffic-region", help="Query traffic packages by region")
    tr_p.add_argument("--target-region", "-t", required=True)
    
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    
    client = InstanceQueryClient(ak=args.ak, sk=args.sk, security_token=args.security_token, region=args.region)
    
    if args.cmd == "list":
        client.list_all_regions()
    elif args.cmd == "detail":
        client.query_instance(args.instance_id)
    elif args.cmd == "free-resources":
        client.list_free_resources()
    elif args.cmd == "traffic":
        client.query_traffic(args.traffic_ids)
    elif args.cmd == "traffic-region":
        client.query_traffic_by_region(args.target_region)


if __name__ == "__main__":
    main()
