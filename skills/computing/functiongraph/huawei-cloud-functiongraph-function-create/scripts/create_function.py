#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunctionGraph function creation tool

Create FunctionGraph functions on Huawei Cloud based on user input
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
    from huaweicloudsdkfunctiongraph.v2.model.create_function_request_body import CreateFunctionRequestBody
except ImportError as e:
    print(f"Please install SDK first: pip install huaweicloudsdkfunctiongraph (Error: {e})")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FunctionCreator:
    """FunctionGraph function creator"""

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

        return True, ""

    def create_function(self, params: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, error_msg = self.validate_params(params)
        if not is_valid:
            return {'status': 'failed', 'error_code': 'InvalidParameter', 'message': error_msg}

        try:
            encoded_code = base64.b64encode(params['code_content'].encode('utf-8')).decode('utf-8')
            func_code = FuncCode(file=encoded_code)

            request_body = CreateFunctionRequestBody(
                func_name=params['function_name'],
                package='default',
                runtime=params['runtime'],
                handler=params['handler'],
                code_type='inline',
                func_code=func_code,
                memory_size=params.get('memory_size', 128),
                timeout=params.get('timeout', 3),
                description=params.get('description', '')
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
                'message': 'Function created successfully'
            }

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


def load_config() -> Dict[str, str]:
    config = {
        'ak': os.environ.get('HUAWEI_AK'),
        'sk': os.environ.get('HUAWEI_SK'),
        'region': os.environ.get('HUAWEI_REGION', 'cn-north-4'),
        'project_id': os.environ.get('HUAWEI_PROJECT_ID')
    }
    if not config['ak'] or not config['sk']:
        raise ValueError("Please set environment variables HUAWEI_AK and HUAWEI_SK")
    return config


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create FunctionGraph function')
    parser.add_argument('--name', required=True, help='Function name')
    parser.add_argument('--runtime', required=True, help='Runtime environment')
    parser.add_argument('--handler', required=True, help='Function entry point')
    parser.add_argument('--code', required=True, help='Code file path or code content')
    parser.add_argument('--memory', type=int, default=128, help='Memory size (MB)')
    parser.add_argument('--timeout', type=int, default=3, help='Timeout (seconds)')
    parser.add_argument('--description', default='', help='Function description')

    args = parser.parse_args()

    try:
        config = load_config()
    except ValueError as e:
        print(f"Config error: {e}")
        sys.exit(1)

    if os.path.isfile(args.code):
        with open(args.code, 'r', encoding='utf-8') as f:
            code_content = f.read()
    else:
        code_content = args.code

    params = {
        'function_name': args.name,
        'runtime': args.runtime,
        'handler': args.handler,
        'code_content': code_content,
        'memory_size': args.memory,
        'timeout': args.timeout,
        'description': args.description
    }

    creator = FunctionCreator(
        ak=config['ak'],
        sk=config['sk'],
        region=config['region'],
        project_id=config['project_id']
    )

    result = creator.create_function(params)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['status'] != 'success':
        sys.exit(1)


if __name__ == '__main__':
    main()
