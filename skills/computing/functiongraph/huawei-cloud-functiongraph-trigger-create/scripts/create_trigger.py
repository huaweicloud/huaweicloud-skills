#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunctionGraph trigger creation tool

Create and configure TIMER triggers for FunctionGraph functions
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, Tuple

try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
    from huaweicloudsdkfunctiongraph.v2.functiongraph_client import FunctionGraphClient
    from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
    from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request import CreateFunctionTriggerRequest
    from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request_body import CreateFunctionTriggerRequestBody
    from huaweicloudsdkfunctiongraph.v2.model.trigger_event_data_request_body import TriggerEventDataRequestBody
except ImportError as e:
    print(f"Please install SDK first: pip install huaweicloudsdkfunctiongraph (Error: {e})")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CronValidator:
    """Cron expression validator"""

    FIELD_RANGES = {
        'second': (0, 59),
        'minute': (0, 59),
        'hour': (0, 23),
        'day': (1, 31),
        'month': (1, 12),
        'weekday': (1, 7)
    }

    @classmethod
    def validate(cls, cron_expression: str) -> Tuple[bool, str]:
        if not cron_expression:
            return False, "Cron expression cannot be empty"

        parts = cron_expression.strip().split()
        if len(parts) < 6 or len(parts) > 7:
            return False, f"Cron expression should have 6 or 7 fields, got {len(parts)}"

        field_names = ['second', 'minute', 'hour', 'day', 'month', 'weekday']
        for i, (part, field_name) in enumerate(zip(parts[:6], field_names)):
            is_valid, error = cls._validate_field(part, field_name)
            if not is_valid:
                return False, f"Field '{field_name}' invalid: {error}"

        return True, ""

    @classmethod
    def _validate_field(cls, field: str, field_name: str) -> Tuple[bool, str]:
        min_val, max_val = cls.FIELD_RANGES[field_name]

        if field == '*':
            return True, ""
        if field == '?':
            if field_name in ['day', 'weekday']:
                return True, ""
            return False, "'?' can only be used for day or weekday fields"
        if '-' in field:
            try:
                start, end = map(int, field.split('-'))
                if start < min_val or end > max_val or start > end:
                    return False, f"Range should be between {min_val}-{max_val}"
                return True, ""
            except ValueError:
                return False, "Invalid range format"
        if field.startswith('*/'):
            try:
                step = int(field[2:])
                if step < 1 or step > max_val:
                    return False, f"Step should be between 1-{max_val}"
                return True, ""
            except ValueError:
                return False, "Invalid step format"
        if ',' in field:
            try:
                values = [int(v) for v in field.split(',')]
                for v in values:
                    if v < min_val or v > max_val:
                        return False, f"Value should be between {min_val}-{max_val}"
                return True, ""
            except ValueError:
                return False, "Invalid list format"
        try:
            value = int(field)
            if value < min_val or value > max_val:
                return False, f"Value should be between {min_val}-{max_val}"
            return True, ""
        except ValueError:
            return False, "Invalid numeric value"


class TriggerCreator:
    """Trigger creator for FunctionGraph"""

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
        required_fields = ['function_urn', 'trigger_name', 'schedule']
        for field in required_fields:
            if not params.get(field):
                return False, f"Missing required parameter: {field}"

        schedule_type = params.get('schedule_type', 'Cron')
        if schedule_type not in ['Rate', 'Cron']:
            return False, "schedule_type must be 'Rate' or 'Cron'"

        if schedule_type == 'Cron':
            is_valid, error = CronValidator.validate(params['schedule'])
            if not is_valid:
                return False, f"Invalid Cron expression: {error}"

        trigger_name = params['trigger_name']
        if len(trigger_name) < 1 or len(trigger_name) > 64:
            return False, "Trigger name must be 1-64 characters"

        enable_status = params.get('enable_status', 'ACTIVE')
        if enable_status not in ['ACTIVE', 'DISABLED']:
            return False, "enable_status must be 'ACTIVE' or 'DISABLED'"

        return True, ""

    def check_function_exists(self, function_urn: str) -> Tuple[bool, str]:
        try:
            from huaweicloudsdkfunctiongraph.v2.model.show_function_config_request import ShowFunctionConfigRequest
            request = ShowFunctionConfigRequest(function_urn=function_urn)
            self.client.show_function_config(request)
            return True, ""
        except ClientRequestException as e:
            if 'not found' in str(e).lower() or e.status_code == 404:
                return False, "Target function not found"
            return False, f"Failed to check function: {str(e)}"

    def create_trigger(self, params: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, error_msg = self.validate_params(params)
        if not is_valid:
            return {'status': 'failed', 'error_code': 'InvalidParameter', 'message': error_msg}

        exists, error = self.check_function_exists(params['function_urn'])
        if not exists:
            return {'status': 'failed', 'error_code': 'FunctionNotFound', 'message': error}

        try:
            event_data = TriggerEventDataRequestBody(
                name=params['trigger_name'],
                schedule_type=params.get('schedule_type', 'Cron'),
                schedule=params['schedule']
            )

            user_event = params.get('user_event')
            if user_event:
                event_data.user_event = user_event

            request_body = CreateFunctionTriggerRequestBody(
                trigger_type_code='TIMER',
                trigger_status=params.get('enable_status', 'ACTIVE'),
                event_data=event_data
            )

            request = CreateFunctionTriggerRequest(
                function_urn=params['function_urn'],
                body=request_body
            )

            logger.info(f"Creating trigger: {params['trigger_name']}")
            response = self.client.create_function_trigger(request)

            trigger_name = params['trigger_name']
            trigger_type_code = response.trigger_type_code or 'TIMER'
            trigger_status = response.trigger_status or 'ACTIVE'

            if response.event_data and hasattr(response.event_data, 'name') and response.event_data.name:
                trigger_name = response.event_data.name

            result = {
                'status': 'success',
                'trigger_id': response.trigger_id,
                'trigger_name': trigger_name,
                'trigger_type': trigger_type_code,
                'schedule': params['schedule'],
                'enable_status': trigger_status,
                'message': 'Trigger created successfully'
            }

            logger.info(f"Trigger created successfully: {response.trigger_id}")
            return result

        except ClientRequestException as e:
            error_code = e.error_code if hasattr(e, 'error_code') else 'Unknown'
            error_msg = e.error_msg if hasattr(e, 'error_msg') else str(e)

            logger.error(f"Failed to create trigger: {error_code} - {error_msg}")

            if e.status_code == 409 or 'already exist' in error_msg.lower():
                error_code = 'TriggerAlreadyExists'
            elif 'limit' in error_msg.lower():
                error_code = 'TriggerLimitExceeded'

            return {'status': 'failed', 'error_code': error_code, 'message': error_msg}

        except Exception as e:
            logger.error(f"Exception creating trigger: {str(e)}")
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

    parser = argparse.ArgumentParser(description='Create FunctionGraph TIMER trigger')
    parser.add_argument('--function-urn', required=True, help='Target function URN')
    parser.add_argument('--name', required=True, help='Trigger name')
    parser.add_argument('--schedule', required=True, help='Cron expression or Rate value')
    parser.add_argument('--schedule-type', choices=['Cron', 'Rate'], default='Cron',
                        help='Schedule type: Cron (default) or Rate')
    parser.add_argument('--status', choices=['ACTIVE', 'DISABLED'], default='ACTIVE',
                        help='Trigger status: ACTIVE (default) or DISABLED')
    parser.add_argument('--user-event', default='', help='Additional user event data')
    parser.add_argument('--skip-check', action='store_true',
                        help='Skip function existence check')

    args = parser.parse_args()

    try:
        config = load_config()
    except ValueError as e:
        print(f"Config error: {e}")
        sys.exit(1)

    params = {
        'function_urn': args.function_urn,
        'trigger_name': args.name,
        'schedule': args.schedule,
        'schedule_type': args.schedule_type,
        'enable_status': args.status,
        'user_event': args.user_event
    }

    creator = TriggerCreator(
        ak=config['ak'],
        sk=config['sk'],
        region=config['region'],
        project_id=config['project_id']
    )

    if args.skip_check:
        exists = True
    else:
        exists, error = creator.check_function_exists(params['function_urn'])
        if not exists:
            print(json.dumps({'status': 'failed', 'error_code': 'FunctionNotFound', 'message': error},
                             indent=2, ensure_ascii=False))
            sys.exit(1)

    result = creator.create_trigger(params)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['status'] != 'success':
        sys.exit(1)


if __name__ == '__main__':
    main()
