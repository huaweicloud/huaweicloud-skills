"""LTS group, stream, and log query helpers through hcloud."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import time
from typing import Any, Dict, List, Optional

from . import common


_AGENT_ACCESS_CONFIG_TYPE = "AGENT"
_K8S_CCE_ACCESS_CONFIG_TYPE = "K8S_CCE"


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "y", "on"}


def _string_list(value: Optional[str]) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _access_config_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    detail = item.get("access_config_detail") or {}
    log_info = item.get("log_info") or {}
    return {
        "access_config_id": item.get("access_config_id"),
        "access_config_name": item.get("access_config_name"),
        "access_config_type": item.get("access_config_type"),
        "cluster_id": item.get("cluster_id"),
        "path_type": detail.get("pathType"),
        "paths": detail.get("paths") or [],
        "namespace_regex": detail.get("namespaceRegex"),
        "pod_name_regex": detail.get("podNameRegex"),
        "container_name_regex": detail.get("containerNameRegex"),
        "stdout": detail.get("stdout"),
        "stderr": detail.get("stderr"),
        "log_group_id": log_info.get("log_group_id"),
        "log_group_name": log_info.get("log_group_name"),
        "log_stream_id": log_info.get("log_stream_id"),
        "log_stream_name": log_info.get("log_stream_name"),
        "create_time": item.get("create_time"),
    }


def list_access_configs(
    region: str,
    access_config_name: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    command = common.hcloud_command("LTS", "ListAccessConfig", region, ak, sk, project_id, security_token)
    if access_config_name:
        command.append(f"--access_config_name_list.1={access_config_name}")
    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    configs = [item for item in data.get("result", []) if isinstance(item, dict)]
    return {
        "success": True,
        "total": data.get("total", len(configs)),
        "access_configs": [_access_config_summary(item) for item in configs],
    }


def _access_config_path_type(params: Dict[str, str]) -> Optional[str]:
    value = params.get("path_type") or params.get("source_type")
    if not value:
        return None
    mapping = {
        "container_stdout": "CONTAINER_STDOUT",
        "container_file": "CONTAINER_FILE",
        "host_file": "HOST_FILE",
    }
    normalized = str(value).strip()
    return mapping.get(normalized.lower(), normalized.upper())


def _access_config_type(params: Dict[str, str]) -> str:
    """Choose the compatible LTS creation path for the requested collection."""
    value = params.get("access_config_type")
    if not value:
        path_type = _access_config_path_type(params)
        value = (
            _K8S_CCE_ACCESS_CONFIG_TYPE
            if params.get("cluster_id") and path_type in {"CONTAINER_STDOUT", "CONTAINER_FILE"}
            else _AGENT_ACCESS_CONFIG_TYPE
        )
    value = value.strip().upper()
    if value not in {_AGENT_ACCESS_CONFIG_TYPE, _K8S_CCE_ACCESS_CONFIG_TYPE}:
        raise ValueError("access_config_type must be AGENT or K8S_CCE")
    return value


def _access_config_format(params: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """Build the required LTS log timestamp format."""
    mode = (params.get("format_mode") or "system").lower()
    if mode not in {"system", "wildcard"}:
        raise ValueError("format_mode must be system or wildcard")
    value = params.get("format_value")
    if mode == "wildcard" and not value:
        raise ValueError("format_value is required when format_mode is wildcard")
    return {"single": {"mode": mode, "value": value or str(int(time.time() * 1000))}}


def _append_access_config_format(command: List[str], params: Dict[str, str]) -> None:
    """Append the required LTS log format for an Access Config."""
    single = _access_config_format(params)["single"]
    command.extend(
        [
            f"--access_config_detail.format.single.mode={single['mode']}",
            f"--access_config_detail.format.single.value={single['value']}",
        ]
    )


def _resolve_k8s_host_group_id(params: Dict[str, str], cluster_id: str) -> str:
    """Resolve the CCE-managed LTS host group for a K8S_CCE access config."""
    if params.get("host_group_id"):
        return params["host_group_id"]
    expected_name = f"k8s-log-{cluster_id}"
    command = common.hcloud_command(
        "LTS", "ListHostGroup", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    result = common.run_hcloud(command)
    if not result.get("success"):
        raise ValueError(f"unable to discover the K8S_CCE host group: {result.get('error')}")
    groups = [item for item in (result.get("data") or {}).get("result", []) if isinstance(item, dict)]
    matches = [item for item in groups if item.get("host_group_name") == expected_name]
    if len(matches) != 1 or not matches[0].get("host_group_id"):
        raise ValueError(
            f"unable to find one host group named {expected_name}; provide host_group_id explicitly"
        )
    return matches[0]["host_group_id"]


def _resolve_container_name_regex(params: Dict[str, str]) -> str:
    """Use an explicit container regex or the all-container default."""
    return params.get("container_name_regex") or "^.*$"


def _k8s_cce_access_config_body(params: Dict[str, str]) -> Dict[str, Any]:
    """Build an LTS API request body for CCE container stdout or file collection."""
    name = params.get("access_config_name") or params.get("name")
    log_group_id = params.get("log_group_id")
    log_stream_id = params.get("log_stream_id")
    cluster_id = params.get("cluster_id")
    path_type = _access_config_path_type(params) or "CONTAINER_STDOUT"
    if not name:
        raise ValueError("access_config_name is required")
    if not log_group_id or not log_stream_id:
        raise ValueError("log_group_id and log_stream_id are required")
    if not cluster_id:
        raise ValueError("cluster_id is required for K8S_CCE access configs")
    if path_type not in {"CONTAINER_STDOUT", "CONTAINER_FILE"}:
        raise ValueError("K8S_CCE access configs support CONTAINER_STDOUT or CONTAINER_FILE")
    paths = _string_list(params.get("paths") or params.get("path") or params.get("log_path"))
    if path_type == "CONTAINER_STDOUT" and paths:
        raise ValueError("paths is not supported for K8S_CCE CONTAINER_STDOUT access configs")
    if path_type == "CONTAINER_FILE" and not paths:
        raise ValueError("paths, path, or log_path is required for K8S_CCE CONTAINER_FILE access configs")
    namespace_regex = params.get("namespace_regex")
    pod_name_regex = params.get("pod_name_regex")
    if not namespace_regex or not pod_name_regex:
        raise ValueError("namespace_regex and pod_name_regex are required for K8S_CCE access configs")
    host_group_id = _resolve_k8s_host_group_id(params, cluster_id)
    container_name_regex = _resolve_container_name_regex(params)
    return {
        "access_config_name": name,
        "access_config_type": _K8S_CCE_ACCESS_CONFIG_TYPE,
        "access_config_detail": {
            "pathType": path_type,
            "paths": paths,
            "stdout": _to_bool(params.get("stdout"), path_type == "CONTAINER_STDOUT"),
            "stderr": _to_bool(params.get("stderr"), path_type == "CONTAINER_STDOUT"),
            "format": _access_config_format(params),
            "namespaceRegex": namespace_regex,
            "podNameRegex": pod_name_regex,
            "containerNameRegex": container_name_regex,
            "repeat_collect": _to_bool(params.get("repeat_collect"), True),
        },
        "log_info": {"log_group_id": log_group_id, "log_stream_id": log_stream_id},
        "host_group_info": {"host_group_id_list": [host_group_id]},
        "binary_collect": _to_bool(params.get("binary_collect"), False),
        "incremental_collect": _to_bool(params.get("incremental_collect"), True),
        "cluster_id": cluster_id,
    }


def _create_k8s_cce_access_config(params: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    """Create K8S_CCE collection through the LTS SDK because hcloud rejects this enum."""
    if params.get("_explicit_cli_credentials") == "true":
        ak, sk, project_id = params.get("ak"), params.get("sk"), params.get("project_id")
    else:
        ak, sk, project_id = common.get_credentials(params.get("ak"), params.get("sk"), params.get("project_id"))
    if not ak or not sk or not project_id:
        return {"success": False, "error": "AK, SK, and project_id are required for K8S_CCE API creation"}
    try:
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkcore.exceptions.exceptions import ClientRequestException
        from huaweicloudsdklts.v2 import LtsClient, CreateAccessConfigRequest
        from huaweicloudsdklts.v2.model import (
            AccessConfigBaseLogInfoCreate,
            AccessConfigDeatilCreate,
            AccessConfigFormatCreate,
            AccessConfigFormatSingleCreate,
            AccessConfigHostGroupIdListCreate,
            CreateAccessConfigRequestBody,
        )
        from huaweicloudsdklts.v2.region.lts_region import LtsRegion
    except ImportError as exc:
        return {"success": False, "error": f"Huawei Cloud LTS SDK is required for K8S_CCE creation: {exc}"}

    detail_data = body["access_config_detail"]
    single = detail_data["format"]["single"]
    detail = AccessConfigDeatilCreate(
            paths=detail_data["paths"],
            path_type=detail_data["pathType"],
        stdout=detail_data["stdout"],
        stderr=detail_data["stderr"],
        format=AccessConfigFormatCreate(single=AccessConfigFormatSingleCreate(mode=single["mode"], value=single["value"])),
        namespace_regex=detail_data["namespaceRegex"],
        pod_name_regex=detail_data["podNameRegex"],
        container_name_regex=detail_data["containerNameRegex"],
        repeat_collect=detail_data["repeat_collect"],
    )
    request = CreateAccessConfigRequest(
        body=CreateAccessConfigRequestBody(
            access_config_name=body["access_config_name"],
            access_config_type=body["access_config_type"],
            access_config_detail=detail,
            log_info=AccessConfigBaseLogInfoCreate(**body["log_info"]),
            host_group_info=AccessConfigHostGroupIdListCreate(**body["host_group_info"]),
            binary_collect=body["binary_collect"],
            incremental_collect=body["incremental_collect"],
            cluster_id=body["cluster_id"],
        )
    )
    try:
        credentials = BasicCredentials(ak, sk, project_id)
        if params.get("security_token"):
            credentials = credentials.with_security_token(params["security_token"])
        client = LtsClient.new_builder().with_credentials(credentials).with_region(
            LtsRegion.value_of(params["region"])
        ).build()
        return {"success": True, "data": client.create_access_config(request).to_dict()}
    except ClientRequestException as exc:
        return {"success": False, "error": f"{exc.error_code}: {exc.error_msg}"}
    except Exception as exc:
        return {"success": False, "error": f"LTS K8S_CCE API request failed: {exc}"}


def _create_access_config_command(params: Dict[str, str]) -> List[str]:
    name = params.get("access_config_name") or params.get("name")
    if not name:
        raise ValueError("access_config_name is required")
    log_group_id = params.get("log_group_id")
    log_stream_id = params.get("log_stream_id")
    if not log_group_id or not log_stream_id:
        raise ValueError("log_group_id and log_stream_id are required")

    access_config_type = _access_config_type(params)
    if access_config_type == _K8S_CCE_ACCESS_CONFIG_TYPE:
        raise ValueError("K8S_CCE access configs use the LTS API, not hcloud")
    path_type = _access_config_path_type(params)
    command = common.hcloud_command(
        "LTS", "CreateAccessConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    command.extend(
        [
            f"--access_config_name={name}",
            f"--access_config_type={access_config_type}",
            f"--log_info.log_group_id={log_group_id}",
            f"--log_info.log_stream_id={log_stream_id}",
        ]
    )
    cluster_id = params.get("cluster_id")
    if cluster_id:
        command.append(f"--cluster_id={cluster_id}")
    if path_type:
        if path_type not in {"CONTAINER_STDOUT", "CONTAINER_FILE", "HOST_FILE"}:
            raise ValueError("path_type must be CONTAINER_STDOUT, CONTAINER_FILE, or HOST_FILE")
        command.append(f"--access_config_detail.pathType={path_type}")
        paths = _string_list(params.get("paths") or params.get("path") or params.get("log_path"))
        if not paths:
            if path_type == "CONTAINER_STDOUT":
                paths = ["/var/log/containers"]
            else:
                raise ValueError("paths, path, or log_path is required for container_file and host_file AGENT access configs")
        for index, path in enumerate(paths, 1):
            command.append(f"--access_config_detail.paths.{index}={path}")
        _append_access_config_format(command, params)
        command.append(f"--access_config_detail.stdout={str(_to_bool(params.get('stdout'), path_type == 'CONTAINER_STDOUT')).lower()}")
        command.append(f"--access_config_detail.stderr={str(_to_bool(params.get('stderr'), False)).lower()}")
        for param_name, cli_name in (
            ("namespace_regex", "namespaceRegex"),
            ("pod_name_regex", "podNameRegex"),
            ("container_name_regex", "containerNameRegex"),
        ):
            value = params.get(param_name)
            if param_name == "container_name_regex" and path_type == "CONTAINER_STDOUT" and not value:
                value = _resolve_container_name_regex(params)
            if value:
                command.append(f"--access_config_detail.{cli_name}={value}")
    host_group_id = params.get("host_group_id")
    if path_type == "HOST_FILE" and not host_group_id:
        if not cluster_id:
            raise ValueError("cluster_id or host_group_id is required for AGENT HOST_FILE access configs")
        host_group_id = _resolve_k8s_host_group_id(params, cluster_id)
    if host_group_id:
        command.append(f"--host_group_info.host_group_id_list.1={host_group_id}")
    return command


def create_access_config_action(params: Dict[str, str]) -> Dict[str, Any]:
    destination_check = require_explicit_cluster_log_destination(params)
    if destination_check:
        return destination_check
    try:
        access_config_type = _access_config_type(params)
        api_body = _k8s_cce_access_config_body(params) if access_config_type == _K8S_CCE_ACCESS_CONFIG_TYPE else None
        command = None if api_body else _create_access_config_command(params)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    name = params.get("access_config_name") or params.get("name")
    path_type = _access_config_path_type(params) or ("CONTAINER_STDOUT" if api_body else None)
    existing_result = list_access_configs(
        params["region"],
        access_config_name=name,
        ak=params.get("ak"),
        sk=params.get("sk"),
        project_id=params.get("project_id"),
        security_token=params.get("security_token"),
    )
    if not existing_result.get("success"):
        return {
            "success": False,
            "error": f"unable to check existing LTS Access Configs before creation: {existing_result.get('error', '')}",
        }
    existing = [
        item for item in existing_result.get("access_configs", [])
        if item.get("access_config_name") == name
    ]
    if existing:
        return {
            "success": False,
            "error": "LTS Access Config with the same name already exists; creation will not overwrite it",
            "access_config_name": name,
            "existing_access_configs": existing,
            "requires_new_name": True,
        }

    if not _to_bool(params.get("confirm"), False):
        return {
            "success": False,
            "requires_confirmation": True,
            "message": "Creating an LTS access config changes log collection. Re-run with confirm=true after review.",
            "access_config_name": name,
            "access_config_type": access_config_type,
            "cluster_id": params.get("cluster_id"),
            "path_type": path_type,
            "log_group_id": params.get("log_group_id"),
            "log_stream_id": params.get("log_stream_id"),
            "api_request_preview": api_body,
            "command_preview": common.redact_command(command) if command else None,
        }
    result = _create_k8s_cce_access_config(params, api_body) if api_body else common.run_hcloud(command)
    if not result.get("success"):
        return result
    return {
        "success": True,
        "access_config_name": name,
        "access_config_type": access_config_type,
        "cluster_id": params.get("cluster_id"),
        "path_type": path_type,
        "log_group_id": params.get("log_group_id"),
        "log_stream_id": params.get("log_stream_id"),
        "response": result.get("data"),
    }


def require_explicit_cluster_log_destination(params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Discover a cluster destination, but never select or create one automatically."""
    log_group_id = params.get("log_group_id")
    log_stream_id = params.get("log_stream_id")
    if log_group_id and log_stream_id:
        return None
    if log_group_id or log_stream_id:
        return {
            "success": False,
            "error": "log_group_id and log_stream_id must be provided together",
            "requires_log_destination": True,
        }

    cluster_id = params.get("cluster_id")
    if not cluster_id:
        return {
            "success": False,
            "error": "log_group_id and log_stream_id are required; cluster_id is required to discover a cluster-specific LTS destination",
            "requires_log_destination": True,
        }

    expected_group_name = f"k8s-log-{cluster_id}"
    groups_result = list_log_groups(
        params["region"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token")
    )
    if not groups_result.get("success"):
        return {
            "success": False,
            "error": f"unable to discover the cluster LTS log group: {groups_result.get('error')}",
            "requires_log_destination": True,
        }
    all_log_groups = groups_result.get("log_groups", [])
    all_streams_result = list_log_streams(
        params["region"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token")
    )
    if not all_streams_result.get("success"):
        return {
            "success": False,
            "error": f"unable to discover existing LTS log streams: {all_streams_result.get('error')}",
            "requires_log_destination": True,
        }
    all_log_streams = all_streams_result.get("log_streams", [])
    log_groups = [
        group for group in all_log_groups
        if group.get("log_group_name") == expected_group_name
    ]
    if not log_groups:
        return {
            "success": False,
            "requires_log_destination": True,
            "cluster_id": cluster_id,
            "expected_log_group_name": expected_group_name,
            "available_log_groups": all_log_groups,
            "available_log_streams": all_log_streams,
            "message": (
                "No LTS log group dedicated to this cluster was found. Existing log groups and streams are "
                "listed as user-selectable alternatives. Prefer creating the dedicated log group and stream, "
                "then provide both IDs to continue. The tool will not create or select a destination automatically."
            ),
            "hcloud_next_steps": [
                f"hcloud LTS CreateLogGroup --cli-region={params['region']} --log_group_name={expected_group_name} --ttl_in_days=<1-365>",
                "hcloud LTS CreateLogStream --cli-region=<region> --log_group_id=<log-group-id> --log_stream_name=<stream-name>",
            ],
        }

    log_group = log_groups[0]
    streams_result = list_log_streams(
        params["region"], log_group["log_group_id"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token")
    )
    if not streams_result.get("success"):
        return {
            "success": False,
            "error": f"unable to discover log streams for {expected_group_name}: {streams_result.get('error')}",
            "requires_log_destination": True,
        }
    log_streams = streams_result.get("log_streams", [])
    message = (
        "Select one listed log stream and provide its log_group_id and log_stream_id to continue. "
        "The tool will not select a destination automatically."
        if log_streams else
        "The cluster log group has no log streams. Existing log groups and streams are listed as "
        "user-selectable alternatives. Prefer creating a stream in the cluster log group, then provide both "
        "log_group_id and log_stream_id to continue. The tool will not create or select a destination automatically."
    )
    return {
        "success": False,
        "requires_log_destination": True,
        "cluster_id": cluster_id,
        "expected_log_group_name": expected_group_name,
        "available_log_groups": all_log_groups if not log_streams else log_groups,
        "available_log_streams": all_log_streams if not log_streams else log_streams,
        "message": message,
        "hcloud_next_steps": [] if log_streams else [
            f"hcloud LTS CreateLogStream --cli-region={params['region']} --log_group_id={log_group['log_group_id']} --log_stream_name=<stream-name>"
        ],
    }


def delete_access_config_action(params: Dict[str, str]) -> Dict[str, Any]:
    access_config_id = params.get("access_config_id")
    if not access_config_id:
        return {"success": False, "error": "access_config_id is required"}
    listed = list_access_configs(
        params["region"], ak=params.get("ak"), sk=params.get("sk"), project_id=params.get("project_id"), security_token=params.get("security_token")
    )
    if not listed.get("success"):
        return listed
    existing = next((item for item in listed.get("access_configs", []) if item.get("access_config_id") == access_config_id), None)
    if not existing:
        return {"success": False, "error": f"LTS access config {access_config_id} was not found"}
    command = common.hcloud_command(
        "LTS", "DeleteAccessConfig", params["region"], params.get("ak"), params.get("sk"), params.get("project_id"), params.get("security_token")
    )
    command.append(f"--access_config_id_list.1={access_config_id}")
    if not _to_bool(params.get("confirm"), False):
        return {
            "success": False,
            "requires_confirmation": True,
            "message": "Deleting an LTS access config stops its log collection. Re-run with confirm=true after review.",
            "access_config": existing,
            "command_preview": common.redact_command(command),
        }
    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    return {"success": True, "deleted_access_config": existing, "response": result.get("data")}


def _timestamp(value: Optional[str], default: datetime) -> int:
    if not value:
        return int(default.timestamp() * 1000)
    if "-" in value:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1000)
    return int(value)


def _groups(region: str, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None) -> Dict[str, Any]:
    return common.run_hcloud(common.hcloud_command("LTS", "ListLogGroups", region, ak, sk, project_id, security_token))


def list_log_groups(
    region: str,
    limit: int = 0,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    result = _groups(region, ak, sk, project_id, security_token)
    if not result.get("success"):
        return result
    groups = [group for group in (result["data"].get("log_groups") or []) if isinstance(group, dict)]
    if limit > 0:
        groups = groups[:limit]
    return {
        "success": True,
        "total": len(groups),
        "log_groups": [
            {
                "log_group_id": group.get("log_group_id"),
                "log_group_name": group.get("log_group_name"),
                "creation_time": group.get("creation_time"),
                "ttl_in_days": group.get("ttl_in_days"),
            }
            for group in groups
        ],
    }


def list_log_streams(
    region: str,
    log_group_id: Optional[str] = None,
    limit: int = 0,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    group_name = None
    if log_group_id:
        groups_result = _groups(region, ak, sk, project_id, security_token)
        if not groups_result.get("success"):
            return groups_result
        group = next(
            (item for item in (groups_result["data"].get("log_groups") or []) if item.get("log_group_id") == log_group_id),
            None,
        )
        if not group:
            return {"success": False, "error": f"LTS log group {log_group_id} was not found"}
        group_name = group.get("log_group_name")

    command = common.hcloud_command("LTS", "ListLogStreams", region, ak, sk, project_id, security_token)
    if group_name:
        command.append(f"--log_group_name={group_name}")
    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    streams = [stream for stream in (result["data"].get("log_streams") or []) if isinstance(stream, dict)]
    if limit > 0:
        streams = streams[:limit]
    return {
        "success": True,
        "total": len(streams),
        "log_streams": [
            {
                "log_stream_id": stream.get("log_stream_id"),
                "log_stream_name": stream.get("log_stream_name"),
                "log_group_id": stream.get("log_group_id") or log_group_id,
                "creation_time": stream.get("creation_time"),
            }
            for stream in streams
        ],
    }


def list_log_stream_index(
    region: str,
    log_group_id: str,
    log_stream_id: str,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the configured field-index names for one LTS log stream."""
    command = common.hcloud_command("LTS", "ListLogStreamIndex", region, ak, sk, project_id, security_token)
    command.extend([f"--group_id={log_group_id}", f"--stream_id={log_stream_id}"])
    if project_id:
        command.append(f"--project_id={project_id}")
    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    data = result.get("data") or {}
    return {
        "success": True,
        "full_text_index_enabled": bool((data.get("fullTextIndex") or {}).get("enable")),
        "indexed_fields": {
            field.get("fieldName")
            for field in data.get("fields") or []
            if isinstance(field, dict) and field.get("fieldName")
        },
    }


def query_logs(
    region: str,
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 1000,
    scroll_id: Optional[str] = None,
    is_desc: bool = True,
    is_iterative: bool = False,
    labels: Optional[Dict[str, str]] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    security_token: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    command = common.hcloud_command("LTS", "ListLogs", region, ak, sk, project_id, security_token)
    command.extend(
        [
            f"--log_group_id={log_group_id}",
            f"--log_stream_id={log_stream_id}",
            f"--start_time={_timestamp(start_time, now - timedelta(hours=1))}",
            f"--end_time={_timestamp(end_time, now)}",
            f"--limit={max(1, min(limit, 1000))}",
            f"--is_desc={str(is_desc).lower()}",
            "--highlight=false",
        ]
    )
    if keywords:
        command.append(f"--keywords={keywords}")
    if scroll_id:
        command.append(f"--scroll_id={scroll_id}")
    if is_iterative:
        command.append("--is_iterative=true")
    for key, value in (labels or {}).items():
        command.append(f"--labels.{key}={value}")

    result = common.run_hcloud(command)
    if not result.get("success"):
        return result
    response = result["data"]
    logs = [
        {
            "content": item.get("content", ""),
            "timestamp": item.get("timestamp"),
            "log_group_id": log_group_id,
            "log_stream_id": log_stream_id,
        }
        for item in (response.get("logs") or [])
        if isinstance(item, dict)
    ]
    next_scroll_id = response.get("scroll_id")
    return {
        "success": True,
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "start_time": _timestamp(start_time, now - timedelta(hours=1)),
        "end_time": _timestamp(end_time, now),
        "total": len(logs),
        "scroll_id": next_scroll_id,
        "has_more": bool(next_scroll_id),
        "logs": logs,
    }
