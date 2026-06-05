#!/usr/bin/env python3
"""
Utility Functions for JiuwenSwarm Deployment
Shared helper functions for Huawei Cloud COC operations, credential management,
status querying, and deployment workflow support.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Constant definitions
VALID_ROTATION_STRATEGIES = ["CONTINUE", "STOP"]
VALID_SCRIPT_TYPES = ["SHELL", "PYTHON", "BAT"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]

def _error(code: str, message: str) -> dict[str, Any]:
    """Error response formatting function (referenced from OpenClaw implementation)"""
    return {
        "ok": False,
        "text": f"Error: {message}",
        "result": None,
        "error": {"code": code, "message": message}
    }

def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    if not file_path.exists():
        log.warning(f"File not found: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to read JSON file {file_path}: {e}")
        return None

def save_json_file(file_path: Path, data: Dict[str, Any]) -> bool:
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        log.error(f"Failed to save JSON file {file_path}: {e}")
        return False

def get_huaweicloud_credentials():
    """
    Get Huawei Cloud credentials from environment variables.
    Supports both permanent credentials and temporary security credentials (STS token).
    
    Permanent credentials: HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK, HUAWEICLOUD_REGION
    Temporary credentials: Add HUAWEICLOUD_SDK_SECURITY_TOKEN to permanent credentials
    
    
    Returns:
        tuple: (AK, SK, REGION, SECURITY_TOKEN)
               SECURITY_TOKEN is None for permanent credentials
    """
    AK = os.getenv("HUAWEICLOUD_SDK_AK")
    SK = os.getenv("HUAWEICLOUD_SDK_SK")
    SECURITY_TOKEN = os.getenv("HUAWEICLOUD_SDK_SECURITY_TOKEN")
    REGION = os.getenv("HUAWEICLOUD_REGION", "cn-north-4")

    if not AK or not SK:
        raise ValueError("Please set environment variables HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK")

    return AK, SK, REGION, SECURITY_TOKEN

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_success(message: str):
    print(f"[SUCCESS] {message}")

def print_error(message: str):
    print(f"[ERROR] {message}")

def print_warning(message: str):
    print(f"[WARNING] {message}")

def print_info(message: str):
    print(f"[INFO] {message}")

# COC related utility functions
def get_coc_client():
    """Get COC client with support for Huawei Cloud credentials (permanent and temporary)"""
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
    from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
    from huaweicloudsdkcoc.v1 import CocClient
    from huaweicloudsdkcoc.v1.model.create_script_request import CreateScriptRequest
    from huaweicloudsdkcoc.v1.model.script_detail_model import ScriptDetailModel
    from huaweicloudsdkcoc.v1.model.execute_script_request import ExecuteScriptRequest
    from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
    from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
    from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
    from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
    from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
    from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
    
    AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    
    # Use BasicCredentials with security token if available (temporary credentials)
    # Otherwise use GlobalCredentials for permanent credentials
    if SECURITY_TOKEN:
        log.info(f"Using temporary security credentials (STS token)")
        credentials = BasicCredentials(AK, SK).with_security_token(SECURITY_TOKEN)
    else:
        credentials = GlobalCredentials(AK, SK)
    
    return CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(REGION)) \
        .build()

def coc_query_execution(execute_uuid: str) -> dict:
    """
    Query script execution status - using Huawei Cloud COC GetScriptJobInfo API
    
    Parameters:
        execute_uuid: Execution UUID (format: SCT20250101000000000000000)
    
    Returns:
        {
            "ok": True/False,
            "text": "Status description",
            "result": {
                "status": "Execution status",
                "execute_uuid": "Execution UUID",
                "script_name": "Script name",
                "script_content": "Script content",
                "execute_user": "Execute user",
                "create_time": "Create time",
                "finish_time": "Finish time",
                "execute_costs": "Execution duration(ms)",
                "creator": "Creator",
                "properties": {...},
                "output": "Script output",
                "error": "Error message",
                "total_count": 1,
                "success_count": 1,
                "fail_count": 0,
                "processing_count": 0,
                "error_details": ["Error detail 1", "Error detail 2"],
                "instance_details": [
                    {
                        "instance_id": "instance-example-001",
                        "status": "SUCCESS",
                        "output": "Instance output",
                        "error": "Instance error"
                    }
                ]
            },
            "error": None
        }
    """
    if not execute_uuid:
        return _error("INPUT_ERROR", "execute_uuid is required")

    try:
        client = get_coc_client()
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
        from huaweicloudsdkcoc.v1 import GetScriptJobInfoRequest
        
        request = GetScriptJobInfoRequest()
        request.execute_uuid = execute_uuid
        
        response = client.get_script_job_info(request)
        
        # Parse API response
        result_dict = {}
        if hasattr(response, 'data'):
            data = response.data
            
            # Extract basic fields
            if hasattr(data, 'execute_uuid'):
                result_dict['execute_uuid'] = data.execute_uuid
            if hasattr(data, 'status'):
                result_dict['status'] = data.status
            if hasattr(data, 'creator'):
                result_dict['creator'] = data.creator
            if hasattr(data, 'gmt_created'):
                result_dict['create_time'] = data.gmt_created
            if hasattr(data, 'gmt_finished'):
                result_dict['finish_time'] = data.gmt_finished
            if hasattr(data, 'execute_costs'):
                result_dict['execute_costs'] = data.execute_costs
                # Add seconds conversion
                result_dict['execute_costs_seconds'] = data.execute_costs / 1000 if data.execute_costs else 0
            if hasattr(data, 'script_content'):
                result_dict['script_content'] = data.script_content
            
            # Extract information from properties
            if hasattr(data, 'properties'):
                props = data.properties
                if hasattr(props, 'script_name'):
                    result_dict['script_name'] = props.script_name
                if hasattr(props, 'script_uuid'):
                    result_dict['script_uuid'] = props.script_uuid
                if hasattr(props, 'script_source'):
                    result_dict['script_source'] = props.script_source
                if hasattr(props, 'current_execute_batch_index'):
                    result_dict['current_execute_batch_index'] = props.current_execute_batch_index
                
                # Extract information from execute_param
                if hasattr(props, 'execute_param'):
                    execute_param = props.execute_param
                    if hasattr(execute_param, 'execute_user'):
                        result_dict['execute_user'] = execute_param.execute_user
                    if hasattr(execute_param, 'timeout'):
                        result_dict['timeout'] = execute_param.timeout
                    if hasattr(execute_param, 'success_rate'):
                        result_dict['success_rate'] = execute_param.success_rate
                    if hasattr(execute_param, 'resourceful'):
                        result_dict['resourceful'] = execute_param.resourceful
                
                # Save the entire properties object for later parsing
                result_dict['properties'] = props
            
            # Set default values
            result_dict.setdefault('total_count', 1)
            result_dict.setdefault('success_count', 0)
            result_dict.setdefault('fail_count', 0)
            result_dict.setdefault('processing_count', 0)
            
            # Set success/failure counts based on status
            if result_dict.get('status') == 'FINISHED':
                result_dict['success_count'] = 1
                result_dict['total_count'] = 1
                result_dict['fail_count'] = 0
                result_dict['processing_count'] = 0
            elif result_dict.get('status') in ['FAILED', 'ABNORMAL', 'TIMEOUT', 'CANCELED']:
                result_dict['success_count'] = 0
                result_dict['total_count'] = 1
                result_dict['fail_count'] = 1
                result_dict['processing_count'] = 0
            elif result_dict.get('status') in ['PROCESSING', 'RUNNING', 'PENDING']:
                result_dict['success_count'] = 0
                result_dict['total_count'] = 1
                result_dict['fail_count'] = 0
                result_dict['processing_count'] = 1
            
            # Set default instance details
            result_dict['instance_details'] = []
            
            return {
                "ok": True,
                "text": "Execution status query successful",
                "result": result_dict,
                "error": None,
            }
        else:
            return _error("API_ERROR", "API response does not contain data field")

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)


def get_script_job_status(client, execute_uuid):
    """Get script job status (maintain backward compatibility)"""
    result = coc_query_execution(execute_uuid)
    if result.get("ok"):
        return result.get("result")
    return None


def get_script_job_detail(client, execute_uuid):
    """Get script job detail (maintain backward compatibility)"""
    result = coc_query_execution(execute_uuid)
    if result.get("ok"):
        return result.get("result")
    return None

def wait_for_execution_completion(client, execute_uuid, timeout=1800, interval=60, max_retries=3):
    """Wait for script execution completion (referenced from OpenClaw implementation)"""
    import time
    from datetime import datetime
    
    print_info(f"Waiting for script execution to complete...")
    print_info(f"Timeout: {timeout}s ({timeout/60:.0f} minutes), Polling Interval: {interval}s")
    print_info(f"Max Retries: {max_retries}")
    print("="*60)

    start_time = time.time()
    retry_count = 0
    last_status = None
    last_progress_time = time.time()
    progress_interval = 30  # Display detailed progress every 30 seconds
    status_retry_count = 0  # Retry count for status fetch failures
    max_status_retries = 5  # Max retries for status fetch failures

    # Status mapping - based on Huawei Cloud COC GetScriptJobInfo API
    STATUS_MAP = {
        'PROCESSING': 'Processing',
        'RUNNING': 'Processing',
        'FINISHED': 'Completed',
        'COMPLETED': 'Completed',
        'ABNORMAL': 'Abnormal',
        'FAILED': 'Failed',
        'TIMEOUT': 'Timeout',
        'SUCCESS': 'Success',
        'SUCCEEDED': 'Success',
        'CANCELED': 'Canceled',
        'PENDING': 'Pending',
        'PAUSED': 'Paused',
        'STOPPED': 'Stopped',
        'UNKNOWN': 'Unknown'
    }

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        remaining = timeout - elapsed
        remaining_minutes = remaining // 60
        
        # 计算进度百分比
        progress_percent = min(100, int((elapsed / timeout) * 100))
        
        # 创建进度条
        bar_length = 30
        filled_length = int(bar_length * elapsed // timeout)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Query status using the new coc_query_execution function
        query_result = coc_query_execution(execute_uuid)
        
        # Check if query_result is None
        if query_result is None:
            status_retry_count += 1
            if status_retry_count >= max_status_retries:
                print_error(f"Failed to get task status {max_status_retries} consecutive times")
                job_info = None
            else:
                print_warning(f"Failed to get task status ({status_retry_count}/{max_status_retries}): Result is empty")
                job_info = None
        else:
            job_info = query_result.get("result") if query_result.get("ok") else None
            
            if not job_info:
                status_retry_count += 1
                if status_retry_count >= max_status_retries:
                    print_error(f"Failed to get task status {max_status_retries} consecutive times")
                    job_info = None
                else:
                    # Safely get error information
                    error_info = query_result.get("error")
                    if error_info is None:
                        error_msg = "Unknown error"
                    elif isinstance(error_info, dict):
                        error_msg = error_info.get("message", "Unknown error")
                    else:
                        error_msg = str(error_info)
                    print_warning(f"Failed to get task status ({status_retry_count}/{max_status_retries}): {error_msg}")
                    job_info = None
            else:
                status_retry_count = 0  # Reset status fetch failure count

        if job_info:
            status = job_info.get('status', 'UNKNOWN')
            status_display = STATUS_MAP.get(status, status)
            
            # Display detailed information when status changes
            if status != last_status:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Status: {status} ({status_display})")
                
                if status in ['PROCESSING', 'RUNNING']:
                    print_info("Script is executing...")
                    # Display script name
                    if job_info.get('script_name'):
                        print_info(f"Executing script: {job_info['script_name']}")
                
                elif status == 'FINISHED':
                    print_success("Script execution completed successfully!")
                    print_info("="*40)
                    print_info(f"Execution UUID: {execute_uuid}")
                    print_info(f"Script Name: {job_info.get('script_name', 'N/A')}")
                    print_info(f"Execute User: {job_info.get('execute_user', 'N/A')}")
                    print_info(f"Execution Result: Total {job_info.get('total_count', 1)} instances")
                    print_info(f"          Success: {job_info.get('success_count', 0)}")
                    print_info(f"          Failed: {job_info.get('fail_count', 0)}")
                    if job_info.get('create_time'):
                        print_info(f"Create Time: {job_info['create_time']}")
                    if job_info.get('finish_time'):
                        print_info(f"Finish Time: {job_info['finish_time']}")
                    print_info("="*40)
                    
                    # Display script output
                    if job_info.get('output'):
                        output = job_info['output']
                        print_info("\nScript Output:")
                        print(output[:2000] if len(output) > 2000 else output)
                    
                    # Display error message if any
                    if job_info.get('error'):
                        print_error(f"\nError Message: {job_info['error']}")
                    
                    return True, job_info
                
                # Also support SUCCESS status for backward compatibility
                elif status == 'SUCCESS':
                    print_success("Script execution completed successfully!")
                    print_info("="*40)
                    print_info(f"Execution UUID: {execute_uuid}")
                    print_info(f"Script Name: {job_info.get('script_name', 'N/A')}")
                    print_info(f"Execute User: {job_info.get('execute_user', 'N/A')}")
                    print_info(f"Execution Result: Total {job_info.get('total_count', 1)} instances")
                    print_info(f"          Success: {job_info.get('success_count', 0)}")
                    print_info(f"          Failed: {job_info.get('fail_count', 0)}")
                    if job_info.get('create_time'):
                        print_info(f"Create Time: {job_info['create_time']}")
                    if job_info.get('finish_time'):
                        print_info(f"Finish Time: {job_info['finish_time']}")
                    print_info("="*40)
                    
                    # Display script output
                    if job_info.get('output'):
                        output = job_info['output']
                        print_info("\nScript Output:")
                        print(output[:2000] if len(output) > 2000 else output)
                    
                    # Display error message if any
                    if job_info.get('error'):
                        print_error(f"\nError Message: {job_info['error']}")
                    
                    return True, job_info
                
                elif status in ['ABNORMAL', 'FAILED', 'TIMEOUT', 'CANCELED']:
                    print_error("Script execution failed!")
                    print_info("="*40)
                    print_info(f"Execution UUID: {execute_uuid}")
                    
                    # Get detailed error information
                    error_msg = job_info.get('error', job_info.get('error_message', 'Unknown error'))
                    print_error(f"Failure Reason: {error_msg}")
                    
                    # Display script output
                    if job_info.get('output'):
                        output = job_info['output']
                        print_info("\nScript Output:")
                        print(output[:2000] if len(output) > 2000 else output)
                    print_info("="*40)
                    
                    if retry_count < max_retries:
                        retry_count += 1
                        print_warning(f"\nRetry attempt {retry_count}/{max_retries}, retrying in 30 seconds...")
                        time.sleep(30)
                        return 'RETRY', None
                    else:
                        print_error(f"\nExceeded maximum retries ({max_retries})")
                        return False, job_info
                last_status = status
            
            # Display detailed progress information periodically
            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Status: {status} ({status_display})")
                print_info(f"Progress: {progress_percent}% |{bar}| {elapsed}s/{timeout}s")
                print_info(f"Remaining Time: {remaining_minutes} minutes {remaining%60} seconds")
                if job_info.get('total_count', 0) > 0:
                    success_rate = (job_info.get('success_count', 0) / job_info.get('total_count', 1)) * 100
                    print_info(f"Success Rate: {success_rate:.1f}% ({job_info.get('success_count', 0)}/{job_info.get('total_count', 0)})")
                last_progress_time = current_time

        else:
            # Display progress when job status cannot be retrieved
            if time.time() - last_progress_time >= progress_interval:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking job status...")
                print_info(f"Progress: {progress_percent}% |{bar}| {elapsed}s/{timeout}s")
                print_info(f"Remaining Time: {remaining_minutes} minutes {remaining%60} seconds")
                print_warning("Cannot retrieve job status temporarily, continuing to poll...")
                last_progress_time = time.time()

        # Display progress bar (updated every 5 seconds)
        if int(time.time()) % 5 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {progress_percent}% |{bar}| {elapsed}s/{timeout}s", end='\r')
        
        time.sleep(interval)

    print_error(f"\nScript execution timeout, exceeded {timeout}s ({timeout/60:.0f} minutes)")
    print_error(f"Elapsed Time: {int(time.time() - start_time)} seconds")

    if retry_count < max_retries:
        retry_count += 1
        print_warning(f"Retry attempt {retry_count}/{max_retries}...")
        time.sleep(10)
        return 'RETRY', None

    return False, None

def create_and_execute_script(client, name, script_content, description, target_instances, timeout=600):
    """Create and execute COC script"""
    try:
        from huaweicloudsdkcoc.v1.model.create_script_request import CreateScriptRequest
        from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
        from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
        from huaweicloudsdkcoc.v1.model.execute_script_request import ExecuteScriptRequest
        from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
        from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
        from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
        from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam
        
        print_info(f"Creating COC script: {name}")
        
        properties = ScriptPropertiesModel(risk_level="LOW", version="1.0.0")
        request = CreateScriptRequest()
        request.body = AddScriptModel(
            name=name,
            type="SHELL",
            content=script_content,
            description=description,
            properties=properties
        )

        response = client.create_script(request)
        script_uuid = response.data if hasattr(response, 'data') else str(response)
        print_info(f"Script created successfully: {script_uuid}")
        
        print_info("Executing script on target instances...")
        execute_request = ExecuteScriptRequest()
        execute_request.script_uuid = script_uuid

        execute_param = ScriptExecuteParam(timeout=timeout, success_rate=100, execute_user="root")

        list_target_instances = []
        for instance_info in target_instances:
            instance = ExecuteResourceInstance(
                resource_id=instance_info["resource_id"],
                region_id=instance_info["region_id"],
                provider=instance_info.get("provider", "HCSS"),
                type=instance_info.get("type", "L-INSTANCE")
            )
            list_target_instances.append(instance)

        execute_request.body = ScriptExecuteModel(
            execute_batches=[ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=list_target_instances,
                rotation_strategy="CONTINUE"
            )],
            execute_param=execute_param
        )

        execute_response = client.execute_script(execute_request)
        execute_uuid = execute_response.data if hasattr(execute_response, 'data') else str(execute_response)
        print_info(f"Execution submitted successfully: {execute_uuid}")
        return execute_uuid
        
    except Exception as e:
        print_error(f"COC script operation failed: {e}")
        return None

def submit_and_monitor_script(client, name, script_content, description, target_instances, timeout=600, max_retries=3):
    """Submit and monitor script execution"""
    execute_uuid = create_and_execute_script(client, name, script_content, description, target_instances, timeout)
    if not execute_uuid:
        return None
    
    # COC task creation may have delays, wait for task creation to complete
    print_info(f"Waiting for task creation...")
    import time
    for _ in range(3):
        result = coc_query_execution(execute_uuid)
        if result.get("ok") and result.get("result", {}).get("status"):
            print_info("Task created, starting execution status monitoring...")
            break
        print_info(f"Task not ready yet, waiting 2 seconds...")
        time.sleep(2)
    else:
        print_warning("Task creation may be delayed, continuing to monitor...")

    result, job_info = wait_for_execution_completion(client, execute_uuid, timeout, max_retries=max_retries)
    
    if result == 'RETRY':
        print_warning("Retrying script execution...")
        return submit_and_monitor_script(client, name, script_content, description, target_instances, timeout, max_retries)
    
    return result, job_info


def coc_create_script(
    name: str,
    script_type: str,
    content: str,
    description: str,
    risk_level: str = "LOW",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """
    Create custom script in COC (referenced from OpenClaw implementation)
    
    Parameters:
        name: Script name
        script_type: Script type (SHELL/PYTHON/BAT)
        content: Script content
        description: Script description
        risk_level: Risk level (LOW/MEDIUM/HIGH), default LOW
        version: Script version, default 1.0.0
    
    Returns:
        {
            "ok": True,
            "text": "Script created successfully: SC20250101000000000000000",
            "result": { Raw API result },
            "error": None
        }
    """
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
        client = get_coc_client()
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


def coc_query_execution_with_statistics(execute_uuid: str) -> dict[str, Any]:
    """
    Query script execution status - Enhanced version, supports Huawei Cloud COC GetScriptJobInfo API
    Provides more detailed statistics and instance-level execution details
    
    Parameters:
        execute_uuid: Execution UUID (format: SCT20250101000000000000000)
    
    Returns:
        {
            "ok": True,
            "text": "Execution status query successful",
            "result": {
                "status": "Execution status",
                "execute_uuid": "Execution UUID",
                "script_name": "Script name",
                "execute_user": "Execute user",
                "create_time": "Create time",
                "finish_time": "Finish time",
                "execute_costs": "Execution duration(ms)",
                "creator": "Creator",
                "properties": {...},
                "output": "Script output",
                "error": "Error message",
                "total_count": 1,
                "success_count": 1,
                "fail_count": 0,
                "processing_count": 0,
                "error_details": ["Error detail 1", "Error detail 2"],
                "instance_details": [
                    {
                        "instance_id": "instance-example-001",
                        "status": "SUCCESS",
                        "output": "Instance output",
                        "error": "Instance error"
                    }
                ]
            },
            "error": None
        }
    """
    # Directly call coc_query_execution since we've updated it to support the new API format
    result = coc_query_execution(execute_uuid)
    
    if not result.get("ok"):
        return result
    
    result_dict = result.get("result", {})
    
    # Add additional statistics (calculate if not provided by API)
    total_count = result_dict.get('total_count', 0)
    success_count = result_dict.get('success_count', 0)
    fail_count = result_dict.get('fail_count', 0)
    
    # Calculate processing instance count
    if total_count > 0:
        processing_count = max(0, total_count - success_count - fail_count)
        result_dict['processing_count'] = processing_count
    else:
        result_dict['processing_count'] = 0
    
    # Add error details list
    error_details = []
    if result_dict.get('error'):
        error_details.append(result_dict['error'])
    
    # Try to get error details from other fields
    if 'error_details' not in result_dict and error_details:
        result_dict['error_details'] = error_details
    
    # Add empty list if no instance details
    if 'instance_details' not in result_dict:
        result_dict['instance_details'] = []
    
    return {
            "ok": True,
            "text": "Execution status query successful (enhanced)",
            "result": result_dict,
            "error": None
        }


def coc_execute_script(
    script_uuid: str,
    execute_user: str,
    timeout: int,
    success_rate: float,
    target_instances: List[Dict[str, str]],
    rotation_strategy: str = "CONTINUE",
    wait_for_complete: bool = True,
) -> dict[str, Any]:
    """
    Execute custom script on target instances (referenced from OpenClaw implementation)
    
    Parameters:
        script_uuid: UUID of the script to execute
        execute_user: User to execute the script (e.g., root)
        timeout: Execution timeout in seconds (5 < timeout < 1800)
        success_rate: Success rate (supports one decimal place, e.g., 1 or 100)
        target_instances: List of target instances, each containing:
            - resource_id: Instance ID (required)
            - region_id: Region where server is located (required)
            - provider: Resource provider (not required for ECS, defaults to "HCSS" for L instances)
            - type: Resource type (not required for ECS, defaults to "L-INSTANCE" for L instances)
        rotation_strategy: Rotation strategy (CONTINUE/STOP), default CONTINUE
        wait_for_complete: Whether to wait for execution completion and get logs, default True
    
    Returns:
        {
            "ok": True,
            "text": "Script execution started: SCT20250101000000000000000",
            "result": { 
                "execute_uuid": "SCT20250101000000000000000",
                "status": "SUCCESS",
                "output": "Script execution output log...",
                "error": "Error message (if any)"
            },
            "error": None
        }
    """
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
        client = get_coc_client()
    except ValueError as e:
        return _error("CONFIG_ERROR", str(e))

    try:
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
        
        # 获取响应状态码，200或202代表任务提交成功
        status_code = response.status_code if hasattr(response, 'status_code') else 200
        
        # 检查状态码是否为200或202
        if status_code not in [200, 202]:
            return {
                "ok": False,
                "text": f"任务提交失败，响应状态码: {status_code}",
                "result": None,
                "error": {"code": "HTTP_ERROR", "message": f"HTTP状态码错误: {status_code}"},
                "status_code": status_code
            }
        
        execute_uuid = response.data if hasattr(response, 'data') else str(response)

        if not wait_for_complete:
            return {
                "ok": True,
                "text": f"脚本执行已启动: {execute_uuid}",
                "result": {"execute_uuid": execute_uuid},
                "error": None,
                "status_code": status_code
            }

        max_wait_time = timeout + 60
        wait_interval = 5
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            query_result = coc_query_execution(execute_uuid)
            if not query_result.get("ok"):
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue
            
            result_data = query_result.get("result", {})
            status = result_data.get("status", "")
            output = result_data.get("output", "")
            error = result_data.get("error", "")
            
            # 如果状态为空，表示任务可能还在创建中，继续等待
            if not status:
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue
            
            # According to Huawei Cloud COC GetScriptJobInfo API, FINISHED indicates task execution completion
            if status in ["FINISHED", "FAILED", "TIMEOUT", "CANCELED", "ABNORMAL"]:
                result_data = {
                    "execute_uuid": execute_uuid,
                    "status": status,
                    "output": output,
                    "error": error
                }
                
                if status == "FINISHED":
                    return {
                        "ok": True,
                        "text": f"脚本执行成功: {execute_uuid}",
                        "result": result_data,
                        "error": None,
                    }
                else:
                    error_msg = f"脚本执行失败，状态: {status}"
                    if error:
                        error_msg += f", 错误: {error}"
                    elif output:
                        error_msg += f", 输出: {output}"
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
            "text": f"脚本执行超时（等待超过 {max_wait_time} 秒）",
            "result": {"execute_uuid": execute_uuid},
            "error": {"code": "TIMEOUT", "message": "脚本执行超时"}
        }

    except Exception as e:
        error_msg = str(e)
        if "error_code" in error_msg.lower() or "error_msg" in error_msg.lower():
            return _error("API_ERROR", error_msg)
        return _error("UNKNOWN_ERROR", error_msg)
