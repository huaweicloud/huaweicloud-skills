#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunctionGraph function creation and invocation tool

Create and invoke FunctionGraph functions on Huawei Cloud based on user input.
Supports VPC configuration, environment variables, and function invocation.
"""

import os
import sys
import json
import logging
import base64
from typing import Dict, Any, Optional, Tuple

try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
    from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
    from huaweicloudsdkfunctiongraph.v2.model.create_function_request import CreateFunctionRequest
    from huaweicloudsdkfunctiongraph.v2.model.func_code import FuncCode
    from huaweicloudsdkfunctiongraph.v2.model.func_vpc import FuncVpc
    from huaweicloudsdkfunctiongraph.v2.model.create_function_request_body import CreateFunctionRequestBody
    from huaweicloudsdkfunctiongraph.v2.model.invoke_function_request import InvokeFunctionRequest
    from huaweicloudsdkfunctiongraph.v2.model.async_invoke_function_request import AsyncInvokeFunctionRequest
except ImportError as e:
    print(f"Please install SDK first: pip install huaweicloudsdkfunctiongraph (Error: {e})")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FunctionGraphManager:
    """FunctionGraph function manager supporting create, invoke, and configuration"""

    SUPPORTED_RUNTIMES = [
        'Python3.9', 'Python3.10', 'Python3.11',
        'Node.js14.18', 'Node.js16.17', 'Node.js18.15',
        'Java11', 'Java17',
        'Go1.x', 'Custom'
    ]

    def __init__(self, ak: str, sk: str, region: str = 'cn-north-4', project_id: str = None):
        self.ak = ak
        self.sk = sk
        self.region = region
        self.project_id = project_id
        self.client = self._init_client()

    def _init_client(self) -> FunctionGraphClient:
        credentials = BasicCredentials(ak=self.ak, sk=self.sk, project_id=self.project_id)
        client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(self.region)) \
            .build()
        return client

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        required_fields = ['function_name', 'runtime', 'code_content', 'handler']
        for field in required_fields:
            if not params.get(field):
                return False, f"Missing required parameter: {field}"

        function_name = params['function_name']
        if not function_name.replace('_', '').replace('-', '').isalnum():
            return False, "Function name can only contain letters, numbers, underscores and hyphens"

        if len(function_name) < 1 or len(function_name) > 64:
            return False, "Function name length must be between 1-64 characters"

        runtime = params['runtime']
        if runtime not in self.SUPPORTED_RUNTIMES:
            return False, f"Unsupported runtime: {runtime}, supported: {', '.join(self.SUPPORTED_RUNTIMES)}"

        memory_size = params.get('memory_size', 128)
        if memory_size < 128 or memory_size > 4096 or memory_size % 128 != 0:
            return False, "Memory size must be between 128-4096MB and a multiple of 128"

        timeout = params.get('timeout', 3)
        if timeout < 1 or timeout > 900:
            return False, "Timeout must be between 1-900 seconds"

        # VPC configuration: all three parameters must be provided together
        vpc_params = [
            ('vpc_id', params.get('vpc_id')),
            ('subnet_id', params.get('subnet_id')),
            ('security_group_id', params.get('security_group_id')),
        ]
        provided_vpc = [name for name, value in vpc_params if value]
        if provided_vpc and len(provided_vpc) != len(vpc_params):
            missing = [name for name, _ in vpc_params if name not in provided_vpc]
            return False, (
                "VPC configuration requires all three parameters: "
                f"--vpc-id, --subnet-id, --security-group-id (missing: {', '.join(missing)})"
            )

        return True, ""

    def create_function(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a FunctionGraph function with optional VPC and environment variable config."""
        is_valid, error_msg = self.validate_params(params)
        if not is_valid:
            return {'status': 'failed', 'error_code': 'InvalidParameter', 'message': error_msg}

        try:
            encoded_code = base64.b64encode(params['code_content'].encode('utf-8')).decode('utf-8')
            func_code = FuncCode(file=encoded_code)

            # Build VPC configuration if provided
            func_vpc = None
            vpc_id = params.get('vpc_id')
            subnet_id = params.get('subnet_id')
            security_group_id = params.get('security_group_id')
            if vpc_id and subnet_id and security_group_id:
                func_vpc = FuncVpc(
                    vpc_id=vpc_id,
                    subnet_id=subnet_id,
                    security_groups=[security_group_id],
                )

            # Build environment variables if provided
            # user_data is a JSON string type in the FunctionGraph API (SDK declares str)
            user_data = json.dumps(params.get('environment_variables')) if params.get('environment_variables') else None

            request_body = CreateFunctionRequestBody(
                func_name=params['function_name'],
                package='default',
                runtime=params['runtime'],
                handler=params['handler'],
                code_type='inline',
                func_code=func_code,
                memory_size=params.get('memory_size', 128),
                timeout=params.get('timeout', 3),
                description=params.get('description', ''),
                func_vpc=func_vpc,
                user_data=user_data,
            )

            request = CreateFunctionRequest()
            request.body = request_body

            logger.info(f"Creating function: {params['function_name']}")
            response = self.client.create_function(request)

            result = {
                'status': 'success',
                'function_urn': response.func_urn,
                'function_name': response.func_name,
                'runtime': response.runtime,
                'handler': response.handler,
                'memory_size': response.memory_size,
                'timeout': response.timeout,
                'code_size': response.code_size,
                'message': 'Function created successfully',
            }

            # Include VPC info if configured
            if response.func_vpc:
                result['vpc_id'] = response.func_vpc.vpc_id
                result['subnet_id'] = response.func_vpc.subnet_id

            logger.info(f"Function created successfully: {response.func_urn}")
            return result

        except ClientRequestException as e:
            error_code = e.error_code if hasattr(e, 'error_code') else 'Unknown'
            error_msg = e.error_msg if hasattr(e, 'error_msg') else str(e)
            logger.error(f"Failed to create function: {error_code} - {error_msg}")
            return {'status': 'failed', 'error_code': error_code, 'message': error_msg}

        except Exception as e:
            logger.error(f"Exception creating function: {str(e)}")
            return {'status': 'failed', 'error_code': 'InternalError', 'message': str(e)}

    def invoke_function(self, function_urn: str, body: Dict[str, Any] = None,
                        invocation_type: str = 'sync', log_type: str = None) -> Dict[str, Any]:
        """
        Invoke a FunctionGraph function.

        Args:
            function_urn: The URN of the function to invoke
            body: Event data to pass to the function (JSON dict)
            invocation_type: 'sync' for synchronous, 'async' for asynchronous invocation
            log_type: Optional log type header ('tail' to return last 4KB log)
        """
        try:
            logger.info(f"Invoking function: {function_urn} ({invocation_type})")

            if invocation_type == 'async':
                # Async invocation requires AsyncInvokeFunctionRequest; the response only
                # carries the request id (the function output is not returned).
                request = AsyncInvokeFunctionRequest(
                    function_urn=function_urn,
                    body=body or {},
                )
                response = self.client.async_invoke_function(request)

                result = {
                    'status': 'success',
                    'function_urn': function_urn,
                    'invocation_type': invocation_type,
                    'message': 'Function invoked successfully',
                }
                # AsyncInvokeFunctionResponse exposes request_id (from X-Cff-Request-Id
                # response header / body) when returned by the service.
                request_id = getattr(response, 'request_id', None) or getattr(response, 'x_cff_request_id', None)
                if request_id:
                    result['request_id'] = request_id

                logger.info(f"Function invoked successfully: {function_urn}")
                return result

            # Sync invocation. X-CFF-Request-Version: v1 requests the structured body
            # carrying request_id/result/log; X-Cff-Log-Type: tail appends the last 4KB log.
            request = InvokeFunctionRequest(
                function_urn=function_urn,
                body=body or {},
            )
            request.x_cff_request_version = 'v1'
            if log_type:
                request.x_cff_log_type = log_type

            response = self.client.invoke_function(request)

            result: Dict[str, Any] = {
                'status': 'success',
                'function_urn': function_urn,
                'invocation_type': invocation_type,
                'message': 'Function invoked successfully',
            }

            # Structured response body: response.result holds the function output,
            # response.request_id / x_cff_request_id hold the invocation request id.
            output = getattr(response, 'result', None)
            if output is not None:
                result['result'] = {'output': output}

            exec_log = getattr(response, 'log', None)
            if exec_log is not None:
                result['log'] = exec_log

            request_id = getattr(response, 'request_id', None) or getattr(response, 'x_cff_request_id', None)
            if request_id:
                result['request_id'] = request_id

            logger.info(f"Function invoked successfully: {function_urn}")
            return result

        except ClientRequestException as e:
            error_code = e.error_code if hasattr(e, 'error_code') else 'Unknown'
            error_msg = e.error_msg if hasattr(e, 'error_msg') else str(e)
            logger.error(f"Failed to invoke function: {error_code} - {error_msg}")
            return {'status': 'failed', 'error_code': error_code, 'message': error_msg}

        except Exception as e:
            logger.error(f"Exception invoking function: {str(e)}")
            return {'status': 'failed', 'error_code': 'InternalError', 'message': str(e)}


def load_config() -> Dict[str, str]:
    config = {
        'ak': os.environ.get('HUAWEI_AK'),
        'sk': os.environ.get('HUAWEI_SK'),
        'region': os.environ.get('HUAWEI_REGION', 'cn-north-4'),
        'project_id': os.environ.get('HUAWEI_PROJECT_ID'),
    }
    if not config['ak'] or not config['sk']:
        raise ValueError("Please set environment variables HUAWEI_AK and HUAWEI_SK")
    return config


def cmd_create(args) -> None:
    """Handle the 'create' subcommand."""
    if os.path.isfile(args.code):
        with open(args.code, 'r', encoding='utf-8') as f:
            code_content = f.read()
    else:
        code_content = args.code

    # Parse environment variables if provided
    env_vars = None
    if args.env_vars:
        try:
            env_vars = json.loads(args.env_vars)
            if not isinstance(env_vars, dict):
                print("Error: --env-vars must be a valid JSON object")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: --env-vars must be valid JSON: {e}")
            sys.exit(1)

    params = {
        'function_name': args.name,
        'runtime': args.runtime,
        'handler': args.handler,
        'code_content': code_content,
        'memory_size': args.memory,
        'timeout': args.timeout,
        'description': args.description,
        'vpc_id': args.vpc_id,
        'subnet_id': args.subnet_id,
        'security_group_id': args.security_group_id,
        'environment_variables': env_vars,
    }

    config = load_config()
    manager = FunctionGraphManager(
        ak=config['ak'],
        sk=config['sk'],
        region=config['region'],
        project_id=config['project_id'],
    )

    result = manager.create_function(params)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['status'] != 'success':
        sys.exit(1)


def cmd_invoke(args) -> None:
    """Handle the 'invoke' subcommand."""
    # Parse invoke body if provided
    invoke_body = {}
    if args.body:
        try:
            invoke_body = json.loads(args.body)
            if not isinstance(invoke_body, dict):
                print("Error: --body must be a valid JSON object")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: --body must be valid JSON: {e}")
            sys.exit(1)

    config = load_config()
    manager = FunctionGraphManager(
        ak=config['ak'],
        sk=config['sk'],
        region=config['region'],
        project_id=config['project_id'],
    )

    result = manager.invoke_function(
        function_urn=args.function_urn,
        body=invoke_body,
        invocation_type=args.invocation_type,
        log_type=args.log_type,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['status'] != 'success':
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='FunctionGraph function management tool')
    subparsers = parser.add_subparsers(dest='action', help='Action to perform')

    # --- Create subcommand ---
    create_parser = subparsers.add_parser('create', help='Create a new function')
    create_parser.add_argument('--name', required=True, help='Function name')
    create_parser.add_argument('--runtime', required=True, help='Runtime environment')
    create_parser.add_argument('--handler', required=True, help='Function entry point')
    create_parser.add_argument('--code', required=True, help='Code file path or code content')
    create_parser.add_argument('--memory', type=int, default=128, help='Memory size (MB)')
    create_parser.add_argument('--timeout', type=int, default=3, help='Timeout (seconds)')
    create_parser.add_argument('--description', default='', help='Function description')

    # VPC configuration (optional)
    create_parser.add_argument('--vpc-id', help='VPC ID for VPC configuration')
    create_parser.add_argument('--subnet-id', help='Subnet ID for VPC configuration')
    create_parser.add_argument('--security-group-id', help='Security group ID for VPC configuration')

    # Environment variables (optional)
    create_parser.add_argument(
        '--env-vars',
        help='Environment variables as JSON string, e.g. \'{"DB_HOST":"localhost","DB_PORT":"3306"}\'',
    )

    # --- Invoke subcommand ---
    invoke_parser = subparsers.add_parser('invoke', help='Invoke an existing function')
    invoke_parser.add_argument('--function-urn', required=True, help='Function URN to invoke')
    invoke_parser.add_argument(
        '--body', default='{}',
        help='Event payload as JSON string, e.g. \'{"key1":"value1"}\'',
    )
    invoke_parser.add_argument(
        '--invocation-type', choices=['sync', 'async'], default='sync',
        help='Invocation type: sync (default) or async',
    )
    invoke_parser.add_argument(
        '--log-type', choices=['tail', 'none'], default=None,
        help='Log type: "tail" to return last 4KB of log',
    )

    args = parser.parse_args()

    if args.action == 'create':
        cmd_create(args)
    elif args.action == 'invoke':
        cmd_invoke(args)
    else:
        # Backward compatibility: if no subcommand given, assume "create"
        # by re-parsing with original-style arguments
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()