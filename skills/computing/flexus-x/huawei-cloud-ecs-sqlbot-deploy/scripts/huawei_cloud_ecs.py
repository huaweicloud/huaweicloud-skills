#!/usr/bin/env python3
"""
Huawei Cloud ECS SDK wrapper class for SQLBot Deployment
"""

import json
import requests
import uuid
import urllib3
import subprocess
import time
from urllib.parse import urlparse
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest

# ECS SDK imports
from huaweicloudsdkecs.v2 import EcsClient, CreateServersRequest, CreateServersRequestBody, ShowJobRequest
from huaweicloudsdkecs.v2 import PrePaidServer, PrePaidServerNic, PrePaidServerRootVolume
from huaweicloudsdkecs.v2 import PrePaidServerPublicip, PrePaidServerEip, PrePaidServerEipBandwidth
from huaweicloudsdkecs.v2 import PrePaidServerExtendParam, PrePaidServerSecurityGroup
from huaweicloudsdkecs.v2 import PostPaidServer, PostPaidServerNic, PostPaidServerRootVolume
from huaweicloudsdkecs.v2 import PostPaidServerPublicip, PostPaidServerEip, PostPaidServerEipBandwidth
from huaweicloudsdkecs.v2 import PostPaidServerSecurityGroup
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

urllib3.disable_warnings()

# Import configuration constants
from config import (
    DEFAULT_CONFIG, REGION_FLAVOR_PRIORITY, REGION_FLAVOR_MAP,
    FLAVOR_DESCRIPTION
)


class HuaweiCloudECS:
    def __init__(self, ak, sk, project_id, region="cn-north-4", security_token=None):
        self.ak = ak
        self.sk = sk
        self.project_id = project_id
        self.region = region
        self.security_token = security_token
        
        # Support both temporary and permanent credentials
        if self.security_token:
            # Temporary credentials: AK/SK + Security Token
            self.credentials = BasicCredentials(ak, sk, project_id).with_security_token(self.security_token)
        else:
            # Permanent credentials: AK/SK only
            self.credentials = BasicCredentials(ak, sk, project_id)
        
        self.signer = Signer(self.credentials)
    
    def get_flavor_details(self, flavor_id):
        """Query detailed information for a single flavor
        
        Args:
            flavor_id: Flavor ID
            
        Returns:
            dict: Flavor details including name, vcpus, ram, etc.
        """
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/flavors/{flavor_id}"
        
        try:
            resp = self._do_request("GET", url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("flavor", {})
            else:
                return None
                
        except Exception as e:
            return None
    
    def get_available_flavors(self):
        """Query available flavors in current region
        
        Returns:
            list: List of flavors, each flavor is a dict containing name, vcpus, ram, etc.
        """
        print(f"🔍 Querying available flavors in region {self.region}...")
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/flavors"
        
        try:
            resp = self._do_request("GET", url, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                flavors = data.get("flavors", [])
                print(f"✅ Found {len(flavors)} available flavors")
                return flavors
            else:
                print(f"❌ Failed to query flavors: {resp.status_code}")
                print(f"Response: {resp.text[:200]}")
                return []
                
        except Exception as e:
            print(f"❌ Error querying flavors: {e}")
            return []
    
    def find_best_flavor(self, target_vcpus=4, target_ram_gb=8):
        """Find the best suitable flavor (try in region priority order)
        
        Args:
            target_vcpus: Target vCPU count
            target_ram_gb: Target memory size (GB)
        
        Returns:
            str: Flavor name, e.g. "x1.4u.8g" or "x1e.4u.8g"
        """
        target_ram_mb = target_ram_gb * 1024
        
        # 1. According to region priority order, directly construct flavor name and query details
        # ⚠️ Important: list_flavors API does not return x1.* series, need to use get_flavor_details
        region_priority = REGION_FLAVOR_PRIORITY.get(self.region, REGION_FLAVOR_PRIORITY["default"])
        print(f"🔍 X instance type priority for region {self.region}: {region_priority}")
        
        # Construct possible flavor names and query directly
        for series_prefix in region_priority:
            # Construct exact matching flavor name, e.g. x1.2u.4g, x1.4u.8g
            flavor_name = f"{series_prefix}.{target_vcpus}u.{target_ram_gb}g"
            print(f"🔍 Trying flavor: {flavor_name}")
            
            detail = self.get_flavor_details(flavor_name)
            if detail:
                vcpus = detail.get("vcpus")
                ram = detail.get("ram")
                if vcpus and ram:
                    print(f"✅ Found exact match: {flavor_name} ({vcpus}vCPU, {ram//1024}GB)")
                    return flavor_name
        
        print(f"⚠️ No exact {target_vcpus}vCPU {target_ram_gb}GB flavor found")
        print(f"🔍 Trying to query flavor list...")
        
        # 2. Fallback to list_flavors query
        flavors = self.get_available_flavors()
        if not flavors:
            print(f"⚠️ Cannot query flavor list, using region default mapping")
            return self.get_default_flavor_from_map()
        
        # 2. If no exact match, find closest flavor in priority order
        for series_prefix in region_priority:
            # Collect all flavors in this series
            series_flavors = []
            for flavor in flavors:
                if flavor.get("name", "").startswith(series_prefix):
                    vcpu_diff = abs(flavor.get("vcpus", 0) - target_vcpus)
                    ram_diff = abs(flavor.get("ram", 0) - target_ram_mb)
                    total_diff = vcpu_diff * 1000 + ram_diff  # vCPU has higher weight
                    
                    series_flavors.append({
                        "flavor": flavor,
                        "vcpu_diff": vcpu_diff,
                        "ram_diff": ram_diff,
                        "total_diff": total_diff
                    })
            
            if series_flavors:
                # Sort by difference
                series_flavors.sort(key=lambda x: x["total_diff"])
                best_flavor = series_flavors[0]["flavor"]
                flavor_name = best_flavor.get("name")
                vcpus = best_flavor.get("vcpus")
                ram_gb = best_flavor.get("ram") / 1024
                
                print(f"✅ Selected flavor: {flavor_name} ({vcpus}vCPU, {ram_gb:.1f}GB, Priority: {series_prefix})")
                return flavor_name
        
        # 3. If no flavors in specified series found, find closest available flavor
        print(f"⚠️ Region priority flavors unavailable, finding closest available flavor...")
        flavors_with_diff = []
        for flavor in flavors:
            vcpu_diff = abs(flavor.get("vcpus", 0) - target_vcpus)
            ram_diff = abs(flavor.get("ram", 0) - target_ram_mb)
            total_diff = vcpu_diff * 1000 + ram_diff  # vCPU has higher weight
            
            flavors_with_diff.append({
                "flavor": flavor,
                "vcpu_diff": vcpu_diff,
                "ram_diff": ram_diff,
                "total_diff": total_diff
            })
        
        # Sort by difference
        flavors_with_diff.sort(key=lambda x: x["total_diff"])
        
        if flavors_with_diff:
            best_flavor = flavors_with_diff[0]["flavor"]
            flavor_name = best_flavor.get("name")
            vcpus = best_flavor.get("vcpus")
            ram_gb = best_flavor.get("ram") / 1024
            
            print(f"✅ Selected closest flavor: {flavor_name} ({vcpus}vCPU, {ram_gb:.1f}GB)")
            return flavor_name
        
        # 4. If still not found, use region mapping
        print(f"⚠️ No suitable flavor found, using region default mapping")
        return self.get_default_flavor_from_map()
    
    def get_default_flavor_from_map(self):
        """Get default flavor from region mapping (fallback solution)"""
        flavor = REGION_FLAVOR_MAP.get(self.region)
        if flavor:
            return flavor
        
        return REGION_FLAVOR_MAP.get("default", "x1.4u.8g")
    
    def get_default_flavor(self, flavor_override=None):
        """Get default flavor by region (enhanced version)
        
        Args:
            flavor_override: User-specified flavor (used with priority)
        
        Returns:
            tuple: (flavor ID, flavor description)
        """
        # 1. If user specified a flavor, use it directly
        if flavor_override:
            description = FLAVOR_DESCRIPTION.get(flavor_override, f"Custom flavor: {flavor_override}")
            return flavor_override, description
        
        # 2. Dynamically query the best suitable flavor
        try:
            best_flavor = self.find_best_flavor(target_vcpus=4, target_ram_gb=8)
            if best_flavor:
                description = FLAVOR_DESCRIPTION.get(best_flavor, f"Dynamically selected: {best_flavor}")
                return best_flavor, description
        except Exception as e:
            print(f"⚠️ Dynamic flavor query failed: {e}")
            # Continue with mapping table
        
        # 3. Get from region mapping (fallback)
        flavor = REGION_FLAVOR_MAP.get(self.region)
        if flavor:
            description = FLAVOR_DESCRIPTION.get(flavor, f"Region default: {flavor}")
            return flavor, description
        
        # 4. Use default
        default_flavor = REGION_FLAVOR_MAP.get("default", "x1.4u.8g")
        description = FLAVOR_DESCRIPTION.get(default_flavor, f"Default: {default_flavor}")
        return default_flavor, description

    def _sign_request(self, method, url, body=""):
        """Sign request"""
        parsed_url = urlparse(url)

        # Build header params
        header_params = {
            "X-Project-Id": self.project_id,
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }

        # Add X-Security-Token header for temporary credentials
        if self.security_token:
            header_params["X-Security-Token"] = self.security_token

        request = SdkRequest(
            method=method,
            schema=parsed_url.scheme,
            host=parsed_url.netloc,
            resource_path=parsed_url.path,
            query_params=[],
            header_params=header_params,
            body=body if body else ""
        )

        self.signer.sign(request)
        return request

    def _do_request(self, method, url, body=None, timeout=120):
        """Execute signed request"""
        body_str = json.dumps(body, ensure_ascii=False) if body else ""
        request = self._sign_request(method, url, body_str)
        full_url = f"{request.schema}://{request.host}{request.resource_path}"
        
        if method == "GET":
            resp = requests.get(url=full_url, headers=request.header_params, verify=False, timeout=timeout)
        elif method == "POST":
            resp = requests.post(url=full_url, headers=request.header_params, data=body_str, verify=False, timeout=timeout)
        elif method == "PUT":
            resp = requests.put(url=full_url, headers=request.header_params, data=body_str, verify=False, timeout=timeout)
        elif method == "DELETE":
            resp = requests.delete(url=full_url, headers=request.header_params, verify=False, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return resp
        
    def test_connection(self):
        """Test AK/SK connection"""
        print("📡 Testing AK/SK connection...")
        
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers?limit=1"
        resp = self._do_request("GET", url)
        
        if resp.status_code == 200:
            print("✅ AK/SK verification successful!")
            return True
        else:
            print(f"❌ AK/SK verification failed: {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            return False
            
    def get_ubuntu_image_id(self, os_version="22.04"):
        """Dynamically get Ubuntu image ID
        
        ⚠️ Important: Only returns x86_64 architecture images, ARM64 does not support SQLBot
        
        Args:
            os_version: Ubuntu version, e.g. "22.04"
            
        Returns:
            Image ID, returns None if not found
        """
        print(f"🔍 Querying Ubuntu {os_version} image (x86_64 architecture)...")
        print(f"⚠️ Note: SQLBot requires x86_64 architecture, ARM64 is not supported")
        
        # Use ECS Nova API to query images
        # Filter conditions: public images (gold), Ubuntu, specified version, x86_64 architecture
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/images/detail"
        resp = self._do_request("GET", url)
        
        if resp.status_code != 200:
            print(f"❌ Image query failed: {resp.status_code}")
            return None
            
        images = resp.json().get("images", [])
        
        # Filter Ubuntu 22.04 server 64bit public images
        # Exact match target name (priority)
        exact_target = f"Ubuntu {os_version} server 64bit"
        # Fuzzy match target names (alternatives)
        fuzzy_targets = [
            f"Ubuntu {os_version} server 64bit",
            f"ubuntu {os_version} server 64bit",
            f"Ubuntu-{os_version}-server",
        ]
        
        # Exclude keywords (bare metal, special images, ARM architecture)
        exclude_keywords = ["baremetal", "bms", "vroce", "with uniagent", "gpu", "ai", "arm", "aarch64", "kunpeng", "with graphic", "with cuda", "with tesla"]
        
        # Priority: exact match
        exact_match = None
        candidates = []
        
        for img in images:
            name = img.get("name", "")
            name_lower = name.lower()
            metadata = img.get("metadata", {})
            image_type = metadata.get("__image_type", "")
            hw_cpu_arch = metadata.get("hw_cpu_arch", "")
            
            # ⚠️ Critical: Only allow x86_64 architecture
            if hw_cpu_arch and hw_cpu_arch != "x86_64":
                print(f"  ⏭️ Skipping non-x86 image: {name} (Arch: {hw_cpu_arch})")
                continue
            
            # Exclude bare metal and special images
            if any(kw in name_lower for kw in exclude_keywords):
                continue
            
            # Priority: exact match
            if name == exact_target:
                if image_type == "gold":
                    exact_match = (img, name)
                    break  # Exact match to public image, use directly
                else:
                    exact_match = (img, name)
            
            # Fuzzy match (alternatives)
            for target in fuzzy_targets:
                if target.lower() in name_lower:
                    # Prefer public images (gold)
                    if image_type == "gold":
                        candidates.insert(0, (img, name))  # Public images first
                    else:
                        candidates.append((img, name))
                    break
        
        # Priority: use exact match result
        if exact_match:
            img, name = exact_match
            arch = img.get("metadata", {}).get("hw_cpu_arch", "x86_64")
            print(f"✅ Found image (exact match): {name}")
            print(f"   ID: {img['id']}")
            print(f"   Architecture: {arch} (✅ Meets requirements)")
            return img["id"], name
        elif candidates:
            img, name = candidates[0]
            arch = img.get("metadata", {}).get("hw_cpu_arch", "x86_64")
            print(f"✅ Found image: {name}")
            print(f"   ID: {img['id']}")
            print(f"   Architecture: {arch} (✅ Meets requirements)")
            return img["id"], name
                
        print(f"❌ Ubuntu {os_version} x86_64 image not found")
        print(f"⚠️ Please verify x86_64 Ubuntu images are available in this region")
        return None
            
    def get_default_network(self):
        """Get default network configuration, create automatically if not exists"""
        # Query subnets
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
        resp = self._do_request("GET", url)
        
        subnets = []
        if resp.status_code == 200:
            subnets = resp.json().get("subnets", [])
            
        # If no subnets, automatically create VPC and subnet
        if not subnets:
            print("\n⚠️ No available subnets found, will create VPC and subnet automatically...")
            
            # Create VPC
            vpc_id = self.create_vpc("sqlbot-vpc", "192.168.0.0/16")
            if not vpc_id:
                print("❌ VPC creation failed, cannot continue deployment")
                return {
                    "subnet_id": None,
                    "subnet_name": None,
                    "availability_zone": f"{self.region}a",
                    "security_group_id": None,
                    "security_group_name": None,
                    "vpc_id": None,
                }
            
            # Get availability zone
            availability_zone = f"{self.region}a"
            try:
                zones = self.get_available_zones()
                if zones:
                    availability_zone = zones[0]
            except:
                pass
            
            # Create subnet
            subnet_id = self.create_subnet(vpc_id, "sqlbot-subnet", "192.168.0.0/24", availability_zone)
            if not subnet_id:
                print("❌ Subnet creation failed, cannot continue deployment")
                return {
                    "subnet_id": None,
                    "subnet_name": None,
                    "availability_zone": availability_zone,
                    "security_group_id": None,
                    "security_group_name": None,
                    "vpc_id": vpc_id,
                }
            
            print(f"✅ Network environment created successfully")
            print(f"  VPC ID: {vpc_id}")
            print(f"  Subnet ID: {subnet_id}")
            
            # Re-query subnet information
            url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
            resp = self._do_request("GET", url)
            if resp.status_code == 200:
                subnets = resp.json().get("subnets", [])
        
        # Query security groups
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("GET", url)
        
        security_groups = []
        if resp.status_code == 200:
            security_groups = resp.json().get("security_groups", [])
            
        # Find default security group
        default_sg = None
        for sg in security_groups:
            if "default" in sg.get("name", "").lower():
                default_sg = sg
                break
        if not default_sg and security_groups:
            default_sg = security_groups[0]
            
        subnet = subnets[0] if subnets else None
        
        return {
            "subnet_id": subnet.get("id") if subnet else None,
            "subnet_name": subnet.get("name") if subnet else None,
            "availability_zone": subnet.get("availability_zone") if subnet else f"{self.region}a",
            "security_group_id": default_sg.get("id") if default_sg else None,
            "security_group_name": default_sg.get("name") if default_sg else None,
            "vpc_id": subnet.get("vpc_id") if subnet else None,
        }
    
    # ==================== Availability Zone Management ====================
    
    def get_available_zones(self):
        """Query available availability zones in current region
        
        Returns:
            list: List of availability zone names, e.g. ['cn-south-1c', 'cn-south-1e', ...]
        """
        print(f"🔍 Querying availability zones...")
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/os-availability-zone"
        resp = self._do_request("GET", url, timeout=30)
        
        if resp.status_code == 200:
            zones_info = resp.json().get("availabilityZoneInfo", [])
            available_zones = [
                z["zoneName"] for z in zones_info 
                if z.get("zoneState", {}).get("available", False)
            ]
            # Filter out cross-region availability zones (e.g., cn-south-2b in cn-south-1 region)
            available_zones = [z for z in available_zones if z.startswith(self.region)]
            print(f"✅ Availability zones: {', '.join(available_zones)}")
            return available_zones
        else:
            print(f"❌ Failed to query availability zones: {resp.status_code}")
            return []
    
    def get_random_available_zone(self):
        """Randomly select an available zone
        
        Returns:
            str: Availability zone name, e.g. 'cn-south-1c'
        """
        import random
        zones = self.get_available_zones()
        if zones:
            selected = random.choice(zones)
            print(f"🎲 Randomly selected zone: {selected}")
            return selected
        else:
            # Fallback to default zone
            default_zone = f"{self.region}a"
            print(f"⚠️ No zone info available, using default: {default_zone}")
            return default_zone
        
    # ==================== Security Group Management ====================
    
    def get_security_group_by_name(self, name):
        """Get security group by name"""
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("GET", url)
        
        if resp.status_code == 200:
            sgs = resp.json().get("security_groups", [])
            for sg in sgs:
                if sg.get("name") == name:
                    return sg
        return None
    
    def create_vpc(self, name="sqlbot-vpc", cidr="192.168.0.0/16"):
        """Create VPC
        
        Args:
            name: VPC name
            cidr: VPC CIDR block
            
        Returns:
            str: VPC ID, returns None on failure
        """
        print(f"\n🌐 Creating VPC: {name}")
        print(f"  CIDR: {cidr}")
        
        request_body = {
            "vpc": {
                "name": name,
                "cidr": cidr
            }
        }
        
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/vpcs"
        resp = self._do_request("POST", url, request_body)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            vpc = data.get("vpc", {})
            vpc_id = vpc.get("id")
            print(f"✅ VPC created successfully: {vpc_id}")
            return vpc_id
        else:
            print(f"❌ VPC creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None
    
    def create_subnet(self, vpc_id, name="sqlbot-subnet", cidr="192.168.0.0/24", availability_zone=None):
        """Create subnet
        
        Args:
            vpc_id: VPC ID
            name: Subnet name
            cidr: Subnet CIDR block
            availability_zone: Availability zone
            
        Returns:
            str: Subnet ID, returns None on failure
        """
        print(f"\n🔗 Creating subnet: {name}")
        print(f"  VPC ID: {vpc_id}")
        print(f"  CIDR: {cidr}")
        if availability_zone:
            print(f"  Availability zone: {availability_zone}")
        
        request_body = {
            "subnet": {
                "name": name,
                "cidr": cidr,
                "vpc_id": vpc_id
            }
        }
        
        if availability_zone:
            request_body["subnet"]["availability_zone"] = availability_zone
        
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
        resp = self._do_request("POST", url, request_body)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            subnet = data.get("subnet", {})
            subnet_id = subnet.get("id")
            print(f"✅ Subnet created successfully: {subnet_id}")
            return subnet_id
        else:
            print(f"❌ Subnet creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None
    
    def create_security_group(self, name, vpc_id=None, description=""):
        """Create security group"""
        print(f"\n🛡️ Creating security group: {name}")
        
        if not vpc_id:
            network = self.get_default_network()
            vpc_id = network.get("vpc_id")
            
        request_body = {
            "security_group": {
                "name": name,
                "vpc_id": vpc_id,
                "description": description or f"Security group for SQLBot deployment"
            }
        }
        
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("POST", url, request_body)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            sg = data.get("security_group", {})
            sg_id = sg.get("id")
            print(f"✅ Security group created successfully: {sg_id}")
            return sg_id
        else:
            print(f"❌ Security group creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None
            
    def add_security_group_rule(self, sg_id, direction="ingress", protocol="tcp", 
                                 port_range_min=None, port_range_max=None, 
                                 remote_ip_prefix="0.0.0.0/0", description=""):
        """Add security group rule"""
        rule_body = {
            "security_group_rule": {
                "security_group_id": sg_id,
                "direction": direction,
                "protocol": protocol,
                "remote_ip_prefix": remote_ip_prefix,
                "description": description
            }
        }
        
        if port_range_min:
            rule_body["security_group_rule"]["port_range_min"] = port_range_min
        if port_range_max:
            rule_body["security_group_rule"]["port_range_max"] = port_range_max
            
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-group-rules"
        resp = self._do_request("POST", url, rule_body)
        
        if resp.status_code in [200, 201]:
            port_str = f"{port_range_min}" if port_range_min == port_range_max else f"{port_range_min}-{port_range_max}"
            print(f"✅ Rule added: {direction} {protocol} {port_str} from {remote_ip_prefix}")
            return True
        else:
            print(f"❌ Rule addition failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return False
            
    def ensure_security_group(self, sg_name="sg-sqlbot"):
        """Ensure security group exists, create if not"""
        # Check if security group exists
        existing_sg = self.get_security_group_by_name(sg_name)
        if existing_sg:
            sg_id = existing_sg.get("id")
            print(f"✅ Using existing security group: {sg_name} ({sg_id})")
            return sg_id
        
        # Create security group
        network = self.get_default_network()
        sg_id = self.create_security_group(sg_name, network.get("vpc_id"))
        return sg_id
            
    def bind_security_group_to_server(self, server_id, sg_id, sg_name):
        """Bind security group to server"""
        print(f"\n🔗 Binding security group {sg_name} to server...")
        
        # Use changeSecurityGroup API
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}/action"
        request_body = {
            "changeSecurityGroup": {
                "security_groups": [
                    {"id": sg_id}
                ]
            }
        }
        
        resp = self._do_request("POST", url, request_body)
        
        if resp.status_code == 202:
            print(f"✅ Security group bound successfully")
            return True
        else:
            print(f"❌ Security group binding failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return False
            
    # ==================== Server Management ====================
        
    def create_prepaid_server_with_sdk(self, server_name, flavor_id, image_id, volume_size=80,
                                       vpc_id=None, subnet_id=None, security_group_id=None,
                                       admin_pass=None, availability_zone=None,
                                       eip_bandwidth=300):
        """Create monthly-billed server using Huawei Cloud SDK
        
        Args:
            server_name: Server name
            flavor_id: Flavor ID
            image_id: Image ID
            volume_size: System disk size (GB)
            vpc_id: VPC ID
            subnet_id: Subnet ID
            security_group_id: Security group ID
            admin_pass: Administrator password
            availability_zone: Availability zone
            eip_bandwidth: EIP bandwidth (Mbps)
            
        Returns:
            dict: Server info {"id": ..., "public_ip": ..., "password": ...}
        """
        admin_pass = admin_pass or DEFAULT_CONFIG["admin_pass"]
        
        # Get network info
        if not vpc_id or not subnet_id:
            network = self.get_default_network()
            vpc_id = vpc_id or network.get("vpc_id")
            subnet_id = subnet_id or network.get("subnet_id")
        
        if not vpc_id or not subnet_id:
            print("❌ Failed to get network information")
            return None
        
        # Get security group ID
        if not security_group_id:
            security_group_id = self.ensure_security_group()
        
        print(f"\n📦 Creating monthly-billed server using SDK")
        print(f"  Server name: {server_name}")
        print(f"  Flavor: {flavor_id}")
        print(f"  System disk: {volume_size}GB")
        print(f"  Billing mode: Monthly (1 month, auto-pay)")
        print(f"  Public IP: Auto-create ({eip_bandwidth}M bandwidth)")
        
        try:
            # Create client using pre-initialized credentials
            client = EcsClient.new_builder() \
                .with_credentials(self.credentials) \
                .with_region(EcsRegion.value_of(self.region)) \
                .build()
            
            # Build request
            request = CreateServersRequest()
            
            # ✅ EIP configuration: Even for monthly-billed servers, EIP uses pay-as-you-go, traffic-based billing
            # Use extendparam.chargingMode = "postPaid" to specify EIP as pay-as-you-go
            bandwidth_eip = PrePaidServerEipBandwidth(
                size=eip_bandwidth,
                sharetype="PER",
                chargemode="traffic"  # Traffic-based billing
            )
            
            eip_publicip = PrePaidServerEip(
                iptype="5_bgp",  # Full dynamic BGP
                bandwidth=bandwidth_eip,
                extendparam={"chargingMode": "postPaid", "delete_on_termination": "true"}  # EIP pay-as-you-go, released with instance
            )
            
            publicip_server = PrePaidServerPublicip(
                eip=eip_publicip
            )
            
            # Network interface configuration
            list_nics_server = [
                PrePaidServerNic(
                    subnet_id=subnet_id
                )
            ]
            
            # System disk configuration
            root_volume_server = PrePaidServerRootVolume(
                volumetype="SAS",
                size=volume_size
            )
            
            # Monthly billing configuration (auto-pay)
            extendparam_server = PrePaidServerExtendParam(
                charging_mode="prePaid",  # Monthly/yearly billing
                period_type="month",      # Monthly
                period_num=1,             # Buy 1 month
                is_auto_renew="false",    # Auto-renew disabled
                is_auto_pay="true"        # Auto-pay enabled
            )
            
            # Security group configuration
            list_security_groups_server = [
                PrePaidServerSecurityGroup(
                    id=security_group_id
                )
            ]
            
            # Server configuration
            server_body = PrePaidServer(
                image_ref=image_id,
                flavor_ref=flavor_id,
                name=server_name,
                vpcid=vpc_id,
                nics=list_nics_server,
                publicip=publicip_server,
                root_volume=root_volume_server,
                admin_pass=admin_pass,
                security_groups=list_security_groups_server,
                extendparam=extendparam_server
            )
            
            # Add availability zone
            if availability_zone:
                server_body.availability_zone = availability_zone
            
            request.body = CreateServersRequestBody(
                server=server_body
            )
            
            print(f"\n⏳ Sending create request...")
            
            response = client.create_servers(request)
            result = response.to_dict()
            
            job_id = result.get("job_id")
            order_id = result.get("order_id")
            server_ids = result.get("serverIds", [])
            
            print(f"✅ Create request sent")
            print(f"  Job ID: {job_id}")
            print(f"  Order ID: {order_id}")
            
            # Wait for server ID (monthly orders take longer)
            if not server_ids:
                print(f"\n⏳ Waiting for monthly order processing...")
                for i in range(60):  # Wait up to 2 minutes
                    time.sleep(3)
                    # Query job status
                    job_url = f"https://ecs.{self.region}.myhuaweicloud.com/v1/{self.project_id}/jobs/{job_id}"
                    job_resp = self._do_request("GET", job_url)
                    if job_resp.status_code == 200:
                        job_data = job_resp.json().get("job", {})
                        status = job_data.get("status")
                        if status == "SUCCESS":
                            server_ids = job_data.get("entities", {}).get("server_ids", [])
                            if server_ids:
                                print(f"✅ Order processed, server created")
                                break
                        elif status == "FAIL":
                            print(f"❌ Job failed: {job_data.get('fail_reason')}")
                            return None
                        else:
                            print(f"  [{i*3}s] Job status: {status}")
            
            # If still no server_ids, try querying via order
            if not server_ids and order_id:
                print(f"\n⏳ Querying server via order...")
                # Wait longer, order processing may take minutes
                for i in range(40):
                    time.sleep(5)
                    # List recently created servers
                    list_url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/detail?limit=5"
                    list_resp = self._do_request("GET", list_url)
                    if list_resp.status_code == 200:
                        servers = list_resp.json().get("servers", [])
                        for s in servers:
                            if s.get("name") == server_name:
                                server_ids = [s.get("id")]
                                print(f"✅ Found server: {s.get('id')}")
                                break
                    if server_ids:
                        break
            
            if not server_ids:
                print(f"⚠️ Server ID not retrieved, but order created: {order_id}")
                print(f"💡 Please check order status in Huawei Cloud Console")
                return {
                    "server_id": None,
                    "public_ip": None,
                    "admin_pass": admin_pass,
                    "order_id": order_id,
                    "job_id": job_id
                }
            
            server_id = server_ids[0]
            print(f"\n✅ Server created: {server_id}")
            
            # Wait for server to be ready and get public IP
            print(f"\n⏳ Waiting for server to be ready...")
            public_ip = None
            
            for i in range(60):
                time.sleep(3)
                server_url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
                server_resp = self._do_request("GET", server_url)
                
                if server_resp.status_code == 200:
                    server = server_resp.json().get("server", {})
                    status = server.get("status")
                    
                    # Get public IP
                    addresses = server.get("addresses", {})
                    for network_name, addr_list in addresses.items():
                        for addr in addr_list:
                            if addr.get("OS-EXT-IPS:type") == "floating":
                                public_ip = addr.get("addr")
                    
                    print(f"  [{i*3}s] Status: {status}, Public IP: {public_ip or 'acquiring...'}")
                    
                    if status == "ACTIVE":
                        break
                elif server_resp.status_code == 404:
                    print(f"  [{i*3}s] Server still being created...")
            
            if public_ip:
                print(f"\n✅ Public IP auto-assigned: {public_ip}")
            else:
                print(f"\n⚠️ Public IP not retrieved, EIP may still be creating")
            
            return {
                "server_id": server_id,
                "public_ip": public_ip,
                "admin_pass": admin_pass,
                "order_id": order_id
            }
            
        except Exception as e:
            print(f"❌ SDK creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_postpaid_server_with_sdk(self, server_name, flavor_id, image_id, volume_size=80,
                                        vpc_id=None, subnet_id=None, security_group_id=None,
                                        admin_pass=None, availability_zone=None,
                                        eip_bandwidth=300):
        """Create pay-as-you-go server using Huawei Cloud SDK
        
        Args:
            server_name: Server name
            flavor_id: Flavor ID
            image_id: Image ID
            volume_size: System disk size (GB)
            vpc_id: VPC ID
            subnet_id: Subnet ID
            security_group_id: Security group ID
            admin_pass: Administrator password
            availability_zone: Availability zone
            eip_bandwidth: EIP bandwidth (Mbps)
            
        Returns:
            dict: Server info {"server_id": ..., "public_ip": ..., "admin_pass": ...}
        """
        admin_pass = admin_pass or DEFAULT_CONFIG["admin_pass"]
        
        # Get network info
        if not vpc_id or not subnet_id:
            network = self.get_default_network()
            vpc_id = vpc_id or network.get("vpc_id")
            subnet_id = subnet_id or network.get("subnet_id")
        
        if not vpc_id or not subnet_id:
            print("❌ Failed to get network information")
            return None
        
        # Get security group ID
        if not security_group_id:
            security_group_id = self.ensure_security_group()
        
        print(f"\n📦 Creating pay-as-you-go server using SDK")
        print(f"  Server name: {server_name}")
        print(f"  Flavor: {flavor_id}")
        print(f"  System disk: {volume_size}GB")
        print(f"  Billing mode: Pay-as-you-go")
        print(f"  Public IP: Auto-create ({eip_bandwidth}M bandwidth)")
        
        try:
            # Create client using pre-initialized credentials
            client = EcsClient.new_builder() \
                .with_credentials(self.credentials) \
                .with_region(EcsRegion.value_of(self.region)) \
                .build()
            
            # Build request
            request = CreateServersRequest()
            
            # EIP configuration - pay-as-you-go, traffic-based billing
            bandwidth_eip = PostPaidServerEipBandwidth(
                size=eip_bandwidth,
                sharetype="PER",
                chargemode="traffic"  # Traffic-based billing
            )
            
            eip_publicip = PostPaidServerEip(
                iptype="5_bgp",  # Full dynamic BGP
                bandwidth=bandwidth_eip,
                extendparam={"chargingMode": "postPaid", "delete_on_termination": "true"}  # EIP pay-as-you-go, released with instance
            )
            
            publicip_server = PostPaidServerPublicip(
                eip=eip_publicip
            )
            
            # Network interface configuration
            list_nics_server = [
                PostPaidServerNic(
                    subnet_id=subnet_id
                )
            ]
            
            # System disk configuration
            root_volume_server = PostPaidServerRootVolume(
                volumetype="SAS",
                size=volume_size
            )
            
            # Security group configuration
            list_security_groups_server = [
                PostPaidServerSecurityGroup(
                    id=security_group_id
                )
            ]
            
            # Server configuration
            server_body = PostPaidServer(
                image_ref=image_id,
                flavor_ref=flavor_id,
                name=server_name,
                vpcid=vpc_id,
                nics=list_nics_server,
                publicip=publicip_server,
                root_volume=root_volume_server,
                admin_pass=admin_pass,
                security_groups=list_security_groups_server
            )
            
            # Add availability zone
            if availability_zone:
                server_body.availability_zone = availability_zone
            
            request.body = CreateServersRequestBody(
                server=server_body
            )
            
            print(f"\n⏳ Sending create request...")
            
            response = client.create_servers(request)
            result = response.to_dict()
            
            job_id = result.get("job_id")
            server_ids = result.get("serverIds", [])
            
            print(f"✅ Create request sent")
            print(f"  Job ID: {job_id}")
            
            # Wait for server ID
            if not server_ids:
                print(f"\n⏳ Waiting for server creation...")
                for i in range(60):
                    time.sleep(3)
                    # Query job status using SDK
                    try:
                        job_request = ShowJobRequest(job_id=job_id)
                        job_response = client.show_job(job_request)
                        job_data = job_response.to_dict()
                        status = job_data.get("status")
                        
                        if status == "SUCCESS":
                            # Get server ID from sub-jobs
                            sub_jobs = job_data.get("entities", {}).get("sub_jobs", [])
                            if sub_jobs:
                                server_id = sub_jobs[0].get("entities", {}).get("server_id")
                                if server_id:
                                    server_ids = [server_id]
                                    print(f"✅ Server created")
                                    break
                        elif status == "FAIL":
                            print(f"❌ Job failed: {job_data.get('fail_reason')}")
                            return None
                        else:
                            print(f"  [{i*3}s] Job status: {status}")
                    except Exception as e:
                        print(f"  [{i*3}s] Failed to query job status: {e}")
            
            if not server_ids:
                print(f"❌ Server ID not retrieved")
                return None
            
            server_id = server_ids[0]
            print(f"\n✅ Server created: {server_id}")
            
            # Wait for server to be ready
            print(f"\n⏳ Waiting for server to be ready...")
            public_ip = None
            
            for i in range(60):
                time.sleep(3)
                server_url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
                server_resp = self._do_request("GET", server_url)
                
                if server_resp.status_code == 200:
                    server = server_resp.json().get("server", {})
                    status = server.get("status")
                    
                    # Get public IP
                    addresses = server.get("addresses", {})
                    for network_name, ips in addresses.items():
                        for ip_info in ips:
                            if ip_info.get("OS-EXT-IPS:type") == "floating":
                                public_ip = ip_info.get("addr")
                                break
                    
                    print(f"  [{i*3}s] Status: {status}, Public IP: {public_ip or 'none'}")
                    
                    if status == "ACTIVE" and public_ip:
                        break
                elif server_resp.status_code == 404:
                    print(f"  [{i*3}s] Server still being created...")
            
            if not public_ip:
                print(f"⚠️ Server ready but public IP not retrieved")
            
            return {
                "server_id": server_id,
                "public_ip": public_ip,
                "admin_pass": admin_pass
            }
            
        except Exception as e:
            print(f"❌ SDK creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_server_detail(self, server_id):
        """Get server detail"""
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
        resp = self._do_request("GET", url)
        
        if resp.status_code == 200:
            data = resp.json()
            server = data.get("server", {})
            
            result = {
                "name": server.get("name"),
                "id": server.get("id"),
                "status": server.get("status"),
                "flavor": server.get("flavor", {}).get("id"),
            }
            
            addresses = server.get("addresses", {})
            for network_name, ips in addresses.items():
                for ip_info in ips:
                    addr = ip_info.get("addr")
                    if ip_info.get("OS-EXT-IPS:type") == "floating":
                        result["public_ip"] = addr
                    else:
                        result["private_ip"] = addr
                        
            return result
        return None
        
    def wait_server_active(self, server_id, timeout=600):
        """Wait for server to become active"""
        print(f"\n⏳ Waiting for server to start, this may take 3-5 minutes...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            detail = self.get_server_detail(server_id)
            if detail:
                status = detail.get("status")
                elapsed = int(time.time() - start_time)
                if status == "ACTIVE":
                    print(f"\n✅ Server ready (elapsed: {elapsed}s)")
                    return detail
                elif status == "ERROR":
                    print(f"\n❌ Server status error")
                    return None
                print(f"  Status: {status}... (waited: {elapsed}s)", end="\r")
            time.sleep(10)  # Longer check interval
            
        print(f"\n❌ Timeout waiting ({timeout}s)")
        return None
