#!/usr/bin/env python3
"""RDS Smart Service - Health Inspection Script

Performs a comprehensive health check on RDS instances.
Usage: python3 rds_health_check.py [--instance_id=xxx] [--region=cn-north-4]
"""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rds_sdk_fallback import get_client


def health_check(instance_id=None, region=None):
    """Run health check on RDS instances."""
    client = get_client(region)
    results = []

    # Step 1: List all instances (or specific one)
    from huaweicloudsdkrds.v3.model.list_instances_request import ListInstancesRequest
    request = ListInstancesRequest()
    if instance_id:
        request.instance_id = instance_id

    try:
        response = client.list_instances(request)
        instances = response.instances or []
    except Exception as e:
        print(json.dumps({"error": f"Failed to list instances: {e}"}, indent=2))
        return

    for inst in instances:
        result = {
            "instance_id": inst.id,
            "name": inst.name,
            "status": inst.status,
            "engine": inst.datastore.type if inst.datastore else None,
            "engine_version": inst.datastore.version if inst.datastore else None,
            "flavor": inst.flavor_ref,
            "disk_size": inst.volume.size if inst.volume else None,
            "checks": []
        }

        # Check 1: Instance status
        if inst.status == 'ACTIVE':
            result["checks"].append({"check": "status", "result": "PASS", "detail": "Instance is active"})
        else:
            result["checks"].append({"check": "status", "result": "WARN", "detail": f"Status: {inst.status}"})

        # Check 2: Backup policy
        try:
            from huaweicloudsdkrds.v3.model.show_backup_policy_request import ShowBackupPolicyRequest
            bp_req = ShowBackupPolicyRequest(instance_id=inst.id)
            bp_resp = client.show_backup_policy(bp_req)
            if bp_resp and bp_resp.backup_policy:
                result["checks"].append({"check": "backup_policy", "result": "PASS", "detail": "Backup policy configured"})
            else:
                result["checks"].append({"check": "backup_policy", "result": "WARN", "detail": "No backup policy"})
        except Exception:
            result["checks"].append({"check": "backup_policy", "result": "SKIP", "detail": "Could not query backup policy"})

        results.append(result)

    print(json.dumps({"health_check": results, "timestamp": datetime.now().isoformat()}, indent=2, default=str))


if __name__ == '__main__':
    instance_id = None
    region = None
    for arg in sys.argv[1:]:
        if arg.startswith('--instance_id='):
            instance_id = arg.split('=', 1)[1]
        elif arg.startswith('--region='):
            region = arg.split('=', 1)[1]

    health_check(instance_id, region)
