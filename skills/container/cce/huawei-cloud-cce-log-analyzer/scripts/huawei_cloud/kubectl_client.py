"""kubectl access for CCE log queries and LogConfig management."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List, Optional

from . import common

def _run(command: List[str], *, environment: Optional[Dict[str, str]] = None, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    safe_command = common.redact_command(command)
    try:
        process = subprocess.run(command, text=True, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, env=environment)
    except FileNotFoundError:
        return {"success": False, "error": f"{command[0]} not found in PATH", "command": safe_command}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "command timed out after 60s", "command": safe_command}
    if process.returncode:
        return {"success": False, "error": (process.stderr or process.stdout or f"command exited with code {process.returncode}")[:2000], "command": safe_command}
    if not expect_json:
        return {"success": True, "output": process.stdout, "command": safe_command}
    try:
        return {"success": True, "data": json.loads(process.stdout or "{}"), "command": safe_command}
    except json.JSONDecodeError as exc:
        return {"success": False, "error": f"kubectl returned non-JSON output: {exc}", "command": safe_command}


def _plugin_kubectl(region: str, cluster_id: str, arguments: List[str], ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str], explicit_cli_credentials: bool, stdin: Optional[str], expect_json: bool) -> Dict[str, Any]:
    env_ak, env_sk, env_project = (None, None, None) if explicit_cli_credentials else common.get_credentials()
    environment = _subprocess_environment()
    environment.update({"CCE_CLUSTER_ID": cluster_id, "CCE_REGION": region, "HW_REGION": region})
    if not explicit_cli_credentials:
        credentials = ((ak or env_ak, ("HW_ACCESS_KEY", "HUAWEICLOUD_SDK_AK")), (sk or env_sk, ("HW_SECRET_KEY", "HUAWEICLOUD_SDK_SK")), (project_id or env_project, ("CCE_PROJECT_ID", "HW_PROJECT_ID")))
        for value, names in credentials:
            if value:
                environment.update(dict.fromkeys(names, value))
    token = security_token if explicit_cli_credentials else security_token or os.getenv("HW_SECURITY_TOKEN")
    if token and not explicit_cli_credentials:
        environment.update({"HW_SECURITY_TOKEN": token, "HUAWEICLOUD_SECURITY_TOKEN": token})
    command = ["kubectl", "cce", "--cce-insecure-upstream-tls=true", "--cluster-id", cluster_id, "--region", region]
    resolved_project_id = project_id if explicit_cli_credentials else project_id or env_project
    if resolved_project_id:
        command.extend(["--project-id", resolved_project_id])
    if explicit_cli_credentials:
        command.extend([f"--cli-access-key={ak}", f"--cli-secret-key={sk}"])
        if security_token:
            command.append(f"--cli-security-token={security_token}")
    command.extend(arguments)
    result = _run(command, environment=environment, stdin=stdin, expect_json=expect_json)
    if result.get("success"):
        result["access_method"] = "kubectl_cce_plugin"
    return result


def _subprocess_environment() -> Dict[str, str]:
    """Build a minimal environment for kubectl subprocesses.

    Only the variables required to invoke `kubectl` are read by name; the
    process environment is never copied wholesale, so unrelated secrets in
    the runtime environment cannot leak into the kubectl subprocess.
    """
    env: Dict[str, str] = {}
    for name in ("PATH", "HOME", "LANG", "LC_ALL", "HCLOUD_CONFIG_DIR"):
        value = os.getenv(name)
        if value is not None:
            env[name] = value
    return env


def run_kubectl(region: str, cluster_id: str, arguments: List[str], *, ak: Optional[str] = None, sk: Optional[str] = None, project_id: Optional[str] = None, security_token: Optional[str] = None, explicit_cli_credentials: bool = False, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
    """Run a Kubernetes command through the kubectl-cce plugin."""
    plugin = _plugin_kubectl(region, cluster_id, arguments, ak, sk, project_id, security_token, explicit_cli_credentials, stdin, expect_json)
    if plugin.get("success"):
        return plugin
    return {"success": False, "error": "kubectl access failed through kubectl cce", "plugin_error": plugin.get("error")}


def get_pod_logs(region: str, cluster_id: str, pod_name: str, namespace: str, container: Optional[str], previous: bool, tail_lines: int, ak: Optional[str], sk: Optional[str], project_id: Optional[str], security_token: Optional[str] = None, explicit_cli_credentials: bool = False) -> Dict[str, Any]:
    args = ["logs", pod_name, "--namespace", namespace, f"--tail={tail_lines}"]
    if container:
        args.extend(["--container", container])
    if previous:
        args.append("--previous")
    result = run_kubectl(region, cluster_id, args, ak=ak, sk=sk, project_id=project_id, security_token=security_token, explicit_cli_credentials=explicit_cli_credentials, expect_json=False)
    if result.get("success"):
        result["logs"] = result.pop("output")
    return result


class KubectlCustomObjectsApi:
    """Subset of CustomObjectsApi backed by kubectl resource commands."""

    def __init__(self, params: Dict[str, str]):
        self.params = params

    def _resource(self, group: str, plural: str) -> str:
        return f"{plural}.{group}"

    def _run(self, arguments: List[str], *, stdin: Optional[str] = None, expect_json: bool = True) -> Dict[str, Any]:
        result = run_kubectl(
            self.params["region"], self.params["cluster_id"], arguments, ak=self.params.get("ak"),
            sk=self.params.get("sk"), project_id=self.params.get("project_id"), security_token=self.params.get("security_token"),
            explicit_cli_credentials=self.params.get("_explicit_cli_credentials") == "true", stdin=stdin, expect_json=expect_json,
        )
        if not result.get("success"):
            errors = [result.get("error", "kubectl command failed")]
            if result.get("plugin_error"):
                errors.append(f"kubectl cce: {result['plugin_error']}")
            raise RuntimeError("; ".join(errors))
        return result.get("data") or {}

    def list_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), "--namespace", namespace, "--output=json"])

    def list_cluster_custom_object(self, group: str, version: str, plural: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), "--all-namespaces", "--output=json"])

    def get_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, name: str) -> Dict[str, Any]:
        return self._run(["get", self._resource(group, plural), name, "--namespace", namespace, "--output=json"])

    def create_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, body: Dict[str, Any]) -> Dict[str, Any]:
        # CCE does not expose OpenAPI schemas for every custom resource; let the API server validate the object.
        return self._run(["apply", "--namespace", namespace, "--filename=-", "--output=json", "--validate=false"], stdin=json.dumps(body))

    def delete_namespaced_custom_object(self, group: str, version: str, namespace: str, plural: str, name: str) -> Dict[str, Any]:
        self._run(["delete", self._resource(group, plural), name, "--namespace", namespace, "--output=name"], expect_json=False)
        return {"metadata": {"name": name, "namespace": namespace}}
