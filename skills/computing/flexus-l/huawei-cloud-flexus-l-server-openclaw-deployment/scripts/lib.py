#!/usr/bin/env python3
# Copyright (c) Huawei Technologies CO., LTD. 2022-2025. All rights reserved.
# coding=utf-8
"""
Huawei Cloud Flexus L Instance One-Click OpenClaw Deployment Core Module
Contains:
1. L instance creation functionality
2. COC script management functionality (create script, execute script)
3. Model installation functionality
4. Channel installation functionality
"""

import json
import os
import requests
import uuid
from datetime import datetime
from urllib.parse import urlparse
from typing import Any, Optional, List, Dict


class Credentials:
    def __init__(self, ak, sk, security_token=None):
        self.ak = ak
        self.sk = sk
        self.security_token = security_token


def get_project_id_by_region(region: str, ak: str, sk: str, security_token: str = None) -> Optional[str]:
    """
    Get Project ID for specified region via AK/SK
    
    Args:
        region: Target region, e.g. cn-north-4, cn-southwest-2
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
    
    Returns:
        Project ID string, or None if failed
    """
    if not ak or not sk:
        print("Error: Credentials not configured")
        return None
    
    iam_endpoint = f"https://iam.{region}.myhuaweicloud.com/v3/projects"
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = "https"
        request.host = f"iam.{region}.myhuaweicloud.com"
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
        
        print(f"Getting Project ID - Request URL: {iam_endpoint}")
        
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
            else:
                print("Error: Project not found")
                return None
        else:
            print(f"Failed to get Project ID - Status code: {resp.status_code}, Response: {resp.text}")
            return None
            
    except ImportError as e:
        print(f"SDK import failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Error getting Project ID: {str(e)}")
        return None


def get_coc_client(ak: str, sk: str, security_token: str = None):
    """
    Create and return COC client
    
    Args:
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)
    
    Returns:
        CocClient instance
    """
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    from huaweicloudsdkcoc.v1 import CocClient
    
    if not ak or not sk:
        raise ValueError("COC credentials not configured, please provide AK and SK parameters")
    
    region = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")
    
    if security_token is None:
        credentials = GlobalCredentials(ak, sk)
    else:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(region)) \
        .build()
    
    return client


def create_openclaw_instance(instance_name = None, region = None, ak = None, sk = None, security_token = None):
    """
    Create Huawei Cloud Flexus L instance (dedicated for OpenClaw)
    
    API Reference: https://support.huaweicloud.com/api-flexusl/create_instance_0001.html
    
    Args:
        instance_name: Instance name, optional, auto-generated as openclaw-timestamp if not specified
        region: Target region, optional, defaults to cn-north-4 if not specified
        ak: Huawei Cloud AK (can be temporary AK), required
        sk: Huawei Cloud SK (can be temporary SK), required
        security_token: Security token for temporary credentials (optional)
    
    Returns:
        dict: Result dictionary containing ok, text, result, error fields
    """
    if not ak or not sk:
        return {
            "ok": False,
            "text": "Authentication credentials not configured",
            "result": None,
            "error": {
                "code": "CONFIG_ERROR",
                "message": "Please provide AK and SK parameters"
            }
        }
    
    target_region = region if region else "cn-north-4"
    
    project_id = get_project_id_by_region(target_region, ak, sk, security_token)
    if not project_id:
        return {
            "ok": False,
            "text": "Failed to get Project ID",
            "result": None,
            "error": {
                "code": "PROJECT_ID_ERROR",
                "message": f"Cannot get Project ID for region {target_region}, please verify credentials"
            }
        }
    
    if not instance_name:
        instance_name = f"openclaw-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    endpoint = "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances"
    
    if target_region == "cn-southwest-2":
        plan_spec = "ahf.small.1.linux"
    else:
        plan_spec = "hf.small.1.linux"
    
    request_body = {
        "instance_name": instance_name,
        "plan_spec": plan_spec,
        "image_ref": {
            "image_name": "OpenClaw",
            "image_version": "2026.1.30"
        },
        "region": target_region,
        "charging_mode": "prePaid",
        "period_type": "month",
        "period_num": 1,
        "purchase_quantity": 1,
        "description": "OpenClaw one-click deployment",
        "is_auto_renew": True,
        "is_auto_pay": True,
        "extra_resources": [
            {"type": "evs", "size": 50},
            {"type": "cbr", "size": 50},
            {"type": "hss"}
        ]
    }
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        parsed_url = urlparse(endpoint)
        body_str = json.dumps(request_body, ensure_ascii=False, separators=(',', ':'))
        
        request = SdkRequest()
        request.method = "POST"
        request.schema = parsed_url.scheme
        request.host = parsed_url.hostname
        request.resource_path = parsed_url.path
        request.body = body_str
        request.header_params = {
            "X-Project-Id": project_id,
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
        
        print(f"Authorization info: {headers.get('Authorization')}")
        print(f"Request headers: {headers}")
        print(f"Request body: {body_str}")
        
        resp = requests.request(
            "POST",
            endpoint,
            headers=headers,
            data=body_str.encode('utf-8'),
            verify=True
        )
        
        print(f"Status code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code in [200, 201, 202]:
            response_data = resp.json()
            return {
                "ok": True,
                "text": f"Instance creation request submitted, instance ID: {response_data.get('instance_id', 'Unknown')}",
                "result": response_data,
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": f"Instance creation failed: {resp.reason}",
                "result": None,
                "error": {
                    "code": str(resp.status_code),
                    "message": resp.text
                }
            }
    
    except ImportError as e:
        return {
            "ok": False,
            "text": "SDK import failed",
            "result": None,
            "error": {
                "code": "SDK_ERROR",
                "message": f"Please install huaweicloudsdkcore: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error creating instance: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]


def _error(code: str, message: str) -> dict:
    """
    Create error response
    
    Args:
        code: Error code
        message: Error message
    
    Returns:
        dict: Standard error response dictionary
    """
    return {
        "ok": False,
        "text": "",
        "result": None,
        "error": {"code": code, "message": message},
    }


def coc_create_script(
    name: str,
    script_type: str,
    content: str,
    description: str,
    risk_level: str = "LOW",
    version: str = "1.0.0",
    ak: str = None,
    sk: str = None,
    security_token: str = None
) -> dict[str, Any]:
    """
    Create custom script in COC

    Args:
        name: Script name
        script_type: Script type (SHELL/PYTHON/BAT)
        content: Script content
        description: Script description
        risk_level: Risk level (LOW/MEDIUM/HIGH), default LOW
        version: Script version, default 1.0.0
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script created successfully: SC2023102521413701c4a8a62",
            "result": { original API result },
            "error": None
        }
    """
    if not name:
        return _error("INPUT_ERROR", "name parameter is required")
    if script_type not in VALID_SCRIPT_TYPES:
        return _error("INPUT_ERROR", f"script_type must be one of {VALID_SCRIPT_TYPES}")
    if not content:
        return _error("INPUT_ERROR", "content parameter is required")
    if not description:
        return _error("INPUT_ERROR", "description parameter is required")
    if risk_level not in VALID_RISK_LEVELS:
        return _error("INPUT_ERROR", f"risk_level must be one of {VALID_RISK_LEVELS}")

    try:
        client = get_coc_client(ak, sk,security_token)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import CreateScriptRequest
        from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
        from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
        
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
            "result": {"script_uuid": script_uuid},
            "error": None,
        }

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)


def coc_execute_script(
    script_uuid: str,
    execute_user: str,
    timeout: int,
    success_rate: float,
    target_instances: List[Dict[str, str]],
    rotation_strategy: str = "CONTINUE",
    wait_for_complete: bool = True,
    ak: str = None,
    sk: str = None,
    security_token: str = None

) -> dict[str, Any]:
    """
    Execute custom script on target instances

    Args:
        script_uuid: Script UUID to execute
        execute_user: User to execute script (e.g., root)
        timeout: Execution timeout (seconds, 5 < timeout < 1800)
        success_rate: Success rate (supports one decimal, e.g., 1 or 100)
        target_instances: Target instance list, each instance contains:
            - resource_id: Instance ID (required)
            - region_id: Server region (required)
            - provider: Resource provider (not needed for ECS, defaults to "HCSS" for L instances)
            - type: Resource type (not needed for ECS, defaults to "L-INSTANCE" for L instances)
        rotation_strategy: Rotation strategy (CONTINUE/STOP), default CONTINUE
        wait_for_complete: Whether to wait for execution completion and get logs, default True
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": { 
                "execute_uuid": "SCT2023083109562601af694bf",
                "status": "SUCCESS",
                "output": "Script execution output log...",
                "error": "Error message (if any)"
            },
            "error": None
        }
    """
    if not script_uuid:
        return _error("INPUT_ERROR", "script_uuid parameter is required")
    if not execute_user:
        return _error("INPUT_ERROR", "execute_user parameter is required")
    if timeout <= 5 or timeout >= 1800:
        return _error("INPUT_ERROR", "timeout must be between 5 and 1800 seconds")
    if success_rate < 0 or success_rate > 100:
        return _error("INPUT_ERROR", "success_rate must be between 0 and 100")
    if not target_instances or not isinstance(target_instances, list):
        return _error("INPUT_ERROR", "target_instances parameter is required")
    if rotation_strategy not in VALID_ROTATION_STRATEGIES:
        return _error("INPUT_ERROR", f"rotation_strategy must be one of {VALID_ROTATION_STRATEGIES}")

    try:
        client = get_coc_client(ak, sk, security_token)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        import time
        from huaweicloudsdkcoc.v1 import ExecuteScriptRequest
        from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
        from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
        from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
        from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
        
        request = ExecuteScriptRequest()
        request.script_uuid = script_uuid

        execute_param = ScriptExecuteParam(
            timeout=timeout,
            success_rate=success_rate,
            execute_user=execute_user
        )

        listTargetInstancesExecuteBatches = []
        for instance_info in target_instances:
            instance_kwargs = {
                "resource_id": instance_info.get("resource_id", ""),
                "region_id": instance_info.get("region_id", "cn-north-4")
            }
            
            provider = instance_info.get("provider")
            instance_type = instance_info.get("type")
            if provider:
                instance_kwargs["provider"] = provider
            if instance_type:
                instance_kwargs["type"] = instance_type
            
            instance = ExecuteResourceInstance(**instance_kwargs)
            listTargetInstancesExecuteBatches.append(instance)

        listExecuteBatchesbody = [
            ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=listTargetInstancesExecuteBatches,
                rotation_strategy=rotation_strategy
            )
        ]

        request.body = ScriptExecuteModel(
            execute_batches=listExecuteBatchesbody,
            execute_param=execute_param
        )

        response = client.execute_script(request)
        execute_uuid = response.data if hasattr(response, 'data') else str(response)

        if not wait_for_complete:
            return {
                "ok": True,
                "text": f"Script execution started: {execute_uuid}",
                "result": {"execute_uuid": execute_uuid},
                "error": None,
            }

        max_wait_time = timeout + 60
        wait_interval = 5
        elapsed_time = 0
        status = ""
        
        while elapsed_time < max_wait_time:
            query_result = coc_query_execution(execute_uuid, ak, sk, security_token)
            
            data = query_result.get("data", {})
            if not data:
                # Query failed, log and continue
                error_msg = query_result.get("error", {}).get("message", "Unknown error") if isinstance(query_result, dict) else "Query failed"
                print(f"Failed to query execution status: {error_msg}")
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue
            
            # Extract status and output from new format
            instances = data.get("execute_instances", [])
            if instances:
                status = instances[0].get("status", "")
                output = instances[0].get("message", "")
                error = output if status == "ABNORMAL" else ""
            else:
                status = data.get("status", "")
                output = data.get("message", "")
                error = output if status == "ABNORMAL" else ""
            
            # If status is UNKNOWN and waited for some time (e.g., 30 seconds), return error
            if status == "UNKNOWN" and elapsed_time > 60:
                return {
                    "ok": False,
                    "text": f"Script execution status unknown, possibly execution ID does not exist or API not responding",
                    "result": {"execute_uuid": execute_uuid, "status": status},
                    "error": {"code": "UNKNOWN_STATUS", "message": "Execution status unknown, possibly execution ID does not exist or API not responding"}
                }
            
            if status in ["SUCCESS", "FAILED", "TIMEOUT", "CANCELLED", "FINISHED", "ABNORMAL"]:
                        result_data = {
                            "execute_uuid": execute_uuid,
                            "status": status,
                            "output": output,
                            "error": error
                        }
                        
                        if status in ["SUCCESS", "FINISHED"]:
                            return {
                                "ok": True,
                                "text": f"Script executed successfully: {execute_uuid}",
                                "result": result_data,
                                "error": None,
                            }
                        else:
                            error_msg = f"Script execution failed, status: {status}"
                            if error:
                                error_msg += f", error: {error[:200]}" if len(error) > 200 else f", error: {error}"
                            elif output:
                                error_msg += f", output: {output[:200]}" if len(output) > 200 else f", output: {output}"
                            return {
                                "ok": False,
                                "text": error_msg,
                                "result": result_data,
                                "error": {"code": "EXECUTE_FAILED", "message": error_msg}
                            }
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval

        return {
            "ok": False,
            "text": f"Script execution timeout (waited more than {max_wait_time} seconds)",
            "result": {"execute_uuid": execute_uuid},
            "error": {"code": "TIMEOUT", "message": "Script execution timeout"}
        }

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)


def coc_list_scripts(page: int = 1, limit: int = 10, ak: str = None, sk: str = None, security_token: str = None) -> dict[str, Any]:
    """
    List COC scripts

    Args:
        page: Page number (starting from 1)
        limit: Number per page
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script list obtained",
            "result": {
                "scripts": [...],
                "total": 100
            },
            "error": None
        }
    """
    try:
        client = get_coc_client(ak, sk, security_token)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import ListScriptsRequest
        
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

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)


def coc_query_execution(execute_uuid: str, ak: str = None, sk: str = None, security_token: str = None) -> dict[str, Any]:
    """
    Query script execution status

    Args:
        execute_uuid: Execution UUID (format: SCT2023083109562601af694bf)
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "data": {
                "batch_index": 1,
                "total_instances": 1,
                "execute_instances": [{
                    "id": 40304358,
                    "cmd_uuid": "xxx",
                    "job_sign": null,
                    "status": "FINISHED",
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
        return _error("INPUT_ERROR", "execute_uuid parameter is required")

    try:
        client = get_coc_client(ak, sk, security_token)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import GetScriptJobBatchRequest
        
        request = GetScriptJobBatchRequest()
        request.batch_index = 1
        request.execute_uuid = execute_uuid
        request.limit = 50
        
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
            result_dict['message'] = 'Execution record does not exist or data is empty'

        return {
            "data": result_dict
        }

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)


SCRIPT_TEMPLATES = {
    "install_maas": {
        "name": "OpenClaw-MaaS-Model-Installation",
        "type": "SHELL",
        "description": "Install MaaS models on OpenClaw instance",
        "risk_level": "MEDIUM",
        "content": '''#!/bin/bash
curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-clawdbot-agents/userdata/multi_model.sh | bash -s '${modelParams}'

if [ -d "/home/openclaw" ]; then
  export PNPM_HOME="/home/openclaw/.local/share/pnpm"
  export NVM_DIR="/home/openclaw/.nvm"
  ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/node /usr/local/bin/node
  ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/npm /usr/local/bin/npm
  CMD_NAME=/home/openclaw/.local/share/pnpm/openclaw
  sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway restart >> /var/manage_operate.log 2>&1
  GATEWAY_STATUS_OUTPUT=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway status 2>&1)
else
  ln -sf /root/.nvm/versions/node/v22.22.0/bin/node /usr/local/bin/node
  ln -sf /root/.nvm/versions/node/v22.22.0/bin/npm /usr/local/bin/npm
  CMD_NAME=/root/.local/share/pnpm/openclaw
  /root/.local/share/pnpm/openclaw gateway restart >> /var/manage_operate.log 2>&1
  GATEWAY_STATUS_OUTPUT=$($CMD_NAME gateway status 2>&1)
fi'''
    },
    "install_channel": {
        "name": "OpenClaw-Channel-Installation",
        "type": "SHELL",
        "description": "Install channels on OpenClaw instance (WeChat Work/Feishu/DingTalk/QQ)",
        "risk_level": "MEDIUM",
        "content": '''#!/bin/bash
curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-clawdbot-agents/userdata/multi_channel.sh | bash -s '${channelList}'

if [ -d "/home/openclaw" ]; then
  export PNPM_HOME="/home/openclaw/.local/share/pnpm"
  export NVM_DIR="/home/openclaw/.nvm"
  ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/node /usr/local/bin/node
  ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/npm /usr/local/bin/npm
  CMD_NAME=/home/openclaw/.local/share/pnpm/openclaw
  sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway restart >> /var/manage_operate.log 2>&1
  GATEWAY_STATUS_OUTPUT=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway status 2>&1)
else
  ln -sf /root/.nvm/versions/node/v22.22.0/bin/node /usr/local/bin/node
  ln -sf /root/.nvm/versions/node/v22.22.0/bin/npm /usr/local/bin/npm
  CMD_NAME=/root/.local/share/pnpm/openclaw
  /root/.local/share/pnpm/openclaw gateway restart >> /var/manage_operate.log 2>&1
  GATEWAY_STATUS_OUTPUT=$($CMD_NAME gateway status 2>&1)
fi'''
    },
    "check_gateway": {
        "name": "OpenClaw-Gateway-Status",
        "type": "SHELL",
        "description": "Query OpenClaw gateway status",
        "risk_level": "LOW",
        "content": '''#!/bin/bash
curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-clawdbot-agents/userdata/openclaw_gateway_manager.sh | bash -s status'''
    }
}


def install_maas_models_remote(
    resource_id: str,
    region_id: str,
    model_params: str = "",
    timeout: int = 600,
    execute_user: str = "root",
    ak: str = None,
    sk: str = None,
    security_token: str = None
) -> dict[str, Any]:
    """
    Install MaaS models on remote L instance via COC

    Args:
        resource_id: L instance resource ID
        region_id: L instance region
        model_params: Model parameters string, format: {"provider":"huawei","api_key":"xxx","model_ids":["model1","model2"]}
        timeout: Execution timeout (seconds), default 600
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    import time
    script_info = SCRIPT_TEMPLATES["install_maas"]
    
    content = script_info["content"].replace("${modelParams}", model_params)
    
    create_result = coc_create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        risk_level=script_info["risk_level"],
        ak=ak,
        sk=sk,
        security_token=security_token
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = coc_execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        rotation_strategy="CONTINUE",
        ak=ak,
        sk=sk,
        security_token=security_token
    )
    
    return execute_result


def install_channel_remote(
    resource_id: str,
    region_id: str,
    channel_list: str = "",
    timeout: int = 600,
    execute_user: str = "root",
    ak: str = None,
    sk: str = None,
    security_token: str = None
) -> dict[str, Any]:
    """
    Install channels on remote L instance via COC

    Args:
        resource_id: L instance resource ID
        region_id: L instance region
        channel_list: Channel configuration JSON array string, format: [{"channel":"wecom","id":"xxx","secret":"xxx",...}]
            Channel JSON object fields:
            - channel: Channel type (required): 'wecom' (WeCom), 'feishu' (Feishu), 'dingtalk' (DingTalk), 'qqbot' (QQ)
            - id: Bot ID/APP ID/Client ID (required)
            - secret: Bot secret/APP secret/Client secret (required)
            - account_id: Bot enterprise account ID (optional, auto-generated as 'bot-{timestamp}' if not provided)
            - bot_name: Bot name (optional, auto-generated as 'bot-{4-random-lowercase-letters}' if not provided)
        timeout: Execution timeout (seconds), default 600
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    import time
    import random
    import string
    
    # Parse channel_list and auto-generate missing account_id and bot_name
    if channel_list:
        try:
            channels = json.loads(channel_list)
            for channel in channels:
                # Generate account_id if not provided
                if "account_id" not in channel or not channel["account_id"]:
                    timestamp = int(time.time() * 1000)
                    channel["account_id"] = f"bot-{timestamp}"
                
                # Generate bot_name if not provided
                if "bot_name" not in channel or not channel["bot_name"]:
                    random_chars = ''.join(random.choices(string.ascii_lowercase, k=4))
                    channel["bot_name"] = f"bot-{random_chars}"
            
            # Convert back to JSON string
            channel_list = json.dumps(channels, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse channel_list JSON: {e}")
            # Keep original channel_list if parsing fails
    
    script_info = SCRIPT_TEMPLATES["install_channel"]
    
    content = script_info["content"].replace("${channelList}", channel_list)
    
    create_result = coc_create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        risk_level=script_info["risk_level"],
        ak=ak,
        sk=sk,
        security_token=security_token
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = coc_execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        rotation_strategy="CONTINUE",
        ak=ak,
        sk=sk,
        security_token=security_token
    )
    
    return execute_result


def install_maas_models_local(model_params=""):
    """
    Install models on local OpenClaw instance (via local bash execution)
    
    Args:
        model_params: Model parameters, e.g. custom vendor model name, format: provider/model-name
    
    Returns:
        None: Directly prints execution result
    """
    import subprocess
    
    try:
        print("Starting model installation...")
        
        install_command = f"curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-clawdbot-agents/userdata/multi_model.sh | bash -s {model_params}"
        
        print(f"Executing command: {install_command}")
        
        result = subprocess.run(
            install_command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(f"Command execution completed, exit code: {result.returncode}")
        
        if result.stdout:
            print(f"Standard output:\n{result.stdout}")
        if result.stderr:
            print(f"Error output:\n{result.stderr}")
        
        if os.path.exists("/home/openclaw"):
            print("\nDetected OpenClaw installed in /home/openclaw")
            subprocess.run("ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/node /usr/local/bin/node", shell=True)
            subprocess.run("ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/npm /usr/local/bin/npm", shell=True)
            cmd_name = "/home/openclaw/.local/share/pnpm/openclaw"
            restart_cmd = f"sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus {cmd_name} gateway restart >> /var/manage_operate.log 2>&1"
            subprocess.run(restart_cmd, shell=True)
            status_cmd = f"sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus {cmd_name} gateway status 2>&1"
            status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
            print(f"Gateway status:\n{status_result.stdout}")
            
        elif os.path.exists("/root/.local/share/pnpm/openclaw"):
            print("\nDetected OpenClaw installed in /root")
            subprocess.run("ln -sf /root/.nvm/versions/node/v22.22.0/bin/node /usr/local/bin/node", shell=True)
            subprocess.run("ln -sf /root/.nvm/versions/node/v22.22.0/bin/npm /usr/local/bin/npm", shell=True)
            cmd_name = "/root/.local/share/pnpm/openclaw"
            subprocess.run(f"{cmd_name} gateway restart >> /var/manage_operate.log 2>&1", shell=True)
            status_result = subprocess.run(f"{cmd_name} gateway status 2>&1", shell=True, capture_output=True, text=True)
            print(f"Gateway status:\n{status_result.stdout}")
        
        if result.returncode == 0:
            return {
                "ok": True,
                "text": "Model installation completed",
                "result": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                },
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": "Model installation failed",
                "result": None,
                "error": {
                    "code": str(result.returncode),
                    "message": result.stderr or result.stdout
                }
            }
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error installing models: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


def install_channel_local(channel_list=""):
    """
    Install channels on local OpenClaw instance (via local bash execution)
    
    Args:
        channel_list: Channel list parameters, e.g. wecom dingtalk
    
    Returns:
        None: Directly prints execution result
    """
    import subprocess
    
    try:
        print("Starting channel installation...")
        
        install_command = f"curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-clawdbot-agents/userdata/multi_channel.sh | bash -s {channel_list}"
        
        print(f"Executing command: {install_command}")
        
        result = subprocess.run(
            install_command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(f"Command execution completed, exit code: {result.returncode}")
        
        if result.stdout:
            print(f"Standard output:\n{result.stdout}")
        if result.stderr:
            print(f"Error output:\n{result.stderr}")
        
        if os.path.exists("/home/openclaw"):
            print("\nDetected OpenClaw installed in /home/openclaw")
            subprocess.run("ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/node /usr/local/bin/node", shell=True)
            subprocess.run("ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/npm /usr/local/bin/npm", shell=True)
            cmd_name = "/home/openclaw/.local/share/pnpm/openclaw"
            restart_cmd = f"sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus {cmd_name} gateway restart >> /var/manage_operate.log 2>&1"
            subprocess.run(restart_cmd, shell=True)
            status_cmd = f"sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus {cmd_name} gateway status 2>&1"
            status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
            print(f"Gateway status:\n{status_result.stdout}")
            
        elif os.path.exists("/root/.local/share/pnpm/openclaw"):
            print("\nDetected OpenClaw installed in /root")
            subprocess.run("ln -sf /root/.nvm/versions/node/v22.22.0/bin/node /usr/local/bin/node", shell=True)
            subprocess.run("ln -sf /root/.nvm/versions/node/v22.22.0/bin/npm /usr/local/bin/npm", shell=True)
            cmd_name = "/root/.local/share/pnpm/openclaw"
            subprocess.run(f"{cmd_name} gateway restart >> /var/manage_operate.log 2>&1", shell=True)
            status_result = subprocess.run(f"{cmd_name} gateway status 2>&1", shell=True, capture_output=True, text=True)
            print(f"Gateway status:\n{status_result.stdout}")
        
        if result.returncode == 0:
            return {
                "ok": True,
                "text": "Channel installation completed",
                "result": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                },
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": "Channel installation failed",
                "result": None,
                "error": {
                    "code": str(result.returncode),
                    "message": result.stderr or result.stdout
                }
            }
            
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error installing channels: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


def check_gateway_status_remote(
    resource_id: str,
    region_id: str,
    timeout: int = 600,
    execute_user: str = "root",
    ak: str = None,
    sk: str = None,
    security_token: str = None
) -> dict[str, Any]:
    """
    Query OpenClaw gateway status on remote L instance via COC

    Args:
        resource_id: L instance resource ID
        region_id: L instance region
        timeout: Execution timeout (seconds), default 600
        execute_user: Execute user, default root
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    import time
    script_info = SCRIPT_TEMPLATES["check_gateway"]
    
    content = script_info["content"]
    
    create_result = coc_create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        risk_level=script_info["risk_level"],
        ak=ak,
        sk=sk,
        security_token=security_token        
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]
    
    execute_result = coc_execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        rotation_strategy="CONTINUE",
        ak=ak,
        sk=sk,
        security_token=security_token
    )
    
    return execute_result


def query_uniagent_status(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None
) -> dict[str, Any]:
    """
    Query L instance UniAgent status via COC API

    Args:
        resource_id: L instance resource ID
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials (optional)

    Returns:
        {
            "ok": True,
            "text": "Query successful",
            "result": {...},
            "error": None
        }
    """
    if not resource_id:
        return _error("INPUT_ERROR", "resource_id parameter is required")
    
    if not ak or not sk:
        return _error("CONFIG_ERROR", "Please provide AK and SK parameters")
    
    region = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")
    
    try:
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from urllib.parse import urlparse
        
        credentials = Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        endpoint = "https://coc.myhuaweicloud.com/v1/resources"
        
        query_params = {
            "resource_id_list": resource_id,
            "limit": "100",
            "provider": "hcss",
            "type": "l-instance"
        }
        
        url_with_params = endpoint + "?" + "&".join([f"{k}={v}" for k, v in query_params.items()])
        parsed_url = urlparse(url_with_params)
        
        request = SdkRequest()
        request.method = "GET"
        request.schema = parsed_url.scheme
        request.host = parsed_url.hostname
        request.resource_path = parsed_url.path
        request.query_params = [[k, v] for k, v in query_params.items()]
        request.header_params = {
            "Content-Type": "application/json",
            "Client-Request-Id": str(uuid.uuid4())
        }
        
        if security_token:
            request.header_params["X-Security-Token"] = security_token
        
        signed_request = signer.sign(request)
        
        headers = {}
        for key, value in signed_request.header_params.items():
            if isinstance(value, bytes):
                headers[key] = value.decode('iso-8859-1')
            else:
                headers[key] = str(value)
        
        print(f"Request URL: {url_with_params}")
        print(f"Request headers: {headers}")
        
        resp = requests.request(
            "GET",
            url_with_params,
            headers=headers,
            verify=True
        )
        
        print(f"Response status code: {resp.status_code}")
        print(f"Response content: {resp.text}")
        
        if resp.status_code in [200, 202]:
            response_data = resp.json()
            return {
                "ok": True,
                "text": "UniAgent status query successful",
                "result": response_data,
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": f"Query failed: {resp.reason}",
                "result": None,
                "error": {
                    "code": str(resp.status_code),
                    "message": resp.text
                }
            }
    
    except ImportError as e:
        return _error("SDK_ERROR", f"Please install huaweicloudsdkcore: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        return _error("UNKNOWN_ERROR", error_msg)
