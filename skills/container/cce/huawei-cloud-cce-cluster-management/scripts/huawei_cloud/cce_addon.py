"""CCE Addon management functions."""

from typing import Any, Dict, Optional

from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
from huaweicloudsdkcce.v3 import (
    ShowAddonInstanceRequest,
    ListAddonInstancesRequest,
    CreateAddonInstanceRequest,
    AddonInstance,
    InstanceSpec,
    AddonMetadata,
    UpdateAddonInstanceRequest,
    DeleteAddonInstanceRequest,
)

from .common import get_credentials, create_cce_client, SDK_AVAILABLE, IMPORT_ERROR


def get_cce_addon_detail(region: str, cluster_id: str, addon_name: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information of a specific CCE addon."""
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ShowAddonInstanceRequest()
        request.cluster_id = cluster_id
        request.addon_name = addon_name

        response = client.show_addon(request)

        addon_info = {}
        if hasattr(response, 'spec') and response.spec:
            spec = response.spec
            addon_info["name"] = getattr(spec, 'name', None)
            addon_info["version"] = getattr(spec, 'version', None)
            addon_info["status"] = getattr(spec, 'status', None)
            addon_info["description"] = getattr(spec, 'description', None)

            if hasattr(spec, 'custom') and spec.custom:
                custom = spec.custom
                addon_info["custom_params"] = {}

                if hasattr(custom, 'aom_id'):
                    addon_info["custom_params"]["aom_id"] = custom.aom_id
                if hasattr(custom, 'aom_instance_id'):
                    addon_info["custom_params"]["aom_instance_id"] = custom.aom_instance_id
                if hasattr(custom, 'prom_instance_id'):
                    addon_info["custom_params"]["prom_instance_id"] = custom.prom_instance_id
                if hasattr(custom, 'remote_write_url'):
                    addon_info["custom_params"]["remote_write_url"] = custom.remote_write_url
                if hasattr(custom, 'remote_read_url'):
                    addon_info["custom_params"]["remote_read_url"] = custom.remote_read_url

                if isinstance(custom, dict):
                    addon_info["custom_params"] = custom
                    if 'aom_id' in custom:
                        addon_info["aom_id"] = custom['aom_id']
                    if 'aom_instance_id' in custom:
                        addon_info["aom_instance_id"] = custom['aom_instance_id']
                    if 'prom_instance_id' in custom:
                        addon_info["aom_instance_id"] = custom['prom_instance_id']

        if hasattr(response, 'metadata') and response.metadata:
            metadata = response.metadata
            addon_info["uid"] = getattr(metadata, 'uid', None)
            addon_info["creation_timestamp"] = str(getattr(metadata, 'creation_timestamp', None))

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "get_cce_addon_detail",
            "addon": addon_info
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def list_cce_addons(region: str, cluster_id: str, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """List addons (plugins) in a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with addon list
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = ListAddonInstancesRequest()
        request.cluster_id = cluster_id

        response = client.list_addon_instances(request)

        addons = []
        if hasattr(response, 'items') and response.items:
            for addon in response.items:
                addon_info = {
                    "name": addon.metadata.name if hasattr(addon, 'metadata') and hasattr(addon.metadata, 'name') else None,
                    "uid": addon.metadata.uid if hasattr(addon, 'metadata') and hasattr(addon.metadata, 'uid') else None,
                    "template_name": addon.spec.template_name if hasattr(addon, 'spec') and hasattr(addon.spec, 'template_name') else None,
                    "version": addon.spec.version if hasattr(addon, 'spec') and hasattr(addon.spec, 'version') else None,
                    "status": addon.status.status if hasattr(addon, 'status') and hasattr(addon.status, 'status') else None,
                    "description": addon.spec.description if hasattr(addon, 'spec') and hasattr(addon.spec, 'description') else None,
                    "created_at": str(addon.metadata.creation_timestamp) if hasattr(addon, 'metadata') and hasattr(addon.metadata, 'creation_timestamp') else None,
                }
                addons.append(addon_info)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "list_cce_addons",
            "count": len(addons),
            "addons": addons
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def install_cce_addon(
    region: str,
    cluster_id: str,
    addon_template_name: str,
    addon_version: str,
    values: Dict[str, Any],
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """Install an addon to a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        addon_template_name: Addon template name (e.g., "coredns", "metrics-server")
        addon_version: Addon version to install
        values: Addon-specific configuration values
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with installation result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not addon_template_name:
        return {
            "success": False,
            "error": "addon_template_name is required"
        }

    if not addon_version:
        return {
            "success": False,
            "error": "addon_version is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        metadata = AddonMetadata(
            annotations={"addon.install/type": "install"}
        )

        spec = InstanceSpec(
            cluster_id=cluster_id,
            version=addon_version,
            template_name=addon_template_name,
            values=values
        )

        body = AddonInstance(
            kind="Addon",
            api_version="v3",
            metadata=metadata,
            spec=spec
        )

        request = CreateAddonInstanceRequest()
        request.body = body

        response = client.create_addon_instance(request)

        addon_info = {}
        if hasattr(response, 'metadata') and response.metadata:
            addon_info["uid"] = getattr(response.metadata, 'uid', None)
            addon_info["name"] = getattr(response.metadata, 'name', None)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "install_cce_addon",
            "addon_template_name": addon_template_name,
            "addon_version": addon_version,
            "addon": addon_info
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def uninstall_cce_addon(
    region: str,
    cluster_id: str,
    addon_id: str,
    confirm: bool,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """Uninstall an addon from a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        addon_id: Addon ID (name or UID)
        confirm: Must be True to proceed with uninstallation
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with uninstallation result
    """
    if not confirm:
        return {
            "success": False,
            "error": "Uninstallation requires explicit confirmation. Set confirm=True to proceed."
        }

    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not addon_id:
        return {
            "success": False,
            "error": "addon_id is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        request = DeleteAddonInstanceRequest()
        request.cluster_id = cluster_id
        request.addon_name = addon_id

        client.delete_addon_instance(request)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "uninstall_cce_addon",
            "addon_id": addon_id,
            "message": f"Addon {addon_id} uninstallation initiated"
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def update_cce_addon(
    region: str,
    cluster_id: str,
    addon_id: str,
    addon_version: str,
    values: Dict[str, Any],
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """Update an addon in a CCE cluster

    Args:
        region: Huawei Cloud region (e.g., cn-north-4)
        cluster_id: CCE cluster ID
        addon_id: Addon ID (name or UID)
        addon_version: New addon version
        values: Addon-specific configuration values
        ak: Access Key ID (optional)
        sk: Secret Access Key (optional)
        project_id: Project ID (optional)

    Returns:
        Dictionary with update result
    """
    access_key, secret_key, proj_id = get_credentials(ak, sk, project_id)

    if not access_key or not secret_key:
        return {
            "success": False,
            "error": "Credentials not provided. Set HUAWEI_AK and HUAWEI_SK environment variables or pass as parameters."
        }

    if not cluster_id:
        return {
            "success": False,
            "error": "cluster_id is required"
        }

    if not addon_id:
        return {
            "success": False,
            "error": "addon_id is required"
        }

    if not addon_version:
        return {
            "success": False,
            "error": "addon_version is required"
        }

    if not SDK_AVAILABLE:
        return {
            "success": False,
            "error": f"Huawei Cloud SDK not installed: {IMPORT_ERROR}"
        }

    try:
        client = create_cce_client(region, access_key, secret_key, proj_id)

        metadata = AddonMetadata(
            annotations={"addon.upgrade/type": "upgrade"}
        )

        spec = InstanceSpec(
            cluster_id=cluster_id,
            version=addon_version,
            values=values
        )

        body = AddonInstance(
            kind="Addon",
            api_version="v3",
            metadata=metadata,
            spec=spec
        )

        request = UpdateAddonInstanceRequest()
        request.addon_name = addon_id
        request.body = body

        response = client.update_addon_instance(request)

        addon_info = {}
        if hasattr(response, 'metadata') and response.metadata:
            addon_info["uid"] = getattr(response.metadata, 'uid', None)
            addon_info["name"] = getattr(response.metadata, 'name', None)

        return {
            "success": True,
            "region": region,
            "cluster_id": cluster_id,
            "action": "update_cce_addon",
            "addon_id": addon_id,
            "addon_version": addon_version,
            "addon": addon_info
        }

    except ClientRequestException as e:
        return {
            "success": False,
            "error": f"{e.error_code} - {e.error_msg}",
            "request_id": getattr(e, 'request_id', None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }