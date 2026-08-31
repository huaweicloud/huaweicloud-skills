#!/usr/bin/env python3
"""
Huawei Cloud ECS SDK wrapper class for DeepSeek Harness (dsh) Deployment
"""

import json
import os
import requests
import uuid
import urllib3
import time
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest
from huaweicloudsdkecs.v2 import EcsClient, CreateServersRequest, CreateServersRequestBody
from huaweicloudsdkecs.v2 import PostPaidServer, PostPaidServerNic, PostPaidServerRootVolume
from huaweicloudsdkecs.v2 import PostPaidServerPublicip, PostPaidServerEip, PostPaidServerEipBandwidth
from huaweicloudsdkecs.v2 import PostPaidServerSecurityGroup
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

urllib3.disable_warnings()

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
        # SSL verification: default enabled, can be disabled via env var for testing
        self.verify_ssl = os.environ.get('HW_VERIFY_SSL', 'true').lower() == 'true'
        self.credentials = BasicCredentials(ak, sk, project_id)
        if security_token:
            self.credentials = self.credentials.with_security_token(security_token)
        self.signer = Signer(self.credentials)

    def _sign_request(self, method, url, body=""):
        parsed_url = urlparse(url)

        header_params = {
            "X-Project-Id": self.project_id,
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }

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
        body_str = json.dumps(body, ensure_ascii=False) if body else ""
        request = self._sign_request(method, url, body_str)
        full_url = f"{request.schema}://{request.host}{request.resource_path}"

        if method == "GET":
            resp = requests.get(url=full_url, headers=request.header_params, verify=self.verify_ssl, timeout=timeout)
        elif method == "POST":
            resp = requests.post(url=full_url, headers=request.header_params, data=body_str, verify=self.verify_ssl, timeout=timeout)
        elif method == "PUT":
            resp = requests.put(url=full_url, headers=request.header_params, data=body_str, verify=self.verify_ssl, timeout=timeout)
        elif method == "DELETE":
            resp = requests.delete(url=full_url, headers=request.header_params, verify=self.verify_ssl, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return resp

    def parse_error_response(self, response, operation="operation"):
        error_info = {
            "error_code": "Unknown",
            "error_msg": "Unknown error",
            "suggestion": "",
            "raw_response": response.text[:500] if hasattr(response, 'text') else ""
        }

        try:
            if hasattr(response, 'status_code'):
                error_info["status_code"] = response.status_code

            if hasattr(response, 'json'):
                try:
                    error_data = response.json()

                    if "error" in error_data:
                        err = error_data["error"]
                        error_info["error_code"] = err.get("code", "Unknown")
                        error_info["error_msg"] = err.get("message", str(err))
                    elif "error_code" in error_data:
                        error_info["error_code"] = error_data.get("error_code", "Unknown")
                        error_info["error_msg"] = error_data.get("error_msg", "Unknown error")
                    elif "errCode" in error_data:
                        error_info["error_code"] = error_data.get("errCode", "Unknown")
                        error_info["error_msg"] = error_data.get("errMsg", "Unknown error")
                    elif "message" in error_data:
                        error_info["error_msg"] = error_data.get("message", "Unknown error")

                except:
                    pass

        except Exception as e:
            error_info["parse_error"] = str(e)

        error_code = error_info.get("error_code", "")
        error_msg = error_info.get("error_msg", "").lower()

        suggestions = {
            "Ecs.0707": "Flavor not available in current region. Try another region or flavor.",
            "Ecs.0079": "Market image requires accepting terms of service in console, or use public image instead.",
            "Ecs.0007": "Resource quota exceeded. Check account quotas or release unused resources.",
            "QuotaExceeded": "Resource quota exceeded. Apply for quota increase in console.",
            "AuthFailure": "AK/SK authentication failed. Check if credentials are correct.",
            "401": "Authentication failed. AK/SK may have expired or insufficient permissions.",
            "403": "Permission denied. Check if IAM policies include required permissions.",
            "404": "Resource not found. Check if resource ID is correct.",
        }

        for code, suggestion in suggestions.items():
            if code in str(error_code) or code in error_msg:
                error_info["suggestion"] = suggestion
                break

        if not error_info["suggestion"]:
            if "market image" in error_msg:
                error_info["suggestion"] = "Market image requires accepting terms of service in console"
            elif "flavor" in error_msg or "product" in error_msg:
                error_info["suggestion"] = "Flavor not available. Try another region or flavor."
            elif "quota" in error_msg:
                error_info["suggestion"] = "Resource quota exceeded. Check account quotas."

        return error_info

    def format_error_message(self, response, operation="operation"):
        error_info = self.parse_error_response(response, operation)

        msg_lines = [
            f"❌ {operation} failed",
            f"   Status: {error_info.get('status_code', 'N/A')}",
            f"   Error Code: {error_info.get('error_code', 'Unknown')}",
            f"   Error Message: {error_info.get('error_msg', 'Unknown')}",
        ]

        if error_info.get("suggestion"):
            msg_lines.append(f"   💡 Suggestion: {error_info['suggestion']}")

        return "\n".join(msg_lines)

    def get_flavor_details(self, flavor_id):
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/flavors/{flavor_id}"

        try:
            resp = self._do_request("GET", url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("flavor", {})
        except Exception:
            pass

        return None

    def get_available_flavors(self):
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
        except Exception as e:
            print(f"❌ Error querying flavors: {e}")

        return []

    def find_best_flavor(self, target_vcpus=2, target_ram_gb=4):
        target_ram_mb = target_ram_gb * 1024
        region_priority = REGION_FLAVOR_PRIORITY.get(self.region, REGION_FLAVOR_PRIORITY["default"])
        print(f"🔍 Flexus X instance type priority for region {self.region}: {region_priority}")

        for series_prefix in region_priority:
            flavor_name = f"{series_prefix}.{target_vcpus}u.{target_ram_gb}g"
            print(f"🔍 Trying flavor: {flavor_name}")

            detail = self.get_flavor_details(flavor_name)
            if detail and detail.get("vcpus") and detail.get("ram"):
                print(f"✅ Found exact match: {flavor_name} ({detail['vcpus']}vCPU, {detail['ram']//1024}GB)")
                return flavor_name

        print(f"⚠️ No exact {target_vcpus}vCPU {target_ram_gb}GB flavor found")
        flavors = self.get_available_flavors()
        if not flavors:
            print(f"⚠️ Cannot query flavor list, using region default mapping")
            return self.get_default_flavor_from_map()

        for series_prefix in region_priority:
            series_flavors = []
            for flavor in flavors:
                if flavor.get("name", "").startswith(series_prefix):
                    vcpu_diff = abs(flavor.get("vcpus", 0) - target_vcpus)
                    ram_diff = abs(flavor.get("ram", 0) - target_ram_mb)
                    series_flavors.append({
                        "flavor": flavor,
                        "total_diff": vcpu_diff * 1000 + ram_diff
                    })

            if series_flavors:
                series_flavors.sort(key=lambda x: x["total_diff"])
                best = series_flavors[0]["flavor"]
                print(f"✅ Selected flavor: {best['name']} ({best['vcpus']}vCPU, {best['ram']/1024:.1f}GB)")
                return best["name"]

        flavors_with_diff = []
        for flavor in flavors:
            vcpu_diff = abs(flavor.get("vcpus", 0) - target_vcpus)
            ram_diff = abs(flavor.get("ram", 0) - target_ram_mb)
            flavors_with_diff.append({
                "flavor": flavor,
                "total_diff": vcpu_diff * 1000 + ram_diff
            })

        if flavors_with_diff:
            flavors_with_diff.sort(key=lambda x: x["total_diff"])
            best = flavors_with_diff[0]["flavor"]
            print(f"✅ Selected closest flavor: {best['name']} ({best['vcpus']}vCPU, {best['ram']/1024:.1f}GB)")
            return best["name"]

        print(f"⚠️ No suitable flavor found, using region default mapping")
        return self.get_default_flavor_from_map()

    def get_default_flavor_from_map(self):
        return REGION_FLAVOR_MAP.get(self.region, REGION_FLAVOR_MAP.get("default", "x1.2u.4g"))

    def get_default_flavor(self, flavor_override=None):
        if flavor_override:
            description = FLAVOR_DESCRIPTION.get(flavor_override, f"Custom flavor: {flavor_override}")
            return flavor_override, description

        try:
            best_flavor = self.find_best_flavor(target_vcpus=2, target_ram_gb=4)
            if best_flavor:
                description = FLAVOR_DESCRIPTION.get(best_flavor, f"Dynamically selected: {best_flavor}")
                return best_flavor, description
        except Exception as e:
            print(f"⚠️ Dynamic flavor query failed: {e}")

        flavor = REGION_FLAVOR_MAP.get(self.region)
        if flavor:
            description = FLAVOR_DESCRIPTION.get(flavor, f"Region default: {flavor}")
            return flavor, description

        default_flavor = REGION_FLAVOR_MAP.get("default", "x1.2u.4g")
        description = FLAVOR_DESCRIPTION.get(default_flavor, f"Default: {default_flavor}")
        return default_flavor, description

    def test_connection(self):
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
        print(f"🔍 Querying Ubuntu {os_version} image (x86_64 architecture)...")

        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/images/detail"
        resp = self._do_request("GET", url)

        if resp.status_code != 200:
            print(f"❌ Image query failed: {resp.status_code}")
            return None

        images = resp.json().get("images", [])

        exact_target = f"Ubuntu {os_version} server 64bit"
        fuzzy_targets = [
            f"Ubuntu {os_version} server 64bit",
            f"ubuntu {os_version} server 64bit",
            f"Ubuntu-{os_version}-server",
        ]

        exclude_keywords = ["baremetal", "bms", "vroce", "with uniagent", "gpu", "ai", "arm", "aarch64", "kunpeng", "with graphic", "with cuda", "with tesla"]

        exact_match = None
        candidates = []

        for img in images:
            name = img.get("name", "")
            name_lower = name.lower()
            metadata = img.get("metadata", {})
            image_type = metadata.get("__image_type", "")
            hw_cpu_arch = metadata.get("hw_cpu_arch", "")

            if hw_cpu_arch and hw_cpu_arch != "x86_64":
                print(f"  ⏭️ Skipping non-x86 image: {name} (Arch: {hw_cpu_arch})")
                continue

            if any(kw in name_lower for kw in exclude_keywords):
                continue

            if name == exact_target:
                if image_type == "gold":
                    exact_match = (img, name)
                    break
                else:
                    exact_match = (img, name)

            for target in fuzzy_targets:
                if target.lower() in name_lower:
                    if image_type == "gold":
                        candidates.insert(0, (img, name))
                    else:
                        candidates.append((img, name))
                    break

        if exact_match:
            img, name = exact_match
            arch = img.get("metadata", {}).get("hw_cpu_arch", "x86_64")
            img_type = img.get("metadata", {}).get("__image_type", "unknown")
            print(f"✅ Found image (exact match): {name}")
            print(f"   ID: {img['id']}")
            print(f"   Architecture: {arch}")
            print(f"   Type: {img_type}")
            return (img["id"], name)
        elif candidates:
            img, name = candidates[0]
            arch = img.get("metadata", {}).get("hw_cpu_arch", "x86_64")
            img_type = img.get("metadata", {}).get("__image_type", "unknown")
            print(f"✅ Found image: {name}")
            print(f"   ID: {img['id']}")
            print(f"   Architecture: {arch}")
            print(f"   Type: {img_type}")
            return (img["id"], name)

        print(f"❌ Ubuntu {os_version} x86_64 image not found")
        return None

    def get_default_network(self):
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
        resp = self._do_request("GET", url)
        subnets = resp.json().get("subnets", []) if resp.status_code == 200 else []

        if not subnets:
            print("\n⚠️ No available subnets found, will create VPC and subnet automatically...")

            vpc_id = self.create_vpc("dsh-vpc", "192.168.0.0/16")
            if not vpc_id:
                print("❌ VPC creation failed")
                return {"subnet_id": None, "subnet_name": None, "availability_zone": f"{self.region}a", "security_group_id": None, "security_group_name": None, "vpc_id": None}

            availability_zone = f"{self.region}a"
            try:
                zones = self.get_available_zones()
                if zones:
                    availability_zone = zones[0]
            except:
                pass

            subnet_id = self.create_subnet(vpc_id, "dsh-subnet", "192.168.0.0/24", availability_zone)
            if not subnet_id:
                print("❌ Subnet creation failed")
                return {"subnet_id": None, "subnet_name": None, "availability_zone": availability_zone, "security_group_id": None, "security_group_name": None, "vpc_id": vpc_id}

            print(f"✅ Network environment created successfully")
            url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
            resp = self._do_request("GET", url)
            if resp.status_code == 200:
                subnets = resp.json().get("subnets", [])

        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("GET", url)
        security_groups = resp.json().get("security_groups", []) if resp.status_code == 200 else []

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

    def get_available_zones(self):
        print(f"🔍 Querying availability zones...")
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/os-availability-zone"
        resp = self._do_request("GET", url, timeout=30)

        if resp.status_code == 200:
            zones_info = resp.json().get("availabilityZoneInfo", [])
            available_zones = [z["zoneName"] for z in zones_info if z.get("zoneState", {}).get("available", False)]
            available_zones = [z for z in available_zones if z.startswith(self.region)]
            print(f"✅ Availability zones: {', '.join(available_zones)}")
            return available_zones
        else:
            print(f"❌ Failed to query availability zones: {resp.status_code}")
            return []

    def get_random_available_zone(self):
        import random
        zones = self.get_available_zones()
        if zones:
            selected = random.choice(zones)
            print(f"🎲 Randomly selected zone: {selected}")
            return selected
        else:
            default_zone = f"{self.region}a"
            print(f"⚠️ No zone info available, using default: {default_zone}")
            return default_zone

    def get_security_group_by_name(self, name):
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("GET", url)

        if resp.status_code == 200:
            for sg in resp.json().get("security_groups", []):
                if sg.get("name") == name:
                    return sg
        return None

    def create_vpc(self, name="dsh-vpc", cidr="192.168.0.0/16"):
        print(f"\n🌐 Creating VPC: {name}")

        request_body = {"vpc": {"name": name, "cidr": cidr}}
        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/vpcs"
        resp = self._do_request("POST", url, request_body)

        if resp.status_code in [200, 201]:
            vpc_id = resp.json().get("vpc", {}).get("id")
            print(f"✅ VPC created successfully: {vpc_id}")
            return vpc_id
        else:
            print(f"❌ VPC creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None

    def create_subnet(self, vpc_id, name="dsh-subnet", cidr="192.168.0.0/24", availability_zone=None):
        print(f"\n🔗 Creating subnet: {name}")

        request_body = {"subnet": {"name": name, "cidr": cidr, "vpc_id": vpc_id}}
        if availability_zone:
            request_body["subnet"]["availability_zone"] = availability_zone

        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/subnets"
        resp = self._do_request("POST", url, request_body)

        if resp.status_code in [200, 201]:
            subnet_id = resp.json().get("subnet", {}).get("id")
            print(f"✅ Subnet created successfully: {subnet_id}")
            return subnet_id
        else:
            print(f"❌ Subnet creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None

    def create_security_group(self, name, vpc_id=None, description=""):
        print(f"\n🛡️ Creating security group: {name}")

        if not vpc_id:
            network = self.get_default_network()
            vpc_id = network.get("vpc_id")

        request_body = {
            "security_group": {
                "name": name,
                "vpc_id": vpc_id,
                "description": description or "Security group for DeepSeek Harness (dsh) deployment"
            }
        }

        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-groups"
        resp = self._do_request("POST", url, request_body)

        if resp.status_code in [200, 201]:
            sg_id = resp.json().get("security_group", {}).get("id")
            print(f"✅ Security group created successfully: {sg_id}")
            return sg_id
        else:
            print(f"❌ Security group creation failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return None

    def add_security_group_rule(self, sg_id, direction="ingress", protocol="tcp",
                                 port_range_min=None, port_range_max=None,
                                 remote_ip_prefix="0.0.0.0/0", description="",
                                 ip_version="IPv4", remote_group_id=None):
        rule_body = {
            "security_group_rule": {
                "security_group_id": sg_id,
                "direction": direction,
                "protocol": protocol,
                "description": description
            }
        }

        if ip_version == "IPv6":
            rule_body["security_group_rule"]["ip_version"] = "IPv6"

        if remote_group_id:
            rule_body["security_group_rule"]["remote_group_id"] = remote_group_id
        else:
            rule_body["security_group_rule"]["remote_ip_prefix"] = remote_ip_prefix

        if port_range_min:
            rule_body["security_group_rule"]["port_range_min"] = port_range_min
        if port_range_max:
            rule_body["security_group_rule"]["port_range_max"] = port_range_max

        url = f"https://vpc.{self.region}.myhuaweicloud.com/v1/{self.project_id}/security-group-rules"
        resp = self._do_request("POST", url, rule_body)

        if resp.status_code in [200, 201]:
            port_str = f"{port_range_min}" if port_range_min == port_range_max else f"{port_range_min}-{port_range_max}"
            source = remote_group_id if remote_group_id else remote_ip_prefix
            print(f"✅ Rule added: {direction} {protocol} {port_str or 'all'} from {source}")
            return True
        else:
            print(f"❌ Rule addition failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return False

    def ensure_security_group(self, sg_name="sg-dsh"):
        existing_sg = self.get_security_group_by_name(sg_name)
        if existing_sg:
            sg_id = existing_sg.get("id")
            print(f"✅ Using existing security group: {sg_name} ({sg_id})")
            return sg_id

        network = self.get_default_network()
        return self.create_security_group(sg_name, network.get("vpc_id"))

    def bind_security_group_to_server(self, server_id, sg_id, sg_name):
        print(f"\n🔗 Binding security group {sg_name} to server...")

        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}/action"
        request_body = {"changeSecurityGroup": {"security_groups": [{"id": sg_id}]}}

        resp = self._do_request("POST", url, request_body)

        if resp.status_code == 202:
            print(f"✅ Security group bound successfully")
            return True
        else:
            print(f"❌ Security group binding failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return False

    def _build_server_body(self, server_name, flavor_id, image_id, volume_size,
                          vpc_id, subnet_id, security_group_id, admin_pass,
                          availability_zone, eip_bandwidth, charging_mode,
                          create_eip=True):
        list_nics_server = [PostPaidServerNic(subnet_id=subnet_id)]

        root_volume_server = PostPaidServerRootVolume(volumetype="SAS", size=volume_size)

        list_security_groups_server = [PostPaidServerSecurityGroup(id=security_group_id)]

        publicip_server = None
        if create_eip:
            bandwidth_eip = PostPaidServerEipBandwidth(
                size=eip_bandwidth,
                sharetype="PER",
                chargemode="traffic"
            )
            eip_publicip = PostPaidServerEip(iptype="5_bgp", bandwidth=bandwidth_eip)
            publicip_server = PostPaidServerPublicip(eip=eip_publicip)

        if charging_mode == "prePaid":
            from huaweicloudsdkecs.v2 import PrePaidServer, PrePaidServerExtendParam
            extendparam_server = PrePaidServerExtendParam(
                charging_mode="prePaid",
                period_type="month",
                period_num=1,
                is_auto_renew="false",
                is_auto_pay="true"
            )
            if create_eip and eip_publicip is not None:
                eip_publicip.extendparam = {"chargingMode": "postPaid", "delete_on_termination": "true"}

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
        else:
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

        if availability_zone:
            server_body.availability_zone = availability_zone

        return server_body

    def _wait_for_job(self, job_id):
        print(f"\n⏳ Waiting for job {job_id}...")

        try:
            from huaweicloudsdkecs.v2 import ShowJobRequest

            client = EcsClient.new_builder() \
                .with_credentials(self.credentials) \
                .with_region(EcsRegion.value_of(self.region)) \
                .build()

            for i in range(60):
                time.sleep(3)
                try:
                    job_request = ShowJobRequest(job_id=job_id)
                    job_response = client.show_job(job_request)
                    job_data = job_response.to_dict()
                    status = job_data.get("status")

                    if status == "SUCCESS":
                        sub_jobs = job_data.get("entities", {}).get("sub_jobs", [])
                        if sub_jobs:
                            server_id = sub_jobs[0].get("entities", {}).get("server_id")
                            if server_id:
                                return [server_id]
                        return job_data.get("entities", {}).get("server_ids", [])
                    elif status == "FAIL":
                        print(f"❌ Job failed: {job_data.get('fail_reason')}")
                        return None
                    else:
                        print(f"  [{i*3}s] Job status: {status}")
                except Exception as e:
                    print(f"  [{i*3}s] Failed to query job: {str(e)[:30]}...")

            print(f"❌ Job timeout")
            return None
        except Exception as e:
            print(f"❌ Job query failed: {e}")
            return None

    def _wait_for_server_public_ip(self, server_id, timeout=180):
        print(f"\n⏳ Waiting for public IP...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            server_url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
            server_resp = self._do_request("GET", server_url)

            if server_resp.status_code == 200:
                server = server_resp.json().get("server", {})
                status = server.get("status")

                addresses = server.get("addresses", {})
                for network_name, addr_list in addresses.items():
                    for addr in addr_list:
                        if addr.get("OS-EXT-IPS:type") == "floating":
                            public_ip = addr.get("addr")
                            print(f"✅ Public IP assigned: {public_ip}")
                            return public_ip, status

                print(f"  [{int(time.time()-start_time)}s] Status: {status}, IP acquiring...")
            elif server_resp.status_code == 404:
                print(f"  [{int(time.time()-start_time)}s] Server still being created...")

            time.sleep(3)

        print(f"⚠️ Public IP not retrieved within {timeout}s")
        return None, None

    def create_server(self, server_name, flavor_id, image_id, volume_size=40,
                      vpc_id=None, subnet_id=None, security_group_id=None,
                      admin_pass=None, availability_zone=None,
                      eip_bandwidth=100, charging_mode="postPaid",
                      create_eip=True):
        admin_pass = admin_pass or DEFAULT_CONFIG["admin_pass"]

        if not vpc_id or not subnet_id:
            network = self.get_default_network()
            vpc_id = vpc_id or network.get("vpc_id")
            subnet_id = subnet_id or network.get("subnet_id")

        if not vpc_id or not subnet_id:
            print("❌ Failed to get network information")
            return None

        if not security_group_id:
            security_group_id = self.ensure_security_group()

        billing_mode_desc = "Monthly" if charging_mode == "prePaid" else "Pay-as-you-go"
        print(f"\n📦 Creating {billing_mode_desc} server")
        print(f"  Server name: {server_name}")
        print(f"  Flavor: {flavor_id}")
        print(f"  System disk: {volume_size}GB")
        print(f"  Billing mode: {billing_mode_desc}")
        if create_eip:
            print(f"  Public IP: Auto-create ({eip_bandwidth}M bandwidth)")
        else:
            print(f"  Public IP: Not created")

        try:
            client = EcsClient.new_builder() \
                .with_credentials(self.credentials) \
                .with_region(EcsRegion.value_of(self.region)) \
                .build()

            request = CreateServersRequest()
            server_body = self._build_server_body(
                server_name, flavor_id, image_id, volume_size,
                vpc_id, subnet_id, security_group_id, admin_pass,
                availability_zone, eip_bandwidth, charging_mode,
                create_eip
            )
            request.body = CreateServersRequestBody(server=server_body)

            print(f"\n⏳ Sending create request...")
            response = client.create_servers(request)
            result = response.to_dict()

            job_id = result.get("job_id")
            server_ids = result.get("serverIds", [])

            print(f"✅ Create request sent")
            print(f"  Job ID: {job_id}")

            if charging_mode == "prePaid":
                order_id = result.get("order_id")
                print(f"  Order ID: {order_id}")

                if not server_ids and order_id:
                    print(f"\n⏳ Waiting for monthly order processing...")
                    for i in range(60):
                        time.sleep(3)
                        job_url = f"https://ecs.{self.region}.myhuaweicloud.com/v1/{self.project_id}/jobs/{job_id}"
                        job_resp = self._do_request("GET", job_url)
                        if job_resp.status_code == 200:
                            job_data = job_resp.json().get("job", {})
                            status = job_data.get("status")
                            if status == "SUCCESS":
                                server_ids = job_data.get("entities", {}).get("server_ids", [])
                                if server_ids:
                                    print(f"✅ Order processed")
                                    break
                            elif status == "FAIL":
                                print(f"❌ Job failed: {job_data.get('fail_reason')}")
                                return None
                            else:
                                print(f"  [{i*3}s] Job status: {status}")

            if not server_ids and job_id:
                server_ids = self._wait_for_job(job_id)

            if not server_ids:
                print(f"❌ Failed to get server ID")
                return None

            server_id = server_ids[0]
            print(f"\n✅ Server created: {server_id}")

            public_ip, status = self._wait_for_server_public_ip(server_id)

            result = {
                "server_id": server_id,
                "public_ip": public_ip,
                "admin_pass": admin_pass
            }

            if charging_mode == "prePaid":
                result["order_id"] = order_id

            return result

        except Exception as e:
            print(f"❌ Server creation failed: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(e, 'response'):
                print(self.format_error_message(e.response, "Server creation"))
            return None

    def create_prepaid_server_with_sdk(self, **kwargs):
        return self.create_server(charging_mode="prePaid", **kwargs)

    def create_postpaid_server_with_sdk(self, **kwargs):
        return self.create_server(charging_mode="postPaid", **kwargs)

    def get_server_detail(self, server_id):
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
        resp = self._do_request("GET", url)

        if resp.status_code == 200:
            server = resp.json().get("server", {})
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
        else:
            print(f"❌ Failed to get server detail: {resp.status_code}")
            return None

    def wait_server_active(self, server_id, timeout=600):
        print(f"\n⏳ Waiting for server to be active...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            detail = self.get_server_detail(server_id)
            if detail:
                status = detail.get("status")
                print(f"  [{int(time.time()-start_time)}s] Server status: {status}")

                if status == "ACTIVE":
                    print(f"✅ Server is now active")
                    return detail

                if status in ["ERROR", "DELETED", "UNKNOWN"]:
                    print(f"❌ Server status error: {status}")
                    return None

            time.sleep(10)

        print(f"❌ Server status check timed out after {timeout}s")
        return None

    def list_servers(self, name_filter=None):
        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/detail"
        resp = self._do_request("GET", url)

        if resp.status_code == 200:
            servers = resp.json().get("servers", [])
            result = []

            for s in servers:
                server_info = {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "status": s.get("status"),
                    "flavor": s.get("flavor", {}).get("id"),
                }

                addresses = s.get("addresses", {})
                for network_name, ips in addresses.items():
                    for ip_info in ips:
                        if ip_info.get("OS-EXT-IPS:type") == "floating":
                            server_info["public_ip"] = ip_info.get("addr")
                        else:
                            server_info["private_ip"] = ip_info.get("addr")

                if name_filter and name_filter not in server_info.get("name", ""):
                    continue

                result.append(server_info)

            return result
        else:
            print(f"❌ Failed to list servers: {resp.status_code}")
            return []

    def delete_server(self, server_id=None, server_name=None, confirm=True):
        if server_name:
            servers = self.list_servers(name_filter=server_name)
            if not servers:
                print(f"❌ Server not found: {server_name}")
                return False
            server_id = servers[0]["id"]
            server_name = servers[0]["name"]

        if not server_id:
            print("❌ Server ID is required")
            return False

        detail = self.get_server_detail(server_id)
        if not detail:
            print(f"❌ Server not found: {server_id}")
            return False

        if confirm:
            print(f"\n⚠️ Confirm deletion of server:")
            print(f"   Name: {detail.get('name')}")
            print(f"   ID: {server_id}")
            print(f"   Public IP: {detail.get('public_ip', 'N/A')}")

            while True:
                choice = input("\nAre you sure you want to delete this server? (yes/no/CONFIRM): ").strip().lower()
                if choice in ['yes', 'y', 'confirm']:
                    break
                elif choice in ['no', 'n']:
                    print("❌ Deletion cancelled")
                    return False
                else:
                    print("❌ Invalid input, please enter 'yes', 'no' or 'CONFIRM'")

        url = f"https://ecs.{self.region}.myhuaweicloud.com/v2.1/{self.project_id}/servers/{server_id}"
        resp = self._do_request("DELETE", url)

        if resp.status_code == 204:
            print(f"✅ Server deletion request submitted")
            return True
        elif resp.status_code == 404:
            print(f"⚠️ Server not found, may have already been deleted")
            return True
        else:
            print(f"❌ Server deletion failed: {resp.status_code}")
            print(f"Response: {resp.text[:300]}")
            return False

    def get_deployment_status(self, server_id):
        detail = self.get_server_detail(server_id)

        if not detail:
            return {
                "server_name": "N/A",
                "server_status": "N/A",
                "public_ip": "N/A",
                "private_ip": "N/A",
                "flavor": "N/A",
                "created": "N/A",
                "services": {}
            }

        services = {}

        public_ip = detail.get("public_ip")

        # dsh listens on 127.0.0.1:3080 (loopback only) and is NOT exposed publicly
        # (security group only allows port 22 for SSH tunnel). Health check must be
        # done via SSH tunnel: ssh -L 3080:127.0.0.1:3080 root@{public_ip}, then
        # open http://127.0.0.1:3080, or run `curl http://127.0.0.1:3080` on the server.
        if public_ip:
            services["dsh"] = {
                "healthy": False,
                "checked": False,
                "http_status": None,
                "note": "Verify via SSH tunnel: ssh -L 3080:127.0.0.1:3080 root@{public_ip}, then open http://127.0.0.1:3080"
            }
        else:
            services["dsh"] = {"checked": False}

        return {
            "server_name": detail.get("name"),
            "server_status": detail.get("status"),
            "public_ip": public_ip,
            "private_ip": detail.get("private_ip"),
            "flavor": detail.get("flavor"),
            "created": "N/A",
            "services": services
        }
