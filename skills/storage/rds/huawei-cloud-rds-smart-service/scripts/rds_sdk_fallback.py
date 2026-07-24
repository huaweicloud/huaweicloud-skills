#!/usr/bin/env python3
"""RDS Smart Service - SDK Fallback Executor

Executes RDS operations via Python SDK when CLI is unavailable.
This is a fallback module called by rds_cli.sh.
"""

import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_credentials():
    """Build BasicCredentials from environment variables."""
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
    except ImportError:
        logger.error("huaweicloudsdkcore not installed")
        sys.exit(1)

    ak = os.environ.get('HUAWEI_ACCESS_KEY') or os.environ.get('HWC_AK')
    sk = os.environ.get('HUAWEI_SECRET_KEY') or os.environ.get('HWC_SK')
    project_id = os.environ.get('HUAWEI_PROJECT_ID') or os.environ.get('HWC_PROJECT_ID')

    if not ak or not sk:
        logger.error("Missing AK/SK credentials. Set HUAWEI_ACCESS_KEY and HUAWEI_SECRET_KEY environment variables.")
        sys.exit(1)

    creds = BasicCredentials().with_ak(ak).with_sk(sk)
    if project_id:
        creds = creds.with_project_id(project_id)
    return creds


def get_client(region=None):
    """Build RDS client for specified region."""
    try:
        from huaweicloudsdkrds.v3.rds_client import RdsClient
        from huaweicloudsdkcore.region.region import Region
    except ImportError:
        logger.error("huaweicloudsdkrds not installed")
        sys.exit(1)

    region = region or os.environ.get('HUAWEI_REGION', 'cn-north-4')
    creds = get_credentials()

    client = RdsClient.new_builder() \
        .with_credentials(creds) \
        .with_region(Region.value_of(region)) \
        .build()
    return client


def list_instances(client, params):
    """List RDS instances."""
    from huaweicloudsdkrds.v3.model.list_instances_request import ListInstancesRequest
    request = ListInstancesRequest()
    if 'datastore_type' in params:
        request.datastore_type = params['datastore_type']
    response = client.list_instances(request)
    return response.to_dict() if hasattr(response, 'to_dict') else str(response)


def list_flavors(client, params):
    """List RDS flavors."""
    from huaweicloudsdkrds.v3.model.list_flavors_request import ListFlavorsRequest
    request = ListFlavorsRequest()
    if 'database_name' in params:
        request.database_name = params['database_name']
    if 'version_name' in params:
        request.version_name = params['version_name']
    response = client.list_flavors(request)
    return response.to_dict() if hasattr(response, 'to_dict') else str(response)


def show_backup_policy(client, params):
    """Show backup policy for an instance."""
    from huaweicloudsdkrds.v3.model.show_backup_policy_request import ShowBackupPolicyRequest
    if 'instance_id' not in params:
        return {"error": "instance_id is required"}
    request = ShowBackupPolicyRequest(instance_id=params['instance_id'])
    response = client.show_backup_policy(request)
    return response.to_dict() if hasattr(response, 'to_dict') else str(response)


def list_backups(client, params):
    """List backups for an instance."""
    from huaweicloudsdkrds.v3.model.list_backups_request import ListBackupsRequest
    request = ListBackupsRequest()
    if 'instance_id' in params:
        request.instance_id = params['instance_id']
    response = client.list_backups(request)
    return response.to_dict() if hasattr(response, 'to_dict') else str(response)


# Operation mapping
OPERATIONS = {
    'ListInstances': list_instances,
    'ListFlavors': list_flavors,
    'ShowBackupPolicy': show_backup_policy,
    'ListBackups': list_backups,
}


def parse_args(args):
    """Parse command-line arguments into operation and params dict."""
    if not args:
        return None, {}

    operation = args[0]
    params = {}
    for arg in args[1:]:
        if arg.startswith('--'):
            key, _, value = arg[2:].partition('=')
            params[key.replace('-', '_')] = value
    return operation, params


def main():
    operation, params = parse_args(sys.argv[1:])

    if not operation:
        logger.error("No operation specified")
        sys.exit(1)

    region = params.pop('cli_region', None) or params.pop('region', None)
    client = get_client(region)

    handler = OPERATIONS.get(operation)
    if not handler:
        logger.error(f"Unsupported operation: {operation}")
        logger.info(f"Supported operations: {', '.join(OPERATIONS.keys())}")
        sys.exit(1)

    try:
        result = handler(client, params)
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        logger.error(f"SDK execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
