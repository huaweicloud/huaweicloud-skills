#!/usr/bin/env python3
"""
Huawei Cloud Flexus L Instance Lifecycle Management Tool
Integrates three core functions: create, renewal, and unsubscribe

Supports automatic spec matching for system images
Data is fetched dynamically from official documentation
"""

import os
import sys
import json
import argparse
import requests
import uuid
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import Huawei Cloud SDK
try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials, GlobalCredentials
    from huaweicloudsdkcore.signer.signer import Signer
    from huaweicloudsdkcore.sdk_request import SdkRequest
    from huaweicloudsdkcore.exceptions import exceptions
    from huaweicloudsdkcore.http.http_config import HttpConfig
    from huaweicloudsdkbss.v2.region.bss_region import BssRegion
    from huaweicloudsdkbss.v2 import *
    SDK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Huawei Cloud BSS SDK import failed: {e}")
    print("Please install: pip install huaweicloudsdkcore huaweicloudsdkbss")
    SDK_AVAILABLE = False

from urllib.parse import urlparse

from config import REGIONS


# ============================================================================
# Dynamic Data Fetching
# ============================================================================

def get_script_dir() -> str:
    """Get the directory where this script is located"""
    return os.path.dirname(os.path.abspath(__file__))


def fetch_specs_data(data_type: str = "all") -> Dict:
    """
    Call flexus_specs_extractor.py to fetch latest data
    
    Args:
        data_type: all / regions / specs / images
    
    Returns:
        Fetched data dictionary
    """
    extractor_path = os.path.join(get_script_dir(), "flexus_specs_extractor.py")
    
    if not os.path.exists(extractor_path):
        print(f"❌ Extractor script not found: {extractor_path}")
        return {}
    
    try:
        cmd = ["python3", extractor_path]
        if data_type != "all":
            cmd.append(f"--{data_type}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"❌ Failed to fetch data: {result.stderr}")
            return {}
            
    except subprocess.TimeoutExpired:
        print("❌ Fetch timeout (30s)")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse data: {e}")
        return {}
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return {}


def get_region_ids() -> List[str]:
    """Get all region ID list"""
    regions = fetch_specs_data("regions")
    return list(regions.keys())


def get_region_by_name(region_name: str) -> Optional[str]:
    """Get region ID by region name"""
    regions = fetch_specs_data("regions")
    for region_id, info in regions.items():
        if info.get("name") == region_name:
            return region_id
    return None


def get_region_name_by_id(region_id: str) -> Optional[str]:
    """Get region name by region ID"""
    regions = fetch_specs_data("regions")
    return regions.get(region_id, {}).get("name")


# ============================================================================
# Spec Query Functions
# ============================================================================


def get_available_images(region: str) -> Dict[str, Dict]:
    """
    Get available images for a specified region
    
    Args:
        region: Region ID
    
    Returns:
        Mapping from image names to version/specs info
    """
    system_images = fetch_specs_data("images")
    
    result = {}
    region_short = REGIONS.get(region, {}).get("short", "beijing")
    
    for img_name, img_info in system_images.items():
        region_data = img_info.get(region_short, {})
        version = region_data.get("version", "")
        specs = region_data.get("specs", [])
        if specs:
            result[img_name] = {"version": version, "specs": specs}
    
    return result


def get_available_specs(region: str, image_name: str) -> List[str]:
    """
    Get available specs for a specified region and image
    
    Args:
        region: Region ID
        image_name: Image name
    
    Returns:
        List of available spec codes
    """
    system_images = fetch_specs_data("images")
    
    region_short = REGIONS.get(region, {}).get("short", "beijing")
    
    if image_name in system_images:
        return system_images[image_name].get(region_short, {}).get("specs", [])
    
    return []


def get_spec_info(spec_code: str) -> Optional[Dict]:
    """
    Get detailed information for a spec code
    
    Args:
        spec_code: Spec code
    
    Returns:
        Spec info dictionary
    """
    data = fetch_specs_data("specs")
    return data.get(spec_code)


def find_matching_spec(region: str, cpu: int, memory: int, os_type: str = "linux", image_name: str = None) -> Optional[str]:
    """
    Find matching spec based on CPU, memory and OS type (region-aware)
    
    Args:
        region: Region ID
        cpu: CPU cores
        memory: Memory in GB
        os_type: OS type (linux/windows)
        image_name: Optional, image name for precise matching
    
    Returns:
        Matching spec code, or None if not found
    """
    data = fetch_specs_data("all")
    spec_defs = data.get("spec_definitions", {})
    system_images = data.get("system_images", {})
    
    region_short = REGIONS.get(region, {}).get("short", "beijing")
    
    # If image is specified, search from that image's available specs first
    if image_name and image_name in system_images:
        available_specs = system_images[image_name].get(region_short, {}).get("specs", [])
        if available_specs:
            # Prefer exact match
            for spec_code in available_specs:
                spec_info = spec_defs.get(spec_code, {})
                if spec_info.get("os") == os_type:
                    if spec_info.get("vcpu") == cpu and spec_info.get("memory") == memory:
                        return spec_code
            
            # No exact match, find closest
            best_match = None
            best_diff = float('inf')
            for spec_code in available_specs:
                spec_info = spec_defs.get(spec_code, {})
                if spec_info.get("os") == os_type:
                    diff = abs(spec_info.get("vcpu", 0) - cpu) + abs(spec_info.get("memory", 0) - memory)
                    if diff < best_diff:
                        best_diff = diff
                        best_match = spec_code
            
            if best_match:
                return best_match
    
    # Search from all specs
    for spec_code, spec_info in spec_defs.items():
        if spec_info.get("os") == os_type:
            if spec_info.get("vcpu") == cpu and spec_info.get("memory") == memory:
                return spec_code
    
    # No exact match, find closest
    best_match = None
    best_diff = float('inf')
    
    for spec_code, spec_info in spec_defs.items():
        if spec_info.get("os") == os_type:
            diff = abs(spec_info.get("vcpu", 0) - cpu) + abs(spec_info.get("memory", 0) - memory)
            if diff < best_diff:
                best_diff = diff
                best_match = spec_code
    
    return best_match


def is_region_supported(region: str) -> Tuple[bool, str]:
    """
    Check if a region supports Flexus L
    
    Args:
        region: Region ID
    
    Returns:
        (is_supported, reason)
    """
    regions = fetch_specs_data("regions")
    
    if region not in regions:
        return False, f"Region {region} not supported"
    
    return True, "Supported"


# ============================================================================
# Authentication
# ============================================================================

def get_project_id_by_region(ak: str, sk: str, security_token: Optional[str], region: str) -> Optional[str]:
    """Get Project ID for a specified region"""
    iam_endpoint = "https://iam.myhuaweicloud.com/v3/projects"
    
    try:
        if security_token:
            credentials = BasicCredentials(ak, sk).with_security_token(security_token)
        else:
            credentials = BasicCredentials(ak, sk)
        signer = Signer(credentials)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = "iam.myhuaweicloud.com"
        request.resource_path = "/v3/projects"
        request.body = ""
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        if security_token:
            request.header_params["X-Security-Token"] = security_token
        request.query_params = []
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        resp = requests.get(iam_endpoint, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            projects = data.get('projects', [])
            if projects:
                for project in projects:
                    project_name = project.get('name', '')
                    if project_name == region:
                        return project.get('id')
                return projects[0].get('id')
        return None
    except Exception as e:
        print(f"Failed to get Project ID: {e}")
        return None


def create_bss_client(ak: str, sk: str, security_token: Optional[str], region: str = "cn-north-1"):
    """Create BSS client"""
    if not SDK_AVAILABLE:
        raise ImportError("Huawei Cloud BSS SDK not installed")
    
    if security_token:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    else:
        credentials = GlobalCredentials(ak, sk)
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = True
    
    client = BssClient.new_builder() \
        .with_credentials(credentials) \
        .with_http_config(config) \
        .with_region(BssRegion.value_of(region)) \
        .build()
    
    return client


# ============================================================================
# Create Instance
# ============================================================================

def create_flexus_l_instance(
    ak: str,
    sk: str,
    security_token: Optional[str],
    region: str = "cn-north-4",
    plan_spec: str = "hf.small.1.win",
    image_name: str = "WindowsServer",
    image_version: str = "2012R2_standard_ch",
    period_num: int = 1,
    period_type: str = "month",
    instance_name: Optional[str] = None,
    auto_renew: bool = True,
    auto_pay: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Create Flexus L instance
    """
    # Check if region is supported
    supported, reason = is_region_supported(region)
    if not supported:
        return {"success": False, "error": reason}
    
    # Get project ID
    project_id = get_project_id_by_region(ak, sk, security_token, region)
    if not project_id:
        return {"success": False, "error": f"Failed to get project ID for region {region}"}
    
    # Generate instance name
    if not instance_name:
        instance_name = f"flexus{int(uuid.uuid4().hex[:8], 16)}"
    else:
        if instance_name[0].isdigit():
            instance_name = f"flexus{instance_name}"
        instance_name = instance_name.replace("_", "-")
    
    # Build request body
    request_body = {
        "instance_name": instance_name,
        "description": "Flexus L instance created via API",
        "plan_spec": plan_spec,
        "image_ref": {
            "image_name": image_name,
            "image_version": image_version
        },
        "region": region,
        "charging_mode": "prePaid",
        "period_type": period_type,
        "period_num": period_num,
        "purchase_quantity": 1,
        "is_auto_renew": auto_renew,
        "is_auto_pay": auto_pay,
        "extra_resources": [
            {"type": "evs", "size": 20},
            {"type": "cbr", "size": 20},
            {"type": "hss"}
        ]
    }
    
    # Dry run
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "message": "Dry run successful, parameters validated",
            "params": {
                "instance_name": instance_name,
                "plan_spec": plan_spec,
                "image": f"{image_name}:{image_version}",
                "region": region,
                "region_name": get_region_name_by_id(region),
                "period_num": period_num,
                "period_type": period_type,
                "auto_renew": auto_renew,
                "auto_pay": auto_pay
            }
        }
    
    # Actual creation - URL hardcoded to cn-north-4 as per API requirement
    try:
        if security_token:
            credentials = BasicCredentials(ak, sk, project_id).with_security_token(security_token)
        else:
            credentials = BasicCredentials(ak, sk, project_id)
        signer = Signer(credentials)
        
        # API URL is hardcoded to cn-north-4 (global endpoint)
        url = "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances"
        parsed_url = urlparse(url)
        
        body_json = json.dumps(request_body, ensure_ascii=False)
        
        header_params = {
            "X-Project-Id": project_id,
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        if security_token:
            header_params["X-Security-Token"] = security_token
        
        request = SdkRequest(
            method="POST",
            schema=parsed_url.scheme,
            host=parsed_url.netloc,
            resource_path=parsed_url.path,
            query_params=[],
            header_params=header_params,
            body=body_json
        )
        
        signed_request = signer.sign(request)
        full_url = f"{signed_request.schema}://{signed_request.host}{signed_request.resource_path}"
        
        resp = requests.request(
            signed_request.method,
            full_url,
            headers=signed_request.header_params,
            data=signed_request.body,
            verify=False,
            timeout=60
        )
        
        if resp.status_code == 202:
            result = resp.json()
            return {
                "success": True,
                "order_id": result.get('order_id'),
                "instance_ids": result.get('instance_ids', []),
                "instance_name": instance_name,
                "message": "Instance creation request submitted successfully"
            }
        else:
            error_data = resp.json() if resp.text else {}
            return {
                "success": False,
                "error": f"Creation failed: {resp.status_code}",
                "error_code": error_data.get('error_code'),
                "error_msg": error_data.get('error_msg'),
                "response": resp.text
            }
    except Exception as e:
        return {"success": False, "error": f"Creation exception: {str(e)}"}


# ============================================================================
# Renewal
# ============================================================================

def renewal_resources(
    ak: str,
    sk: str,
    security_token: Optional[str],
    resource_ids: List[str],
    period_num: int = 1,
    period_type: str = "month",
    auto_pay: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Renew resources"""
    if not isinstance(resource_ids, list):
        resource_ids = [resource_ids]
    
    period_type_map = {"month": 2, "year": 3}
    period_type_value = period_type_map.get(period_type, 2)
    
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "message": "Dry run successful",
            "params": {
                "resource_ids": resource_ids,
                "period_num": period_num,
                "period_type": period_type,
                "auto_pay": auto_pay
            }
        }
    
    try:
        client = create_bss_client(ak, sk, security_token)
        
        request = RenewalResourcesRequest()
        request.body = RenewalResourcesReq(
            is_auto_pay=1 if auto_pay else 0,
            period_num=period_num,
            period_type=period_type_value,
            resource_ids=resource_ids
        )
        
        response = client.renewal_resources(request)
        
        if hasattr(response, 'order_ids') and response.order_ids:
            return {
                "success": True,
                "order_ids": response.order_ids,
                "message": "Renewal successful"
            }
        else:
            return {"success": False, "error": "Renewal successful but no order ID returned"}
    except exceptions.ClientRequestException as e:
        return {"success": False, "error": f"Client request exception: {e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": f"Renewal exception: {str(e)}"}


# ============================================================================
# Unsubscribe
# ============================================================================

def unsubscribe_resources(
    ak: str,
    sk: str,
    security_token: Optional[str],
    resource_ids: List[str],
    unsubscribe_type: int = 1,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Unsubscribe resources"""
    if not isinstance(resource_ids, list):
        resource_ids = [resource_ids]
    
    if dry_run:
        type_desc = "Immediate unsubscribe" if unsubscribe_type == 1 else "Expire unsubscribe"
        return {
            "success": True,
            "dry_run": True,
            "message": "Dry run successful",
            "params": {
                "resource_ids": resource_ids,
                "unsubscribe_type": unsubscribe_type,
                "unsubscribe_type_desc": type_desc,
                "reason": reason
            }
        }
    
    try:
        client = create_bss_client(ak, sk, security_token)
        
        request = CancelResourcesSubscriptionRequest()
        request.body = UnsubscribeResourcesReq(
            unsubscribe_type=unsubscribe_type,
            resource_ids=resource_ids
        )
        
        if reason:
            request.body.unsubscribe_reason = reason
        
        response = client.cancel_resources_subscription(request)
        
        if response and hasattr(response, 'order_ids'):
            return {
                "success": True,
                "order_ids": response.order_ids,
                "message": "Unsubscribe request submitted"
            }
        else:
            return {"success": False, "error": "Invalid API response format"}
    except exceptions.ClientRequestException as e:
        return {"success": False, "error": f"Client request exception: {e.error_code} - {e.error_msg}"}
    except Exception as e:
        return {"success": False, "error": f"Unsubscribe exception: {str(e)}"}


# ============================================================================
# Helper Functions
# ============================================================================

def show_regions():
    """Display all available regions"""
    print("Fetching region information...")
    regions = fetch_specs_data("regions")
    
    print("\n" + "=" * 60)
    print("Flexus L Available Regions")
    print("=" * 60)
    print(f"{'Region ID':<25} {'Region Name':<20}")
    print("-" * 60)
    
    for region_id, region_info in regions.items():
        region_name = region_info.get("name", "Unknown")
        print(f"{region_id:<25} {region_name:<20}")
    
    print("=" * 60)


def show_images(region: str):
    """Display available images for a region"""
    supported, reason = is_region_supported(region)
    if not supported:
        print(f"[ERROR] {reason}")
        return
    
    print(f"Fetching image information for region {region}...")
    images = get_available_images(region)
    
    if not images:
        print(f"Region {region} has no configured image information")
        return
    
    region_name = get_region_name_by_id(region) or region
    
    print("\n" + "=" * 60)
    print(f"Region {region} ({region_name}) Available Images")
    print("=" * 60)
    
    for img_name, img_data in images.items():
        version = img_data.get("version", "")
        specs = img_data.get("specs", [])
        print(f"\n[IMAGE] {img_name}")
        if version:
            print(f"  |-- Version: {version.replace(chr(10), ', ')}")
        if specs:
            print(f"  |-- Available Specs: {', '.join(specs[:3])}{'...' if len(specs) > 3 else ''}")
    
    print("\n" + "=" * 60)


def show_specs(region: str, image_name: str):
    """Display available specs for an image"""
    print(f"Fetching spec information for {image_name} in {region}...")
    specs = get_available_specs(region, image_name)
    spec_defs = fetch_specs_data("specs")
    
    if not specs:
        print(f"[ERROR] Image {image_name} has no configured specs in region {region}")
        return
    
    print("\n" + "=" * 70)
    print(f"Available Specs for {image_name} in Region {region}")
    print("=" * 70)
    print(f"{'Spec Code':<30} {'CPU':<8} {'Memory':<8} {'Disk':<8} {'Bandwidth':<8}")
    print("-" * 70)
    
    for spec_code in specs:
        info = spec_defs.get(spec_code, {})
        cpu = info.get("vcpu", "?")
        memory = info.get("memory", "?")
        disk = info.get("disk", "?")
        bandwidth = info.get("bandwidth", "?")
        print(f"{spec_code:<30} {cpu} cores   {memory}GB      {disk}GB      {bandwidth}Mbps")
    
    print("=" * 70)


def show_unsubscribe_policy():
    """Display unsubscribe policy"""
    print("=" * 60)
    print("Huawei Cloud Flexus L Instance Unsubscribe Policy")
    print("=" * 60)
    print()
    print("[Unsubscribe Types]")
    print()
    print("Type 1: Unsubscribe resource and its renewed periods")
    print("  - Effect: Resource stops and releases immediately")
    print("  - Refund: Proportional refund based on remaining time")
    print()
    print("Type 2: Unsubscribe renewal period only")
    print("  - Effect: Resource continues until expiration")
    print("  - Refund: Refund the renewal portion")
    print()
    print("[General Rules]")
    print("  * Please backup important data before unsubscribing")
    print("  * Unsubscribe operation is irreversible")
    print("=" * 60)


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Huawei Cloud Flexus L Instance Lifecycle Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--ak", help="Huawei Cloud Access Key AK (can be temporary AK, or set HW_ACCESS_KEY env var)")
    parser.add_argument("--sk", help="Huawei Cloud Access Key SK (can be temporary SK, or set HW_SECRET_KEY env var)")
    parser.add_argument("--security-token", help="Security token for temporary credentials (required when using temporary AK/SK, or set HW_SECURITY_TOKEN env var)")
    parser.add_argument("--region", default="cn-north-4", help="Region ID")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--confirm", action="store_true", help="Force confirm")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("show-regions", help="Show all available regions")
    
    subparsers.add_parser("show-images", help="Show available images for a region")
    
    show_specs_parser = subparsers.add_parser("show-specs", help="Show available specs for an image")
    show_specs_parser.add_argument("--image", required=True, help="Image name")
    
    create_parser = subparsers.add_parser("create-instance", help="Create Flexus L instance")
    create_parser.add_argument("--plan-spec", help="Instance spec")
    create_parser.add_argument("--image", default="Ubuntu", help="Image name")
    create_parser.add_argument("--cpu", type=int, help="CPU cores")
    create_parser.add_argument("--memory", type=int, help="Memory in GB")
    create_parser.add_argument("--period-num", type=int, default=1)
    create_parser.add_argument("--period-type", default="month", choices=["month", "year"])
    create_parser.add_argument("--instance-name")
    create_parser.add_argument("--auto-renew", type=lambda x: x.lower() != 'false', default=True)
    create_parser.add_argument("--auto-pay", type=lambda x: x.lower() != 'false', default=True)
    
    renewal_parser = subparsers.add_parser("renewal", help="Renew instance")
    renewal_parser.add_argument("--resource-ids", required=True)
    renewal_parser.add_argument("--period-num", type=int, default=1)
    renewal_parser.add_argument("--period-type", default="month", choices=["month", "year"])
    renewal_parser.add_argument("--auto-pay", type=lambda x: x.lower() != 'false', default=True)
    
    unsubscribe_parser = subparsers.add_parser("unsubscribe", help="Unsubscribe instance")
    unsubscribe_parser.add_argument("--resource-ids", required=True)
    unsubscribe_parser.add_argument("--type", type=int, choices=[1, 2], default=1)
    unsubscribe_parser.add_argument("--reason")
    
    subparsers.add_parser("unsubscribe-policy", help="Show unsubscribe policy")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "show-regions":
            show_regions()
            
        elif args.command == "show-images":
            show_images(args.region)
            
        elif args.command == "show-specs":
            show_specs(args.region, args.image)
            
        elif args.command == "create-instance":
            # Get credentials from args or environment variables
            ak = args.ak or os.environ.get("HW_ACCESS_KEY")
            sk = args.sk or os.environ.get("HW_SECRET_KEY")
            security_token = args.security_token or os.environ.get("HW_SECURITY_TOKEN")
            
            if not ak or not sk:
                print("Error: --ak and --sk are required (or set HW_ACCESS_KEY and HW_SECRET_KEY env vars)")
                print("Note: --security-token is recommended for temporary credentials")
                return
            
            supported, reason = is_region_supported(args.region)
            if not supported:
                print(f"[ERROR] {reason}")
                return
            
            # Parse image name and version
            image_input = args.image
            if ":" in image_input:
                image_name, image_version = image_input.split(":", 1)
            else:
                image_name = image_input
                image_version = None
            
            plan_spec = args.plan_spec
            
            if not plan_spec:
                if args.cpu and args.memory:
                    os_type = "windows" if "win" in image_name.lower() or "windows" in image_name.lower() else "linux"
                    plan_spec = find_matching_spec(args.region, args.cpu, args.memory, os_type, image_name)
                    if not plan_spec:
                        print(f"[ERROR] Cannot find matching spec for {args.cpu} cores {args.memory}GB in region {args.region}")
                        return
                    print(f"[OK] Auto-matched spec: {plan_spec} (region: {args.region})")
                else:
                    available_specs = get_available_specs(args.region, image_name)
                    if available_specs:
                        plan_spec = available_specs[0]
                        print(f"[OK] Using default spec: {plan_spec}")
                    else:
                        print(f"[ERROR] Image {image_name} has no configured specs in region {args.region}")
                        return
            
            spec_info = get_spec_info(plan_spec)
            
            print("\n" + "=" * 70)
            print("Create Flexus L Instance")
            print("=" * 70)
            print(f"Region: {args.region} ({get_region_name_by_id(args.region) or 'Unknown'})")
            print(f"Image: {image_name}")
            print(f"Spec: {plan_spec}")
            if spec_info:
                print(f"  |-- CPU: {spec_info.get('vcpu', '?')} cores, Memory: {spec_info.get('memory', '?')}GB")
            print(f"Period: {args.period_num} {args.period_type}")
            print("=" * 70)
            
            if not args.dry_run and not args.confirm:
                print("\n[WARNING] This operation will incur charges!")
                confirm = input("Confirm creation? (type 'yes' to confirm): ")
                if confirm.lower() != 'yes':
                    print("Cancelled")
                    return
            
            result = create_flexus_l_instance(
                ak=ak, sk=sk, region=args.region, security_token=security_token,
                plan_spec=plan_spec, image_name=image_name, image_version=image_version or "22.04",
                period_num=args.period_num, period_type=args.period_type,
                instance_name=args.instance_name, auto_renew=args.auto_renew,
                auto_pay=args.auto_pay, dry_run=args.dry_run
            )
            
            if result["success"]:
                if args.dry_run:
                    print("\n[OK] Dry run successful")
                else:
                    print("\n[OK] Creation successful!")
                    print(f"Order ID: {result.get('order_id')}")
                    print(f"Instance ID: {result.get('instance_ids')}")
            else:
                print(f"\n[ERROR] Creation failed: {result.get('error')}")
                
        elif args.command == "renewal":
            # Get credentials from args or environment variables
            ak = args.ak or os.environ.get("HW_ACCESS_KEY")
            sk = args.sk or os.environ.get("HW_SECRET_KEY")
            security_token = args.security_token or os.environ.get("HW_SECURITY_TOKEN")
            
            if not ak or not sk:
                print("Error: --ak and --sk are required (or set HW_ACCESS_KEY and HW_SECRET_KEY env vars)")
                print("Note: --security-token is recommended for temporary credentials")
                return
            
            resource_ids = [rid.strip() for rid in args.resource_ids.split(",")]
            
            print("\n" + "=" * 60)
            print("Renew Flexus L Instance")
            print("=" * 60)
            print(f"Instance: {resource_ids}")
            print(f"Period: {args.period_num} {args.period_type}")
            print("=" * 60)
            
            if not args.dry_run and not args.confirm:
                confirm = input("Confirm renewal? (type 'yes' to confirm): ")
                if confirm.lower() != 'yes':
                    print("Cancelled")
                    return
            
            result = renewal_resources(
                ak=ak, sk=sk, resource_ids=resource_ids, security_token=security_token,
                period_num=args.period_num, period_type=args.period_type,
                auto_pay=args.auto_pay, dry_run=args.dry_run
            )
            
            if result["success"]:
                print("\n[OK] Renewal successful!")
                print(f"Order ID: {result.get('order_ids')}")
            else:
                print(f"\n[ERROR] Renewal failed: {result.get('error')}")
                
        elif args.command == "unsubscribe":
            # Get credentials from args or environment variables
            ak = args.ak or os.environ.get("HW_ACCESS_KEY")
            sk = args.sk or os.environ.get("HW_SECRET_KEY")
            security_token = args.security_token or os.environ.get("HW_SECURITY_TOKEN")
            
            if not ak or not sk:
                print("Error: --ak and --sk are required (or set HW_ACCESS_KEY and HW_SECRET_KEY env vars)")
                print("Note: --security-token is recommended for temporary credentials")
                return
            
            resource_ids = [rid.strip() for rid in args.resource_ids.split(",")]
            
            print("\n" + "=" * 60)
            print("Unsubscribe Flexus L Instance")
            print("=" * 60)
            print(f"Instance: {resource_ids}")
            print(f"Unsubscribe Type: {args.type}")
            print("=" * 60)
            
            if not args.dry_run and not args.confirm:
                print("\n[WARNING] This operation is irreversible!")
                confirm = input("Confirm unsubscribe? (type 'yes' to confirm): ")
                if confirm.lower() != 'yes':
                    print("Cancelled")
                    return
            
            result = unsubscribe_resources(
                ak=ak, sk=sk, resource_ids=resource_ids, security_token=security_token,
                unsubscribe_type=args.type, reason=args.reason, dry_run=args.dry_run
            )
            
            if result["success"]:
                print("\n[OK] Unsubscribe successful!")
                print(f"Order ID: {result.get('order_ids')}")
            else:
                print(f"\n[ERROR] Unsubscribe failed: {result.get('error')}")
                
        elif args.command == "unsubscribe-policy":
            show_unsubscribe_policy()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nExecution failed: {e}")


if __name__ == "__main__":
    main()
