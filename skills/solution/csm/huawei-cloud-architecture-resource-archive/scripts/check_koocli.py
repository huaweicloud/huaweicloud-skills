#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify/install/configure Huawei Cloud KooCLI (hcloud).

Behavior:
1. Check whether hcloud is available (PATH or default install dir)
2. If unavailable → auto-download the platform-specific build and extract to <SKILL_DIR>/../koocli/
3. Check whether AK/SK is configured (env vars HW_ACCESS_KEY/HW_SECRET_KEY or --ak/--sk args)
4. First checks whether hcloud can already authenticate (lightweight IAM ListProjects call).
   If yes → skip configure set, no disk write.
   If no  → call hcloud configure set with AK/SK from env vars or --ak/--sk args
   (writes encrypted credentials to ~/.hcloud/config.json; this is the only way hcloud CLI accepts credentials).
   **Supports temporary STS credentials**: AK/SK + security-token configured together
   (temporary credentials without token cause IAM APIGW.0301 Unauthorized)
5. Verify connectivity: call `hcloud VPC ListVpcs --cli-region=<region>` to confirm data is returned
6. Download API metadata: run `hcloud meta download` to ensure all services (CloudTable, GEIP, etc.)
   are available. hcloud ships with only iam/vpc templates; without metadata download, non-default
   services return 'Unsupported service'. Always runs to keep metadata up to date.

Usage:
    python check_koocli.py [--region cn-north-4] [--install-dir <dir>] [--force]

Dependencies: standard library only (urllib), no extra pip packages.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import tarfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from marker_constants import HCLOUD_CONFIG_OK_PROMPT, HCLOUD_MULTI_VERSION_PROMPT_HINT
from common import is_auth_error

DEFAULT_INSTALL_DIR = SCRIPT_DIR.parent / "koocli"
OBS_BASE = "https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest"


def log(msg: str) -> None:
    print(f"[KooCLI] {msg}")



def find_hcloud() -> Path | None:
    """Find hcloud in PATH and the default install directories."""
    exe = "hcloud.exe" if platform.system() == "Windows" else "hcloud"
    # 1) PATH
    found = shutil.which(exe)
    if found:
        return Path(found)
    # 2) Default install directories
    for d in [DEFAULT_INSTALL_DIR, Path.home() / "hcloud", Path("/usr/local/hcloud")]:
        cand = d / exe
        if cand.exists():
            return cand
    return None


def platform_pkg_name() -> str:
    """Return the KooCLI install package filename (without extension)."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    arch = "amd64" if ("amd64" in machine or "x86_64" in machine) else "arm64"
    ext = "zip" if sys_name == "windows" else "tar.gz"
    if sys_name == "windows":
        return f"huaweicloud-cli-windows-{arch}.zip"
    if sys_name == "darwin":
        return f"huaweicloud-cli-mac-{arch}.tar.gz"
    return f"huaweicloud-cli-linux-{arch}.tar.gz"


def download_koocli(install_dir: Path) -> Path:
    """Download and extract KooCLI, returning the hcloud executable path."""
    pkg = platform_pkg_name()
    url = f"{OBS_BASE}/{pkg}"
    install_dir.mkdir(parents=True, exist_ok=True)
    tmp = install_dir / pkg
    log(f"Downloading {url} ...")
    with urllib.request.urlopen(url, timeout=300) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=65536)
    log(f"Download complete: {tmp.stat().st_size} bytes")

    exe_name = "hcloud.exe" if platform.system() == "Windows" else "hcloud"
    if pkg.endswith(".zip"):
        with zipfile.ZipFile(tmp) as z:
            z.extractall(install_dir)
    else:
        with tarfile.open(tmp, "r:gz") as t:
            t.extractall(install_dir)
    hcloud = install_dir / exe_name
    if not hcloud.exists():
        raise RuntimeError(f"{exe_name} not found after extraction; actual files: {[p.name for p in install_dir.iterdir()]}")
    tmp.unlink(missing_ok=True)
    log(f"KooCLI installed: {hcloud}")
    return hcloud


def _env_credentials() -> tuple[str, str, str]:
    """Read AK/SK/token from environment variables (not persisted, highest priority)."""
    return (os.environ.get("HW_ACCESS_KEY", ""),
            os.environ.get("HW_SECRET_KEY", ""),
            os.environ.get("HW_SECURITY_TOKEN", ""))


def _hcloud_works(hcloud: Path, region: str) -> bool:
    """Quickly test whether hcloud can already authenticate (lightweight IAM call)."""
    try:
        result = subprocess.run(
            [str(hcloud), "IAM", "KeystoneListProjects", f"--cli-region={region}"],
            capture_output=True, text=True, timeout=30,
        )
        out = (result.stdout or "") + (result.stderr or "")
        # Success = valid JSON with "projects" key, no auth error
        if result.returncode == 0 and "projects" in out and not is_auth_error(out):
            return True
    except Exception:
        pass
    return False


def configure_koocli(hcloud: Path, ak: str, sk: str, token: str, region: str, domain_id: str = "") -> bool:
    """Configure KooCLI credentials.

    First checks whether hcloud can already authenticate (lightweight IAM ListProjects call).
    If yes → skip configure set entirely, no disk write.
    If no  → resolve AK/SK from env vars or --ak/--sk args, call configure set (writes encrypted
    credentials to ~/.hcloud/config.json; this is the only way hcloud CLI accepts credentials).

    Temporary STS credentials require AK/SK/token to be configured together, otherwise IAM returns APIGW.0301 Unauthorized.
    """
    # Step 1: check if hcloud already works — if so, skip configure set (no disk write)
    if _hcloud_works(hcloud, region):
        log("hcloud already authenticated (IAM KeystoneListProjects OK); skipping configure set, no disk write")
        return True

    # Step 2: hcloud not yet configured — need configure set
    env_ak, env_sk, env_token = _env_credentials()
    use_ak, use_sk, use_token = (env_ak or ak, env_sk or sk, env_token or token)
    if not use_ak or not use_sk:
        log("hcloud not configured and no AK/SK found. Set env vars HW_ACCESS_KEY / HW_SECRET_KEY, or pass via --ak/--sk.")
        return False

    log("hcloud not yet authenticated; calling configure set (writes encrypted credentials to ~/.hcloud/config.json)")
    cmd = [str(hcloud), "configure", "set",
           f"--cli-access-key={use_ak}",
           f"--cli-secret-key={use_sk}",
           f"--cli-region={region}"]
    if use_token:
        cmd.append(f"--cli-security-token={use_token}")
    if domain_id:
        cmd.append(f"--cli-domain-id={domain_id}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                            input="y\n")  # Accept the privacy agreement
    ok = result.returncode == 0 or HCLOUD_CONFIG_OK_PROMPT in (result.stdout or "") or HCLOUD_CONFIG_OK_PROMPT in (result.stderr or "")
    if ok:
        # Fix agreePrivacy if configure set didn't set it
        _fix_privacy_agreement()
        tok_note = " + security-token" if use_token else " (no token; temporary credentials without token cause Unauthorized)"
        log(f"KooCLI configured successfully (region={region}{tok_note})")
    else:
        log(f"KooCLI configure output: {result.stdout} {result.stderr}")
    return ok


def _fix_privacy_agreement() -> None:
    """Ensure agreePrivacy=true in hcloud config so non-interactive calls don't prompt."""
    config_path = Path.home() / ".hcloud" / "config.json"
    if not config_path.exists():
        return
    try:
        with open(config_path, "r") as f:
            config = json.loads(f.read())
        if config.get("agreePrivacy") != "true":
            config["agreePrivacy"] = "true"
            with open(config_path, "w") as f:
                json.dump(config, f, indent="\t")
    except Exception:
        pass


def strip_non_json(raw: str) -> str:
    """Remove KooCLI prompt lines (the '<op>有多个版本' multi-version hint defined in marker_constants) and ANSI color codes, keeping only the JSON part."""
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    p1 = clean.find("{")
    p2 = clean.find("[")
    pos = p1 if p1 >= 0 and (p2 < 0 or p1 < p2) else p2
    return clean[pos:] if pos >= 0 else ""


def verify_connectivity(hcloud: Path, region: str) -> bool:
    """Call VPC ListVpcs to verify authentication/network connectivity (tolerant of version prompt lines, compatible with various return keys)."""
    log(f"Verifying connectivity: VPC ListVpcs @ {region} ...")
    cmd = [str(hcloud), "VPC", "ListVpcs", f"--cli-region={region}"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = (result.stdout or "") + (result.stderr or "")
    body = strip_non_json(out)
    try:
        data = json.loads(body)
    except Exception:
        log(f"Connectivity failed (non-JSON output): {out[:300]}")
        return False
    if not isinstance(data, dict):
        log(f"Connectivity failed (non-object JSON): {out[:300]}")
        return False
    err = data.get("error_code") or data.get("error_msg")
    if err:
        log(f"Connectivity failed: {err} {data.get('error_msg', '')}".strip())
        return False
    # Success: at least one list key exists and no error
    for key in ("vpcs", "subnets", "security_groups"):
        if isinstance(data.get(key), list):
            log(f"Connectivity OK: returned {len(data[key])} {key}")
            return True
    log(f"Connectivity OK (JSON returned, keys: {list(data.keys())[:6]})")
    return True

def ensure_metadata(hcloud: Path) -> bool:
    """Download hcloud API metadata so all services (not just default iam/vpc) are available.

    hcloud ships with only iam and vpc templates pre-installed. Without downloading metadata,
    services like CloudTable, GEIP, etc. return 'Unsupported service'. Always runs
    `hcloud meta download` to ensure metadata is up to date.
    """
    meta_dir = Path.home() / ".hcloud" / "metaOrigin" / "template"
    log("Downloading API metadata (hcloud meta download) ...")
    try:
        result = subprocess.run(
            [str(hcloud), "meta", "download"],
            capture_output=True, text=True, timeout=300,
            input="y\n",
        )
        out = (result.stdout or "") + (result.stderr or "")
        if "下载成功" in out or "Download successful" in out or result.returncode == 0:
            if meta_dir.exists():
                svc_count = sum(1 for d in meta_dir.iterdir() if d.is_dir())
                log(f"API metadata downloaded successfully ({svc_count} service templates)")
                return True
            log("API metadata download reported success but template dir not found")
            return True
        log(f"API metadata download may have failed: {out[:300]}")
        return False
    except Exception as exc:
        log(f"API metadata download exception: {exc}")
        return False



# Third-party Python dependencies used across the skill scripts.
# Each entry: (import_name, pip_package, description, blocks_main_flow)
PYTHON_DEPS = [
    ("kubernetes",        "kubernetes",        "CCE K8s sub-resource direct connection (query_cce_k8s.py)",          False),
    ("huaweicloudsdkcore","huaweicloudsdkcore","CCE proxy fallback for K8s sub-resources (query_cce_k8s.py)",      False),
    ("openpyxl",          "openpyxl",          "Marker table Excel generation (generate_marker_table.py, Step 4)",  True),
    ("requests",          "requests",          "CCE proxy HTTP calls (query_cce_k8s.py)",                            False),
    ("urllib3",           "urllib3",           "SSL warning suppression in K8s query (query_cce_k8s.py)",            False),
    ("yaml",              "pyyaml",            "Kubeconfig YAML parsing (query_cce_k8s.py)",                         False),
]


def check_python_deps() -> bool:
    """Check and auto-install all third-party Python dependencies required by the skill scripts.

    Scans every .py file in this directory via ast to discover imports, then cross-references
    with PYTHON_DEPS. Missing packages are pip-installed automatically. Returns True if all
    blocking dependencies are ready; non-blocking missing deps emit a warning but do not fail.
    """
    import ast

    # ── Discover all third-party imports from source ──
    script_dir = Path(__file__).resolve().parent
    local_modules = {f.stem for f in script_dir.glob("*.py")}
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
    discovered = set()
    for pyfile in script_dir.glob("*.py"):
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in stdlib and top not in local_modules and top != "__future__":
                        discovered.add(top)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top not in stdlib and top not in local_modules and top != "__future__":
                    discovered.add(top)

    # ── Check each declared dependency ──
    all_ok = True
    for import_name, pip_name, desc, blocks in PYTHON_DEPS:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "?")
            log(f"Python dep {import_name} available (v{ver}) OK — {desc}")
            continue
        except ImportError:
            pass

        # Missing → attempt auto-install
        log(f"Python dep {import_name} not found, installing (pip install {pip_name}) ...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name, "-q"],
                capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                mod = __import__(import_name)
                ver = getattr(mod, "__version__", "?")
                log(f"Python dep {import_name} installed successfully (v{ver}) OK — {desc}")
                continue
            log(f"  pip install failed: {(result.stderr or result.stdout)[:200]}")
        except Exception as exc:
            log(f"  Auto-install exception: {exc}")

        # Install failed
        if blocks:
            log(f"ERROR: {import_name} is required ({desc}); pipeline will fail at the step that needs it")
            all_ok = False
        else:
            log(f"WARNING: {import_name} not ready — {desc} will be skipped")
        log(f"   Manual install: pip install {pip_name}")

    # ── Check for discovered imports not in PYTHON_DEPS (new deps added to scripts) ──
    declared = {d[0] for d in PYTHON_DEPS}
    undeclared = discovered - declared
    if undeclared:
        log(f"NOTE: discovered undeclared third-party imports: {sorted(undeclared)} — consider adding to PYTHON_DEPS")

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Check/install/configure Huawei Cloud KooCLI")
    parser.add_argument("--region", default="cn-north-4", help="Default region (for config + verification)")
    parser.add_argument("--ak", default="", help="Access Key (defaults to env var HW_ACCESS_KEY)")
    parser.add_argument("--sk", default="", help="Secret Key (defaults to env var HW_SECRET_KEY)")
    parser.add_argument("--token", default="", help="Security Token (required for temporary credentials; defaults to HW_SECURITY_TOKEN)")
    parser.add_argument("--domain-id", default="", help="Domain/account ID (optional, used for global services)")
    parser.add_argument("--install-dir", default=str(DEFAULT_INSTALL_DIR), help="KooCLI install directory")
    parser.add_argument("--force", action="store_true", help="Force re-download and install")
    args = parser.parse_args()

    # 1) Find hcloud
    hcloud = None if args.force else find_hcloud()
    if hcloud:
        log(f"KooCLI found: {hcloud}")
    else:
        log("KooCLI not found, starting install ...")
        try:
            hcloud = download_koocli(Path(args.install_dir))
        except Exception as exc:
            log(f"Install failed: {exc}")
            return 1

    # 2) Version
    try:
        v = subprocess.run([str(hcloud), "version"], capture_output=True, text=True, timeout=30, input="y\n")
        log(f"Version: {(v.stdout or v.stderr).strip()[:80]}")
    except Exception:
        pass

    # 3) AK/SK(/token) configuration
    if not configure_koocli(hcloud, args.ak, args.sk, args.token, args.region, args.domain_id):
        return 1

    # 4) Connectivity verification
    if not verify_connectivity(hcloud, args.region):
        log("Connectivity verification failed: if using temporary credentials, ensure HW_SECURITY_TOKEN is set; also check network connectivity")
        return 1

    # 4.5) API metadata download (ensures all services are available, not just default iam/vpc)
    ensure_metadata(hcloud)

    # 5) Third-party Python dependencies (kubernetes, huaweicloudsdkcore, openpyxl, requests, urllib3, pyyaml)
    check_python_deps()

    log("KooCLI verification passed OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())