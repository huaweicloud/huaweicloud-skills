#!/usr/bin/env python3
# Copyright (c) Huawei Technologies CO., LTD. 2022-2025. All rights reserved.
# coding=utf-8
"""
Huawei Cloud Flexus L Instance One-Click FlexusAgent Deployment - Core Module
Includes:
1. L Instance creation functionality
2. COC script management (create script, execute script)
3. Large model installation functionality
4. Admin password change functionality
"""

import json
import os
import requests
import uuid
import time
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
    Get Project ID for specified region using AK/SK

    Parameters:
        region: Target region, e.g. cn-north-4, cn-southwest-2
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

    Returns:
        Project ID string, returns None on failure
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

    Parameters:
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

    Returns:
        CocClient instance
    """
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    from huaweicloudsdkcoc.v1 import CocClient

    if not ak or not sk:
        raise ValueError("COC credentials not configured, please provide AK and SK parameters")

    region = os.environ.get("HUAWEICLOUD_REGION", "cn-north-4")

    if not security_token:
        credentials = GlobalCredentials(ak, sk)
    else:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    
    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(region)) \
        .build()

    return client


def create_flexusagent_instance(instance_name=None, region=None, ak=None, sk=None, security_token=None, spec=None):
    """
    Create Huawei Cloud Flexus L Instance (dedicated for FlexusAgent)

    API Reference: https://support.huaweicloud.com/api-flexusl/create_instance_0001.html

    Parameters:
        instance_name: Instance name, optional, auto-generated as FlexusAgent-timestamp if not specified
        region: Target region, required
        ak: Huawei Cloud AK, required
        sk: Huawei Cloud SK, required
        security_token: Security token for temporary credentials (required when using temporary AK/SK, optional for permanent AK/SK)
        spec: Instance spec, required, must be one of: hf.xlarge.1.linux, ahf.xlarge.1.linux, hf.xlarge.3.linux, ahf.xlarge.3.linux
              Note: For cn-southwest-2 region, only ahf.xlarge.1.linux and ahf.xlarge.3.linux are available
                    For other regions, only hf.xlarge.1.linux and hf.xlarge.3.linux are available

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
                "message": "Please provide AK, SK and security_token parameters"
            }
        }

    target_region = region

    project_id = get_project_id_by_region(target_region, ak, sk, security_token)
    if not project_id:
        return {
            "ok": False,
            "text": "Failed to get Project ID",
            "result": None,
            "error": {
                "code": "PROJECT_ID_ERROR",
                "message": f"Unable to get Project ID for region {target_region}, please verify credentials"
            }
        }

    if not instance_name:
        instance_name = f"FlexusAgent-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    endpoint = "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances"

    # Use specified spec, or auto-select based on region if not specified
    if spec:
        plan_spec = spec
    elif target_region == "cn-southwest-2":
        plan_spec = "ahf.xlarge.1.linux"
    else:
        plan_spec = "hf.xlarge.1.linux"

    request_body = {
        "instance_name": instance_name,
        "plan_spec": plan_spec,
        "image_ref": {
            "image_name": "FlexusAgent",
            "image_version": "1.7.1"
        },
        "region": target_region,
        "charging_mode": "prePaid",
        "period_type": "month",
        "period_num": 1,
        "purchase_quantity": 1,
        "description": "FlexusAgent one-click deployment",
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

        print(f"Authorization: {headers.get('Authorization')}")
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
            
            # Fix: Get instance ID from instance_ids array
            instance_ids = response_data.get('instance_ids', [])
            instance_id = instance_ids[0] if instance_ids else 'Unknown'
            
            return {
                "ok": True,
                "text": f"Instance creation request submitted",
                "result": {
                    "order_id": response_data.get('order_id', 'Unknown'),
                    "instance_ids": instance_ids,
                    "instance_id": instance_id
                },
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

    Parameters:
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
        security_token: str = None,
) -> dict[str, Any]:
    """
    Create custom script in COC

    Parameters:
        name: Script name
        script_type: Script type (SHELL/PYTHON/BAT)
        content: Script content
        description: Script description
        risk_level: Risk level (LOW/MEDIUM/HIGH), default LOW
        version: Script version, default 1.0.0
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

    Returns:
        {
            "ok": True,
            "text": "Script created successfully: SC2023102521413701c4a8a62",
            "result": { Raw API result },
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
        client = get_coc_client(ak, sk, security_token)
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
        security_token: str = None,
) -> dict[str, Any]:
    """
    Execute custom script on target instances

    Parameters:
        script_uuid: UUID of script to execute
        execute_user: User to execute script (e.g. root)
        timeout: Execution timeout in seconds (5 < timeout < 1800)
        success_rate: Success rate (supports one decimal place, e.g. 1 or 100)
        target_instances: List of target instances, each containing:
            - resource_id: Instance ID (required)
            - region_id: Server region (required)
            - provider: Resource provider (not required for ECS, default "HCSS" for L Instance)
            - type: Resource type (not required for ECS, default "L-INSTANCE" for L Instance)
        rotation_strategy: Rotation strategy (CONTINUE/STOP), default CONTINUE
        wait_for_complete: Whether to wait for completion and get logs, default True
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

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
                error_msg = query_result.get("error", {}).get("message", "Unknown error") if isinstance(query_result,
                                                                                                   dict) else "Query failed"
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

            # Return error if status is UNKNOWN and we've waited a while (e.g. 30 seconds)
            if status == "UNKNOWN" and elapsed_time > 30:
                return {
                    "ok": False,
                    "text": f"Script execution status unknown, execution ID may not exist or API is unresponsive",
                    "result": {"execute_uuid": execute_uuid, "status": status},
                    "error": {"code": "UNKNOWN_STATUS", "message": "Execution status unknown, execution ID may not exist or API is unresponsive"}
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

    Parameters:
        page: Page number (starts from 1)
        limit: Number per page
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

    Returns:
        {
            "ok": True,
            "text": "Script list retrieved",
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

    Parameters:
        execute_uuid: Execution UUID (format: SCT2023083109562601af694bf)
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

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
                            "host_name": "flexusagent-test-001",
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


def query_uniagent_status(
        resource_id: str,
        ak: str,
        sk: str,
        security_token: str = None,
) -> dict[str, Any]:
    """
    Query L Instance UniAgent status via COC API

    Parameters:
        resource_id: L Instance resource ID
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

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
        return _error("CONFIG_ERROR", "Please provide AK, SK and security_token parameters")

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


SCRIPT_TEMPLATES = {
    "change_password": {
        "name": "FlexusAgent-Admin-Password",
        "type": "SHELL",
        "description": "Change FlexusAgent admin user password",
        "risk_level": "LOW",
        "content": '''#!/bin/bash
curl -sSL https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/agent/reset_admin_password.sh | bash -s "${adminPassword}"'''
    },
    "import_dify_app_workflow": {
        "name": "import_dify_app_workflow",
        "type": "SHELL",
        "description": "import dify app workflow on dify server instance",
        "risk_level": "MEDIUM",
        "content": '''curl -sSL https://flexus-config-cn-north-4-product.obs.cn-north-4.myhuaweicloud.com/stable/dify/scripts/import_yml_to_dify.sh | bash -s ${base64String} ${dify_admin_password}'''
    },
}


def change_flexusagent_admin_password(
        resource_id: str,
        region_id: str,
        admin_password: str = "",
        timeout: int = 600,
        execute_user: str = "root",
        ak: str = None,
        sk: str = None,
        security_token: str = None,
) -> dict[str, Any]:
    """
    Change FlexusAgent admin password via COC on remote L Instance

    Parameters:
        resource_id: L Instance resource ID
        region_id: L Instance region
        admin_password: New password for FlexusAgent admin user
        timeout: Execution timeout in seconds, default 600
        execute_user: Execution user, default root
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)

    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    }
    """
    import time
    script_info = SCRIPT_TEMPLATES["change_password"]

    content = script_info["content"].replace("${adminPassword}", admin_password)

    create_result = coc_create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        risk_level=script_info["risk_level"],
        ak=ak,
        sk=sk,
        security_token=security_token,
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
        security_token=security_token,
    )

    return execute_result


def import_app_workflow_remote(
        resource_id: str,
        region_id: str,
        flexusagent_email: str,
        flexusagent_password: str,
        app_workflow_id: str,
        timeout: int = 600,
        execute_user: str = "root",
        ak: str = None,
        sk: str = None,
        security_token: str = None,
) -> dict[str, Any]:
    """
    Import Dify app workflow to FlexusAgent instance via COC
    
    Parameters:
        resource_id: L Instance resource ID
        region_id: L Instance region
        flexusagent_email: FlexusAgent admin email
        flexusagent_password: FlexusAgent admin password
        app_workflow_id: Dify app workflow ID (e.g., "Bid_Writing_And_Templated_Adaptation")
        timeout: Execution timeout in seconds, default 600
        execute_user: Execution user, default root
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (required)
    
    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT2023083109562601af694bf",
            "result": {...},
            "error": None
        }
    """
    import time
    import base64
    import requests
    
    print(f"\nDownloading workflow template: {app_workflow_id}...")
    template_url = f"https://flexus-config-cn-north-4-product.obs.cn-north-4.myhuaweicloud.com/stable/dify/dify-templates/national/templates/{app_workflow_id}/template.yml?timestamp={int(time.time())}"
    
    try:
        resp = requests.get(template_url, timeout=30)
        if resp.status_code != 200:
            return {
                "ok": False,
                "text": f"Failed to download workflow template: HTTP {resp.status_code}",
                "result": None,
                "error": {"code": "DOWNLOAD_FAILED", "message": f"Failed to download from {template_url}"}
            }
        
        # 正确解码UTF-8内容，移除BOM和控制字符
        yaml_content = resp.content.decode('utf-8-sig')
        
        # 移除不可见的控制字符（保留换行符、制表符等格式字符）
        import re
        yaml_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', yaml_content)
        
        print(f"  [OK] Downloaded template ({len(yaml_content)} bytes)")
        
    except Exception as e:
        return {
            "ok": False,
            "text": f"Failed to download workflow template: {str(e)}",
            "result": None,
            "error": {"code": "DOWNLOAD_ERROR", "message": str(e)}
        }
    
    print("\nConstructing import payload...")
    payload = {
        "host": "",
        "email": flexusagent_email,
        "language": "zh-CN",
        "mode": "yaml-content",
        "yaml_content": yaml_content,
        "execute_type": "app"
    }
    
    payload_json = json.dumps(payload, ensure_ascii=False)
    base64_string = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')
    print(f"  [OK] Payload encoded (base64 length: {len(base64_string)})")
    
    print("\nCreating COC script...")
    script_info = SCRIPT_TEMPLATES["import_dify_app_workflow"]
    
    content = script_info["content"].replace("${base64String}", base64_string).replace("${dify_admin_password}", flexusagent_password)
    
    create_result = coc_create_script(
        name=f"{script_info['name']}-{int(time.time())}",
        script_type=script_info["type"],
        content=content,
        description=script_info["description"],
        risk_level=script_info["risk_level"],
        ak=ak,
        sk=sk,
        security_token=security_token,
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    print(f"  [OK] Script created: {script_uuid}")
    
    print("\nExecuting COC script...")
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
        security_token=security_token,
    )
    
    return execute_result


def get_security_group_id_by_name(
        ak: str,
        sk: str,
        region: str,
        group_name: str,
        security_token: str = None,
) -> dict:
    """
    Get security group ID by name

    Parameters:
        ak:         Huawei Cloud Access Key
        sk:         Huawei Cloud Secret Key
        region:     Region, e.g. "cn-north-4"
        group_name: Security group name
        security_token: Security token for temporary credentials (required)

    Returns:
        Security group ID, returns None if not found
    """
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkvpc.v2 import VpcClient, ListSecurityGroupsRequest
        from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

        # 1. Initialize authentication and client
        if not security_token:
            credentials = BasicCredentials(ak, sk)
        else:
            credentials = BasicCredentials(ak, sk).with_security_token(security_token)
            
        client = (
            VpcClient.new_builder()
            .with_credentials(credentials)
            .with_region(VpcRegion.value_of(region))
            .build()
        )

        # 2. Query security groups
        request = ListSecurityGroupsRequest()
        response = client.list_security_groups(request)

        if response.status_code in [200, 201, 202]:
            all_groups = response.to_dict().get("security_groups", [])
            for group in all_groups:
                if group.get("name") == str(group_name):
                    return {
                        "ok": True,
                        "text": "Query successful",
                        "result": group.get("id"),
                        "error": None
                    }
            else:
                return {
                    "ok": False,
                    "text": f"Query failed: No security group with name {group_name}",
                    "result": None,
                    "error": None
                }
        else:
            return {
                "ok": False,
                "text": f"Query failed: {response.reason}",
                "result": None,
                "error": {
                    "code": str(response.status_code),
                    "message": response.text
                }
            }
    except ImportError as e:
        return {
            "ok": False,
            "text": "SDK import failed",
            "result": None,
            "error": {
                "code": "SDK_ERROR",
                "message": f"Please install huaweicloudsdkvpc: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error creating security group ingress rule: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


def create_ingress_rule(
        ak: str,
        sk: str,
        region: str,
        security_group_id: str,
        protocol: str = "tcp",
        port: str = "80",
        remote_ip: str = "0.0.0.0/0",
        description: str = "Web UI port",
        ethertype: str = "IPv4",
        security_token: str = None,
) -> dict:
    """
    Add ingress rule to specified security group

    Parameters:
        ak:            Huawei Cloud Access Key
        sk:            Huawei Cloud Secret Key
        region:        Region, e.g. "cn-north-4"
        security_group_id: Security group ID
        protocol:      Protocol type, supports tcp / udp / icmp / gre
        port:          Port number, e.g. "22" or "22-30"
        remote_ip:     Source IP address or CIDR, e.g. "192.168.1.0/24" or "0.0.0.0/0"
        description:   Rule description (optional)
        ethertype:     Address type, IPv4 or IPv6
        security_token: Security token for temporary credentials (required)

    Returns:
        Dictionary with rule details on success
    """
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkvpc.v2 import (
            VpcClient,
            CreateSecurityGroupRuleRequest,
            CreateSecurityGroupRuleOption,
            CreateSecurityGroupRuleRequestBody
        )
        from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion
        # 1. Initialize authentication
        if not security_token:
            credentials = BasicCredentials(ak, sk)
        else:
            credentials = BasicCredentials(ak, sk).with_security_token(security_token)

        # 2. Build VPC client
        client = (
            VpcClient.new_builder()
            .with_credentials(credentials)
            .with_region(VpcRegion.value_of(region))
            .build()
        )

        # 3. Build request body
        rule_option = CreateSecurityGroupRuleOption(
            security_group_id=security_group_id,
            direction="ingress",  # Inbound direction
            protocol=protocol,
            port_range_min=int(port.split("-")[0]) if "-" in port else int(port),
            port_range_max=int(port.split("-")[1]) if "-" in port else int(port),
            remote_ip_prefix=remote_ip,
            description=description,
            ethertype=ethertype,
        )

        # 3. Send create request
        request = CreateSecurityGroupRuleRequest()
        request.body = CreateSecurityGroupRuleRequestBody(rule_option)

        response = client.create_security_group_rule(request)
        if response.status_code in [200, 201, 202]:
            return {
                "ok": True,
                "text": f"Security group inbound port {port} opened",
                "result": response.security_group_rule,
                "error": None
            }
        else:
            return {
                "ok": False,
                "text": "Failed to create security group ingress rule",
                "result": None,
                "error": {
                    "code": str(response.status_code),
                    "message": response.text
                }
            }
    except ImportError as e:
        return {
            "ok": False,
            "text": "SDK import failed",
            "result": None,
            "error": {
                "code": "SDK_ERROR",
                "message": f"Please install huaweicloudsdkvpc: {str(e)}"
            }
        }
    except Exception as e:
        return {
            "ok": False,
            "text": f"Error creating security group ingress rule: {str(e)}",
            "result": None,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": str(e)
            }
        }


# ==================== Part 1: Authentication Management ====================
def get_admin_session(
        base_url: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
) -> requests.Session:
    """
    Login to FlexusAgent console via email/password and get session (Session/Cookie).

    Parameters
    ----------
    base_url : str
        FlexusAgent service URL
    email : str
        Admin login email
    password : str
        Admin login password
    timeout : int
        Request timeout

    Returns
    ----------
    requests.Session
        Authenticated session object
    """
    import base64
    base_url = base_url.rstrip("/")
    session = requests.Session()

    if not email or not password:
        raise ValueError("Must provide email and password to login and get session.")

    try:
        # 1. Access homepage or login page to initialize Cookies and get initial CSRF Token
        session.get(f"{base_url}/signin", timeout=timeout)

        # 2. Prepare login
        login_url = f"{base_url}/console/api/login"
        login_payload = {
            "email": email,
            "password": base64.b64encode(password.encode("utf-8")).decode("utf-8"),
            "remember_me": True,
        }

        # Extract CSRF Token from initial Cookies (if any)
        initial_csrf = (
                session.cookies.get('csrf_token') or
                session.cookies.get('_csrf_token') or
                session.cookies.get('__Secure-Ns-Csrf-Token')
        )
        login_headers = {"Content-Type": "application/json"}
        if initial_csrf:
            login_headers["X-Csrf-Token"] = initial_csrf

        resp = session.post(
            login_url, json=login_payload, headers=login_headers, timeout=timeout
        )

        if resp.status_code == 401:
            raise PermissionError("Login failed: Invalid email or password.")
        if resp.status_code == 403:
            raise PermissionError("Login failed: Account not authorized.")

        resp.raise_for_status()

        # 3. After successful login, extract CSRF Token from Cookies and set headers
        # FlexusAgent 1.11.x may use 'csrf_token', '_csrf_token' or '__Secure-Ns-Csrf-Token'
        csrf_token = (
                session.cookies.get('csrf_token') or
                session.cookies.get('_csrf_token') or
                session.cookies.get('__Secure-Ns-Csrf-Token')
        )

        if csrf_token:
            session.headers.update({
                'X-Csrf-Token': csrf_token,
                'Referer': f"{base_url}/plugins?category=discover",
                'Origin': base_url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
            })

        # 4. Verify if session is truly valid (access workspaces endpoint)
        test_resp = session.get(f"{base_url}/console/api/workspaces", timeout=timeout)
        if test_resp.status_code != 200:
            raise PermissionError(f"Login successful but session verification failed (status code: {test_resp.status_code})")

        return session

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Login exception: {str(e)}")


# ==================== Part 2: Built-in Provider Management ====================


def _probe_model_provider_endpoint(
        base_url: str,
        session: requests.Session,
        provider_name: str,
        suffix: str = "",
        method: str = "GET",
        json_data: Any = None,
        params: Any = None,
        timeout: int = 30
) -> requests.Response:
    """Probe and request model provider API endpoint"""
    workspace_id = _get_workspace_id(base_url, session)
    
    # Build candidate path sequence
    base_paths = [f"model-providers/{provider_name}"]
    if "plugin/" not in provider_name and "/" in provider_name:
        base_paths.append(f"model-providers/{provider_name.replace('/', '/plugin/', 1)}")

    endpoints = []
    for bp in base_paths:
        full_path = f"{bp}/{suffix.lstrip('/')}" if suffix else bp
        endpoints.extend([
            f"{base_url}/console/api/workspaces/current/{full_path}",
            f"{base_url}/console/api/workspaces/{workspace_id}/{full_path}",
            f"{base_url}/console/api/{full_path}",
        ])

    last_resp = None
    for url in list(dict.fromkeys(endpoints)):
        try:
            resp = session.request(method, url, json=json_data, params=params, timeout=timeout)
            if resp.status_code != 404: return resp
            last_resp = resp
        except: continue

    return last_resp or requests.Response() # Return empty response as fallback


def add_model_provider(
        base_url: str,
        session: requests.Session,
        provider_name: str,
        credential_schema: Dict[str, Any],
        configurate_method: str = "predefined-model",
        custom_provider_name: Optional[str] = None,
        timeout: int = 30,
) -> Dict[str, Any]:
    """
    Add or update model provider credential configuration (supports automatic name variant attempts).
    """
    base_url = base_url.rstrip("/")
    payload: Dict[str, Any] = {
        "configurate_method": configurate_method,
        "credential_schema": credential_schema,
        "credentials": credential_schema, # Compatible with 1.11.4 spec
    }
    if custom_provider_name:
        payload["custom_provider_name"] = custom_provider_name

    # Build candidate provider name sequence (for path uncertainty in 1.11.4 plugin mode)
    candidates = [provider_name]
    if "/" in provider_name:
        parts = provider_name.split("/")
        if len(parts) >= 3:
            # If already in org/plugin/provider format, try variations of provider part
             org_plugin = "/".join(parts[:2])
             short_name = parts[1]
             candidates.extend([
                 f"{org_plugin}/huaweicloud_{short_name}", # Prefer concatenated format
                 f"{org_plugin}/huawei_cloud_{short_name}",
                 f"{org_plugin}/hcloud_{short_name}",
                 f"{org_plugin}/cloud_{short_name}",
                 f"{org_plugin}/{short_name}", # Fallback to original short name
             ])
    
    # Remove duplicates while preserving order
    candidates = list(dict.fromkeys(candidates))

    last_err = None
    for name in candidates:
        try:
            print(f"  Attempting to configure provider credentials: {name} ...", end=" ", flush=True)
            resp = _probe_model_provider_endpoint(
                base_url, session, name, suffix="credentials", method="POST", json_data=payload, timeout=timeout
            )
            
            if resp.status_code < 400:
                print("✓")
                return resp.json()
            
            last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
            print(f"✗ ({resp.status_code})")
        except Exception as e:
            last_err = str(e)
            print(f"✗ (Error)")
            continue

    raise ValueError(f"Failed to configure model provider credentials, all path variants failed: {candidates}. Last error: {last_err}")


# ==================== Part 3: Model Management ====================


def add_model_to_provider(
        base_url: str,
        session: requests.Session,
        provider_name: str,
        model_name: str,
        model_type: str = "llm",
        model_credential_schema: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
) -> Dict[str, Any]:
    """
    Add a custom model to configured model provider.
    """
    base_url = base_url.rstrip("/")
    payload: Dict[str, Any] = {
        "model": model_name,
        "model_type": model_type,
    }
    if model_credential_schema:
        payload["credential_schema"] = model_credential_schema

    resp = _probe_model_provider_endpoint(
        base_url, session, provider_name, suffix="models", method="POST", json_data=payload, timeout=timeout
    )

    if resp.status_code == 401:
        raise PermissionError("Authentication failed: Session expired.")
    if resp.status_code == 409:
        raise ValueError(f"Model '{model_name}' may already exist.")
    if resp.status_code == 422:
        raise ValueError(f"Invalid request parameters: {resp.text}")

    resp.raise_for_status()
    return resp.json()


def add_models_to_provider(
        base_url: str,
        session: requests.Session,
        provider_name: str,
        models: List[Dict[str, Any]],
        timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Batch add multiple models to provider.
    """
    results = []
    for i, model_cfg in enumerate(models):
        model_name = model_cfg["model_name"]
        print(f"  Adding model ({i + 1}/{len(models)}): {model_name} ...", end=" ", flush=True)
        try:
            result = add_model_to_provider(
                base_url=base_url,
                session=session,
                provider_name=provider_name,
                model_name=model_name,
                model_type=model_cfg.get("model_type", "llm"),
                model_credential_schema=model_cfg.get("model_credential_schema"),
                timeout=timeout,
            )
            results.append({"model_name": model_name, "status": "success", "data": result})
            print("✓")
        except ValueError as e:
            results.append({"model_name": model_name, "status": "skipped", "reason": str(e)})
            print(f"⊘ (Skipped)")
        except Exception as e:
            results.append({"model_name": model_name, "status": "failed", "reason": str(e)})
            print(f"✗ (Failed)")

    return results


def delete_model_from_provider(
        base_url: str,
        session: requests.Session,
        provider_name: str,
        model_name: str,
        model_type: str = "llm",
        timeout: int = 30,
) -> Dict[str, Any]:
    """
    Delete a model from provider.
    """
    base_url = base_url.rstrip("/")
    params = {"model_type": model_type}
    resp = _probe_model_provider_endpoint(
        base_url, session, provider_name, suffix=f"models/{model_name}", method="DELETE", params=params, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()


# ==================== Part 4: Plugin Marketplace Management ====================

def _get_workspace_id(base_url: str, session: requests.Session, timeout: int = 10) -> str:
    """Get Workspace ID (with caching)"""
    if hasattr(session, "_cached_workspace_id"):
        return session._cached_workspace_id
    try:
        resp = session.get(f"{base_url}/console/api/workspaces", timeout=timeout)
        if resp.status_code == 200:
            wid = resp.json().get("workspaces", [{}])[0].get("id", "current")
            session._cached_workspace_id = wid
            return wid
    except: pass
    return "current"

def _get_plugin_base_url(base_url: str, session: requests.Session) -> str:
    """Probe plugin API base path (with caching)"""
    if hasattr(session, "_cached_plugin_base_url"):
        return session._cached_plugin_base_url
    
    workspace_id = _get_workspace_id(base_url, session)
    candidates = [
        f"{base_url}/console/api/workspaces/current/plugin",
        f"{base_url}/plugins",
        f"{base_url}/console/api/workspaces/{workspace_id}/plugin",
    ]
    
    for c in candidates:
        for suffix in ["/list", "/installed", ""]:
            try:
                if session.get(f"{c}{suffix}".rstrip("/"), params={"page":1,"page_size":1}, timeout=3).status_code == 200:
                    session._cached_plugin_base_url = c
                    return c
            except: continue
            
    session._cached_plugin_base_url = f"{base_url}/console/api/workspaces/current/plugin"
    return session._cached_plugin_base_url


def _probe_plugin_endpoint(
        base_url: str,
        session: requests.Session,
        suffix: str = "",
        method: str = "GET",
        json_data: Any = None,
        params: Any = None,
        timeout: int = 30
) -> requests.Response:
    """Internal helper: probe and request plugin API endpoint"""
    base_plugin_url = _get_plugin_base_url(base_url, session)

    # For 1.11.4 spec: write operations must use console path
    if method in ("POST", "PUT", "DELETE") and "/plugins" in base_plugin_url:
        base_plugin_url = f"{base_url}/console/api/workspaces/current/plugin"

    # Path joining logic
    if suffix == "install" and method == "POST":
        target_url = f"{base_plugin_url}/install/marketplace"
    elif suffix == "installed":
        target_url = base_plugin_url if "/plugins" in base_plugin_url else f"{base_plugin_url}/list"
    elif suffix:
        target_url = f"{base_plugin_url}/{suffix.lstrip('/')}".rstrip("/")
    else:
        target_url = base_plugin_url.rstrip("/")

    try:
        resp = session.request(method, target_url, json=json_data, params=params, timeout=timeout)

        # Auto-update CSRF Token
        new_csrf = resp.cookies.get('csrf_token') or resp.cookies.get('_csrf_token') or resp.cookies.get('__Secure-Ns-Csrf-Token')
        if new_csrf:
            session.headers.update({'X-Csrf-Token': new_csrf})

        return resp
    except Exception as e:
        print(f"  ! Failed to request plugin endpoint: {target_url}, error: {str(e)}")
        raise


def list_available_plugins(
        base_url: str,
        session: requests.Session,
        search: Optional[str] = None,
        timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get plugin list only through FlexusAgent official marketplace API.
    """
    base_url = base_url.rstrip("/")
    marketplace_url = "https://marketplace.flexusagent.ai/api/v1/plugins/search/advanced"
    
    try:
        search_payload = {
            "query": search or "",
            "page": 1,
            "page_size": 40,
            "sort_by": "install_count",
            "sort_order": "DESC"
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": base_url,
            "Referer": f"{base_url}/",
            "X-FlexusAgent-Version": "1.11.4",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        }

        print(f"  Requesting official marketplace API: {marketplace_url} ...")
        resp = requests.post(marketplace_url, json=search_payload, headers=headers, timeout=timeout)

        if resp.status_code == 200:
            try:
                data = resp.json()
            except:
                return []

            # Extreme compatibility: deep traverse to find any object with plugin characteristics
            plugins = []
            def find_plugins_recursive(obj):
                if isinstance(obj, list):
                    for item in obj:
                        find_plugins_recursive(item)
                elif isinstance(obj, dict):
                    # If it contains plugin_id or id, and contains some identifier, consider it a plugin object
                    p_id = obj.get("plugin_id") or obj.get("id")
                    p_uid = obj.get("plugin_unique_identifier") or obj.get("latest_package_identifier")
                    if p_id and p_uid:
                        # Normalize fields to ensure subsequent logic can access them
                        if "plugin_id" not in obj: obj["plugin_id"] = p_id
                        if "plugin_unique_identifier" not in obj: obj["plugin_unique_identifier"] = p_uid
                        plugins.append(obj)
                    else:
                        for v in obj.values():
                            find_plugins_recursive(v)

            find_plugins_recursive(data)
            if plugins:
                print(f"  ✓ Found {len(plugins)} results from official marketplace")
                return plugins
    except Exception as e:
        print(f"  ! Official marketplace API request failed: {str(e)}")

    return []


def install_plugin(
        base_url: str,
        session: requests.Session,
        plugin_id: str,
        version: Optional[str] = None,
        source: str = "marketplace",
        timeout: int = 60,
) -> Dict[str, Any]:
    """Install plugin (extreme compatibility version)"""
    base_url = base_url.rstrip("/")
    plugin_unique_identifier = None

    if source == "marketplace":
        try:
            # 1. First check installed list
            installed = get_installed_plugins(base_url, session, timeout=timeout)
            for p in installed:
                p_id = str(p.get("plugin_id") or p.get("id") or "").lower()
                p_uid = str(p.get("plugin_unique_identifier") or p.get("latest_package_identifier") or "").lower()
                if plugin_id.lower() in p_id or plugin_id.lower() in p_uid or p_id in plugin_id.lower():
                    plugin_unique_identifier = p.get("plugin_unique_identifier") or p.get("latest_package_identifier")
                    if plugin_unique_identifier:
                        print(f"  ✓ Plugin already ready: {p_id} ({plugin_unique_identifier})")
                        return {"status": "already_installed", "plugin_unique_identifier": plugin_unique_identifier}

            # 2. Search official marketplace
            search_keywords = [plugin_id]
            if "/" in plugin_id: search_keywords.append(plugin_id.split("/")[-1])
            
            for kw in list(dict.fromkeys(search_keywords)):
                plugins = list_available_plugins(base_url, session, search=kw, timeout=timeout)
                for p in plugins:
                    p_id = str(p.get("plugin_id") or p.get("id") or "").lower()
                    p_uid = str(p.get("plugin_unique_identifier") or p.get("latest_package_identifier") or "").lower()
                    
                    if plugin_id.lower() == p_id or plugin_id.lower() in p_uid or p_id in plugin_id.lower():
                        plugin_unique_identifier = p.get("plugin_unique_identifier") or p.get("latest_package_identifier")
                        if plugin_unique_identifier:
                            print(f"  ✓ Found matching plugin: {p_id} ({plugin_unique_identifier})")
                            break
                if plugin_unique_identifier: break
        except Exception as e:
            print(f"  ! Error searching plugin marketplace: {str(e)}")

    # Final identifier validation
    if not plugin_unique_identifier:
        if "@" in plugin_id and ":" in plugin_id:
            plugin_unique_identifier = plugin_id
        else:
            raise ValueError(f"Missing plugin unique identifier: {plugin_id}")

    # Send installation request
    payload = {"plugin_unique_identifiers": [plugin_unique_identifier]}
    print(f"  Sending installation request: {plugin_unique_identifier}")
    resp = _probe_plugin_endpoint(base_url, session, "install", method="POST", json_data=payload, timeout=timeout)

    # Handle already installed status (1.11.x)
    if resp.status_code < 400:
        try:
            res_data = resp.json()
            if res_data.get("all_installed") is True:
                print(f"  ✓ Plugin already installed")
                return {"status": "already_installed", "plugin_unique_identifier": plugin_unique_identifier, "data": res_data}
            return res_data
        except: return {}

    # Error handling and fault tolerance
    error_msg = f"Installation failed ({resp.status_code})"
    is_already_installed = False
    try:
        error_detail = resp.json()
        error_msg += f": {error_detail}"
        if "already" in str(error_detail).lower() or "exists" in str(error_detail).lower() or resp.status_code == 409:
            is_already_installed = True
    except:
        if "already" in resp.text.lower() or "exists" in resp.text.lower():
            is_already_installed = True

    if is_already_installed:
        print(f"  ✓ Plugin already exists, skipping installation.")
        return {"status": "already_installed", "plugin_unique_identifier": plugin_unique_identifier}

    print(f"  ✗ {error_msg}")
    resp.raise_for_status()
    return resp.json()


def get_installed_plugins(
        base_url: str,
        session: requests.Session,
        timeout: int = 30,
) -> List[Dict[str, Any]]:
    """Get installed plugin list"""
    try:
        resp = _probe_plugin_endpoint(base_url, session, "installed", params={"page": 1, "page_size": 100}, timeout=timeout)
        data = resp.json()
        
        plugins = []
        seen_objs = set()
        def find_plugins(obj, d=0):
            if d > 5 or id(obj) in seen_objs: return
            seen_objs.add(id(obj))
            if isinstance(obj, list):
                for i in obj: find_plugins(i, d+1)
            elif isinstance(obj, dict):
                p_id, p_uid = obj.get("plugin_id") or obj.get("id"), obj.get("plugin_unique_identifier") or obj.get("latest_package_identifier")
                if p_id and p_uid:
                    obj["plugin_id"], obj["plugin_unique_identifier"] = p_id, p_uid
                    plugins.append(obj)
                else:
                    for v in obj.values(): find_plugins(v, d+1)
        find_plugins(data)
        return plugins
    except: return []

# ==================== Part 5: One-click Integration Function ====================

def install_configure_and_add_models(
        base_url: str,
        session: requests.Session,
        plugin_id: str,
        credential_schema: Dict[str, Any],
        provider_name: Optional[str] = None,
        version: Optional[str] = None,
        poll_interval: int = 3,
        max_wait: int = 60,
        timeout: int = 60,
) -> Dict[str, Any]:
    """One-click integration: Install plugin → Wait for ready → Configure provider"""
    if provider_name is None:
        if "/" in plugin_id:
            parts = plugin_id.split("/")
            provider_name = f"{plugin_id}/{parts[-1]}"
        else:
            provider_name = f"{plugin_id}/{plugin_id}"

    print(f"\n{'=' * 20} Starting model integration flow: {provider_name} {'=' * 20}")

    # 1. Install plugin
    print(f"[1/3] Installing plugin: {plugin_id} ...")
    install_result = install_plugin(base_url, session, plugin_id, version, timeout=timeout)

    # 2. Wait for plugin ready
    installed_ok = False
    if isinstance(install_result, dict) and install_result.get("status") == "already_installed":
        print(f"  ✓ Plugin already installed previously, skipping readiness wait.")
        installed_ok = True
    else:
        print(f"[2/3] Waiting for plugin ready (max wait {max_wait}s)...")
        elapsed = 0
        while elapsed < max_wait:
            try:
                installed = get_installed_plugins(base_url, session, timeout=timeout)
                for p in installed:
                    p_id = p.get("plugin_id", "")
                    p_uid = p.get("plugin_unique_identifier") or p.get("latest_package_identifier") or ""
                    status = p.get("status", p.get("installation_status", ""))
                    if (plugin_id in str(p_id) or plugin_id in str(p_uid)) and status in ("installed", "active", "success"):
                        installed_ok = True
                        break
                if installed_ok:
                    print(f"  ✓ Plugin ready (took {elapsed}s)")
                    break
            except: pass
            time.sleep(poll_interval)
            elapsed += poll_interval

    # 3. Configure provider credentials
    print(f"[3/3] Configuring provider credentials: {provider_name} ...")
    add_model_provider(base_url, session, provider_name, credential_schema, timeout=timeout)
    return {"provider_name": provider_name}
