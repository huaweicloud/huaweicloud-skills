#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Query and manage Huawei Cloud BCS (Blockchain Service) resources.

Single entry point for both read-only inspection and state-changing operations.

Executor: huaweicloudsdkbcs Python SDK (v2 API). KooCLI only exposes BCS when its
local metadata cache contains the BCS service template, so the SDK is used here.
Execution-quality reporting is handled by skill-quality-cli (see SKILL.md).

Read-only subcommands never prompt for confirmation; write subcommands always
print an impact preview and require --confirm.

Subcommands (read-only):
  list                   List instances (id/name + detail enrichment)
  detail                 Show one instance detail
  nodes                  Show organization -> peer node information
  channels               List channels of an instance
  members                List union members
  notifications          List union invitation notifications
  flavors                Show supported specifications
  quotas                 Show resource quotas
  status                 Show instance creation/deployment status
  op-record              List asynchronous operation records
  alerts                 List instance alerts/events (--statistics for aggregation)
  metrics                Show instance/entity/node monitoring metrics
  events / events-statistic / metric / entity-metric / instance-metric
                         Original granular aliases kept for compatibility

SAFETY MODEL
  * Every mutating subcommand prints an impact preview and requires `--confirm`.
    Without `--confirm` the script returns exit code 2 and changes nothing.
  * Irreversible operations (delete instance / delete channel / remove peers /
    remove organizations / freeze certificate) are marked in the preview.
  * Asynchronous operations returning an operation_id are followed through
    ListOpRecord so the final BCS-side result is reported (default 60s wait,
    `--no-wait` to skip).

Subcommands (write: cert/sdk):
  download-cert          Download instance/organization certificates
  download-sdk-config    Download the Fabric SDK configuration file
  create-cert            Create a user certificate
  freeze-cert            Freeze (revoke) a user certificate
  unfreeze-cert          Unfreeze a user certificate

Subcommands (write: channel):
  create-channels        Batch create channels
  add-peers              Add peers to a channel
  remove-peers           Remove peers of an organization from a channel
  remove-orgs            Remove organizations from a channel
  delete-channel         Delete a channel

Subcommands (write: lifecycle):
  create-instance        Create a BCS instance
  update-instance        Scale/add or remove an organization
  delete-instance        Delete a BCS instance

Subcommands (write: union invitation):
  invite-members         Invite members to a channel
  delete-invite          Cancel a channel invitation
  handle-notification    Accept/reject a union invitation notification
  quit-union             Invitee leaves a union
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class QualityError(Exception):
    """Business failure carrying a standard error code (U/C/N/B/P prefix)."""

    def __init__(self, error_code, message):
        super().__init__(message)
        self.error_code = error_code
        self.message = message

DEFAULT_REGION = "cn-north-4"
SUPPORTED_REGIONS = "cn-north-1, cn-north-4, cn-south-1, cn-east-2"
# BCS documents "first five metrics" as the server-side default for
# ListBcsMetricRequestBody; send them explicitly so the behaviour is visible.
DEFAULT_METRIC_NAMES = [
    "cpuUsage",
    "diskUsedRate",
    "memUsedRate",
    "sendBytesRate",
    "recvBytesRate",
]


# ---------------------------------------------------------------------------
# credentials / client
# ---------------------------------------------------------------------------
def get_credentials():
    ak = (os.environ.get("HUAWEICLOUD_SDK_AK")
          or os.environ.get("HUAWEI_CLOUD_SDK_AK")
          or os.environ.get("HW_ACCESS_KEY"))
    sk = (os.environ.get("HUAWEICLOUD_SDK_SK")
          or os.environ.get("HUAWEI_CLOUD_SDK_SK")
          or os.environ.get("HW_SECRET_KEY"))
    token = os.environ.get("HW_SECURITY_TOKEN") or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")
    if not ak or not sk:
        raise QualityError(
            "C01",
            "AK/SK not configured. Set HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK.",
        )
    return ak, sk, token


def _sdk_error_code(exc):
    """Map an SDK exception to the skill's U/C error-code space."""
    if getattr(exc, "status_code", None) in (401, 403):
        return "U04"
    return "C02"


def build_client(region):
    ak, sk, token = get_credentials()
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkcore.exceptions import exceptions
        from huaweicloudsdkbcs.v2 import BcsClient
        from huaweicloudsdkbcs.v2.region.bcs_region import BcsRegion
    except ImportError:
        raise QualityError(
            "C01", "huaweicloudsdkbcs is not installed. Run: pip install huaweicloudsdkbcs"
        )
    try:
        region_obj = BcsRegion.value_of(region)
    except KeyError:
        raise QualityError("U02", f"BCS is not available in region '{region}'. Supported: {SUPPORTED_REGIONS}")

    creds = BasicCredentials(ak, sk)
    if token:
        creds = creds.with_security_token(token)
    try:
        return BcsClient.new_builder().with_credentials(creds).with_region(region_obj).build()
    except exceptions.SdkException as exc:
        # IAM project_id resolution / region authorization / transient credential
        # failures surface here (e.g. a region the account has no project in).
        raise QualityError(
            _sdk_error_code(exc),
            f"BCS client initialization failed (IAM project/region resolution): {exc}",
        )


def call_api(fn, request):
    from huaweicloudsdkcore.exceptions import exceptions
    try:
        return fn(request)
    except exceptions.ServiceResponseException as exc:
        code = "U04" if exc.status_code in (401, 403) else "N03"
        raise QualityError(code, f"BCS API error (HTTP {exc.status_code}): {exc.error_msg}")
    except exceptions.ClientRequestException as exc:
        raise QualityError("N03", f"BCS API request failed: {exc}")
    except QualityError:
        raise
    except Exception as exc:  # pragma: no cover - network/runtime guard
        raise QualityError("B01", f"Unexpected BCS SDK error: {exc}")


# ---------------------------------------------------------------------------
# generic output / selector helpers (shared by read and write commands)
# ---------------------------------------------------------------------------
def to_dict(obj):
    if obj is None:
        return {}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def compact(obj):
    """Drop None / empty collections recursively for readable JSON output."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is None or v == "" or v == [] or v == {}:
                continue
            out[k] = compact(v)
        return out
    if isinstance(obj, list):
        return [compact(v) for v in obj]
    return obj


def print_table(headers, rows):
    rows = [[("" if v is None else str(v)) for v in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))


def print_json(value):
    print(json.dumps(compact(value), indent=2, ensure_ascii=False, default=str))


def resolve_blockchain_id(client, blockchain_id=None, name=None):
    """Accept either a raw instance id or an instance name."""
    if blockchain_id:
        return blockchain_id
    if not name:
        raise QualityError("U01", "Provide --blockchain-id <id> or --name <instance-name>.")
    from huaweicloudsdkbcs.v2 import ListBlockchainsRequest
    resp = call_api(client.list_blockchains, ListBlockchainsRequest())
    matches = [b for b in (resp.blockchains or []) if getattr(b, "name", "") == name]
    if not matches:
        raise QualityError("U03", f"No BCS instance named '{name}' in this region.")
    if len(matches) > 1:
        raise QualityError("U02", f"Instance name '{name}' matches multiple instances; use --blockchain-id.")
    return matches[0].id


# ---------------------------------------------------------------------------
# safety helpers
# ---------------------------------------------------------------------------
def preview(args, lines, irreversible=False):
    """Print the impact preview and require --confirm before mutation."""
    title = "IRREVERSIBLE OPERATION" if irreversible else "WRITE OPERATION"
    print(f"=== {title} PREVIEW ({args.command}) ===")
    print(f"Region : {args.region}")
    for line in lines:
        print(f"  {line}")
    if irreversible:
        print("  Impact : this action cannot be undone. Verify the target id before proceeding.")
    if not args.confirm:
        print("\nNo change applied. Review the preview and re-run the same command with --confirm.")
        raise QualityError("U01", "Confirmation required: re-run with --confirm to execute this write operation.")
    print("\n--confirm received, executing...\n")


def load_body_file(path):
    if not path:
        raise QualityError("U01", "--body-file <json> is required for this operation.")
    if not os.path.isfile(path):
        raise QualityError("U02", f"Body file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise QualityError("U02", f"Body file is not valid JSON: {exc}")


def parse_json_arg(value, label):
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise QualityError("U02", f"{label} must be valid JSON: {exc}")


_JSON_STDOUT = None  # real stdout while --json routes human output to stderr


def dump(obj):
    """Emit a JSON block on the real stdout (never on the redirected stream)."""
    stream = _JSON_STDOUT or sys.stdout
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str), file=stream)


# ---------------------------------------------------------------------------
# async operation reporting
# ---------------------------------------------------------------------------
def report_operation(client, operation_id, wait_seconds=60, interval=5, region=DEFAULT_REGION):
    """Follow an asynchronous BCS operation through ListOpRecord."""
    from huaweicloudsdkbcs.v2 import ListOpRecordRequest
    if not operation_id:
        print("No operation_id returned by the API; nothing to poll.")
        return {}
    print(f"Operation id: {operation_id}")

    deadline = time.time() + max(0, wait_seconds)
    last = {}
    while True:
        resp = call_api(client.list_op_record, ListOpRecordRequest(operation_id=operation_id))
        records = resp.operation_records or []
        if records:
            last = to_dict(records[0])
            status = last.get("operation_status", "")
            print(f"  status={status or 'unknown'} desc={last.get('desc', '')}")
            if status in ("finished", "failed", "stop"):
                break
        if time.time() >= deadline:
            print(f"  not finished within {wait_seconds}s; query later with: "
                  f"python3 bcs_manage.py op-record --region {region} "
                  f"--operation-id {operation_id}")
            break
        time.sleep(interval)
    return last


def finish_write(client, resp, args):
    """Print operation summary and poll ListOpRecord unless --no-wait."""
    data = to_dict(resp)
    operation_id = data.get("operation_id", "")
    record = {}
    if operation_id and not args.no_wait:
        if not args.json and data:
            print("API response:")
            dump(data)
        record = report_operation(client, operation_id, wait_seconds=args.timeout, region=args.region)
    elif operation_id:
        print(f"Operation id: {operation_id} (not polled; --no-wait)")
    elif data and not args.json:
        print("API response:")
        dump(data)
    if args.json:
        dump({"response": data, "operation_record": record})
    return data


# ---------------------------------------------------------------------------
# read-only implementations
# ---------------------------------------------------------------------------
def query_list(client, args):
    from huaweicloudsdkbcs.v2 import ListBlockchainsRequest, ShowBlockchainDetailRequest
    resp = call_api(client.list_blockchains, ListBlockchainsRequest())
    instances = []
    for item in (resp.blockchains or []):
        instances.append({"id": getattr(item, "id", ""), "name": getattr(item, "name", "")})

    if not args.no_detail and instances:
        def enrich(inst):
            try:
                detail = call_api(
                    client.show_blockchain_detail,
                    ShowBlockchainDetailRequest(blockchain_id=inst["id"]),
                )
                basic = to_dict(detail.basic_info)
                for key in ("status", "version", "service_type", "charging_mode",
                            "cluster_name", "created_time", "consensus"):
                    inst[key] = basic.get(key, "")
                inst["version_type"] = basic.get("version_type", "")
                return inst
            except QualityError as exc:
                inst["detail_error"] = str(exc)
                return inst

        workers = max(1, min(args.workers, 10))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(enrich, inst) for inst in instances]
            for future in as_completed(futures):
                future.result()

    if args.json:
        print_json({"count": len(instances), "instances": instances})
        return {"count": len(instances)}
    if not instances:
        print("No BCS instances found in this region.")
        return {"count": 0}
    print(f"Total BCS instances: {len(instances)}")
    headers = ["ID", "NAME", "STATUS", "VERSION", "SERVICE_TYPE", "CHARGING_MODE", "CLUSTER_NAME", "CREATED_TIME"]
    rows = [[i.get("id"), i.get("name"), i.get("status", "-"), i.get("version", "-"),
             i.get("service_type", "-"), i.get("charging_mode", "-"),
             i.get("cluster_name", "-"), i.get("created_time", "-")] for i in instances]
    print_table(headers, rows)
    errors = [i for i in instances if i.get("detail_error")]
    if errors:
        print("\nWARNING: detail lookup failed for:")
        for i in errors:
            print(f"  - {i['id']} ({i['name']}): {i['detail_error']}")
    return {"count": len(instances)}


def query_detail(client, args):
    from huaweicloudsdkbcs.v2 import ShowBlockchainDetailRequest
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    resp = call_api(client.show_blockchain_detail, ShowBlockchainDetailRequest(blockchain_id=bid))
    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}

    basic = to_dict(resp.basic_info)
    print("Basic information")
    for key in ("id", "name", "status", "process_status", "version", "version_type",
                "service_type", "purchase_type", "charging_mode", "consensus",
                "sign_algorithm", "database_type", "cluster_name", "cluster_type",
                "cluster_az", "deploy_type", "created_time"):
        print(f"  {key:16s}: {basic.get(key, '')}")

    channels = resp.channels or []
    print(f"\nChannels ({len(channels)})")
    if channels:
        print_table(
            ["NAME", "CONSENSUS", "CREATE_TIME", "PEER_ORGS"],
            [[c.name, c.consensus, c.create_time, ",".join((c.peers or {}).keys())] for c in channels],
        )

    print(f"\nPeer organizations ({len(resp.peer_info or [])})")
    if resp.peer_info:
        print_table(["ORG", "STATUS", "NODE_CNT", "DETAIL"],
                    [[p.name, p.status, p.node_cnt, p.status_detail] for p in resp.peer_info])

    if resp.orderer_info:
        o = resp.orderer_info
        print("\nOrderer")
        print(f"  name={o.name} status={o.status} node_cnt={o.node_cnt} detail={o.status_detail}")

    components = [
        ("CouchDB", resp.couch_db_info), ("SFS", resp.sfs_info),
        ("OBS", resp.obs_bucket_info), ("Kafka", resp.dms_kafka_info),
        ("IEF", resp.ief_info), ("REST API", resp.restapi_info), ("Agent", resp.agent_info),
    ]
    present = [(label, to_dict(value)) for label, value in components if value is not None]
    if present:
        print("\nAttached components")
        for label, value in present:
            flat = ", ".join(f"{k}={v}" for k, v in value.items() if v not in (None, "", []))
            print(f"  {label:10s}: {flat}")
    return {"blockchain_id": bid}


def query_nodes(client, args):
    from huaweicloudsdkbcs.v2 import ShowBlockchainNodesRequest
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    resp = call_api(client.show_blockchain_nodes, ShowBlockchainNodesRequest(blockchain_id=bid))
    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}
    orgs = resp.node_orgs or {}
    if not orgs:
        print("No organization/node information returned.")
        return {"blockchain_id": bid, "orgs": 0}
    rows = []
    for org_name, org in orgs.items():
        peers = org.peers or {}
        if not peers:
            rows.append([org_name, "-", "-", "-"])
        for node_name, node in peers.items():
            rows.append([org_name, node_name, node.ip_port, ",".join(node.channels or [])])
    print_table(["ORG", "NODE", "IP_PORT", "CHANNELS"], rows)
    print(f"\nOrganizations: {len(orgs)}  Nodes: {len(rows)}")
    return {"blockchain_id": bid, "orgs": len(orgs), "nodes": len(rows)}


def query_channels(client, args):
    from huaweicloudsdkbcs.v2 import ListBlockchainChannelsRequest
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    resp = call_api(client.list_blockchain_channels, ListBlockchainChannelsRequest(blockchain_id=bid))
    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}
    channels = resp.channels or []
    if not channels:
        print("No channels found for this instance.")
        return {"blockchain_id": bid, "count": 0}
    print_table(
        ["NAME", "CONSENSUS", "CREATE_TIME", "DESCRIPTION", "PEER_ORGS"],
        [[c.name, c.consensus, c.create_time, c.description, ",".join((c.peers or {}).keys())]
         for c in channels],
    )
    print(f"\nTotal channels: {len(channels)}")
    return {"blockchain_id": bid, "count": len(channels)}


def query_members(client, args):
    from huaweicloudsdkbcs.v2 import ListMembersRequest
    resp = call_api(client.list_members, ListMembersRequest())
    if args.json:
        print_json(to_dict(resp))
        return {"members": len(resp.members or [])}
    members = resp.members or []
    if not members:
        print("No union members found.")
        return {"members": 0}
    rows = []
    for m in members:
        invitor = to_dict(m.invitor_info)
        invitee = to_dict(m.invitee_info)
        invited = ",".join(o.name for o in (m.invited_orgs or []) if getattr(o, "name", None))
        rows.append([
            m.channel_name,
            invitor.get("invitor_bcs_name", ""),
            invitor.get("invitor_username", ""),
            invitee.get("invitee_bcs_name", ""),
            invitee.get("invitee_username", ""),
            invited,
        ])
    print_table(["CHANNEL", "INVITOR_BCS", "INVITOR_USER", "INVITEE_BCS", "INVITEE_USER", "INVITED_ORGS"], rows)
    return {"members": len(members)}


def query_notifications(client, args):
    from huaweicloudsdkbcs.v2 import ListNotificationsRequest
    resp = call_api(client.list_notifications, ListNotificationsRequest())
    if args.json:
        print_json(to_dict(resp))
        return {"notifications": len(resp.notifications or [])}
    items = resp.notifications or []
    if not items:
        print("No invitation notifications found.")
        return {"notifications": 0}
    rows = []
    for n in items:
        invitor = to_dict(n.invitor_info)
        rows.append([
            n.channel_name,
            n.status,
            n.updated_time,
            invitor.get("invitor_bcs_name", ""),
            ",".join(o.name for o in (n.invitee_orgs or []) if getattr(o, "name", None)),
            "read" if getattr(n, "read_status", 0) else "unread",
        ])
    print_table(["CHANNEL", "STATUS", "UPDATED_TIME", "INVITOR_BCS", "INVITEE_ORGS", "READ"], rows)
    return {"notifications": len(items)}


def query_flavors(client, args):
    from huaweicloudsdkbcs.v2 import ShowBlockchainFlavorsRequest
    resp = call_api(
        client.show_blockchain_flavors,
        ShowBlockchainFlavorsRequest(limit=args.limit, offset=args.offset),
    )
    if args.json:
        print_json(to_dict(resp))
        return {"flavors": 1}
    spec = to_dict(resp.enterprise_spec)
    print("Enterprise specification")
    for key in ("org_peer_max_num", "orderer_max_num", "member_max_num"):
        print(f"  {key:20s}: {spec.get(key, '')}")
    return {"flavors": 1}


def query_quotas(client, args):
    from huaweicloudsdkbcs.v2 import ListQuotasRequest
    resp = call_api(client.list_quotas, ListQuotasRequest())
    if args.json:
        print_json(to_dict(resp))
        return {"resources": len(resp.resources or [])}
    resources = resp.resources or []
    if not resources:
        print("No quota information returned.")
        return {"resources": 0}
    print_table(
        ["TYPE", "UNIT", "QUOTA", "USED", "FREE", "MIN", "MAX"],
        [[r.type, r.unit, r.quota, r.used, r.free, r.min, r.max] for r in resources],
    )
    return {"resources": len(resources)}


def query_status(client, args):
    from huaweicloudsdkbcs.v2 import ShowBlockchainStatusRequest
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    resp = call_api(client.show_blockchain_status, ShowBlockchainStatusRequest(blockchain_id=bid))
    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}
    labels = [("bcs", resp.bcs), ("eip", resp.eip), ("sfs", resp.sfs),
              ("obs", resp.obs), ("kafka", resp.kafka), ("cce", resp.cce)]
    rows = []
    for label, detail in labels:
        if detail is None:
            continue
        d = to_dict(detail)
        rows.append([label, d.get("status", ""), d.get("start_time", ""), d.get("end_time", ""), d.get("detail", "")])
    if not rows:
        print("No status detail returned.")
        return {"blockchain_id": bid}
    print_table(["COMPONENT", "STATUS", "START_TIME", "END_TIME", "DETAIL"], rows)
    return {"blockchain_id": bid}


def query_op_record(client, args):
    from huaweicloudsdkbcs.v2 import ListOpRecordRequest
    resp = call_api(
        client.list_op_record,
        ListOpRecordRequest(
            blockchain_id=args.blockchain_id,
            operation_status=args.operation_status,
            resource_type=args.resource_type,
            operation_type=args.operation_type,
            operation_id=args.operation_id,
        ),
    )
    if args.json:
        print_json(to_dict(resp))
        return {"count": resp.count}
    records = resp.operation_records or []
    print(f"Operation records: {len(records)} (total {resp.count})")
    if records:
        print_table(
            ["OPERATION_ID", "BCS_NAME", "OPERATION_TYPE", "STATUS", "RECORD_TIME", "DESC"],
            [[r.operation_id, r.blockchain_name, r.operation_type, r.operation_status,
              r.record_time, r.desc] for r in records],
        )
    return {"count": len(records)}


def _event_body(args):
    from huaweicloudsdkbcs.v2 import EventResultSort, ListBcsEventRequestBody
    sort = None
    if args.order_by:
        sort = EventResultSort(order_by=args.order_by.split(","), order=args.order or "desc")
    return ListBcsEventRequestBody(
        time_range=args.time_range,
        step=args.step,
        search=args.search,
        sort=sort,
    )


def _print_metrics(metrics, max_points):
    if not metrics:
        print("No metric/event data returned.")
        return
    for item in metrics:
        data = to_dict(item)
        metric = data.get("metric") or {}
        name = metric.get("name") or metric.get("metric_name") or "(unnamed metric)"
        dims = metric.get("dimensions") or metric.get("dimensions_value") or []
        dim_text = ", ".join(
            f"{d.get('name')}={d.get('value')}" if isinstance(d, dict) else str(d) for d in dims
        )
        points = data.get("data_points") or []
        print(f"\n[{name}] {dim_text}  data_points={len(points)}")
        shown = points[-max_points:] if max_points else points
        for p in shown:
            print(f"    {p.get('timestamp')}  {p.get('statistics')} {p.get('unit') or ''}")


def query_events(client, args, statistic=False):
    from huaweicloudsdkbcs.v2 import (ListBcsEventsRequest, ListBcsEventsStatisticRequest)
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    body = _event_body(args)
    request_cls = ListBcsEventsStatisticRequest if statistic else ListBcsEventsRequest
    resp = call_api(
        client.list_bcs_events_statistic if statistic else client.list_bcs_events,
        request_cls(blockchain_id=bid, type=args.type, body=body),
    )
    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}
    _print_metrics(resp.metrics, args.max_points)
    print(f"\nMetrics returned: {len(resp.metrics or [])}")
    return {"blockchain_id": bid, "metrics": len(resp.metrics or [])}


def query_metric(client, args, kind):
    from huaweicloudsdkbcs.v2 import (
        ListBcsMetricRequest, ListBcsMetricRequestBody,
        ListEntityMetricRequest, ListEntityMetricRequestBody,
        ListInstanceMetricRequest, ListInstanceMetricRequestBody,
    )
    bid = resolve_blockchain_id(client, args.blockchain_id, args.name)
    if args.user_time_range:
        # The BCS metric request models expose no time-window field, so the value
        # cannot be transmitted; surface that instead of silently dropping it.
        print(
            "WARNING: BCS metric APIs have no time-window parameter; "
            f"--time-range={args.user_time_range} is accepted for CLI consistency "
            "but is NOT sent. BCS applies its own server-side default window.",
            file=sys.stderr,
        )
    if kind == "instance":
        if not args.entity_name:
            raise QualityError("U01", "--entity-name is required for instance-metric.")
        body = ListInstanceMetricRequestBody(
            type=args.type, entity_name=args.entity_name, instance_name=args.instance_name
        )
        resp = call_api(client.list_instance_metric, ListInstanceMetricRequest(blockchain_id=bid, body=body))
    elif kind == "entity":
        body = ListEntityMetricRequestBody(type=args.type, entity_name=args.entity_name)
        resp = call_api(client.list_entity_metric, ListEntityMetricRequest(blockchain_id=bid, body=body))
    else:
        names = args.metric_names.split(",") if args.metric_names else list(DEFAULT_METRIC_NAMES)
        body = ListBcsMetricRequestBody(metric_names=names)
        resp = call_api(client.list_bcs_metric, ListBcsMetricRequest(blockchain_id=bid, body=body))

    if args.json:
        print_json(to_dict(resp))
        return {"blockchain_id": bid}
    _print_metrics(resp.metrics, args.max_points)
    print(f"\nMetrics returned: {len(resp.metrics or [])}")
    return {"blockchain_id": bid, "metrics": len(resp.metrics or [])}


def query_alerts(client, args):
    return query_events(client, args, statistic=args.statistics)


def query_metrics(client, args):
    kind = {"instance": "bcs", "entity": "entity", "node": "instance"}[args.scope]
    return query_metric(client, args, kind)


# ---------------------------------------------------------------------------
# request builders
# ---------------------------------------------------------------------------
def build_body(command, data):
    """Map a JSON body file onto the SDK request-body model."""
    try:
        return _build_body(command, data)
    except TypeError as exc:
        raise QualityError(
            "U02",
            f"Body contains an unknown or mistyped field for '{command}': {exc}",
        )


def _build_body(command, data):
    from huaweicloudsdkbcs.v2 import (
        BatchAddPeersToChannelRequestBody,
        BatchCreateChannelsRequestBody,
        BatchInviteMembersToChannelRequestBody,
        BatchRemoveOrgsFromChannelRequestBody,
        BatchRemovePeersFromChannelRequestBody,
        ChannelCreateInfo,
        CfgRequestBody,
        CreateBlockchainCertByUserNameRequestBody,
        CreateRequestBody,
        DeleteMemberInviteRequestBody,
        HandleNotificationInvitee,
        HandleNotificationInvitor,
        HandleNotificationOrg,
        HandleNotificationRequestBody,
        InvitationDetail,
        InvitedDomain,
        PeerChannelInfo,
        QuitUnionFromMemberListRequestBody,
        UpdateInstanceRequestBody,
    )

    if command == "create-instance":
        return CreateRequestBody(**data)
    if command == "update-instance":
        return UpdateInstanceRequestBody(**data)
    if command == "create-channels":
        channels = [ChannelCreateInfo(**c) for c in data.get("channels", [])]
        if not channels:
            raise QualityError("U01", "Body must contain a non-empty 'channels' array.")
        return BatchCreateChannelsRequestBody(channels=channels)
    if command == "add-peers":
        peers = [PeerChannelInfo(**c) for c in data.get("channel_peers", [])]
        if not peers:
            raise QualityError("U01", "Body must contain a non-empty 'channel_peers' array.")
        return BatchAddPeersToChannelRequestBody(channel_peers=peers)
    if command == "remove-peers":
        return BatchRemovePeersFromChannelRequestBody(
            org_name=data.get("org_name"), peers=data.get("peers")
        )
    if command == "remove-orgs":
        return BatchRemoveOrgsFromChannelRequestBody(org_names=data.get("org_names", []))
    if command == "download-sdk-config":
        return CfgRequestBody(**data)
    if command == "create-cert":
        return CreateBlockchainCertByUserNameRequestBody(security_mode=data.get("security_mode"))
    if command == "invite-members":
        users = [InvitedDomain(**u) for u in data.get("invited_userinfo", [])]
        return BatchInviteMembersToChannelRequestBody(
            bcs_id=data.get("bcs_id"),
            channel_name=data.get("channel_name"),
            invitor_username=data.get("invitor_username"),
            invited_userinfo=users,
        )
    if command == "delete-invite":
        details = [InvitationDetail(**d) for d in data.get("invited_userinfo", [])]
        return DeleteMemberInviteRequestBody(
            bcs_id=data.get("bcs_id"),
            channel_name=data.get("channel_name"),
            invited_userinfo=details,
        )
    if command == "handle-notification":
        invitor = data.get("invitor_info")
        invitee = data.get("invitee_info")
        orgs = [HandleNotificationOrg(**o) for o in data.get("invited_orgs", [])]
        return HandleNotificationRequestBody(
            channel_name=data.get("channel_name"),
            status=data.get("status"),
            invitor_info=HandleNotificationInvitor(**invitor) if invitor else None,
            invitee_info=HandleNotificationInvitee(**invitee) if invitee else None,
            invited_orgs=orgs or None,
        )
    if command == "quit-union":
        return QuitUnionFromMemberListRequestBody(**data)
    raise QualityError("U01", f"Unsupported body command: {command}")


# ---------------------------------------------------------------------------
# write implementations
# ---------------------------------------------------------------------------
def write_download(client, args):
    """Cert / SDK config downloads produce a binary stream written to disk."""
    from huaweicloudsdkbcs.v2 import DownloadBlockchainCertRequest, DownloadBlockchainSdkConfigRequest

    if args.command == "download-cert":
        request = DownloadBlockchainCertRequest(
            blockchain_id=args.blockchain_id,
            org_name=args.org_name,
            cert_type=args.cert_type,
        )
        call = client.download_blockchain_cert
        default_name = f"{args.blockchain_id}-{args.org_name}-{args.cert_type}.zip"
        lines = [
            f"Instance : {args.blockchain_id}",
            f"Org      : {args.org_name}",
            f"Cert type: {args.cert_type}",
        ]
    else:
        body = build_body("download-sdk-config", load_body_file(args.body_file))
        request = DownloadBlockchainSdkConfigRequest(blockchain_id=args.blockchain_id, body=body)
        call = client.download_blockchain_sdk_config
        default_name = f"{args.blockchain_id}-sdk-config.zip"
        lines = [f"Instance : {args.blockchain_id}"]

    out = args.out or default_name
    lines.append(f"Output   : {out}")
    lines.append("Artifact : contains private key material; stored with 0600 permissions")
    preview(args, lines, irreversible=False)

    print(f"Downloading artifact to {out}")
    print("Sensitivity: certificates/SDK config contain private key material; store them securely.")

    resp = call_api(call, request)

    def _write(stream):
        with open(out, "wb") as fh:
            fh.write(stream.read())
        # Certificates / SDK config carry private key material: owner-only.
        try:
            os.chmod(out, 0o600)
        except OSError:
            pass

    try:
        resp.consume_download_stream(_write)
    except Exception as exc:
        raise QualityError("B01", f"Failed to save downloaded artifact to {out}: {exc}")
    size = os.path.getsize(out) if os.path.isfile(out) else 0
    if size <= 0:
        if os.path.isfile(out):
            try:
                os.remove(out)
            except OSError:
                pass
        raise QualityError(
            "B01",
            f"Downloaded artifact is empty (0 bytes); removed {out}. "
            "The API returned no content - verify --cert-type / the request body.",
        )
    print(f"Saved {size} bytes to {out}")
    print("Security: the artifact contains sensitive certificate/key material. Do not commit or share it.")
    data = {"out": out, "bytes": size}
    if args.json:
        dump({"response": data, "operation_record": {}})
    return data


def write_create_cert(client, args):
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Org      : {args.org_name}",
        f"User     : {args.user_name}",
        f"Security mode: {args.security_mode}",
    ], irreversible=False)
    from huaweicloudsdkbcs.v2 import CreateBlockchainCertByUserNameRequest
    body = build_body("create-cert", {"security_mode": args.security_mode})
    resp = call_api(
        client.create_blockchain_cert_by_user_name,
        CreateBlockchainCertByUserNameRequest(
            blockchain_id=args.blockchain_id, org_name=args.org_name,
            user_name=args.user_name, body=body,
        ),
    )
    print("Certificate created.")
    return finish_write(client, resp, args)


def write_freeze(client, args, freeze=True):
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Org      : {args.org_name}",
        f"User     : {args.user_name}",
        f"Effect   : {'FREEZE (revoke) the user certificate' if freeze else 'UNFREEZE the user certificate'}",
    ], irreversible=freeze)
    from huaweicloudsdkbcs.v2 import FreezeCertRequest, UnfreezeCertRequest
    if freeze:
        resp = call_api(
            client.freeze_cert,
            FreezeCertRequest(blockchain_id=args.blockchain_id, org_name=args.org_name, user_name=args.user_name),
        )
        print("Certificate frozen.")
    else:
        resp = call_api(
            client.unfreeze_cert,
            UnfreezeCertRequest(blockchain_id=args.blockchain_id, org_name=args.org_name, user_name=args.user_name),
        )
        print("Certificate unfrozen.")
    return finish_write(client, resp, args)


def write_create_channels(client, args):
    body = build_body("create-channels", load_body_file(args.body_file))
    names = [c.channel_name for c in body.channels]
    preview(args, [f"Instance : {args.blockchain_id}", f"Channels : {', '.join(names)}"])
    from huaweicloudsdkbcs.v2 import BatchCreateChannelsRequest
    resp = call_api(
        client.batch_create_channels,
        BatchCreateChannelsRequest(blockchain_id=args.blockchain_id, body=body),
    )
    print(f"Channel creation submitted for: {', '.join(names)}")
    return finish_write(client, resp, args)


def write_add_peers(client, args):
    body = build_body("add-peers", load_body_file(args.body_file))
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Channels : {', '.join(p.channel_name for p in body.channel_peers)}",
    ])
    from huaweicloudsdkbcs.v2 import BatchAddPeersToChannelRequest
    resp = call_api(
        client.batch_add_peers_to_channel,
        BatchAddPeersToChannelRequest(blockchain_id=args.blockchain_id, body=body),
    )
    print("Add-peers request submitted.")
    return finish_write(client, resp, args)


def write_remove_peers(client, args):
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Channel  : {args.channel_id}",
        f"Org      : {args.org_name}",
        f"Peers    : {args.peers}",
    ], irreversible=True)
    from huaweicloudsdkbcs.v2 import BatchRemovePeersFromChannelRequest
    body = build_body("remove-peers", {"org_name": args.org_name, "peers": args.peers})
    resp = call_api(
        client.batch_remove_peers_from_channel,
        BatchRemovePeersFromChannelRequest(
            blockchain_id=args.blockchain_id, channel_id=args.channel_id, body=body,
        ),
    )
    print("Peer removal submitted.")
    return finish_write(client, resp, args)


def write_remove_orgs(client, args):
    org_names = [o.strip() for o in args.org_names.split(",") if o.strip()]
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Channel  : {args.channel_id}",
        f"Orgs     : {', '.join(org_names)}",
    ], irreversible=True)
    from huaweicloudsdkbcs.v2 import BatchRemoveOrgsFromChannelRequest
    body = build_body("remove-orgs", {"org_names": org_names})
    resp = call_api(
        client.batch_remove_orgs_from_channel,
        BatchRemoveOrgsFromChannelRequest(
            blockchain_id=args.blockchain_id, channel_id=args.channel_id, body=body,
        ),
    )
    print("Organization removal submitted.")
    return finish_write(client, resp, args)


def write_delete_channel(client, args):
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Channel  : {args.channel_id}",
    ], irreversible=True)
    from huaweicloudsdkbcs.v2 import DeleteChannelRequest
    resp = call_api(
        client.delete_channel,
        DeleteChannelRequest(blockchain_id=args.blockchain_id, channel_id=args.channel_id),
    )
    print("Channel deletion submitted.")
    return finish_write(client, resp, args)


def write_create_instance(client, args):
    data = load_body_file(args.body_file)
    preview(args, [
        f"Name        : {data.get('name')}",
        f"Type        : {data.get('blockchain_type', 'private')}",
        f"Version     : Fabric {data.get('fabric_version', '?')}",
        f"Consensus   : {data.get('consensus', '?')}",
        f"Orgs/Peers  : {len(data.get('peer_orgs') or [])}",
        "Cost        : creating an instance incurs charges (billing mode varies by spec).",
    ])
    from huaweicloudsdkbcs.v2 import CreateNewBlockchainRequest
    body = build_body("create-instance", data)
    resp = call_api(client.create_new_blockchain, CreateNewBlockchainRequest(body=body))
    print("Instance creation submitted.")
    if not args.json:
        created = to_dict(resp)
        print(f"  blockchain_id   : {created.get('blockchain_id', '')}")
        print(f"  blockchain_name : {created.get('blockchain_name', '')}")
    return finish_write(client, resp, args)


def write_update_instance(client, args):
    data = load_body_file(args.body_file)
    # Build the SDK model first: node_orgs is a list[NodeOrgs] (objects with
    # name/node_count), so the preview must read the parsed model, not the raw body.
    body = build_body("update-instance", data)
    delete_org = bool(getattr(body, "is_delete_org", None) or data.get("is_delete_org", False))
    orgs = []
    for org in (getattr(body, "node_orgs", None) or []):
        # Request models keep nested bodies as raw dicts; response models use
        # objects. Support both so the preview never stringifies a dict.
        if isinstance(org, dict):
            name, node_count = org.get("name"), org.get("node_count")
        else:
            name, node_count = getattr(org, "name", None), getattr(org, "node_count", None)
        name = name or "?"
        orgs.append(f"{name}({node_count} nodes)" if node_count is not None else str(name))
    lines = [
        f"Instance : {args.blockchain_id}",
        f"Node orgs: {', '.join(orgs) if orgs else '(none)'}",
        f"Delete org: {delete_org}",
    ]
    if delete_org:
        lines += [
            "Removing an organization deletes its peers and channel data; the",
            "organization cannot be re-added with its previous state.",
        ]
    preview(args, lines, irreversible=delete_org)
    from huaweicloudsdkbcs.v2 import UpdateInstanceRequest
    resp = call_api(
        client.update_instance,
        UpdateInstanceRequest(blockchain_id=args.blockchain_id, body=body),
    )
    print("Instance update submitted.")
    return finish_write(client, resp, args)


def write_delete_instance(client, args):
    preview(args, [
        f"Instance : {args.blockchain_id}",
        f"Delete storage (EVS) : {args.delete_storage}",
        f"Delete OBS           : {args.delete_obs}",
        f"Delete CCE resources : {args.delete_resource}",
        f"Delete IEF resources : {args.delete_ief}",
        "All data on the instance will be lost.",
    ], irreversible=True)
    from huaweicloudsdkbcs.v2 import DeleteBlockchainRequest
    resp = call_api(
        client.delete_blockchain,
        DeleteBlockchainRequest(
            blockchain_id=args.blockchain_id,
            is_delete_storage=args.delete_storage,
            is_delete_obs=args.delete_obs,
            is_delete_resource=args.delete_resource,
            is_delete_ief=args.delete_ief,
        ),
    )
    print("Instance deletion submitted.")
    return finish_write(client, resp, args)


def _generic_body_write(client, args, body_command, request_cls, call, description):
    body = build_body(body_command, load_body_file(args.body_file))
    preview(args, [f"Operation : {description}", f"Body file : {args.body_file}"])
    resp = call_api(call, request_cls(body=body))
    print(f"{description} submitted.")
    return finish_write(client, resp, args)


def write_invite(client, args):
    from huaweicloudsdkbcs.v2 import BatchInviteMembersToChannelRequest
    return _generic_body_write(client, args, "invite-members",
                               BatchInviteMembersToChannelRequest,
                               client.batch_invite_members_to_channel,
                               "Member invitation")


def write_delete_invite(client, args):
    from huaweicloudsdkbcs.v2 import DeleteMemberInviteRequest
    return _generic_body_write(client, args, "delete-invite",
                               DeleteMemberInviteRequest,
                               client.delete_member_invite,
                               "Invitation cancellation")


def write_handle_notification(client, args):
    from huaweicloudsdkbcs.v2 import HandleNotificationRequest
    return _generic_body_write(client, args, "handle-notification",
                               HandleNotificationRequest,
                               client.handle_notification,
                               "Invitation handling")


def write_quit_union(client, args):
    from huaweicloudsdkbcs.v2 import HandleUnionMemberQuitListRequest
    return _generic_body_write(client, args, "quit-union",
                               HandleUnionMemberQuitListRequest,
                               client.handle_union_member_quit_list,
                               "Union quit request")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def add_common(p):
    p.add_argument("--region", default=DEFAULT_REGION, help="Huawei Cloud region (default cn-north-4)")
    p.add_argument("--json", action="store_true", help="Emit JSON for the final operation record")
    p.add_argument("--confirm", action="store_true", help="Required to actually execute the write operation")
    p.add_argument("--no-wait", action="store_true", help="Do not poll ListOpRecord for completion")
    p.add_argument("--timeout", type=int, default=60, help="Seconds to wait for the async operation (default 60)")


def add_query_common(p):
    p.add_argument("--region", default=DEFAULT_REGION, help="Huawei Cloud region (default cn-north-4)")
    p.add_argument("--json", action="store_true", help="Emit a single structured JSON payload")


def add_instance_selector(p):
    p.add_argument("--blockchain-id", help="BCS instance id")
    p.add_argument("--name", help="BCS instance name (resolved to id)")


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Query and manage Huawei Cloud BCS (Blockchain Service): read-only "
            "inspection plus state-changing operations."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- read-only subcommands (no --confirm) -----------------------------
    p = sub.add_parser("list", help="List BCS instances")
    add_query_common(p)
    p.add_argument("--no-detail", action="store_true", help="Skip detail enrichment (faster)")
    p.add_argument("--workers", type=int, default=4, help="Concurrent detail lookups (default 4)")
    p.set_defaults(func=query_list)

    p = sub.add_parser("detail", help="Show one instance detail")
    add_query_common(p)
    add_instance_selector(p)
    p.set_defaults(func=query_detail)

    p = sub.add_parser("nodes", help="Show organization and node information")
    add_query_common(p)
    add_instance_selector(p)
    p.set_defaults(func=query_nodes)

    p = sub.add_parser("channels", help="List channels of an instance")
    add_query_common(p)
    add_instance_selector(p)
    p.set_defaults(func=query_channels)

    p = sub.add_parser("members", help="List union members")
    add_query_common(p)
    p.set_defaults(func=query_members)

    p = sub.add_parser("notifications", help="List union invitation notifications")
    add_query_common(p)
    p.set_defaults(func=query_notifications)

    p = sub.add_parser("flavors", help="Show supported specifications")
    add_query_common(p)
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.set_defaults(func=query_flavors)

    p = sub.add_parser("quotas", help="Show BCS resource quotas")
    add_query_common(p)
    p.set_defaults(func=query_quotas)

    p = sub.add_parser("status", help="Show instance deployment status")
    add_query_common(p)
    add_instance_selector(p)
    p.set_defaults(func=query_status)

    p = sub.add_parser("op-record", help="List asynchronous operation records")
    add_query_common(p)
    p.add_argument("--blockchain-id", help="Filter by BCS instance id")
    p.add_argument("--operation-id", help="Filter by operation id")
    p.add_argument("--operation-status", choices=["waiting", "processing", "finished", "failed", "stop"])
    p.add_argument("--operation-type", help="e.g. 99(create),00(delete),01(upgrade),02(add org),03(scale org)")
    p.add_argument("--resource-type", help="e.g. BCSSVC01")
    p.set_defaults(func=query_op_record)

    def add_alert_args(p):
        p.add_argument("--type", choices=["active_alert", "history_alert"],
                       help="active_alert=current alerts, history_alert=historical alerts")
        p.add_argument("--time-range", default="-1.-1.60",
                       help="Query window, default last 60 minutes (-1.-1.60)")
        p.add_argument("--step", type=int, help="Statistical step in milliseconds")
        p.add_argument("--search", help="Fuzzy match keyword")
        p.add_argument("--order-by", help="Comma-separated sort fields")
        p.add_argument("--order", choices=["asc", "desc"], default="desc")
        p.add_argument("--max-points", type=int, default=10,
                       help="Print only the latest N data points per metric (default 10)")

    p = sub.add_parser("alerts", help="List instance alerts/events")
    add_query_common(p)
    add_instance_selector(p)
    add_alert_args(p)
    p.add_argument("--statistics", action="store_true",
                   help="Return aggregated alert statistics for the window")
    p.set_defaults(func=query_alerts)

    for name, statistic in (("events", False), ("events-statistic", True)):
        p = sub.add_parser(name, help="List instance events/alerts" + (" statistics" if statistic else ""))
        add_query_common(p)
        add_instance_selector(p)
        add_alert_args(p)
        p.set_defaults(func=lambda c, a, s=statistic: query_events(c, a, statistic=s))

    def add_metric_args(p):
        p.add_argument("--type", help="Entity type: org or plugin")
        p.add_argument("--entity-name", help="Organization/or plugin name")
        p.add_argument("--instance-name", help="Node (pod) name, node scope only")
        p.add_argument("--metric-names", help="Comma-separated metric names, instance scope only "
                                              "(default: first five BCS metrics)")
        p.add_argument("--time-range", dest="user_time_range", default=None,
                       help="Accepted for CLI consistency only: BCS metric APIs have no "
                            "time-window parameter, so BCS applies its server-side default window")
        p.add_argument("--max-points", type=int, default=10,
                       help="Print only the latest N data points per metric (default 10)")

    p = sub.add_parser("metrics", help="Show instance/entity/node monitoring metrics")
    add_query_common(p)
    add_instance_selector(p)
    p.add_argument("--scope", choices=["instance", "entity", "node"], default="instance",
                   help="instance=whole-instance metrics, entity=org/plugin, node=single peer/orderer")
    add_metric_args(p)
    p.set_defaults(func=query_metrics)

    for name, kind in (("metric", "bcs"), ("entity-metric", "entity"), ("instance-metric", "instance")):
        p = sub.add_parser(name, help=f"Show {kind} monitoring metrics")
        add_query_common(p)
        add_instance_selector(p)
        add_metric_args(p)
        p.set_defaults(func=lambda c, a, k=kind: query_metric(c, a, k))

    # ---- write subcommands (impact preview + --confirm) --------------------
    p = sub.add_parser("download-cert", help="Download instance/organization certificates")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--org-name", required=True, help="order or peer organization name")
    p.add_argument("--cert-type", required=True, help="Certificate category required by BCS")
    p.add_argument("--out", help="Output file path")
    p.set_defaults(func=write_download)

    p = sub.add_parser("download-sdk-config", help="Download Fabric SDK configuration")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--body-file", help="JSON body (channel_name, chaincode_name, peer_orgs, ...)")
    p.add_argument("--out", help="Output file path")
    p.set_defaults(func=write_download)

    p = sub.add_parser("create-cert", help="Create a user certificate")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--org-name", required=True, help="peer organization name")
    p.add_argument("--user-name", required=True, help="4-24 lowercase letters/digits, starts with a letter")
    p.add_argument("--security-mode", default="true", choices=["true", "false"],
                   help="true=system-managed certificate, false=user-managed (default true)")
    p.set_defaults(func=write_create_cert)

    for name, freeze in (("freeze-cert", True), ("unfreeze-cert", False)):
        p = sub.add_parser(name, help=("Freeze" if freeze else "Unfreeze") + " a user certificate")
        add_common(p)
        p.add_argument("--blockchain-id", required=True)
        p.add_argument("--org-name", required=True)
        p.add_argument("--user-name", required=True)
        p.set_defaults(func=lambda c, a, f=freeze: write_freeze(c, a, freeze=f))

    p = sub.add_parser("create-channels", help="Batch create channels")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--body-file", required=True, help='JSON: {"channels":[{"channel_name":..,"channel_description":..}]}')
    p.set_defaults(func=write_create_channels)

    p = sub.add_parser("add-peers", help="Add peers to channels")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--body-file", required=True, help='JSON: {"channel_peers":[{"channel_name":..,"peers":{"org":1}}]}')
    p.set_defaults(func=write_add_peers)

    p = sub.add_parser("remove-peers", help="Remove peers of an organization from a channel")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--channel-id", required=True, help="Channel name (as returned by show detail)")
    p.add_argument("--org-name", required=True)
    p.add_argument("--peers", type=int, required=True, help="Number of peers to remove")
    p.set_defaults(func=write_remove_peers)

    p = sub.add_parser("remove-orgs", help="Remove organizations from a channel")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.add_argument("--org-names", required=True, help="Comma-separated organization names")
    p.set_defaults(func=write_remove_orgs)

    p = sub.add_parser("delete-channel", help="Delete a channel")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--channel-id", required=True)
    p.set_defaults(func=write_delete_channel)

    p = sub.add_parser("create-instance", help="Create a BCS instance")
    add_common(p)
    p.add_argument("--body-file", required=True, help="JSON CreateRequestBody (name, blockchain_type, peer_orgs, ...)")
    p.set_defaults(func=write_create_instance)

    p = sub.add_parser("update-instance", help="Add/remove organizations or scale nodes")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--body-file", required=True, help='JSON: {"node_orgs":[...],"is_delete_org":false}')
    p.set_defaults(func=write_update_instance)

    p = sub.add_parser("delete-instance", help="Delete a BCS instance")
    add_common(p)
    p.add_argument("--blockchain-id", required=True)
    p.add_argument("--delete-storage", action="store_true", help="Also delete EVS storage")
    p.add_argument("--delete-obs", action="store_true", help="Also delete OBS buckets")
    p.add_argument("--delete-resource", action="store_true", help="Also delete underlying CCE resources")
    p.add_argument("--delete-ief", action="store_true", help="Also delete IEF edge node resources")
    p.set_defaults(func=write_delete_instance)

    p = sub.add_parser("invite-members", help="Invite members to a channel")
    add_common(p)
    p.add_argument("--body-file", required=True,
                   help='JSON: {"bcs_id":..,"channel_name":..,"invitor_username":..,"invited_userinfo":[{"invited_user":".."}]}')
    p.set_defaults(func=write_invite)

    p = sub.add_parser("delete-invite", help="Cancel a channel invitation")
    add_common(p)
    p.add_argument("--body-file", required=True,
                   help='JSON: {"bcs_id":..,"channel_name":..,"invited_userinfo":[{"invited_user":..,"status":..,"invited_bcs_id":..}]}')
    p.set_defaults(func=write_delete_invite)

    p = sub.add_parser("handle-notification", help="Accept/reject a union invitation notification")
    add_common(p)
    p.add_argument("--body-file", required=True,
                   help='JSON: {"channel_name":..,"status":..,"invitor_info":{..},"invitee_info":{..},"invited_orgs":[{"name":..}]}')
    p.set_defaults(func=write_handle_notification)

    p = sub.add_parser("quit-union", help="Invitee leaves a union")
    add_common(p)
    p.add_argument("--body-file", required=True,
                   help="JSON QuitUnionFromMemberListRequestBody (inviter_*/invitee_* ids, channel_name)")
    p.set_defaults(func=write_quit_union)

    return parser


def main(argv=None):
    global _JSON_STDOUT
    args = build_parser().parse_args(argv)
    previous_stdout = None
    if getattr(args, "json", False) and hasattr(args, "confirm"):
        # Write commands: progress/preview text goes to stderr; only the final
        # JSON block uses stdout. Read-only commands print exactly one JSON
        # block on stdout directly.
        previous_stdout = sys.stdout
        _JSON_STDOUT = sys.stdout
        sys.stdout = sys.stderr
    try:
        try:
            client = build_client(args.region)
            return args.func(client, args)
        except QualityError:
            raise
        except Exception as exc:
            # Last-resort guard: never leak a traceback to the caller.
            try:
                from huaweicloudsdkcore.exceptions import exceptions
            except ImportError:
                exceptions = None
            if exceptions is not None and isinstance(exc, exceptions.SdkException):
                raise QualityError(_sdk_error_code(exc), f"BCS SDK error: {exc}")
            raise QualityError(
                "B01", f"Unexpected error ({type(exc).__name__}): {exc}"
            )
    finally:
        if previous_stdout is not None:
            sys.stdout = previous_stdout
            _JSON_STDOUT = None


if __name__ == "__main__":
    try:
        main()
    except QualityError as exc:
        print(f"ERROR[{exc.error_code}]: {exc.message}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)