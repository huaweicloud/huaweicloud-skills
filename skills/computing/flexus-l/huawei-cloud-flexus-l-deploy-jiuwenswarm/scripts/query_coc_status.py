#!/usr/bin/env python3
"""
Phase 8: COC Remote Script Execution Status Query

This script is used to query the job status of remote script execution on Huawei Cloud COC (Cloud Operations Center).
Supports querying status information for a single execution UUID, including execution progress, duration, output results, etc.

Use cases:
- Query COC task execution status submitted in Phase 3 and Phase 4
- Monitor execution progress of long-running tasks
- Get task execution results and output information
"""

import os
import sys
import json
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils import (
        get_huaweicloud_credentials,
        coc_query_execution,
        print_header,
        print_success,
        print_error,
        print_warning,
        print_info,
        wait_for_execution_completion
    )
except ImportError as e:
    log.error(f"Failed to import utility modules: {e}")
    log.error("Please ensure utils.py exists")
    sys.exit(1)

STATUS_MAP = {
    'READY': 'Ready',
    'PROCESSING': 'Processing',
    'FINISHED': 'Completed',
    'ABNORMAL': 'Abnormal',
    'CANCELED': 'Canceled',
    'SUCCESS': 'Success',
    'FAILED': 'Failed',
    'TIMEOUT': 'Timeout'
}


def query_single_job(execute_uuid, verbose=False):
    """Query single COC job status"""
    print_header("COC Script Execution Status Query")
    print_info(f"Execution UUID: {execute_uuid}")
    print_info(f"Query Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    result = coc_query_execution(execute_uuid)

    if not result.get("ok"):
        error_info = result.get("error", {})
        print_error(f"Query failed: {error_info.get('message', 'Unknown error')}")
        print_error(f"Error code: {error_info.get('code', 'UNKNOWN')}")
        return None

    job_info = result.get("result", {})

    if not job_info:
        print_warning("API call succeeded, but no task data was retrieved")
        print_info("Possible reasons:")
        print_info("  - Task UUID does not exist")
        print_info("  - Task has not started yet")
        print_info("  - API response format has changed")
        return None

    status = job_info.get('status', 'UNKNOWN')
    status_display = STATUS_MAP.get(status, status)

    print_info("=" * 60)
    print_info("Job Basic Info:")
    print_info(f"  Execution UUID: {execute_uuid}")
    print_info(f"  Script Name: {job_info.get('script_name', 'N/A')}")
    print_info(f"  Execute User: {job_info.get('execute_user', 'N/A')}")
    print_info(f"  Status: {status} ({status_display})")

    if job_info.get('execute_costs'):
        costs_ms = job_info.get('execute_costs', 0)
        costs_seconds = job_info.get('execute_costs_seconds', costs_ms / 1000 if costs_ms else 0)
        print_info(f"  Execution Duration: {costs_ms}ms ({costs_seconds:.2f} seconds)")

    if job_info.get('creator'):
        print_info(f"  Creator: {job_info['creator']}")

    total_count = job_info.get('total_count', 0)
    success_count = job_info.get('success_count', 0)
    fail_count = job_info.get('fail_count', 0)
    processing_count = job_info.get('processing_count', 0)

    if total_count > 0:
        print_info(f"\nExecution Statistics:")
        print_info(f"  Total: {total_count} instances")
        print_info(f"  Success: {success_count}")
        print_info(f"  Failed: {fail_count}")
        print_info(f"  Processing: {processing_count}")
        success_rate = (success_count / total_count) * 100
        print_info(f"  Success Rate: {success_rate:.1f}%")

    if job_info.get('create_time'):
        print_info(f"\nTime Info:")
        print_info(f"  Create Time: {job_info['create_time']}")
    if job_info.get('finish_time'):
        print_info(f"  Finish Time: {job_info['finish_time']}")

    if job_info.get('timeout'):
        print_info(f"\nConfiguration Info:")
        print_info(f"  Timeout Setting: {job_info['timeout']} seconds")
    if job_info.get('success_rate'):
        print_info(f"  Required Success Rate: {job_info['success_rate']}%")

    if job_info.get('error'):
        print_error(f"\nError Message: {job_info['error']}")

    if job_info.get('error_details'):
        print_error("Detailed Error Info:")
        for detail in job_info['error_details']:
            print_error(f"  - {detail}")

    print_info("=" * 60)

    if verbose and job_info.get('output'):
        output = job_info['output']
        print_info("\n脚本输出:")
        print("-" * 60)
        print(output[:3000] if len(output) > 3000 else output)
        if len(output) > 3000:
            print_info(f"... (Output truncated, total {len(output)} characters)")
        print("-" * 60)

    if verbose and job_info.get('instance_details'):
        print_info("\nInstance Execution Details:")
        for idx, instance in enumerate(job_info['instance_details'], 1):
            instance_id = instance.get('instance_id', 'N/A')
            instance_status = instance.get('status', 'UNKNOWN')
            instance_output = instance.get('output', '')
            instance_error = instance.get('error', '')

            print_info(f"  Instance {idx}: {instance_id}")
            print_info(f"    Status: {instance_status}")
            if instance_error:
                print_error(f"    Error: {instance_error}")
            if instance_output:
                print_info(f"    Output: {instance_output[:200]}...")

    return job_info


def wait_for_job(execute_uuid, timeout=1800, interval=60):
    """Wait for COC job completion"""
    print_header("Waiting for COC Script Execution Completion")
    print_info(f"Execution UUID: {execute_uuid}")
    print_info(f"Timeout: {timeout} seconds ({timeout/60:.0f} minutes)")
    print_info(f"Polling Interval: {interval} seconds")
    print("=" * 60)

    success, job_info = wait_for_execution_completion(
        client=None,
        execute_uuid=execute_uuid,
        timeout=timeout,
        interval=interval
    )

    if success:
        print_success("任务执行成功!")
    elif job_info:
        print_error("任务执行失败或超时")
    else:
        print_error("任务执行状态未知")

    return success, job_info


def main():
    parser = argparse.ArgumentParser(
        description='COC Remote Script Execution Status Query Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Query single task status
  python query_coc_status.py --uuid SCT20250101000000000000000

  # Query with verbose output
  python query_coc_status.py --uuid SCT20250101000000000000000 --verbose

  # Wait for task completion
  python query_coc_status.py --uuid SCT20250101000000000000000 --wait

  # Custom wait time and polling interval
  python query_coc_status.py --uuid SCT20250101000000000000000 --wait --timeout 3600 --interval 30

  # Load UUID from JSON file (for execute_uuid saved during deployment)
  python query_coc_status.py --from-file new_instance_info.json
        """
    )

    parser.add_argument('--uuid', '-u',
                        help='COC execution UUID (e.g. SCT20250101000000000000000)')

    parser.add_argument('--from-file', '-f',
                        help='Read COC execution UUID from JSON file')

    parser.add_argument('--key', '-k',
                        default='execute_uuid',
                        help='Key name storing UUID in JSON file (default: execute_uuid)')

    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Show verbose output')

    parser.add_argument('--wait', '-w',
                        action='store_true',
                        help='Wait for task completion')

    parser.add_argument('--timeout', '-t',
                        type=int,
                        default=1800,
                        help='Wait timeout in seconds, default 1800s (30 minutes)')

    parser.add_argument('--interval', '-i',
                        type=int,
                        default=60,
                        help='Polling interval in seconds, default 60s')

    args = parser.parse_args()

    execute_uuid = None

    if args.uuid:
        execute_uuid = args.uuid
    elif args.from_file:
        file_path = Path(args.from_file)
        if not file_path.exists():
            print_error(f"File not found: {file_path}")
            sys.exit(1)

        data = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print_error(f"Failed to read JSON file: {e}")
            sys.exit(1)

        execute_uuid = data.get(args.key)
        if not execute_uuid:
            print_error(f"Key '{args.key}' not found in file")
            print_info(f"File content: {json.dumps(data, indent=2, ensure_ascii=False)}")
            sys.exit(1)

        print_info(f"UUID retrieved from file: {execute_uuid}")
    else:
        parser.print_help()
        print("\n")
        print_error("Please provide --uuid or --from-file parameter")
        sys.exit(1)

    if args.wait:
        success, job_info = wait_for_job(execute_uuid, args.timeout, args.interval)
        sys.exit(0 if success else 1)
    else:
        job_info = query_single_job(execute_uuid, verbose=args.verbose)
        if job_info:
            status = job_info.get('status', 'UNKNOWN')
            if status == 'FINISHED':
                sys.exit(0)
            elif status in ['ABNORMAL', 'CANCELED', 'FAILED']:
                sys.exit(1)
            else:
                sys.exit(0)
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
