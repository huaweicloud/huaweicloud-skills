#!/usr/bin/env python3
# coding: utf-8
"""
Huawei Cloud COC Script Management Library

Manages COC scripts using Huawei Cloud SDK, supporting script creation and execution.
AK/SK/Security Token are passed as parameters: ak, sk, security_token, region
"""

import logging
from typing import Any, Optional, List, Dict

from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkcoc.v1 import *
from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel

logger = logging.getLogger(__name__)

# Constants
VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]


def get_valid_coc_regions() -> list[str]:
    """
    Dynamically get the list of regions supported by COC service from SDK.
    
    Returns:
        List of valid COC service regions
    """
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    return list(CocRegion.static_fields.keys())


def get_client(ak: str, sk: str, security_token: str, region: str = "cn-north-4") -> CocClient:
    """
    Create and return a COC client.

    Args:
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication (optional)
        region: COC service region, default cn-north-4

    Returns:
        CocClient instance

    Raises:
        ValueError: If AK/SK not provided or region is invalid
    """
    if not ak:
        raise ValueError("ak is required")
    if not sk:
        raise ValueError("sk is required")
    
    valid_regions = get_valid_coc_regions()
    if region not in valid_regions:
        raise ValueError(f"region must be one of {valid_regions}")

    # Determine authentication method based on security_token presence
    if security_token:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    else:
        credentials = GlobalCredentials(ak, sk)

    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(region)) \
        .build()

    return client


def create_script(
    name: str,
    script_type: str,
    content: str,
    description: str,
    ak: str,
    sk: str,
    security_token: str,
    region: str = "cn-north-4",
    risk_level: str = "LOW",
    version: str = "1.0.0",
    script_params: Optional[List[Dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Create a custom script in COC.

    Args:
        name: Script name
        script_type: Script type (SHELL/PYTHON/BAT)
        content: Script content
        description: Script description
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication
        region: COC service region, default cn-north-4
        risk_level: Risk level (LOW/MEDIUM/HIGH), default LOW
        version: Script version, default 1.0.0
        script_params: Script parameters list

    Returns:
        {
            "ok": True,
            "text": "Script created successfully: SC2023102521413701c4a8a62",
            "result": { Raw API response },
            "error": None
        }
    """
    # Validate input
    if not name:
        return _error("INPUT_ERROR", "name is required")
    if script_type not in VALID_SCRIPT_TYPES:
        return _error("INPUT_ERROR", f"script_type must be one of {VALID_SCRIPT_TYPES}")
    if not content:
        return _error("INPUT_ERROR", "content is required")
    if not description:
        return _error("INPUT_ERROR", "description is required")
    if risk_level not in VALID_RISK_LEVELS:
        return _error("INPUT_ERROR", f"risk_level must be one of {VALID_RISK_LEVELS}")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = CreateScriptRequest()
        properties = ScriptPropertiesModel(
            risk_level=risk_level,
            version=version
        )
        request.body = AddScriptModel(
            name=name,
            type=script_type,
            content=content,
            description=description,
            properties=properties
        )

        response = client.create_script(request)
        script_uuid = response.data if hasattr(response, 'data') else str(response)

        return {
            "ok": True,
            "text": f"Script created successfully: {script_uuid}",
            "result": response,
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def execute_script(
    script_uuid: str,
    execute_user: str,
    timeout: int,
    success_rate: float,
    target_instances: List[Dict[str, str]],
    ak: str,
    sk: str,
    security_token: str,
    region: str = "cn-north-4",
    rotation_strategy: str = "CONTINUE",
) -> dict[str, Any]:
    """
    Execute a custom script on target instances.

    Args:
        script_uuid: UUID of the script to execute
        execute_user: User to execute the script (e.g., root)
        timeout: Execution timeout in seconds (5 < timeout < 1800)
        success_rate: Success rate (supports one decimal place, e.g., 1 or 100)
        target_instances: List of target instances, each containing:
            - resource_id: Instance ID (required)
            - region_id: Region where server is located (required)
            - provider: Resource provider (not required for ECS instances, default "HCSS" for L instances)
            - type: Resource type (not required for ECS instances, default "L-INSTANCE" for L instances)
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication
        region: COC service region, default cn-north-4
        rotation_strategy: Rotation strategy (CONTINUE/PAUSE), default CONTINUE

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": { Raw API response },
            "error": None
        }
    """
    # Validate input
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid is required")
    if not execute_user:
        return _error("INPUT_ERROR", "execute_user is required")
    if timeout <= 5 or timeout >= 1800:
        return _error("INPUT_ERROR", "timeout must be between 5 and 1800 seconds")
    if success_rate < 0 or success_rate > 100:
        return _error("INPUT_ERROR", "success_rate must be between 0 and 100")
    if not target_instances or not isinstance(target_instances, list):
        return _error("INPUT_ERROR", "target_instances is required")
    if rotation_strategy not in VALID_ROTATION_STRATEGIES:
        return _error("INPUT_ERROR", f"rotation_strategy must be one of {VALID_ROTATION_STRATEGIES}")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = ExecuteScriptRequest()
        request.script_uuid = script_uuid

        # Build execution parameters
        execute_param = ScriptExecuteParam(
            timeout=timeout,
            success_rate=success_rate,
            execute_user=execute_user
        )

        # Build target instance list
        listTargetInstancesExecuteBatches = []
        for instance_info in target_instances:
            # Build instance object, add provider/type fields if available
            instance_kwargs = {
                "resource_id": instance_info.get("resource_id", ""),
                "region_id": instance_info.get("region_id", "cn-north-4")
            }
            
            # Add provider and type fields for L instances
            provider = instance_info.get("provider")
            instance_type = instance_info.get("type")
            if provider:
                instance_kwargs["provider"] = provider
            if instance_type:
                instance_kwargs["type"] = instance_type
            
            instance = ExecuteResourceInstance(**instance_kwargs)
            listTargetInstancesExecuteBatches.append(instance)

        # Build batch
        listExecuteBatchesbody = [
            ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=listTargetInstancesExecuteBatches,
                rotation_strategy=rotation_strategy
            )
        ]

        # Build request body
        request.body = ScriptExecuteModel(
            execute_batches=listExecuteBatchesbody,
            execute_param=execute_param
        )

        response = client.execute_script(request)
        execute_uuid = response.data if hasattr(response, 'data') else str(response)

        return {
            "ok": True,
            "text": f"Script execution started: {execute_uuid}",
            "result": response,
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def get_script_detail(script_uuid: str, ak: str, sk: str, security_token: str, region: str = "cn-north-4") -> dict[str, Any]:
    """
    Get script details.

    Args:
        script_uuid: Script UUID
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication
        region: COC service region, default cn-north-4

    Returns:
        {
            "ok": True,
            "text": "Script details retrieved",
            "result": { 
                "script_uuid": "xxx",
                "name": "Script name",
                "type": "SHELL",
                "content": "Script content",
                "description": "Description",
                "risk_level": "LOW",
                "version": "1.0.0",
                "create_time": "Creation time"
            },
            "error": None
        }
    """
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid is required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = GetScriptRequest()
        request.script_uuid = script_uuid
        
        response = client.get_script(request)
        
        # Parse response
        script_data = {}
        if hasattr(response, 'data'):
            data = response.data
            script_data = {
                "script_uuid": data.script_uuid if hasattr(data, 'script_uuid') else "",
                "name": data.name if hasattr(data, 'name') else "",
                "type": data.type if hasattr(data, 'type') else "",
                "content": data.content if hasattr(data, 'content') else "",
                "description": data.description if hasattr(data, 'description') else "",
                "risk_level": data.risk_level if hasattr(data, 'risk_level') else "",
                "version": data.version if hasattr(data, 'version') else "",
                "create_time": data.create_time if hasattr(data, 'create_time') else ""
            }

        return {
            "ok": True,
            "text": "Script details retrieved",
            "result": script_data,
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def list_scripts(ak: str, sk: str, security_token: str, region: str = "cn-north-4", page: int = 1, limit: int = 10) -> dict[str, Any]:
    """
    List scripts.

    Args:
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication
        region: COC service region, default cn-north-4
        page: Page number (starting from 1)
        limit: Page size

    Returns:
        {
            "ok": True,
            "text": "Scripts listed",
            "result": {
                "scripts": [...],
                "total": 100
            },
            "error": None
        }
    """
    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = ListScriptsRequest()
        request.page = page
        request.limit = limit
        
        response = client.list_scripts(request)
        
        scripts = []
        total = 0
        if hasattr(response, 'data'):
            data = response.data
            if hasattr(data, 'data'):
                for script in data.data:
                    # Extract risk level and version from properties
                    risk_level = ""
                    version = ""
                    if hasattr(script, 'properties') and script.properties:
                        props = script.properties
                        risk_level = props.risk_level if hasattr(props, 'risk_level') else ""
                        version = props.version if hasattr(props, 'version') else ""
                    
                    scripts.append({
                        "script_uuid": script.script_uuid if hasattr(script, 'script_uuid') else "",
                        "name": script.name if hasattr(script, 'name') else "",
                        "type": script.type if hasattr(script, 'type') else "",
                        "description": script.description if hasattr(script, 'description') else "",
                        "risk_level": risk_level,
                        "version": version,
                        "create_time": script.gmt_created if hasattr(script, 'gmt_created') else ""
                    })
            if hasattr(data, 'total'):
                total = data.total

        return {
            "ok": True,
            "text": f"Found {total} scripts",
            "result": {
                "scripts": scripts,
                "total": total
            },
            "error": None,
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def get_script_job_batch(
    execute_uuid: str,
    ak: str,
    sk: str,
    security_token: str
) -> dict[str, Any]:
    """
    Query script execution result by execute UUID.
    
    API: GET /v1/job/script/orders/{execute_uuid}/batches/1
    
    Args:
        execute_uuid: Execution UUID (format: SCTxxxxxxxxxxxxxxxbf)
        ak: Huawei Cloud Access Key
        sk: Huawei Cloud Secret Key
        security_token: Temporary security token for STS authentication

    Returns:
        {
            "data": {
                "batch_index": 1,
                "total_instances": 1,
                "execute_instances": [{
                    "id": 40304358,
                    "cmd_uuid": "xxx",
                    "job_sign": null,
                    "status": "FINISHED",  # or "ABNORMAL", "RUNNING", etc.
                    "message": "Execution log...",
                    "gmt_created": 1779934038727,
                    "gmt_finished": 1779934107670,
                    "execute_costs": 68943,
                    "target_instance": {
                        "resource_id": "xxx",
                        "agent_sn": "xxx",
                        "agent_status": null,
                        "agent_version": "1.1.8",
                        "region_id": "cn-north-4",
                        "project_id": null,
                        "properties": {
                            "host_name": "dify-test-001",
                            "fixed_ip": null,
                            "floating_ip": null,
                            "region_id": "cn-north-4",
                            "zone_id": null,
                            "application": null,
                            "group": null,
                            "project_id": null
                        },
                        "custom_attributes": null,
                        "provider": "hcss",
                        "type": "l-instance"
                    }
                }]
            }
        }
    """
    if not execute_uuid:
        return _error("INPUT_ERROR", "execute_uuid is required")

    # Fixed parameters
    region = "cn-north-4"
    batch_index = 1
    limit = 50

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        request = GetScriptJobBatchRequest()
        request.batch_index = batch_index
        request.execute_uuid = execute_uuid
        request.limit = limit
        
        response = client.get_script_job_batch(request)
        
        result_dict = {}
        if hasattr(response, 'data') and response.data is not None:
            data = response.data
            if hasattr(data, 'batch_index'):
                result_dict['batch_index'] = data.batch_index
            if hasattr(data, 'total_instances'):
                result_dict['total_instances'] = data.total_instances
            if hasattr(data, 'execute_instances') and data.execute_instances:
                instances = []
                for instance in data.execute_instances:
                    instance_dict = {}
                    if hasattr(instance, 'id'):
                        instance_dict['id'] = instance.id
                    if hasattr(instance, 'cmd_uuid'):
                        instance_dict['cmd_uuid'] = instance.cmd_uuid
                    if hasattr(instance, 'status'):
                        instance_dict['status'] = instance.status
                    if hasattr(instance, 'message'):
                        instance_dict['message'] = instance.message
                    if hasattr(instance, 'execute_costs'):
                        instance_dict['execute_costs'] = instance.execute_costs
                    if hasattr(instance, 'gmt_created'):
                        instance_dict['gmt_created'] = instance.gmt_created
                    if hasattr(instance, 'gmt_finished'):
                        instance_dict['gmt_finished'] = instance.gmt_finished
                    if hasattr(instance, 'target_instance') and instance.target_instance:
                        target = instance.target_instance
                        target_dict = {}
                        if hasattr(target, 'resource_id'):
                            target_dict['resource_id'] = target.resource_id
                        if hasattr(target, 'agent_sn'):
                            target_dict['agent_sn'] = target.agent_sn
                        if hasattr(target, 'agent_status'):
                            target_dict['agent_status'] = target.agent_status
                        if hasattr(target, 'agent_version'):
                            target_dict['agent_version'] = target.agent_version
                        if hasattr(target, 'region_id'):
                            target_dict['region_id'] = target.region_id
                        if hasattr(target, 'project_id'):
                            target_dict['project_id'] = target.project_id
                        if hasattr(target, 'properties') and target.properties:
                            props = target.properties
                            props_dict = {}
                            if hasattr(props, 'host_name'):
                                props_dict['host_name'] = props.host_name
                            if hasattr(props, 'fixed_ip'):
                                props_dict['fixed_ip'] = props.fixed_ip
                            if hasattr(props, 'floating_ip'):
                                props_dict['floating_ip'] = props.floating_ip
                            if hasattr(props, 'region_id'):
                                props_dict['region_id'] = props.region_id
                            if hasattr(props, 'zone_id'):
                                props_dict['zone_id'] = props.zone_id
                            if hasattr(props, 'application'):
                                props_dict['application'] = props.application
                            if hasattr(props, 'group'):
                                props_dict['group'] = props.group
                            if hasattr(props, 'project_id'):
                                props_dict['project_id'] = props.project_id
                            target_dict['properties'] = props_dict
                        if hasattr(target, 'custom_attributes'):
                            target_dict['custom_attributes'] = target.custom_attributes
                        if hasattr(target, 'provider'):
                            target_dict['provider'] = target.provider
                        if hasattr(target, 'type'):
                            target_dict['type'] = target.type
                        instance_dict['target_instance'] = target_dict
                    if hasattr(instance, 'job_sign'):
                        instance_dict['job_sign'] = instance.job_sign
                    instances.append(instance_dict)
                result_dict['execute_instances'] = instances
        else:
            result_dict['status'] = 'UNKNOWN'
            result_dict['message'] = 'Execution record not found or empty'

        return {
            "data": result_dict
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def _error(code: str, message: str) -> dict:
    """Create error response."""
    return {
        "ok": False,
        "text": "",
        "result": None,
        "error": {"code": code, "message": message},
    }