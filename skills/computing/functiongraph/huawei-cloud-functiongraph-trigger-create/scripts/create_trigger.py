#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunctionGraph trigger creation tool

Create and configure TIMER (scheduled) and OBS (object storage event) triggers
for FunctionGraph functions.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Tuple

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

SUPPORTED_TRIGGER_TYPES = ('TIMER', 'OBS')
SUPPORTED_STATUSES = ('ACTIVE', 'DISABLED')
SUPPORTED_SCHEDULE_TYPES = ('Cron', 'Rate')
# Quartz advanced characters are not supported by FunctionGraph cron scheduling.
UNSUPPORTED_CRON_CHARS = ('L', 'W', '#')


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

        # Reject Quartz-only advanced characters with an explicit message instead
        # of falling through to the generic "Invalid numeric value" error.
        advanced = sorted({char for char in field.upper() if char in UNSUPPORTED_CRON_CHARS})
        if advanced:
            chars = ', '.join(f"'{char}'" for char in advanced)
            return False, (
                f"Quartz advanced character(s) {chars} are not supported, "
                f"including the 'L' (last day), 'W' (nearest weekday), "
                f"'#' (nth weekday) and 'LW' forms; "
                f"please use numeric values with '*', '?', ',', '-' or '*/step' only"
            )

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
    """Trigger creator for FunctionGraph (TIMER and OBS triggers)"""

    def __init__(self, ak: str, sk: str, region: str = 'cn-north-4', project_id: str = None):
        self.ak = ak
        self.sk = sk
        self.region = region
        self.project_id = project_id
        # Machine readable reason of the last failed check_function_exists() call.
        # It keeps the (bool, str) signature of that method while still letting
        # callers report FunctionNotFound / NetworkError / InternalError.
        self.last_check_error_code = None
        self.client = self._init_client()

    def _init_client(self) -> FunctionGraphClient:
        credentials = BasicCredentials(ak=self.ak, sk=self.sk, project_id=self.project_id)
        client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(self.region)) \
            .build()
        return client

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not params.get('function_urn'):
            return False, "Missing required parameter: function_urn"

        trigger_type = params.get('trigger_type', 'TIMER')
        if trigger_type not in SUPPORTED_TRIGGER_TYPES:
            return False, "trigger_type must be 'TIMER' or 'OBS'"

        trigger_name = params.get('trigger_name')
        if not trigger_name:
            return False, "Missing required parameter: trigger_name"
        if len(trigger_name) > 64:
            return False, "Trigger name must be 1-64 characters"

        enable_status = params.get('enable_status', 'ACTIVE')
        if enable_status not in SUPPORTED_STATUSES:
            return False, "enable_status must be 'ACTIVE' or 'DISABLED'"

        if trigger_type == 'OBS':
            return self._validate_obs_params(params)
        return self._validate_timer_params(params)

    def _validate_timer_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not params.get('schedule'):
            return False, "Missing required parameter: schedule (required for TIMER triggers)"

        schedule_type = params.get('schedule_type', 'Cron')
        if schedule_type not in SUPPORTED_SCHEDULE_TYPES:
            return False, "schedule_type must be 'Rate' or 'Cron'"

        if schedule_type == 'Cron':
            is_valid, error = CronValidator.validate(params['schedule'])
            if not is_valid:
                return False, f"Invalid Cron expression: {error}"

        return True, ""

    def _validate_obs_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not params.get('bucket'):
            return False, "Missing required parameter: bucket (required for OBS triggers)"

        if not params.get('events'):
            return False, "Missing required parameter: events (required for OBS triggers)"

        if not self._parse_events(params.get('events')):
            return False, "events must contain at least one event type, e.g. 'ObjectCreated:*' or 'Put,Post'"

        return True, ""

    @staticmethod
    def _parse_events(events: Any) -> List[str]:
        """Normalise the --events input (comma separated string or list) to list[str]."""
        if events is None:
            return []
        if isinstance(events, str):
            raw = events.split(',')
        elif isinstance(events, (list, tuple, set)):
            raw = [str(item) for item in events]
        else:
            return []
        return [item.strip() for item in (str(entry) for entry in raw) if item.strip()]

    def check_function_exists(self, function_urn: str) -> Tuple[bool, str]:
        """Check whether the target function exists.

        Returns a ``(exists, message)`` tuple. On failure the machine readable
        reason is recorded in ``self.last_check_error_code`` so that callers keep
        the tuple signature and still report ``FunctionNotFound`` for a missing
        function and ``NetworkError`` for connection/timeout failures.
        """
        try:
            from huaweicloudsdkfunctiongraph.v2.model.show_function_config_request import ShowFunctionConfigRequest
            request = ShowFunctionConfigRequest(function_urn=function_urn)
            self.client.show_function_config(request)
            self.last_check_error_code = None
            return True, ""
        except ClientRequestException as e:
            if getattr(e, 'status_code', None) == 404 or 'not found' in str(e).lower():
                self.last_check_error_code = 'FunctionNotFound'
                return False, "Target function not found"
            self.last_check_error_code = 'InternalError'
            return False, f"Failed to check function: {str(e)}"
        except Exception as e:
            # Connection reset, DNS failure, timeout and similar transport errors
            # carry no HTTP status code: report them as NetworkError rather than
            # letting the traceback escape.
            status_code = getattr(e, 'status_code', None)
            if status_code is not None:
                self.last_check_error_code = 'InternalError'
                return False, f"Failed to check function (HTTP {status_code}): {str(e)}"
            logger.error(f"Network error while checking function: {type(e).__name__}: {e}")
            self.last_check_error_code = 'NetworkError'
            return False, f"Network error while checking function: {type(e).__name__}: {str(e)}"

    @staticmethod
    def _build_event_data(params: Dict[str, Any], trigger_type: str, event_list: List[str]):
        if trigger_type == 'OBS':
            return TriggerEventDataRequestBody(
                name=params['trigger_name'],
                bucket=params.get('bucket'),
                events=event_list,
                prefix=params.get('prefix') or None,
                suffix=params.get('suffix') or None
            )

        event_data = TriggerEventDataRequestBody(
            name=params['trigger_name'],
            schedule_type=params.get('schedule_type', 'Cron'),
            schedule=params.get('schedule')
        )

        user_event = params.get('user_event')
        if user_event:
            event_data.user_event = user_event

        return event_data

    def create_trigger(self, params: Dict[str, Any]) -> Dict[str, Any]:
        is_valid, error_msg = self.validate_params(params)
        if not is_valid:
            return {'status': 'failed', 'error_code': 'InvalidParameter', 'message': error_msg}

        exists, error = self.check_function_exists(params['function_urn'])
        if not exists:
            return {
                'status': 'failed',
                'error_code': self.last_check_error_code or 'FunctionNotFound',
                'message': error
            }

        trigger_type = params.get('trigger_type', 'TIMER')

        try:
            event_list = self._parse_events(params.get('events')) if trigger_type == 'OBS' else []
            event_data = self._build_event_data(params, trigger_type, event_list)

            request_body = CreateFunctionTriggerRequestBody(
                trigger_type_code=trigger_type,
                trigger_status=params.get('enable_status', 'ACTIVE'),
                event_data=event_data
            )

            request = CreateFunctionTriggerRequest(
                function_urn=params['function_urn'],
                body=request_body
            )

            logger.info(f"Creating {trigger_type} trigger: {params['trigger_name']}")
            response = self.client.create_function_trigger(request)

            trigger_name = params['trigger_name']
            trigger_type_code = response.trigger_type_code or trigger_type
            trigger_status = response.trigger_status or 'ACTIVE'

            if response.event_data and hasattr(response.event_data, 'name') and response.event_data.name:
                trigger_name = response.event_data.name

            result = {
                'status': 'success',
                'trigger_id': response.trigger_id,
                'trigger_name': trigger_name,
                'trigger_type': trigger_type_code,
                'enable_status': trigger_status,
                'message': 'Trigger created successfully'
            }

            if trigger_type == 'OBS':
                result['bucket'] = params.get('bucket')
                result['events'] = event_list
            else:
                result['schedule'] = params.get('schedule')

            logger.info(f"Trigger created successfully: {response.trigger_id}")
            return result

        except ClientRequestException as e:
            error_code = getattr(e, 'error_code', None) or 'InternalError'
            error_msg = getattr(e, 'error_msg', None) or str(e)

            logger.error(f"Failed to create trigger: {error_code} - {error_msg}")

            if getattr(e, 'status_code', None) == 409 or 'already exist' in error_msg.lower():
                error_code = 'TriggerAlreadyExists'
            elif 'limit' in error_msg.lower():
                error_code = 'TriggerLimitExceeded'

            return {'status': 'failed', 'error_code': error_code, 'message': error_msg}

        except Exception as e:
            status_code = getattr(e, 'status_code', None)
            if status_code is None:
                logger.error(f"Network error while creating trigger: {type(e).__name__}: {e}")
                return {
                    'status': 'failed',
                    'error_code': 'NetworkError',
                    'message': f"Network error while creating trigger: {type(e).__name__}: {str(e)}"
                }
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

    parser = argparse.ArgumentParser(
        description='Create a FunctionGraph TIMER (scheduled) or OBS (object storage event) trigger')
    parser.add_argument('--function-urn', required=True, help='Target function URN')
    parser.add_argument('--trigger-type', choices=['TIMER', 'OBS'], default='TIMER',
                        help='Trigger type: TIMER (default) or OBS')
    parser.add_argument('--name', required=True,
                        help='Trigger name (TIMER) or event notification name (OBS), 1-64 characters')
    parser.add_argument('--status', choices=['ACTIVE', 'DISABLED'], default='ACTIVE',
                        help='Trigger status: ACTIVE (default) or DISABLED')
    parser.add_argument('--schedule',
                        help='Cron expression or Rate value (required when --trigger-type is TIMER)')
    parser.add_argument('--schedule-type', choices=['Cron', 'Rate'], default='Cron',
                        help='Schedule type for TIMER triggers: Cron (default) or Rate')
    parser.add_argument('--user-event', default='',
                        help='Additional user event data (TIMER triggers only)')
    parser.add_argument('--bucket',
                        help='OBS bucket name (required when --trigger-type is OBS)')
    parser.add_argument('--events',
                        help="Comma separated OBS event types, e.g. 'ObjectCreated:*' or 'Put,Post' "
                             "(required when --trigger-type is OBS)")
    parser.add_argument('--prefix', default='', help='OBS object key prefix filter (OBS triggers only)')
    parser.add_argument('--suffix', default='', help='OBS object key suffix filter (OBS triggers only)')

    args = parser.parse_args()

    try:
        config = load_config()
    except ValueError as e:
        print(f"Config error: {e}")
        sys.exit(1)

    params = {
        'function_urn': args.function_urn,
        'trigger_type': args.trigger_type,
        'trigger_name': args.name,
        'enable_status': args.status,
        'schedule': args.schedule,
        'schedule_type': args.schedule_type,
        'user_event': args.user_event,
        'bucket': args.bucket,
        'events': args.events,
        'prefix': args.prefix,
        'suffix': args.suffix
    }

    creator = TriggerCreator(
        ak=config['ak'],
        sk=config['sk'],
        region=config['region'],
        project_id=config['project_id']
    )

    # Validate before touching the network so that a TIMER call without
    # --schedule always reports InvalidParameter, never a transport error.
    is_valid, error_msg = creator.validate_params(params)
    if not is_valid:
        print(json.dumps({'status': 'failed', 'error_code': 'InvalidParameter', 'message': error_msg},
                         indent=2, ensure_ascii=False))
        sys.exit(1)

    exists, error = creator.check_function_exists(params['function_urn'])
    if not exists:
        print(json.dumps({'status': 'failed',
                          'error_code': creator.last_check_error_code or 'FunctionNotFound',
                          'message': error},
                         indent=2, ensure_ascii=False))
        sys.exit(1)

    result = creator.create_trigger(params)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result['status'] != 'success':
        sys.exit(1)


if __name__ == '__main__':
    main()
