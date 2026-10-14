"""CCE LogConfig collection rule management."""

from __future__ import annotations

from typing import Any, Dict, List

from . import kubectl_client, lts
from .cce_log_common import (
    _parse_json_value,
    _parse_logconfig_namespaces,
    _to_bool,
)


LOGCONFIG_API_GROUP = "logging.openvessel.io"
LOGCONFIG_API_VERSION = "v1"
LOGCONFIG_PLURAL = "logconfigs"


def _get_cce_custom_objects_api(params: Dict[str, str]) -> Any:
    return kubectl_client.KubectlCustomObjectsApi(params)

def get_cce_logconfigs_action(params: Dict[str, str]) -> Dict[str, Any]:
    cluster_id = params["cluster_id"]
    namespace = params.get("namespace") or "kube-system"

    try:
        custom_api = _get_cce_custom_objects_api(params)

        api_version = f"{LOGCONFIG_API_GROUP}/{LOGCONFIG_API_VERSION}/{LOGCONFIG_PLURAL}"
        probe_errors = []
        try:
            api_result = custom_api.list_namespaced_custom_object(
                group=LOGCONFIG_API_GROUP,
                version=LOGCONFIG_API_VERSION,
                namespace=namespace,
                plural=LOGCONFIG_PLURAL,
            )
        except Exception as exc:
            probe_errors.append(
                {
                    "api_version": api_version,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                }
            )
            return {
                "success": False,
                "error": f"unable to query CCE LogConfig resources through {api_version}",
                "cluster_id": cluster_id,
                "namespace": namespace,
                "tried_api_combinations": [api_version],
                "probe_errors": probe_errors,
            }

        logconfigs = []
        for item in api_result.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            input_detail = spec.get("inputDetail", {})
            output_detail = spec.get("outputDetail", {})
            logconfigs.append(
                {
                    "name": metadata.get("name"),
                    "logconfig_name": metadata.get("name"),
                    "policy_name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "creation_time": str(metadata.get("creationTimestamp")),
                    "input_type": input_detail.get("type"),
                    "output_type": output_detail.get("type"),
                    "spec": spec,
                    "status": item.get("status", {}),
                    "api_version": f"{LOGCONFIG_API_GROUP}/{LOGCONFIG_API_VERSION}",
                }
            )

        return {
            "success": True,
            "cluster_id": cluster_id,
            "namespace": namespace,
            "count": len(logconfigs),
            "tried_api_combinations": [api_version],
            "probe_errors": probe_errors,
            "logconfigs": logconfigs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "error_type": type(exc).__name__}

def _build_file_spec(params: Dict[str, str]) -> Dict[str, str]:
    log_path = params.get("log_path")
    if not log_path:
        raise ValueError("log_path is required for file LogConfig")
    file_pattern = params.get("file_pattern")
    if not file_pattern:
        is_directory_path = log_path.endswith("/")
        normalized_path = log_path.rstrip("/")
        parent, separator, basename = normalized_path.rpartition("/")
        if not is_directory_path and separator and basename:
            log_path = parent or "/"
            file_pattern = basename
        else:
            file_pattern = "*.log"
    return {"logPath": log_path, "filePattern": file_pattern}

def _build_logconfig_workloads(params: Dict[str, str], source_type: str) -> List[Dict[str, Any]]:
    workloads = _parse_json_value(params.get("workloads"), None)
    if workloads is not None:
        if not isinstance(workloads, list):
            raise ValueError("workloads must be a JSON array")
        return workloads

    workload_namespace = params.get("workload_namespace") or params.get("namespace") or "default"
    workload_name = params.get("workload_name") or params.get("app_name")
    if not workload_name:
        raise ValueError("workload_name or app_name is required when workloads is not provided")
    workload = {
        "namespace": workload_namespace,
        "kind": params.get("workload_kind", "Deployment"),
        "name": workload_name,
    }
    container_name = params.get("container")
    if container_name:
        workload["container"] = container_name

    if source_type == "container_file":
        workload["files"] = _parse_json_value(
            params.get("files"),
            [_build_file_spec(params)],
        )
    return [workload]

def _build_logconfig_body(params: Dict[str, str]) -> Dict[str, Any]:
    name = params.get("logconfig_name") or params.get("name")
    if not name:
        raise ValueError("logconfig_name or name is required")
    source_type = params.get("source_type") or params.get("input_type") or "container_stdout"
    if source_type not in {"container_stdout", "container_file", "host_file"}:
        raise ValueError("source_type must be container_stdout, container_file, or host_file")

    log_group_id = params.get("log_group_id")
    log_stream_id = params.get("log_stream_id")
    if not log_group_id or not log_stream_id:
        raise ValueError("log_group_id and log_stream_id are required")

    all_containers = _to_bool(params.get("all_containers"), source_type == "container_stdout" and not params.get("workload_name") and not params.get("app_name") and not params.get("workloads"))
    input_detail: Dict[str, Any] = {
        "containerFile": {"discoveredForwardSize": params.get("discovered_forward_size", "1MB" if source_type == "container_file" else "")},
        "containerStdout": {},
        "event": {
            "normalEvents": {"enable": False},
            "warningEvents": {"enable": False},
        },
        "hostFile": {"file": {}},
        "processors": _parse_json_value(params.get("processors"), {"fluentBitConfig": {}, "type": params.get("processor_type", "singleline")}),
        "type": source_type,
    }

    if source_type == "container_stdout":
        if all_containers:
            input_detail["containerStdout"] = {"allContainers": True}
            namespaces = _parse_logconfig_namespaces(params.get("namespaces"))
            if namespaces:
                input_detail["containerStdout"]["namespaces"] = namespaces
        else:
            input_detail["containerStdout"] = {"allContainers": False, "workloads": _build_logconfig_workloads(params, source_type)}
    else:
        if source_type == "container_file":
            input_detail["containerFile"]["workloads"] = _build_logconfig_workloads(params, source_type)
        else:
            input_detail["hostFile"] = {"file": _build_file_spec(params)}

    return {
        "apiVersion": f"{params.get('api_group', 'logging.openvessel.io')}/{params.get('api_version', 'v1')}",
        "kind": "LogConfig",
        "metadata": {
            "name": name,
            "namespace": params.get("logconfig_namespace", "kube-system"),
        },
        "spec": {
            "inputDetail": input_detail,
            "logConfigStatus": {
                "LTS": {},
                "conditions": [],
            },
            "outputDetail": {
                "AOM": {},
                "LTS": {
                    "isCustomised": _to_bool(params.get("is_customised"), False),
                    "ltsGroupCreateParam": _parse_json_value(params.get("lts_group_create_param"), {}),
                    "ltsGroupID": log_group_id,
                    "ltsStreamCreateParam": _parse_json_value(params.get("lts_stream_create_param"), {}),
                    "ltsStreamID": log_stream_id,
                },
                "kafka": {},
                "type": "LTS",
            },
        },
    }

def _is_not_found_error(error: Exception) -> bool:
    text = str(error).lower()
    return "notfound" in text or "not found" in text or "(404)" in text

def _logconfig_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    input_detail = spec.get("inputDetail", {})
    lts_detail = (spec.get("outputDetail", {}) or {}).get("LTS", {})
    return {
        "name": metadata.get("name"),
        "namespace": metadata.get("namespace"),
        "creation_time": metadata.get("creationTimestamp"),
        "source_type": input_detail.get("type"),
        "log_group_id": lts_detail.get("ltsGroupID"),
        "log_stream_id": lts_detail.get("ltsStreamID"),
        "spec": spec,
    }

def _logconfig_change_summary(existing: Dict[str, Any], requested: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    old = _logconfig_summary(existing)
    new = _logconfig_summary(requested)
    return {
        key: {"current": old.get(key), "requested": new.get(key)}
        for key in ("source_type", "log_group_id", "log_stream_id", "spec")
        if old.get(key) != new.get(key)
    }

def create_cce_logconfig_action(params: Dict[str, str]) -> Dict[str, Any]:
    destination_check = lts.require_explicit_cluster_log_destination(params)
    if destination_check:
        return destination_check
    try:
        body = _build_logconfig_body(params)
        group = params.get("api_group", "logging.openvessel.io")
        version = params.get("api_version", "v1")
        plural = params.get("plural", "logconfigs")
        namespace = body["metadata"]["namespace"]
        custom_api = _get_cce_custom_objects_api(params)
        existing = None
        try:
            existing = custom_api.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=body["metadata"]["name"],
            )
        except Exception as exc:
            if not _is_not_found_error(exc):
                raise

        if existing:
            changes = _logconfig_change_summary(existing, body)
            if not _to_bool(params.get("update_existing"), False):
                return {
                    "success": False,
                    "error": "CCE LogConfig with the same name already exists; creation will not overwrite it",
                    "requires_update_existing": True,
                    "cluster_id": params["cluster_id"],
                    "logconfig_name": body["metadata"]["name"],
                    "logconfig_namespace": namespace,
                    "existing": _logconfig_summary(existing),
                    "requested_changes": changes,
                    "request_body": body,
                }
            if not _to_bool(params.get("confirm"), False):
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": "Updating an existing CCE LogConfig changes log collection. Re-run with update_existing=true and confirm=true after review.",
                    "cluster_id": params["cluster_id"],
                    "logconfig_name": body["metadata"]["name"],
                    "logconfig_namespace": namespace,
                    "existing": _logconfig_summary(existing),
                    "requested_changes": changes,
                    "request_body": body,
                }

        if not _to_bool(params.get("confirm"), False):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "创建CCE LogConfig会修改集群日志采集配置。如确认创建，请带 confirm=true 重新调用。",
                "cluster_id": params["cluster_id"],
                "logconfig_name": body["metadata"]["name"],
                "logconfig_namespace": namespace,
                "api_version": body["apiVersion"],
                "request_body": body,
            }

        response = custom_api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            body=body,
        )
        metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
        return {
            "success": True,
            "cluster_id": params["cluster_id"],
            "logconfig_name": metadata.get("name", body["metadata"]["name"]),
            "logconfig_namespace": metadata.get("namespace", namespace),
            "api_version": body["apiVersion"],
            "source_type": body["spec"]["inputDetail"]["type"],
            "log_group_id": body["spec"]["outputDetail"]["LTS"]["ltsGroupID"],
            "log_stream_id": body["spec"]["outputDetail"]["LTS"]["ltsStreamID"],
            "updated_existing": bool(existing),
            "response": response,
        }
    except Exception as exc:
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None)
        body_text = getattr(exc, "body", None)
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "status": status,
            "reason": reason,
            "response_body": body_text,
        }

def delete_cce_logconfig_action(params: Dict[str, str]) -> Dict[str, Any]:
    try:
        name = params.get("logconfig_name") or params.get("name")
        if not name:
            raise ValueError("logconfig_name or name is required")
        namespace = params.get("logconfig_namespace") or params.get("namespace") or "kube-system"
        group = params.get("api_group", "logging.openvessel.io")
        version = params.get("api_version", "v1")
        plural = params.get("plural", "logconfigs")

        custom_api = _get_cce_custom_objects_api(params)
        existing = custom_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
        metadata = existing.get("metadata", {}) if isinstance(existing, dict) else {}
        spec = existing.get("spec", {}) if isinstance(existing, dict) else {}
        input_detail = spec.get("inputDetail", {})
        output_detail = spec.get("outputDetail", {})

        if not _to_bool(params.get("confirm"), False):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "删除CCE LogConfig会停止对应日志采集。如确认删除，请带 confirm=true 重新调用。",
                "cluster_id": params["cluster_id"],
                "logconfig_name": metadata.get("name", name),
                "logconfig_namespace": metadata.get("namespace", namespace),
                "api_version": f"{group}/{version}",
                "source_type": input_detail.get("type"),
                "output_type": output_detail.get("type"),
                "target": {
                    "group": group,
                    "version": version,
                    "namespace": namespace,
                    "plural": plural,
                    "name": name,
                },
                "existing": {
                    "name": metadata.get("name", name),
                    "namespace": metadata.get("namespace", namespace),
                    "creation_time": metadata.get("creationTimestamp"),
                    "input_type": input_detail.get("type"),
                    "output_type": output_detail.get("type"),
                    "log_group_id": output_detail.get("LTS", {}).get("ltsGroupID"),
                    "log_stream_id": output_detail.get("LTS", {}).get("ltsStreamID"),
                },
            }

        response = custom_api.delete_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
        return {
            "success": True,
            "cluster_id": params["cluster_id"],
            "logconfig_name": name,
            "logconfig_namespace": namespace,
            "api_version": f"{group}/{version}",
            "response": response,
        }
    except Exception as exc:
        status = getattr(exc, "status", None)
        reason = getattr(exc, "reason", None)
        body_text = getattr(exc, "body", None)
        return {
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "status": status,
            "reason": reason,
            "response_body": body_text,
        }
