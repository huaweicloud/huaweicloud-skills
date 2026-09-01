"""hcloud KooCLI execution core for CCE cluster management skill."""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional



class CredentialCtx:
    """Resolved credential context for hcloud/kubectl calls."""
    def __init__(self, ak: str, sk: str, security_token: Optional[str], project_id: Optional[str]):
        self.ak = ak
        self.sk = sk
        self.security_token = security_token
        self.project_id = project_id


_PROJECT_ID_CACHE = {}

# Cached check for hcloud CLI config credentials
_HCLOUD_CONFIG_CHECKED = False
_HCLOUD_HAS_CONFIG = False


def _hcloud_config_has_credentials() -> bool:
    """Check if hcloud CLI has credentials in its config file.

    If hcloud config has AK/SK, skip passing --cli-access-key/--cli-secret-key
    as CLI arguments to avoid exposure in ps aux.
    """
    global _HCLOUD_CONFIG_CHECKED, _HCLOUD_HAS_CONFIG
    if _HCLOUD_CONFIG_CHECKED:
        return _HCLOUD_HAS_CONFIG
    _HCLOUD_CONFIG_CHECKED = True
    try:
        r = subprocess.run(
            ["hcloud", "configure", "show"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        )
        if r.returncode == 0:
            config = json.loads(r.stdout)
            ak = config.get("accessKeyId", "")
            _HCLOUD_HAS_CONFIG = bool(ak) and ak.strip() != ""
    except Exception:
        pass
    return _HCLOUD_HAS_CONFIG


def resolve_credentials(
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    region: Optional[str] = None,
    fetch_project_id: bool = True,
) -> CredentialCtx:
    """Resolve credentials from params > env vars. Auto-fetch project_id if missing.

    Set fetch_project_id=False for operations that don't need project_id
    (e.g., kubectl-cce node operations) to avoid unnecessary credential exposure.
    """
    access_key = ak or os.environ.get("HW_ACCESS_KEY") or os.environ.get("HUAWEI_AK") or os.environ.get("HUAWEICLOUD_SDK_AK")
    secret_key = sk or os.environ.get("HW_SECRET_KEY") or os.environ.get("HUAWEI_SK") or os.environ.get("HUAWEICLOUD_SDK_SK")
    token = os.environ.get("HW_SECURITY_TOKEN")
    proj_id = project_id or os.environ.get("HW_PROJECT_ID") or os.environ.get("HUAWEI_PROJECT_ID") or os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")

    if fetch_project_id and not proj_id and region and access_key and secret_key:
        proj_id = _fetch_project_id(region, access_key, secret_key, token)

    return CredentialCtx(ak=access_key, sk=secret_key, security_token=token, project_id=proj_id)


def _fetch_project_id(region: str, ak: str, sk: str, token: Optional[str]) -> Optional[str]:
    """Fetch project_id via hcloud IAM KeystoneListProjects, cache in process memory."""
    if region in _PROJECT_ID_CACHE:
        return _PROJECT_ID_CACHE[region]

    args = [
        "hcloud", "IAM", "KeystoneListProjects",
        f"--cli-region={region}",
        "--cli-output=json",
        f"--cli-query=projects[?name=='{region}'].id",
    ]
    # Only pass AK/SK as CLI args if hcloud config doesn't have credentials
    if not _hcloud_config_has_credentials():
        args.extend([f"--cli-access-key={ak}", f"--cli-secret-key={sk}"])
        if token:
            args.append(f"--cli-security-token={token}")

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            stdout = r.stdout.strip()
            json_start = stdout.find('[')
            if json_start >= 0:
                decoder = json.JSONDecoder()
                ids, _ = decoder.raw_decode(stdout[json_start:])
            elif stdout:
                decoder = json.JSONDecoder()
                try:
                    ids, _ = decoder.raw_decode(stdout)
                except json.JSONDecodeError:
                    ids = []
            else:
                ids = []
            if ids and len(ids) > 0:
                _PROJECT_ID_CACHE[region] = ids[0]
                return ids[0]
    except Exception:
        pass
    return None


def _build_auth_args(ctx: CredentialCtx) -> list:
    """Build hcloud CLI auth arguments.

    If hcloud config has credentials, skip AK/SK to avoid ps aux exposure.
    """
    args = []
    if not _hcloud_config_has_credentials():
        args.extend([f"--cli-access-key={ctx.ak}", f"--cli-secret-key={ctx.sk}"])
        if ctx.security_token:
            args.append(f"--cli-security-token={ctx.security_token}")
    if ctx.project_id:
        args.append(f"--cli-project-id={ctx.project_id}")
    return args


def run(
    ctx: CredentialCtx,
    region: str,
    service: str,
    operation: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute hcloud command and return normalized result."""
    args = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
    args.extend(_build_auth_args(ctx))

    # Always include project_id as a hcloud param (needed for path-based APIs)
    effective_params = dict(params)
    if ctx.project_id and "project_id" not in effective_params:
        effective_params["project_id"] = ctx.project_id

    for key, value in effective_params.items():
        args.append(f"--{key}={value}")

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            stdout = r.stdout.strip()
            # hcloud returns exit code 0 even for usage errors — check [USE_ERROR] marker
            if "[USE_ERROR]" in stdout:
                return {"success": False, "error": stdout[:500]}
            json_start = stdout.find('{')
            if json_start >= 0:
                # Use raw_decode to parse only the JSON part (hcloud may append table text after JSON)
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(stdout[json_start:])
            else:
                data = {}
            # hcloud returns exit code 0 even for API errors — check response body
            if isinstance(data, dict):
                status = data.get("status", "")
                code = data.get("code")
                error_code = data.get("error_code") or data.get("errorCode")
                if status == "Failure" or (isinstance(code, int) and code >= 400) or error_code or (isinstance(code, str) and code and data.get("message")):
                    err_msg = data.get("error_msg") or data.get("errorMessage") or data.get("message", "")
                    return {"success": False, "error": f"{error_code or code}: {err_msg}", "data": data}
            return {"success": True, "data": data, "message": f"{service} {operation} completed"}
        else:
            return {"success": False, "error": r.stderr.strip() or r.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"hcloud {service} {operation} timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse hcloud output: {e}", "raw": r.stdout[:500]}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


def run_with_body(
    ctx: CredentialCtx,
    region: str,
    service: str,
    operation: str,
    body: Dict[str, Any],
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute hcloud with complex nested body via --cli-jsonInput."""
    # Ensure project_id is in path_params (needed for path-based APIs;
    # --cli-jsonInput path params take priority over CLI args)
    effective_path = dict(path_params) if path_params else {}
    if ctx.project_id and "project_id" not in effective_path:
        effective_path["project_id"] = ctx.project_id

    json_input = {}
    if effective_path:
        json_input["path"] = effective_path
    if query_params:
        json_input["query"] = query_params
    json_input["body"] = body

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_input, f)
        tmp_path = f.name

    try:
        args = ["hcloud", service, operation, f"--cli-region={region}", "--cli-output=json"]
        args.extend(_build_auth_args(ctx))
        args.append(f"--cli-jsonInput={tmp_path}")

        r = subprocess.run(args, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            stdout = r.stdout.strip()
            # hcloud returns exit code 0 even for usage errors — check [USE_ERROR] marker
            if "[USE_ERROR]" in stdout:
                return {"success": False, "error": stdout[:500]}
            json_start = stdout.find('{')
            if json_start >= 0:
                decoder = json.JSONDecoder()
                data, _ = decoder.raw_decode(stdout[json_start:])
            else:
                data = {}
            if isinstance(data, dict):
                status = data.get("status", "")
                code = data.get("code")
                error_code = data.get("error_code") or data.get("errorCode")
                if status == "Failure" or (isinstance(code, int) and code >= 400) or error_code or (isinstance(code, str) and code and data.get("message")):
                    err_msg = data.get("error_msg") or data.get("errorMessage") or data.get("message", "")
                    return {"success": False, "error": f"{error_code or code}: {err_msg}", "data": data}
            return {"success": True, "data": data, "message": f"{service} {operation} completed"}
        else:
            return {"success": False, "error": r.stderr.strip() or r.stdout.strip()}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ============================================================
# kubectl-cce: Kubernetes operations via kubectl cce plugin (no EIP needed)
# ============================================================

def kubectl_cce(ctx: CredentialCtx, region: str, cluster_id: str,
                args: List[str], timeout: int = 120) -> Dict[str, Any]:
    """Execute a kubectl cce command against a CCE cluster.

    Uses the kubectl-cce plugin which connects through the CCE API Gateway.
    No cluster EIP or manual kubeconfig required.

    Credentials are passed via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY,
    HW_SECURITY_TOKEN, HW_PROJECT_ID) which the plugin reads automatically.
    """
    cmd = [
        "kubectl", "cce",
        f"--cluster-id={cluster_id}",
        f"--region={region}",
    ]
    if ctx.project_id:
        cmd.append(f"--project-id={ctx.project_id}")
    cmd.extend(args)

    # Pass credentials via environment — only set if not already present
    # (if HW_ACCESS_KEY is already in os.environ, subprocess inherits it naturally)
    env = dict(os.environ)
    if not env.get("HW_ACCESS_KEY"):
        env["HW_ACCESS_KEY"] = ctx.ak
    if not env.get("HW_SECRET_KEY"):
        env["HW_SECRET_KEY"] = ctx.sk
    if ctx.security_token and not env.get("HW_SECURITY_TOKEN"):
        env["HW_SECURITY_TOKEN"] = ctx.security_token
    if ctx.project_id and not env.get("HW_PROJECT_ID"):
        env["HW_PROJECT_ID"] = ctx.project_id

    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
        if r.returncode == 0:
            stdout = r.stdout.strip()
            # Try to parse JSON output (for -o json commands)
            if stdout.startswith("{") or stdout.startswith("["):
                try:
                    data = json.loads(stdout)
                    return {"success": True, "data": data, "stdout": stdout}
                except json.JSONDecodeError:
                    pass
            return {"success": True, "stdout": stdout}
        else:
            err = r.stderr.strip() or r.stdout.strip()
            return {"success": False, "error": err, "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"kubectl cce command timed out ({timeout}s)"}
    except FileNotFoundError:
        return {"success": False, "error": "kubectl or kubectl-cce plugin not found. Install via huawei-cloud-kubectl-cce-installer skill."}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
