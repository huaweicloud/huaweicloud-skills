#!/usr/bin/env python3
"""
JiuwenSwarm Service Deployment Script
Deploys JiuwenSwarm service to Huawei Cloud Flexus instances using COC (Cloud Operation Center).
Manages remote script execution, status monitoring, and deployment verification.
"""

import os
import sys
import json
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Import utility modules
sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils import (
        get_huaweicloud_credentials,
        get_coc_client,
        coc_query_execution,
        coc_create_script,
        coc_execute_script,
        print_header,
        print_success,
        print_error,
        print_warning,
        print_info
    )
except ImportError as e:
    log.error(f"Failed to import utility modules: {e}")
    log.error("Please ensure utils.py exists")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent.parent / "assets"
SCRIPT_PATH = SCRIPT_DIR / "deploy_script_template.sh"

EXECUTION_TIMEOUT = 1799  # Huawei Cloud COC API limit: must be less than 1800 seconds
EXECUTION_INTERVAL = 30
MAX_RETRIES = 3

# Global variables
AK = None
SK = None
REGION = None
SECURITY_TOKEN = None

def get_credentials():
    """Lazy credential retrieval"""
    global AK, SK, REGION, SECURITY_TOKEN
    if AK is None or SK is None:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    return AK, SK, REGION, SECURITY_TOKEN

def query_instance_by_ip(public_ip):
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
    from huaweicloudsdkrms.v1 import RmsClient
    from huaweicloudsdkrms.v1.region.rms_region import RmsRegion

    # Get credentials
    ak, sk, region, security_token = get_credentials()
    
    # RMS requires GlobalCredentials
    if security_token:
        credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
    else:
        credentials = GlobalCredentials(ak, sk)
    
    client = RmsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(RmsRegion.value_of(region)) \
        .build()

    from huaweicloudsdkrms.v1 import model
    request = model.ListAllResourcesRequest()
    request.region_id = region
    request.type = "hcss.l-instance"
    request.limit = 200

    response = client.list_all_resources(request)
    resources = response.resources if hasattr(response, 'resources') else []

    for r in resources:
        name = getattr(r, 'name', '') or getattr(r, 'resource_name', '')
        instance_id = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
        props = getattr(r, 'properties', None)

        ip = None
        ecs_instance_id = None

        if props:
            resources_list = props.get('resources', [])
            for res in resources_list:
                if isinstance(res, dict):
                    attrs = res.get('resource_attributes', [])
                    for attr in attrs:
                        if isinstance(attr, dict):
                            key = attr.get('key')
                            value = attr.get('value')
                            if key == 'public_ip_address':
                                ip = value
                            if key == 'associate_instance_id':
                                ecs_instance_id = value

        if ip == public_ip:
            return {
                'instance_name': name,
                'instance_id': instance_id,
                'ecs_instance_id': ecs_instance_id,
                'public_ip': ip,
                'region': region,
                'status': props.get('status') if props else 'UNKNOWN'
            }

    return None

def load_instance_info():
    info_file = Path(__file__).parent / "new_instance_info.json"
    if info_file.exists():
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_deploy_script():
    script_path = Path(__file__).parent.parent / "assets" / "deploy_script_template.sh"
    if script_path.exists():
        with open(script_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def execute_script_via_coc(client, instance_id, ecs_instance_id, script_content):
    from huaweicloudsdkcoc.v1.model.create_script_request import CreateScriptRequest
    from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
    from huaweicloudsdkcoc.v1.model.script_properties_model import ScriptPropertiesModel
    from huaweicloudsdkcoc.v1.model.execute_script_request import ExecuteScriptRequest
    from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
    from huaweicloudsdkcoc.v1.model.execute_instances_batch_info import ExecuteInstancesBatchInfo
    from huaweicloudsdkcoc.v1.model.execute_resource_instance import ExecuteResourceInstance
    from huaweicloudsdkcoc.v1.model.script_execute_param import ScriptExecuteParam

    try:
        log.info("Creating COC script...")
        properties = ScriptPropertiesModel(risk_level="LOW", version="1.0.0")
        script_name = f"jiuwenswarm_deploy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        create_request = CreateScriptRequest()
        create_request.body = AddScriptModel(
            name=script_name,
            type="SHELL",
            content=script_content,
            description="JiuwenSwarm deployment script",
            properties=properties
        )

        create_response = client.create_script(create_request)
        script_uuid = create_response.data if hasattr(create_response, 'data') else str(create_response)
        log.info(f"Script created successfully: {script_uuid}")

        log.info("Executing script on target instance...")
        execute_request = ExecuteScriptRequest()
        execute_request.script_uuid = script_uuid

        execute_param = ScriptExecuteParam(timeout=1799, success_rate=100, execute_user="root")

        # Get credentials
        _, _, region, _ = get_credentials()
        
        instance = ExecuteResourceInstance(
            resource_id=instance_id,
            region_id=region,
            provider="HCSS",
            type="L-INSTANCE"
        )

        execute_request.body = ScriptExecuteModel(
            execute_batches=[ExecuteInstancesBatchInfo(
                batch_index=1,
                target_instances=[instance],
                rotation_strategy="CONTINUE"
            )],
            execute_param=execute_param
        )

        execute_response = client.execute_script(execute_request)
        
        # Check response status code, 200 or 202 indicates successful task submission
        status_code = execute_response.status_code if hasattr(execute_response, 'status_code') else 200
        
        if status_code not in [200, 202]:
            log.error(f"Task submission failed, response status code: {status_code}")
            return None
        
        execute_uuid = execute_response.data if hasattr(execute_response, 'data') else str(execute_response)
        log.info(f"Execution submitted successfully: {execute_uuid}")

        return execute_response

    except Exception as e:
        log.error(f"COC script execution failed: {e}")
        return None

def get_script_job_status(client, execute_uuid):
    """Get script job status - using Huawei Cloud COC GetScriptJobInfo API"""
    result = coc_query_execution(execute_uuid)
    if result.get("ok"):
        job_info = result.get("result", {})
        
        # 确保状态字段存在
        status = job_info.get('status', 'UNKNOWN')
        job_info['status'] = status
        
        # 添加统计信息（如果API没有提供，则计算）
        total_count = job_info.get('total_count', 0)
        success_count = job_info.get('success_count', 0)
        fail_count = job_info.get('fail_count', 0)
        processing_count = job_info.get('processing_count', 0)
        
        # 如果API没有提供统计信息，根据状态计算
        if total_count == 0:
            if status == 'FINISHED':
                success_count = 1
                total_count = 1
                fail_count = 0
                processing_count = 0
            elif status in ['FAILED', 'ABNORMAL', 'TIMEOUT', 'CANCELED']:
                success_count = 0
                total_count = 1
                fail_count = 1
                processing_count = 0
            elif status in ['PROCESSING', 'RUNNING', 'PENDING']:
                success_count = 0
                total_count = 1
                fail_count = 0
                processing_count = 1
        
        # 计算进度
        if total_count > 0:
            progress = (success_count + fail_count) / total_count * 100
            job_info['progress'] = f"{progress:.1f}%"
            job_info['progress_percent'] = progress
            job_info['total_count'] = total_count
            job_info['success_count'] = success_count
            job_info['fail_count'] = fail_count
            job_info['processing_count'] = processing_count
        else:
            job_info['progress'] = "0%"
            job_info['progress_percent'] = 0
        
        return job_info
    else:
        # 查询失败，返回错误信息
        error_info = result.get("error", {})
        log.error(f"状态查询失败: {error_info.get('message', '未知错误')}")
        log.error(f"错误码: {error_info.get('code', 'UNKNOWN')}")
        return None

def deploy_jiuwenswarm(instance_id, ecs_instance_id, public_ip, wait=True, timeout=EXECUTION_TIMEOUT):
    print_header("Phase 4: COC Remote Deployment of JiuwenSwarm Service")

    client = get_coc_client()

    deploy_script = get_deploy_script()
    if not deploy_script:
        print_error("无法读取部署脚本模板")
        return None

    print_info(f"在实例 {public_ip} 上执行JiuwenSwarm部署脚本...")
    print_info(f"脚本类型: shell")
    print_info(f"超时时间: {timeout}秒 ({timeout/60:.0f}分钟)")

    result = execute_script_via_coc(client, instance_id, ecs_instance_id, deploy_script)

    if not result:
        print_error("部署任务提交失败")
        return None

    execute_uuid = None
    if hasattr(result, 'data'):
        execute_uuid = result.data

    print_info("部署任务已提交")
    print_info(f"Execute UUID: {execute_uuid}")

    result_file = Path(__file__).parent / "coc_deploy_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'execute_uuid': execute_uuid,
            'instance_id': instance_id,
            'public_ip': public_ip
        }, f, indent=2, ensure_ascii=False)
    print_info(f"部署结果已保存到: {result_file}")

    if wait:
        print_info(f"等待部署完成 (超时: {timeout}秒)...")
        print("=" * 60)

        start_time = time.time()
        retry_count = 0
        last_status = None

        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            job_info = get_script_job_status(client, execute_uuid)

            if job_info:
                status = job_info.get('status', 'UNKNOWN')
                # Update status mapping according to Huawei Cloud COC API documentation
                # Job status values: READY (Preparing), PROCESSING (Processing), ABNORMAL (Abnormal), CANCELED (Canceled), FINISHED (Completed)
                status_display = {
                    'READY': 'Preparing',
                    'PROCESSING': 'Processing',
                    'FINISHED': 'Completed',
                    'ABNORMAL': 'Abnormal',
                    'CANCELED': 'Canceled'
                }.get(status, status)

                if status != last_status:
                    print(f"\n[{elapsed}s] Status: {status} ({status_display})")
                    last_status = status

                # According to Huawei Cloud COC GetScriptJobInfo API, when status becomes FINISHED, CANCELED, or ABNORMAL, the script execution has ended
                # Only FINISHED indicates successful execution
                if status == 'FINISHED':
                    print_success("JiuwenSwarm deployment completed!")
                    print_info("="*50)
                    print_info(f"Execution UUID: {execute_uuid}")
                    print_info(f"Script Name: {job_info.get('script_name', 'N/A')}")
                    print_info(f"Execute User: {job_info.get('execute_user', 'N/A')}")
                    print_info(f"Execution Result: Total {job_info.get('total_count', 1)} instances")
                    print_info(f"          Success: {job_info.get('success_count', 0)}")
                    print_info(f"          Failed: {job_info.get('fail_count', 0)}")
                    
                    # Display execution time
                    if job_info.get('execute_costs'):
                        execute_costs_ms = job_info.get('execute_costs', 0)
                        execute_costs_seconds = job_info.get('execute_costs_seconds', execute_costs_ms / 1000 if execute_costs_ms else 0)
                        print_info(f"Execution Time: {execute_costs_ms}ms ({execute_costs_seconds:.2f} seconds)")
                    
                    # Display time information
                    if job_info.get('create_time'):
                        print_info(f"Create Time: {job_info['create_time']}")
                    if job_info.get('finish_time'):
                        print_info(f"Finish Time: {job_info['finish_time']}")
                    
                    # Display script output
                    if job_info.get('output'):
                        output = job_info['output']
                        print_info("\nScript Output:")
                        print(output[:2000] if len(output) > 2000 else output)
                        if len(output) > 2000:
                            print_info(f"... (Output truncated, total {len(output)} characters)")
                    
                    # Display error message (if any)
                    if job_info.get('error'):
                        print_error(f"\nError Message: {job_info['error']}")
                    
                    print_info("="*50)
                    return execute_uuid

                elif status in ['ABNORMAL', 'CANCELED']:
                    # According to GetScriptJobInfo API, CANCELED and ABNORMAL indicate script execution completed but failed
                    print_error("Deployment job failed!")
                    print_info("="*50)
                    print_info(f"Execution UUID: {execute_uuid}")
                    print_info(f"Status: {status} ({status_display})")

                    # Get detailed error information
                    error_msg = job_info.get('error', job_info.get('error_message', ''))
                    if error_msg:
                        print_error(f"Error Reason: {error_msg}")

                    # Display script output
                    if job_info.get('output'):
                        output = job_info['output']
                        print_info("\nScript Output:")
                        print(output[:2000] if len(output) > 2000 else output)
                        if len(output) > 2000:
                            print_info(f"... (Output truncated, total {len(output)} characters)")

                    print_info("="*50)
                    return None  # 返回None表示执行失败

            time.sleep(EXECUTION_INTERVAL)

        print_error("Deployment timeout")
        return None

    return execute_uuid

def parse_args():
    parser = argparse.ArgumentParser(description='COC Remote Deployment of JiuwenSwarm Service')
    parser.add_argument('--instance-id', type=str, help='Instance RMS resource ID')
    parser.add_argument('--ecs-instance-id', type=str, help='ECS instance ID')
    parser.add_argument('--ip', type=str, help='Instance public IP address')
    parser.add_argument('--wait', action='store_true', default=True, help='Wait for deployment to complete')
    parser.add_argument('--timeout', type=int, default=1800, help='Timeout in seconds')
    return parser.parse_args()

def main():
    args = parse_args()

    if not os.environ.get('HUAWEICLOUD_SDK_AK') or not os.environ.get('HUAWEICLOUD_SDK_SK'):
        print("[ERROR] Please set environment variables HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK")
        sys.exit(1)

    get_credentials()

    instance_info = None

    if args.instance_id and args.ip:
        instance_info = {
            'instance_id': args.instance_id,
            'ecs_instance_id': args.ecs_instance_id,
            'public_ip': args.ip
        }
    elif args.ip:
        print(f"[INFO] Querying instance info by public IP: {args.ip}")
        instance_info = query_instance_by_ip(args.ip)
        if not instance_info:
            print("[ERROR] Cannot find instance with specified IP")
            sys.exit(1)
    else:
        instance_info = load_instance_info()
        if not instance_info:
            print("[ERROR] Cannot get instance info")
            print("[INFO] Please specify --instance-id and --ip parameters, or ensure new_instance_info.json exists")
            sys.exit(1)

    print(f"\nInstance Info:")
    print(f"  - Instance ID: {instance_info['instance_id']}")
    print(f"  - ECS Instance ID: {instance_info['ecs_instance_id']}")
    print(f"  - Public IP: {instance_info['public_ip']}")

    execute_uuid = deploy_jiuwenswarm(
        instance_info['instance_id'],
        instance_info['ecs_instance_id'],
        instance_info['public_ip'],
        args.wait,
        args.timeout
    )

    if execute_uuid:
        print("\nNext step: Run verify_deployment.py to verify JiuwenSwarm service deployment result")
    else:
        print("\n[ERROR] Deployment job failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
