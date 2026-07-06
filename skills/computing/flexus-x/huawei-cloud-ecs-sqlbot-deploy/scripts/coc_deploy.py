#!/usr/bin/env python3
"""
Huawei Cloud COC (Cloud Operations Center) Deployment Module for SQLBot
Supports script creation, execution, and status query on Huawei Cloud ECS instances.
"""

import json
import time
import uuid
import sys
import requests
from typing import Any, Optional, List, Dict
from urllib.parse import urlparse

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

# Constants
VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]

# SQLBot installation script template
# __PUBLIC_IP__ will be replaced with actual public IP from server creation
SQLBOT_INSTALL_SCRIPT = '''#!/bin/bash
# SQLBot Installation Script for Huawei Cloud ECS
# Auto-download and install SQLBot from OBS

OBS_SCRIPT_URL="https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/quickly_implement_intelligent_data_queries_based_on_sqlbot/userdata/install-sqlbot.sh"

echo "=== SQLBot Deployment via COC ==="
echo "Starting SQLBot installation..."

# Download installation script
echo "Downloading install script from OBS..."
if ! wget -O /tmp/install-sqlbot.sh "$OBS_SCRIPT_URL" 2>/dev/null; then
    echo "wget failed, trying curl..."
    curl -o /tmp/install-sqlbot.sh "$OBS_SCRIPT_URL"
fi

if [ ! -f /tmp/install-sqlbot.sh ]; then
    echo "ERROR: Failed to download installation script"
    exit 1
fi

chmod +x /tmp/install-sqlbot.sh

# Public IP from server creation (passed from deploy script)
PUBLIC_IP="__PUBLIC_IP__"
echo "Public IP: $PUBLIC_IP"

# Execute installation script
echo "Executing SQLBot installation script..."
bash /tmp/install-sqlbot.sh "$PUBLIC_IP"

if [ $? -eq 0 ]; then
    echo "=== SQLBot Installation Completed Successfully ==="
    echo "SQLBot URL: http://$PUBLIC_IP:8000"
else
    echo "=== SQLBot Installation Failed ==="
    exit 1
fi
'''


def _error(code: str, message: str) -> dict[str, Any]:
    """Create error response"""
    return {
        "ok": False,
        "text": message,
        "result": None,
        "error": {"code": code, "message": message}
    }


def get_valid_coc_regions() -> list[str]:
    """Dynamically get COC service supported regions from SDK"""
    return list(CocRegion.static_fields.keys())


def get_client(ak: str, sk: str, security_token: str, region: str = None) -> CocClient:
    """Create and return COC client
    
    Args:
        ak: Huawei Cloud temporary AK
        sk: Huawei Cloud temporary SK
        security_token: Security token for temporary credentials
        region: COC region (optional, default cn-north-4)
    """
    if not region:
        region = "cn-north-4"
    
    # Validate region
    valid_regions = get_valid_coc_regions()
    if region not in valid_regions:
        raise ValueError(f"COC region must be one of {valid_regions}")
    
    credentials = GlobalCredentials(ak, sk)
    if security_token:
        credentials = credentials.with_security_token(security_token)
    
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
    security_token: str = None,
    region: str = None,
    risk_level: str = "LOW",
    version: str = "1.0.0",
    script_params: Optional[List[Dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Create custom script in COC (Cloud Operations Center)
    
    Reference: https://support.huaweicloud.com/api-coc/CreateScripts.html
    
    Parameters:
        name: Script name (required, 1-128 characters)
        script_type: Script type (required, SHELL/PYTHON/BAT)
        content: Script content (required)
        description: Script description (required, 1-512 characters)
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials
        region: COC region (default cn-north-4)
        risk_level: Risk level (LOW/MEDIUM/HIGH, default LOW)
        version: Script version (default 1.0.0)
        script_params: List of script parameters (optional)
    
    Returns:
        dict with ok, text, result (containing script_uuid), and error fields
    """
    # Parameter validation according to API documentation
    if not name:
        return _error("INPUT_ERROR", "name is required")
    if len(name) > 128:
        return _error("INPUT_ERROR", "name must be 1-128 characters")
    if script_type not in VALID_SCRIPT_TYPES:
        return _error("INPUT_ERROR", f"script_type must be one of {VALID_SCRIPT_TYPES}")
    if not content:
        return _error("INPUT_ERROR", "content is required")
    if not description:
        return _error("INPUT_ERROR", "description is required")
    if len(description) > 512:
        return _error("INPUT_ERROR", "description must be 1-512 characters")
    if risk_level not in VALID_RISK_LEVELS:
        return _error("INPUT_ERROR", f"risk_level must be one of {VALID_RISK_LEVELS}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        print(f"  Creating COC script: {name}")
        sys.stdout.flush()
        
        # Build request according to API specification
        request = CreateScriptRequest()
        
        # Build properties model
        properties = ScriptPropertiesModel(
            risk_level=risk_level,
            version=version
        )
        
        # Build script parameters if provided
        params_list = []
        if script_params and isinstance(script_params, list):
            for param in script_params:
                if isinstance(param, dict):
                    params_list.append(param)
        
        # Build request body
        add_script_model = AddScriptModel(
            name=name,
            type=script_type,
            content=content,
            description=description,
            properties=properties
        )
        
        # Add script parameters if any
        if params_list:
            add_script_model.params = params_list
        
        request.body = add_script_model

        # Execute API call
        response = client.create_script(request)
        
        # Parse response according to API documentation
        script_uuid = ""
        if hasattr(response, 'data') and response.data is not None:
            script_uuid = response.data
        elif hasattr(response, 'script_uuid'):
            script_uuid = response.script_uuid
        else:
            script_uuid = str(response)

        print(f"  ✓ COC script created successfully: {script_uuid}")
        sys.stdout.flush()
        
        return {
            "ok": True,
            "text": f"Script created successfully: {script_uuid}",
            "result": {"script_uuid": script_uuid},
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
    security_token: str = None,
    region: str = None,
    rotation_strategy: str = "CONTINUE",
    wait_for_completion: bool = False,
) -> dict[str, Any]:
    """
    Execute custom script on target instances via COC (Cloud Operations Center)
    
    Reference: https://support.huaweicloud.com/api-coc/ExecuteScripts.html
    
    Parameters:
        script_uuid: Script UUID to execute (required)
        execute_user: User to execute script (e.g. root, required)
        timeout: Execution timeout in seconds (5 < timeout < 1800, required)
        success_rate: Success rate (0-100, supports one decimal place, required)
        target_instances: List of target instances, each containing:
            - resource_id: Instance ID (required)
            - region_id: Server region (required)
            - provider: Resource provider (default "HUAWEI" for ECS)
            - type: Resource type (default "ECS" for ECS)
        ak: Huawei Cloud AK (required)
        sk: Huawei Cloud SK (required)
        security_token: Security token for temporary credentials (optional)
        region: COC region (optional, default cn-north-4)
        rotation_strategy: Rotation strategy (CONTINUE/STOP), default CONTINUE
        wait_for_completion: Whether to wait for completion and get logs, default False

    Returns:
        {
            "ok": True,
            "text": "Script execution successful: SCT2023083109562601af694bf",
            "result": { 
                "execute_uuid": "SCT2023083109562601af694bf",
                "status": "FINISHED",
                "output": "Script execution output log...",
                "error": "Error message (if any)"
            },
            "error": None
        }
    """
    # Parameter validation according to API documentation
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
    
    # Validate each target instance
    for idx, instance_info in enumerate(target_instances):
        if not instance_info.get("resource_id"):
            return _error("INPUT_ERROR", f"resource_id is required for instance {idx}")
        if not instance_info.get("region_id"):
            return _error("INPUT_ERROR", f"region_id is required for instance {idx}")
    
    if rotation_strategy not in VALID_ROTATION_STRATEGIES:
        return _error("INPUT_ERROR", f"rotation_strategy must be one of {VALID_ROTATION_STRATEGIES}")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        # Build request according to API specification
        request = ExecuteScriptRequest()
        request.script_uuid = script_uuid

        # Build execution parameters
        execute_param = ScriptExecuteParam(
            timeout=timeout,
            success_rate=success_rate,
            execute_user=execute_user
        )

        # Build target instances list
        listTargetInstancesExecuteBatches = []
        for instance_info in target_instances:
            instance_kwargs = {
                "resource_id": instance_info.get("resource_id", ""),
                "region_id": instance_info.get("region_id", "cn-north-4")
            }
            
            provider = instance_info.get("provider", "HUAWEI")
            instance_type = instance_info.get("type", "ECS")
            if provider:
                instance_kwargs["provider"] = provider
            if instance_type:
                instance_kwargs["type"] = instance_type
            
            instance = ExecuteResourceInstance(**instance_kwargs)
            listTargetInstancesExecuteBatches.append(instance)

        # Build execution batches
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

        # Execute script API call
        print(f"\n✓ Submitting COC script execution request")
        sys.stdout.flush()
        print(f"  Script UUID: {script_uuid}")
        sys.stdout.flush()
        print(f"  Target instances: {len(target_instances)}")
        sys.stdout.flush()
        
        response = client.execute_script(request)
        
        # Parse response
        execute_uuid = ""
        if hasattr(response, 'data') and response.data is not None:
            execute_uuid = response.data
        elif hasattr(response, 'execute_uuid'):
            execute_uuid = response.execute_uuid
        else:
            execute_uuid = str(response)

        print(f"  Execution ID: {execute_uuid}")
        sys.stdout.flush()

        if not wait_for_completion:
            return {
                "ok": True,
                "text": f"Script execution started: {execute_uuid}",
                "result": {"execute_uuid": execute_uuid},
                "error": None,
            }

        print(f"  Waiting for COC script execution to complete...")
        sys.stdout.flush()

        max_wait_time = timeout + 60
        wait_interval = 10
        elapsed_time = 0
        last_status = ""
        
        while elapsed_time < max_wait_time:
            query_result = coc_query_execution(execute_uuid, ak, sk, security_token, region)
            
            data = query_result.get("data", {})
            if not data:
                error_msg = query_result.get("error", {}).get("message", "query failed")
                print(f"  Failed to query status: {error_msg}, retrying...")
                sys.stdout.flush()
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue
            
            # Extract status and output from response
            status = ""
            output = ""
            error = ""
            
            instances = data.get("execute_instances", [])
            if instances:
                status = instances[0].get("status", "")
                output = instances[0].get("message", "")
                if status == "ABNORMAL":
                    error = output
            else:
                status = data.get("status", "")
                output = data.get("message", "")
                if status == "ABNORMAL":
                    error = output
            
            # Output progress when status changes
            if status != last_status:
                last_status = status
                print(f"  Execution status: {status}")
                sys.stdout.flush()
            
            # Output heartbeat every 30 seconds to keep user informed
            if elapsed_time % 30 == 0:
                print(f"  Waiting... ({elapsed_time}/{max_wait_time} seconds)")
                sys.stdout.flush()
            
            # Check if execution completed
            if status in ["SUCCESS", "FAILED", "TIMEOUT", "CANCELLED", "FINISHED", "ABNORMAL"]:
                result_data = {
                    "execute_uuid": execute_uuid,
                    "status": status,
                    "output": output,
                    "error": error
                }
                
                if status == "FINISHED":
                    print(f"  Execution completed: SUCCESS")
                    sys.stdout.flush()
                    return {
                        "ok": True,
                        "text": f"Script execution successful: {execute_uuid}",
                        "result": result_data,
                        "error": None,
                    }
                else:
                    print(f"  Execution completed: {status}")
                    sys.stdout.flush()
                    error_msg = f"Script execution failed, status: {status}"
                    if error:
                        error_msg += f", error: {error}"
                    if output:
                        error_msg += f", output: {output}"
                    return {
                        "ok": False,
                        "text": error_msg,
                        "result": result_data,
                        "error": {"code": "EXECUTE_FAILED", "message": error_msg}
                    }
            
            time.sleep(wait_interval)
            elapsed_time += wait_interval

        print(f"  COC execution timeout (waiting exceeded {max_wait_time} seconds)")
        sys.stdout.flush()
        return {
            "ok": False,
            "text": f"Script execution timeout (waiting exceeded {max_wait_time} seconds)",
            "result": {"execute_uuid": execute_uuid},
            "error": {"code": "TIMEOUT", "message": "Script execution timeout"}
        }

    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def coc_query_execution(execute_uuid: str, ak: str = None, sk: str = None, security_token: str = None, region: str = None) -> dict[str, Any]:
    """
    Query script execution status by execute UUID.
    
    API: GET /v1/job/script/orders/{execute_uuid}/batches/1
    
    Parameters:
        execute_uuid: Execution UUID (format: SCT2023083109562601af694bf)
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials
        region: COC region (optional, default cn-north-4)
    """
    if not execute_uuid:
        return _error("INPUT_ERROR", "execute_uuid is required")
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required")

    batch_index = 1
    limit = 50
    if not region:
        region = "cn-north-4"

    try:
        client = get_client(ak, sk, security_token, region)
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import GetScriptJobBatchRequest
        
        request = GetScriptJobBatchRequest()
        request.batch_index = batch_index
        request.execute_uuid = execute_uuid
        request.limit = limit
        
        response = client.get_script_job_batch(request)
        
        result_dict = {}
        if hasattr(response, 'data') and response.data is not None:
            result_dict["data"] = {
                "batch_index": response.data.batch_index,
                "total_instances": response.data.total_instances,
                "execute_instances": []
            }
            if hasattr(response.data, 'execute_instances') and response.data.execute_instances:
                for instance in response.data.execute_instances:
                    instance_dict = {
                        "id": getattr(instance, 'id', ''),
                        "cmd_uuid": getattr(instance, 'cmd_uuid', ''),
                        "status": getattr(instance, 'status', ''),
                        "message": getattr(instance, 'message', ''),
                        "gmt_created": getattr(instance, 'gmt_created', ''),
                        "gmt_finished": getattr(instance, 'gmt_finished', ''),
                        "execute_costs": getattr(instance, 'execute_costs', 0)
                    }
                    if hasattr(instance, 'target_instance') and instance.target_instance:
                        target = instance.target_instance
                        instance_dict["target_instance"] = {
                            "resource_id": target.resource_id,
                            "region_id": target.region_id,
                            "provider": target.provider,
                            "type": target.type
                        }
                    result_dict["data"]["execute_instances"].append(instance_dict)
        else:
            result_dict["data"] = {}
        
        return {"ok": True, "data": result_dict.get("data", {})}
        
    except exceptions.ClientRequestException as e:
        return _error("API_ERROR", f"{e.error_code}: {e.error_msg}")
    except Exception as e:
        return _error("UNKNOWN_ERROR", str(e))


def check_uniagent_status(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None,
    provider: str = "ecs",
    resource_type: str = "cloudservers"
) -> dict[str, Any]:
    """
    Check UniAgent status for an ECS instance via COC API
    
    Parameters:
        resource_id: ECS Instance resource ID
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (optional)
        provider: Resource provider (default "ecs")
        resource_type: Resource type (default "cloudservers")
    
    Returns:
        {
            "ok": True,
            "status": "ONLINE" | "OFFLINE" | "UNKNOWN",
            "agent_id": "...",
            "agent_state": "ONLINE" | "OFFLINE" | ...,
            "error": None
        }
    """
    if not resource_id:
        return {"ok": False, "status": "UNKNOWN", "error": "resource_id is required"}
    if not ak or not sk:
        return {"ok": False, "status": "UNKNOWN", "error": "ak and sk are required"}
    
    try:
        from huaweicloudsdkcore.signer.signer import Signer
        from huaweicloudsdkcore.sdk_request import SdkRequest
        from urllib.parse import urlparse
        
        class _Credentials:
            def __init__(self, ak, sk, security_token=None):
                self.ak = ak
                self.sk = sk
                self.security_token = security_token
        
        credentials = _Credentials(ak, sk, security_token)
        signer = Signer(credentials)
        
        endpoint = "https://coc.myhuaweicloud.com/v1/resources"
        
        query_params = {
            "resource_id_list": resource_id,
            "limit": "100",
            "provider": provider,
            "type": resource_type
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
        
        resp = requests.request("GET", url_with_params, headers=headers, verify=True, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and data["data"]:
                instance = data["data"][0]
                agent_state = instance.get("agent_state", "UNKNOWN")
                agent_id = instance.get("agent_id", "")
                
                return {
                    "ok": True,
                    "status": agent_state,
                    "agent_id": agent_id,
                    "agent_state": agent_state,
                    "error": None
                }
            else:
                return {"ok": False, "status": "UNKNOWN", "error": "Instance not found in COC resources"}
        else:
            return {"ok": False, "status": "UNKNOWN", "error": f"API error: {resp.status_code}"}
    
    except Exception as e:
        return {"ok": False, "status": "UNKNOWN", "error": str(e)}


def wait_for_uniagent_online(
    resource_id: str,
    ak: str,
    sk: str,
    security_token: str = None,
    max_wait_seconds: int = 300,
    check_interval: int = 10
) -> dict[str, Any]:
    """
    Wait for UniAgent to come online
    
    Parameters:
        resource_id: ECS Instance resource ID
        ak: Huawei Cloud AK
        sk: Huawei Cloud SK
        security_token: Security token for temporary credentials (optional)
        max_wait_seconds: Maximum wait time in seconds (default 300)
        check_interval: Check interval in seconds (default 10)
    
    Returns:
        {
            "ok": True,
            "status": "ONLINE",
            "elapsed_seconds": ...,
            "error": None
        }
    """
    print(f"  ⏳ Waiting for UniAgent to come online...")
    sys.stdout.flush()
    
    elapsed = 0
    while elapsed < max_wait_seconds:
        result = check_uniagent_status(resource_id, ak, sk, security_token)
        status = result.get("status", "UNKNOWN")
        
        if status == "ONLINE":
            print(f"  ✅ UniAgent is ONLINE (elapsed: {elapsed}s)")
            sys.stdout.flush()
            return {
                "ok": True,
                "status": "ONLINE",
                "elapsed_seconds": elapsed,
                "error": None
            }
        
        print(f"  ⏳ UniAgent status: {status}, waiting... ({elapsed}/{max_wait_seconds}s)")
        sys.stdout.flush()
        time.sleep(check_interval)
        elapsed += check_interval
    
    print(f"  ❌ UniAgent not online after {max_wait_seconds}s")
    sys.stdout.flush()
    return {
        "ok": False,
        "status": "TIMEOUT",
        "elapsed_seconds": elapsed,
        "error": f"UniAgent not online after {max_wait_seconds} seconds"
    }


def deploy_sqlbot_via_coc(
    resource_id: str,
    region_id: str,
    public_ip: str = None,
    ak: str = None,
    sk: str = None,
    security_token: str = None,
    coc_region: str = None,
    timeout: int = 600,
    execute_user: str = "root"
) -> dict[str, Any]:
    """
    Deploy SQLBot on remote ECS instance via COC
    
    Parameters:
        resource_id: ECS Instance resource ID
        region_id: ECS Instance region
        public_ip: ECS Instance public IP address (from server creation result)
        ak: Huawei Cloud AK (can be temporary AK)
        sk: Huawei Cloud SK (can be temporary SK)
        security_token: Security token for temporary credentials
        coc_region: COC region (optional, default cn-north-4)
        timeout: Execution timeout in seconds, default 600
        execute_user: Execute user, default root
    
    Returns:
        Deployment result dictionary
    """
    if not ak or not sk:
        return _error("CONFIG_ERROR", "ak and sk are required parameters")
    
    import time
    
    # Create installation script with dynamic public IP
    script_content = SQLBOT_INSTALL_SCRIPT
    if public_ip:
        script_content = SQLBOT_INSTALL_SCRIPT.replace("__PUBLIC_IP__", public_ip)
    
    create_result = create_script(
        name=f"SQLBot-Install-{int(time.time())}",
        script_type="SHELL",
        content=script_content,
        description="SQLBot one-click installation script",
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        risk_level="MEDIUM"
    )
    
    if not create_result.get("ok"):
        return create_result
    
    script_uuid = create_result.get("result", {}).get("script_uuid")
    
    if not script_uuid:
        result_data = create_result.get("result")
        if hasattr(result_data, 'data'):
            script_uuid = result_data.data
    
    target_instances = [{
        "resource_id": resource_id,
        "region_id": region_id,
        "provider": "HUAWEI",
        "type": "ECS"
    }]
    
    # Execute script
    execute_result = execute_script(
        script_uuid=script_uuid,
        execute_user=execute_user,
        timeout=timeout,
        success_rate=100.0,
        target_instances=target_instances,
        ak=ak,
        sk=sk,
        security_token=security_token,
        region=coc_region,
        rotation_strategy="CONTINUE",
        wait_for_completion=True
    )
    
    return execute_result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="COC SQLBot Deployment Test")
    parser.add_argument("--ak", required=True, help="Huawei Cloud AK")
    parser.add_argument("--sk", required=True, help="Huawei Cloud SK")
    parser.add_argument("--security-token", help="Security Token")
    parser.add_argument("--resource-id", required=True, help="ECS Instance ID")
    parser.add_argument("--region-id", default="cn-north-4", help="ECS Region")
    parser.add_argument("--coc-region", default="cn-north-4", help="COC Region")
    
    args = parser.parse_args()
    
    print("Testing COC SQLBot deployment...")
    result = deploy_sqlbot_via_coc(
        resource_id=args.resource_id,
        region_id=args.region_id,
        ak=args.ak,
        sk=args.sk,
        security_token=args.security_token,
        coc_region=args.coc_region
    )
    
    print("\nDeployment Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))