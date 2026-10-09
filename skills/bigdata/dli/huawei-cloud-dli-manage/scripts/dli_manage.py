#!/usr/bin/env python3
"""huawei-cloud-dli-manage — Huawei Cloud DLI (Data Lake Insight) resource management.

CLI wrapper that dispatches to `hcloud dli <Operation>` for queue / batch job /
Flink job / database / table / connection / resource package / global variable /
job template / privilege & patrol management. Read-only by default; mutating and
high-risk operations require --confirm so agents do not auto-execute them.

Quality reporting: vendored skill_quality_sdk (scripts/skill_quality_sdk.py).
"""
import argparse
import json
import os
import subprocess
import sys

from skill_quality_sdk import quality_report

HCLOUD = os.environ.get("HCLOUD_BIN", "hcloud")
REGION = os.environ.get("HUAWEICLOUD_SDK_REGION", "cn-north-4")

HIGH_RISK_OPS = {
    "DeleteDatabase", "DeleteTable", "DeleteQueue", "DeleteQueuePlan",
    "CancelSqlJob", "CancelSparkJob", "BatchDeleteFlinkJobs", "DeleteFlinkJob",
    "BatchStopFlinkJobs", "BatchRunFlinkJobs", "DeleteEnhancedConnection",
    "DeleteDatasourceConnection", "DeleteJobResource", "DeleteGlobalVariable",
    "BatchDeleteSqlJobTemplates", "DeleteFlinkSqlJobTemplate",
    "RunQueueAction", "UpdateElasticResourcePool",
}


def run_hcloud(operation, params, confirm=False, region=None):
    """Execute one hcloud dli operation. Returns parsed JSON on success."""
    if operation in HIGH_RISK_OPS and not confirm:
        raise SystemExit(
            f"refused: {operation} is a high-risk operation; re-run with --confirm "
            "and user explicit approval"
        )
    cmd = [HCLOUD, "dli", operation, f"--cli-region={region or REGION}"]
    for key, value in params.items():
        if value is None:
            continue
        cmd.append(f"--{key}={value}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"hcloud dli {operation} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout.strip()}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="huawei-cloud-dli-manage",
        description="Huawei Cloud DLI resource management via hcloud CLI",
    )
    parser.add_argument("--region", default=None, help=f"Region (default {REGION})")
    parser.add_argument("--confirm", action="store_true",
                        help="Acknowledge high-risk operation after user double confirmation")
    sub = parser.add_subparsers(dest="group", required=True)

    # --- queue management ---
    q = sub.add_parser("queues", help="queue management: list/show")
    q.add_argument("--queue_name", help="specific queue")
    q.add_argument("--queue_type", choices=["sql", "general", "all"], default="all")
    q.add_argument("--with-charge-info", action="store_true")
    q.add_argument("--create", action="store_true", help="create queue (requires --cu_count)")
    q.add_argument("--cu_count", type=int, help="CU count for create/scale")
    q.add_argument("--delete", action="store_true", help="delete queue (high risk)")
    q.add_argument("--action", choices=["scale_out", "scale_in"],
                   help="RunQueueAction scale action (scale_in is high risk)")

    # --- batch jobs ---
    j = sub.add_parser("jobs", help="batch jobs (SQL/Spark): list/show")
    j.add_argument("--engine", choices=["sql", "spark"], default="sql")
    j.add_argument("--job_id", help="SQL job id")
    j.add_argument("--batch_id", help="Spark batch id")
    j.add_argument("--job-status", default=None, help="SQL job status filter")
    j.add_argument("--state", default=None, help="Spark job state filter")
    j.add_argument("--cancel", action="store_true", help="cancel job (high risk)")
    j.add_argument("--page-size", type=int, default=10)
    j.add_argument("--size", type=int, default=10)

    # --- flink jobs ---
    f = sub.add_parser("flink", help="Flink stream jobs: list/show/start/stop/delete")
    f.add_argument("--job_id", help="flink job id")
    f.add_argument("--status", default=None, help="flink job status filter")
    f.add_argument("--limit", type=int, default=20)
    f.add_argument("--start", action="store_true", help="start jobs (high risk)")
    f.add_argument("--stop", action="store_true", help="stop jobs (high risk)")
    f.add_argument("--delete", action="store_true", help="delete jobs (high risk)")

    # --- metadata (databases/tables) ---
    m = sub.add_parser("metadata", help="databases/tables: list/show/owner")
    m.add_argument("--database_name", required=True)
    m.add_argument("--table_name", help="table name")
    m.add_argument("--new_owner", help="new owner for update-owner")
    m.add_argument("--limit", type=int, default=50)

    # --- connections ---
    c = sub.add_parser("connections", help="enhanced/datasource connections + connectivity test")
    c.add_argument("--connection_id", help="connection id")
    c.add_argument("--queue_name", help="queue for connectivity test / binding")
    c.add_argument("--address", help="address for CreateConnectivityTask (ip:port)")
    c.add_argument("--task_id", help="connectivity task id")
    c.add_argument("--limit", type=int, default=20)

    # --- resources / variables / templates ---
    r = sub.add_parser("resources", help="resource packages: list/show")
    r.add_argument("--kind", default=None, choices=["jar", "pyFile", "file"])
    r.add_argument("--resource_name", help="resource name")
    v = sub.add_parser("variables", help="global variables: list")
    v.add_argument("--limit", type=int, default=50)
    t = sub.add_parser("templates", help="SQL job templates: list")
    t.add_argument("--keyword", default=None)

    # --- patrol ---
    p = sub.add_parser("patrol", help="resource patrol: queues+pools+quota+jobs")
    p.add_argument("--with-charge-info", action="store_true")

    return parser


@quality_report(skill_name="huawei-cloud-dli-manage", skill_version="1.0.0")
def main(argv=None):
    args = build_parser().parse_args(argv)
    region = args.region or REGION
    out = {}

    if args.group == "queues":
        if args.create:
            if not args.queue_name or not args.cu_count:
                raise SystemExit("queues --create requires --queue_name and --cu_count")
            out = run_hcloud("CreateQueue", {"queue_name": args.queue_name,
                                             "cu_count": args.cu_count,
                                             "queue_type": None if args.queue_type == "all" else args.queue_type},
                             confirm=args.confirm, region=region)
        elif args.delete:
            out = run_hcloud("DeleteQueue", {"queue_name": args.queue_name},
                             confirm=args.confirm, region=region)
        elif args.action:
            if args.action == "scale_in" and not args.confirm:
                raise SystemExit("refused: scale_in is high risk; pass --confirm after user approval")
            out = run_hcloud("RunQueueAction", {"queue_name": args.queue_name, "action": args.action,
                                                "cu_count": args.cu_count},
                             confirm=args.confirm, region=region)
        elif args.queue_name and not args.create:
            out = run_hcloud("ShowQueue", {"queue_name": args.queue_name}, region=region)
        else:
            params = {"queue_type": None if args.queue_type == "all" else args.queue_type}
            if args.with_charge_info:
                params["with-charge-info"] = "true"
            out = run_hcloud("ListQueues", params, region=region)

    elif args.group == "jobs":
        if args.cancel:
            if args.engine == "spark":
                out = run_hcloud("CancelSparkJob", {"batch_id": args.batch_id},
                                 confirm=args.confirm, region=region)
            else:
                out = run_hcloud("CancelSqlJob", {"job_id": args.job_id},
                                 confirm=args.confirm, region=region)
        elif args.engine == "spark" and args.batch_id:
            out = run_hcloud("ShowSparkJob", {"batch_id": args.batch_id}, region=region)
        elif args.engine == "sql" and args.job_id:
            out = run_hcloud("ShowSqlJobStatus", {"job_id": args.job_id}, region=region)
        elif args.engine == "spark":
            out = run_hcloud("ListSparkJobs", {"size": args.size, "state": args.state}, region=region)
        else:
            out = run_hcloud("ListSqlJobs", {"page-size": args.page_size,
                                             "job-status": getattr(args, "job-status", None)},
                             region=region)

    elif args.group == "flink":
        ids = [args.job_id] if args.job_id else []
        if args.start:
            params = {f"job_ids.{i + 1}": v for i, v in enumerate(ids)}
            if ids:
                out = run_hcloud("BatchRunFlinkJobs", params if ids else {"job_ids.1": "?"},
                                 confirm=args.confirm, region=region)
            else:
                raise SystemExit("flink --start requires --job_id")
        elif args.stop:
            if not ids:
                raise SystemExit("flink --stop requires --job_id")
            out = run_hcloud("BatchStopFlinkJobs", {f"job_ids.{i + 1}": v for i, v in enumerate(ids)},
                             confirm=args.confirm, region=region)
        elif args.delete:
            if not ids:
                raise SystemExit("flink --delete requires --job_id")
            out = run_hcloud("BatchDeleteFlinkJobs", {f"job_ids.{i + 1}": v for i, v in enumerate(ids)},
                             confirm=args.confirm, region=region)
        elif args.job_id:
            out = run_hcloud("ShowFlinkJob", {"job_id": args.job_id}, region=region)
        else:
            out = run_hcloud("ListFlinkJobs", {"limit": args.limit, "status": args.status}, region=region)

    elif args.group == "metadata":
        if args.new_owner:
            if args.table_name:
                out = run_hcloud("UpdateTableOwner",
                                 {"database_name": args.database_name, "table_name": args.table_name,
                                  "new_owner": args.new_owner}, confirm=args.confirm, region=region)
            else:
                out = run_hcloud("UpdateDatabaseOwner",
                                 {"database_name": args.database_name, "new_owner": args.new_owner},
                                 confirm=args.confirm, region=region)
        elif args.table_name:
            out = run_hcloud("ShowTable", {"database_name": args.database_name,
                                           "table_name": args.table_name}, region=region)
        else:
            out = run_hcloud("ListTables", {"database_name": args.database_name,
                                            "page-size": args.limit}, region=region)

    elif args.group == "connections":
        if args.task_id:
            out = run_hcloud("ShowConnectivityTask", {"queue_name": args.queue_name,
                                                      "task_id": args.task_id}, region=region)
        elif args.address:
            out = run_hcloud("CreateConnectivityTask", {"queue_name": args.queue_name,
                                                        "address": args.address}, region=region)
        elif args.connection_id:
            out = run_hcloud("ShowEnhancedConnection", {"connection_id": args.connection_id}, region=region)
        else:
            out = run_hcloud("ListEnhancedConnections", {"limit": args.limit}, region=region)

    elif args.group == "resources":
        if args.resource_name:
            out = run_hcloud("ShowJobResource", {"resource_name": args.resource_name}, region=region)
        else:
            out = run_hcloud("ListJobResources", {"kind": args.kind}, region=region)

    elif args.group == "variables":
        out = run_hcloud("ListGlobalVariables", {"limit": args.limit}, region=region)

    elif args.group == "templates":
        out = run_hcloud("ListSqlJobTemplates", {"keyword": args.keyword}, region=region)

    elif args.group == "patrol":
        report = {
            "queues": run_hcloud("ListQueues", {"queue_type": "all",
                                                "with-charge-info": "true" if args.with_charge_info else None},
                                 region=region),
            "databases": run_hcloud("ListDatabases", {"limit": 10}, region=region),
            "sql_jobs": run_hcloud("ListSqlJobs", {"page-size": 10}, region=region),
            "flink_jobs": run_hcloud("ListFlinkJobs", {"limit": 10}, region=region),
            "elastic_pools": run_hcloud("ListElasticResourcePools", {"limit": 10}, region=region),
            "quota": run_hcloud("ShowQuota", {}, region=region),
        }
        out = report

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())