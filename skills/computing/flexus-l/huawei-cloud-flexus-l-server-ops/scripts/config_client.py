#!/usr/bin/env python3
"""
Huawei Cloud Config Service Client
Query all resources using official SDK

⚠️ Security Design: AK/SK only passed via parameters, not saved to any config file
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import Huawei Cloud SDK
try:
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    from huaweicloudsdkcore.exceptions import exceptions
    from huaweicloudsdkcore.http.http_config import HttpConfig
    from huaweicloudsdkconfig.v1.region.config_region import ConfigRegion
    from huaweicloudsdkconfig.v1 import *
    SDK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Huawei Cloud SDK import failed: {e}")
    print("Please install: pip3 install huaweicloudsdkcore huaweicloudsdkconfig")
    SDK_AVAILABLE = False

class HuaweiConfigClient:
    """Huawei Cloud Config Service Client

    ⚠️ Security Design:
    - AK/SK must be passed via constructor parameters
    - Not read from environment variables
    - Not read from config files
    - Not saved to any file
    """

    def __init__(self, ak: str, sk: str, region: str = "cn-north-4"):
        """Initialize client - AK/SK must be passed directly

        Args:
            ak: Access Key ID (required)
            sk: Secret Access Key (required)
            region: Huawei Cloud region (default: cn-north-4)

        Raises:
            ValueError: AK/SK not provided or format incorrect
        """
        if not SDK_AVAILABLE:
            raise ImportError("Huawei Cloud SDK not installed, please install first: pip3 install huaweicloudsdkcore huaweicloudsdkconfig")

        # Validate AK/SK must be passed directly
        if not ak or not sk:
            raise ValueError(
                "❌ AK/SK must be passed via parameters, environment variables or config files not supported.\n"
                "Usage: HuaweiConfigClient(ak='your_AK', sk='your_SK')"
            )

        # Validate AK/SK format
        if len(ak) < 10 or len(sk) < 10:
            raise ValueError("AK/SK format incorrect, please check credentials")

        self.ak = ak
        self.sk = sk
        self.region = region

        # Create client
        self.client = self._create_client()

    def _create_client(self):
        """Create Config client"""
        try:
            credentials = GlobalCredentials(self.ak, self.sk)
            config = HttpConfig.get_default_config()
            config.ignore_ssl_verification = True
            client = ConfigClient.new_builder() \
                .with_http_config(config) \
                .with_credentials(credentials) \
                .with_region(ConfigRegion.value_of(self.region)) \
                .build()
            return client
        except Exception as e:
            raise ValueError(f"Failed to create Huawei Cloud Config client: {e}")

    def list_resources(self, resource_type="hcss.l-instance", region_id=None, limit=20):
        """Query resource list"""
        try:
            region = region_id or self.region

            if resource_type == "hcss.l-instance":
                request = ListAllResourcesRequest()
                request.type = "hcss.l-instance"
                response = self.client.list_all_resources(request)
            elif resource_type is None or resource_type == "all":
                request = ListAllResourcesRequest()
                request.region_id = region
                request.limit = limit
                response = self.client.list_all_resources(request)
            else:
                request = ListResourcesRequest()
                if resource_type:
                    request.resource_type = resource_type
                request.region_id = region
                request.limit = limit
                request.marker = ""
                response = self.client.list_resources(request)

            if response and hasattr(response, 'resources'):
                total_count = len(response.resources)
                if hasattr(response, 'page_info'):
                    page_info = response.page_info
                    if hasattr(page_info, 'total_count'):
                        total_count = page_info.total_count

                return {
                    "success": True,
                    "resources": response.resources,
                    "total": total_count
                }
            else:
                return {"success": False, "error": "API response format incorrect", "resources": []}

        except exceptions.ClientRequestException as e:
            return {"success": False, "error": f"Client request exception: {e.error_msg}", "error_code": e.error_code}
        except Exception as e:
            return {"success": False, "error": f"Query failed: {str(e)}"}

    def list_all_resources(self, resource_type=None, limit=200):
        """Query all resources (supports pagination)"""
        try:
            if resource_type == "hcss.l-instance":
                return self.list_resources(resource_type, self.region, limit)

            all_resources = []
            marker = ""

            while True:
                request = ListAllResourcesRequest()
                request.region_id = self.region
                request.limit = min(limit, 200)
                if marker:
                    request.marker = marker

                response = self.client.list_all_resources(request)

                if not response or not hasattr(response, 'resources'):
                    break

                resources = response.resources
                if not resources:
                    break

                all_resources.extend(resources)

                if hasattr(response, 'page_info') and response.page_info.next_marker:
                    marker = response.page_info.next_marker
                else:
                    break

                if len(all_resources) >= limit:
                    all_resources = all_resources[:limit]
                    break

            if resource_type and resource_type != "all":
                filtered_resources = []
                for resource in all_resources:
                    rtype = getattr(resource, 'type', '')
                    if rtype == resource_type:
                        filtered_resources.append(resource)
                all_resources = filtered_resources

            return {"success": True, "resources": all_resources, "total": len(all_resources)}

        except exceptions.ClientRequestException as e:
            if "RMS.00010025" in str(e):
                if resource_type == "all" or resource_type is None:
                    return self.list_resources(None, self.region, limit)
                else:
                    return self.list_resources(resource_type, self.region, limit)
            return {"success": False, "error": f"Client request exception: {e.error_msg}", "error_code": e.error_code}
        except Exception as e:
            return {"success": False, "error": f"Query failed: {str(e)}"}

    def list_flexus_resources(self, limit=20):
        """Query Flexus L instance resources specifically"""
        try:
            result = self.list_resources(resource_type="hcss.l-instance", limit=limit)

            if result["success"] and result["resources"]:
                return {"success": True, "resources": result["resources"], "query_type": "hcss.l-instance", "total": len(result["resources"])}

            all_result = self.list_all_resources(limit=limit)
            if not all_result["success"]:
                return all_result

            flexus_resources = []
            for resource in all_result["resources"]:
                if self._is_flexus_resource(resource):
                    flexus_resources.append(resource)

            return {"success": True, "resources": flexus_resources[:limit], "query_type": "filtered", "total": len(flexus_resources)}

        except Exception as e:
            return {"success": False, "error": f"Failed to query Flexus L instances: {str(e)}"}

    def search_resources(self, keyword, limit=20):
        """Search resources"""
        try:
            result = self.list_all_resources(limit=limit)
            if not result["success"]:
                return result

            filtered_resources = []
            for resource in result["resources"]:
                resource_name = getattr(resource, 'name', '')
                resource_id = getattr(resource, 'id', '')
                resource_type = getattr(resource, 'type', '')

                if (keyword.lower() in str(resource_name).lower() or 
                    keyword.lower() in str(resource_id).lower() or
                    keyword.lower() in str(resource_type).lower()):
                    filtered_resources.append(resource)

            return {"success": True, "resources": filtered_resources[:limit], "total": len(filtered_resources)}

        except Exception as e:
            return {"success": False, "error": f"Search failed: {str(e)}"}

    def get_resource_summary(self):
        """Get resource summary"""
        try:
            result = self.list_all_resources(limit=200)
            if not result["success"]:
                return result

            resources = result["resources"]
            type_stats = {}
            region_stats = {}
            flexus_resources = []

            for resource in resources:
                rtype = getattr(resource, 'type', 'unknown')
                type_stats[rtype] = type_stats.get(rtype, 0) + 1
                region = getattr(resource, 'region_id', 'unknown')
                region_stats[region] = region_stats.get(region, 0) + 1
                if self._is_flexus_resource(resource):
                    flexus_resources.append(resource)

            summary = {
                "total_resources": len(resources),
                "resource_types": len(type_stats),
                "regions": len(region_stats),
                "flexus_instances": len(flexus_resources),
                "type_stats": type_stats,
                "region_stats": region_stats
            }

            return {"success": True, "summary": summary, "flexus_resources": flexus_resources}

        except Exception as e:
            return {"success": False, "error": f"Failed to get resource summary: {str(e)}"}

    def _is_flexus_resource(self, resource):
        """Determine if resource is a Flexus L instance"""
        if not resource:
            return False

        resource_type = getattr(resource, 'type', '').lower()
        resource_name = getattr(resource, 'name', '').lower()
        provider = getattr(resource, 'provider', '').lower()

        flexus_keywords = ['hcss', 'light', 'flexus', 'lts', 'l-instance']

        for keyword in flexus_keywords:
            if keyword in resource_type or keyword in resource_name or keyword in provider:
                return True
        return False

    def export_resources(self, resource_type=None, output_file="resources.json", format="json"):
        """Export resources"""
        try:
            result = self.list_all_resources(resource_type, limit=1000)
            if not result["success"]:
                return result

            resources = result["resources"]
            export_data = []
            for resource in resources:
                resource_dict = {
                    "id": getattr(resource, 'id', ''),
                    "name": getattr(resource, 'name', ''),
                    "type": getattr(resource, 'type', ''),
                    "region_id": getattr(resource, 'region_id', ''),
                    "status": getattr(resource, 'status', ''),
                    "provider": getattr(resource, 'provider', ''),
                    "created_at": getattr(resource, 'created_at', ''),
                    "updated_at": getattr(resource, 'updated_at', ''),
                    "is_flexus": self._is_flexus_resource(resource)
                }
                export_data.append(resource_dict)

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == "csv":
                import csv
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                    if export_data:
                        writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
                        writer.writeheader()
                        writer.writerows(export_data)
            elif format.lower() == "text":
                with open(output_file, 'w', encoding='utf-8') as f:
                    for i, resource in enumerate(export_data, 1):
                        f.write(f"{i}. {resource['name']} ({resource['type']})\n")
                        f.write(f"   ID: {resource['id']}\n")
                        f.write(f"   Region: {resource['region_id']}\n")
                        f.write(f"   Status: {resource['status']}\n")
                        if resource['is_flexus']:
                            f.write(f"   🔥 Flexus L Instance\n")
                        f.write("\n")
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}

            return {"success": True, "message": f"Successfully exported {len(export_data)} resources to {output_file}", "count": len(export_data), "file": output_file}

        except Exception as e:
            return {"success": False, "error": f"Export failed: {str(e)}"}


def main():
    """Test function"""
    print("=" * 60)
    print("Huawei Cloud Config Service Client")
    print("=" * 60)
    print("\n⚠️  Security Design: AK/SK must be passed via parameters, not saved to any file")
    print("\nUsage Example:")
    print("  from config_client import HuaweiConfigClient")
    print("  client = HuaweiConfigClient(ak='your_AK', sk='your_SK')")
    print("  result = client.list_resources()")
    print("\nCommand Line Usage:")
    print("  python3 config_cli.py list --ak your_AK --sk your_SK")
    print("=" * 60)


if __name__ == "__main__":
    main()
