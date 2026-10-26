#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supplement query for CCE cluster K8s sub-resources.

Two-layer strategy: try direct public network connection first → fall back to CCE endpoint proxy on failure.
"""

from __future__ import annotations

import argparse, json, logging, os, re, sys, warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import find_hcloud, run_hcloud, strip_non_json, timestamp, log, run_regions_concurrent  # noqa: E402

try:
    from kubernetes import client, config
except ImportError:
    print("[FATAL] kubernetes client missing: pip install kubernetes", file=sys.stderr)
    sys.exit(1)

try:
    import requests, urllib3
    urllib3.disable_warnings()
except ImportError:
    requests = None

logging.getLogger("urllib3").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

DEFAULT_RESOURCES = "deployments,services,configmaps,statefulsets,daemonsets,ingresses"

RESOURCE_LISTERS = {
    "deployments": ("apps", "list_deployment_for_all_namespaces"),
    "statefulsets": ("apps", "list_stateful_set_for_all_namespaces"),
    "daemonsets": ("apps", "list_daemon_set_for_all_namespaces"),
    "services": ("core", "list_service_for_all_namespaces"),
    "configmaps": ("core", "list_config_map_for_all_namespaces"),
    "ingresses": ("networking", "list_ingress_for_all_namespaces"),
    "networkpolicies": ("networking", "list_network_policy_for_all_namespaces"),
    "pods": ("core", "list_pod_for_all_namespaces"),
    "endpoints": ("core", "list_endpoints_for_all_namespaces"),
    "secrets": ("core", "list_secret_for_all_namespaces"),
}

RESOURCE_TYPES = {
    "deployments": "CCE_Deployment", "statefulsets": "CCE_StatefulSet",
    "daemonsets": "CCE_DaemonSet", "services": "CCE_Service",
    "configmaps": "CCE_ConfigMap", "ingresses": "CCE_Ingress",
    "networkpolicies": "CCE_NetworkPolicy", "pods": "CCE_Pod",
    "endpoints": "CCE_Endpoints", "secrets": "CCE_Secret",
}

K8S_API_PATHS = {
    "deployments": "/apis/apps/v1/deployments",
    "statefulsets": "/apis/apps/v1/statefulsets",
    "daemonsets": "/apis/apps/v1/daemonsets",
    "services": "/api/v1/services",
    "configmaps": "/api/v1/configmaps",
    "ingresses": "/apis/networking.k8s.io/v1/ingresses",
    "networkpolicies": "/apis/networking.k8s.io/v1/networkpolicies",
    "pods": "/api/v1/pods",
    "endpoints": "/api/v1/endpoints",
    "secrets": "/api/v1/secrets",
}


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.()-]", "_", name)

# ────────────────────────── CCE endpoint proxy ──────────────────────────

def get_project_id(hcloud, region: str) -> str:
    """Get the region project_id via hcloud IAM KeystoneListProjects."""
    raw = run_hcloud(hcloud, "IAM", "KeystoneListProjects", region, [])
    body = strip_non_json(raw)
    s, e = body.find('['), body.rfind(']') + 1
    if s < 0 or e <= s:
        return ""
    try:
        for p in json.loads(body[s:e]):
            if isinstance(p, dict) and region in str(p.get("name", "")):
                return p.get("id", "")
    except json.JSONDecodeError:
        pass
    return ""


def _build_signer(project_id: str):
    """Build a huaweicloudsdkcore Signer (environment-variable AK/SK + STS token)."""
    ak = os.environ.get("HW_ACCESS_KEY", os.environ.get("ACCESS_KEY", ""))
    sk = os.environ.get("HW_SECRET_KEY", os.environ.get("SECRET_KEY", ""))
    st = os.environ.get("HW_SECURITY_TOKEN", os.environ.get("SECURITY_TOKEN", ""))
    if not ak or not sk:
        raise RuntimeError("AK/SK not found in environment variables; cannot use CCE proxy")
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.signer.signer import Signer
    creds = BasicCredentials(ak, sk, project_id)
    if st:
        creds.with_security_token(st)
    return Signer(creds)


def cce_proxy_get(signer, project_id, cce_host, k8s_path, cluster_uid, timeout=15):
    """Call the K8s API via the CCE proxy endpoint; returns a JSON dict."""
    from huaweicloudsdkcore.sdk_request import SdkRequest
    st = os.environ.get("HW_SECURITY_TOKEN", os.environ.get("SECURITY_TOKEN", ""))
    headers = {"X-Cluster-ID": cluster_uid, "Content-Type": "application/json"}
    if st:
        headers["X-Security-Token"] = st
    if project_id:
        headers["X-Project-Id"] = project_id
    sdk_req = SdkRequest(
        method="GET", schema="https", host=cce_host,
        resource_path=k8s_path, uri=k8s_path,
        query_params=[], header_params=headers, body=None, stream=False,
    )
    signed_req = signer.sign(sdk_req)
    r = requests.get(f"https://{cce_host}{k8s_path}",
                     headers=dict(signed_req.header_params),
                     verify=False, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"CCE proxy HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def list_resources_via_proxy(signer, project_id, cce_host, cluster_uid,
                             resource_types, skip_system,
                             cluster_name, region, out_dir):
    """Query K8s sub-resources via the CCE proxy, save JSON, returns {rtype: count}."""
    ts = timestamp()
    counts = {}
    skip_all = False  # Cluster-level error (not ready / not found): skip subsequent on first failure
    for rtype in resource_types:
        if skip_all:
            counts[rtype] = -1
            continue
        k8s_path = K8S_API_PATHS.get(rtype)
        if not k8s_path:
            counts[rtype] = -1
            continue
        try:
            data = cce_proxy_get(signer, project_id, cce_host, k8s_path, cluster_uid)
        except RuntimeError as exc:
            msg = str(exc)
            log(f"  [{rtype}] proxy query failed: {msg}")
            counts[rtype] = -1
            # Cluster-level error: skip all subsequent resource types
            if "not ready" in msg.lower() or "not found" in msg.lower():
                log(f"  cluster-level error, skipping subsequent resource types")
                skip_all = True
            continue
        except Exception as exc:
            log(f"  [{rtype}] proxy query failed: {exc}")
            counts[rtype] = -1
            continue
        items = []
        for obj in (data.get("items") or []):
            ns = (obj.get("metadata") or {}).get("namespace", "")
            if skip_system and ns == "kube-system":
                continue
            items.append(obj)
        counts[rtype] = len(items)
        fname = f"CCE_k8s_{rtype}_{sanitize(cluster_name)}_{cluster_uid}_{ts}.json"
        payload = {"cluster": {"name": cluster_name, "uid": cluster_uid},
                   "region": region, "resource_type": RESOURCE_TYPES.get(rtype, rtype),
                   "k8s_type": rtype, "via_proxy": True, "items": items}
        (out_dir / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"  [{rtype}] proxy saved {len(items)} rows -> {fname}")
    return counts

# ────────────────────────── Cluster discovery & kubeconfig ──────────────────────────

def get_clusters(query_dir, region):
    """Read the latest CCE cluster list for the region, returns [{name, uid}]."""
    cce_dir = query_dir / "CCE" / "temp"
    if not cce_dir.exists():
        return []
    files = sorted(cce_dir.glob("*cluster_vm_new_*.json"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    m = re.compile(r"CCE_cce_cluster_vm_new_(?P<region>[a-z0-9-]+)_\d{8}_\d{6}\.json")
    clusters, seen = [], set()
    for f in files:
        fm = m.match(f.name)
        if fm and fm.group("region") != region:
            continue
        try:
            data = json.loads(strip_non_json(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
        for c in data.get("items") or data.get("clusters") or []:
            meta = c.get("metadata") or {}
            uid, name = meta.get("uid") or c.get("id"), meta.get("name")
            if uid and name and uid not in seen:
                seen.add(uid)
                clusters.append({"name": name, "uid": uid})
    return clusters


def fetch_kubeconfig(hcloud, region, cid):
    """Get kubeconfig via CCE CreateKubernetesClusterCert."""
    raw = run_hcloud(hcloud, "CCE", "CreateKubernetesClusterCert", region,
                     ["--cluster_id=" + cid, "--duration=1"])
    body = strip_non_json(raw)
    if not body:
        raise RuntimeError("certificate API produced no JSON output")
    start = min(p for p in (body.find("{"), body.find("[")) if p >= 0)
    end = max(body.rfind("}"), body.rfind("]"))
    if start < 0 or end <= start:
        raise RuntimeError("certificate response JSON range error")
    data = json.loads(body[start:end + 1])
    if data.get("kind") == "Status" or data.get("status") == "Failure":
        raise RuntimeError(data.get("message") or data.get("error_msg") or "no usable K8s endpoint")
    kube_text = data.get("kubeconfig")
    if isinstance(kube_text, str):
        import yaml
        cfg = yaml.safe_load(kube_text)
        if not isinstance(cfg, dict):
            raise RuntimeError("kubeconfig parse failed")
        return cfg
    return data


def prefer_external_context(cfg):
    contexts = [c.get("name") for c in cfg.get("contexts") or []]
    for name in ("external", "externalTLSVerify"):
        if name in contexts:
            cfg["current-context"] = name
            return cfg
    return cfg


def has_external_endpoint(cfg):
    contexts = [c.get("name") for c in cfg.get("contexts") or []]
    return any(n in contexts for n in ("external", "externalTLSVerify"))


def get_clusters_fresh(hcloud, region):
    """Live-fetch the cluster list from hcloud CCE ListClusters (used for fallback)."""
    raw = run_hcloud(hcloud, "CCE", "ListClusters", region, [])
    body = strip_non_json(raw)
    s, e = body.find('['), body.rfind(']') + 1
    if s < 0 or e <= s:
        return []
    try:
        items = json.loads(body[s:e])
    except json.JSONDecodeError:
        return []
    clusters = []
    for c in items:
        meta = c.get("metadata") or {}
        uid, name = meta.get("uid"), meta.get("name")
        if uid and name:
            clusters.append({"name": name, "uid": uid})
    return clusters

# ────────────────────────── Direct connection query ──────────────────────────

def list_resources(api_client, resource_types, skip_system,
                   cluster_name, cluster_uid, region, out_dir):
    """Query K8s sub-resources via a direct kubernetes client connection."""
    v1 = client.CoreV1Api(api_client)
    apps = client.AppsV1Api(api_client)
    net = client.NetworkingV1Api(api_client)
    apis = {"core": v1, "apps": apps, "networking": net}
    ts = timestamp()
    counts = {}
    for rtype in resource_types:
        api_ver, method_name = RESOURCE_LISTERS[rtype]
        api = apis[api_ver]
        try:
            result = getattr(api, method_name)()
        except Exception as exc:
            log(f"  [{rtype}] query failed: {exc}")
            counts[rtype] = -1
            continue
        items = []
        for obj in (result.items or []):
            ns = obj.metadata.namespace if obj.metadata else ""
            if skip_system and ns == "kube-system":
                continue
            items.append(api_client.sanitize_for_serialization(obj))
        counts[rtype] = len(items)
        fname = f"CCE_k8s_{rtype}_{sanitize(cluster_name)}_{cluster_uid}_{ts}.json"
        payload = {"cluster": {"name": cluster_name, "uid": cluster_uid},
                   "region": region, "resource_type": RESOURCE_TYPES.get(rtype, rtype),
                   "k8s_type": rtype, "via_proxy": False, "items": items}
        (out_dir / fname).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"  [{rtype}] saved {len(items)} rows -> {fname}")
    return counts


def _try_direct_access(cfg, resource_types, skip_system,
                       cluster_name, cluster_uid, region, out_dir):
    """Try a direct public-network connection to the K8s API. Returns a counts dict on success, None on failure."""
    try:
        api_client = config.new_client_from_config_dict(cfg)
    except Exception as exc:
        log(f"  [cluster {cluster_name}] kubeconfig load failed: {exc}")
        return None
    api_client.rest_client.pool_manager.connection_pool_kw["timeout"] = urllib3.Timeout(total=30)
    log(f"  [cluster {cluster_name}] attempting direct K8s API connection (external, timeout=30s) ...")
    try:
        client.CoreV1Api(api_client).list_namespace(timeout_seconds=10)
    except Exception as exc:
        log(f"  [cluster {cluster_name}] direct connection failed: {exc}")
        try:
            api_client.close()
        except Exception:
            pass
        return None
    log(f"  [cluster {cluster_name}] direct connection succeeded, starting sub-resource queries ...")
    counts = list_resources(api_client, resource_types, skip_system,
                            cluster_name, cluster_uid, region, out_dir)
    try:
        api_client.close()
    except Exception:
        pass
    return counts

# ────────────────────────── Main flow ──────────────────────────

def run(hcloud, region, out_root,
        k8s_resources=DEFAULT_RESOURCES, skip_system=False):
    """Query K8s sub-resources for all clusters in a region.

    Strategy: try direct public-network connection first -> fall back to CCE endpoint proxy on failure.
    """
    out_dir = out_root / "CCE" / "temp"
    out_dir.mkdir(parents=True, exist_ok=True)

    resource_types = [t.strip().lower() for t in k8s_resources.split(",") if t.strip()]
    unknown = [t for t in resource_types if t not in RESOURCE_LISTERS]
    if unknown:
        raise ValueError(f"unknown sub-resource type: {unknown} (available: {','.join(RESOURCE_LISTERS)})")
    if "secrets" in resource_types:
        log("WARNING: secrets included; Secret contains sensitive data, please verify the necessity of the query and subsequent handling")

    # Merge cached cluster list + live fetch (deduplicated)
    clusters = get_clusters(out_root, region)
    fresh = get_clusters_fresh(hcloud, region)
    seen_uids = {c["uid"] for c in clusters}
    for c in fresh:
        if c["uid"] not in seen_uids:
            clusters.append(c)
            seen_uids.add(c["uid"])
    if not clusters:
        log(f"[k8s] region {region} has no clusters, skipping K8s sub-resources")
        return {"service": "cce_k8s", "region": region, "files": [], "count": 0}
    log(f"[k8s] region {region} discovered {len(clusters)} clusters: {[c['name'] for c in clusters]}")

    # Prefetch project_id and build signer (used for CCE proxy fallback)
    project_id = ""
    signer = None
    cce_host = f"cce.{region}.myhuaweicloud.com"
    if requests is not None:
        try:
            project_id = get_project_id(hcloud, region)
            signer = _build_signer(project_id)
            log(f"[k8s] CCE proxy ready: host={cce_host}, project_id={project_id[:12]}...")
        except Exception as exc:
            log(f"[k8s] CCE proxy initialization failed (fallback unavailable): {exc}")

    summary = {"region": region, "clusters": {}}
    files = []

    for c in clusters:
        cname, cuid = c["name"], c["uid"]

        # 1. Get kubeconfig (do not skip on failure; try CCE proxy afterwards)
        cfg = None
        try:
            cfg = fetch_kubeconfig(hcloud, region, cuid)
        except RuntimeError as exc:
            log(f"  [cluster {cname}] kubeconfig retrieval failed: {exc}")

        # 2. Try direct public-network connection first (requires kubeconfig + external endpoint)
        direct_ok = False
        if cfg and has_external_endpoint(cfg):
            cfg = prefer_external_context(cfg)
            counts = _try_direct_access(cfg, resource_types, skip_system,
                                        cname, cuid, region, out_dir)
            if counts is not None:
                direct_ok = True
                summary["clusters"][cname] = {"via": "direct", **counts}
                files.extend(out_dir.glob(f"CCE_k8s_*_{cuid}_*.json"))

        # 3. Direct connection failed / no external / kubeconfig failed -> fall back to CCE proxy
        if not direct_ok:
            if signer is None:
                log(f"  [cluster {cname}] skipped: direct connection failed and CCE proxy unavailable")
                summary["clusters"][cname] = {"error": "direct connection failed and proxy unavailable"}
                continue
            if cfg is None:
                log(f"  [cluster {cname}] kubeconfig unavailable, attempting CCE endpoint proxy ...")
            else:
                log(f"  [cluster {cname}] falling back to CCE endpoint proxy to access the intranet K8s API ...")
            try:
                counts = list_resources_via_proxy(
                    signer, project_id, cce_host, cuid,
                    resource_types, skip_system, cname, region, out_dir)
                summary["clusters"][cname] = {"via": "proxy", **counts}
                files.extend(out_dir.glob(f"CCE_k8s_*_{cuid}_*.json"))
            except Exception as exc:
                log(f"  [cluster {cname}] CCE proxy also failed: {exc}")
                summary["clusters"][cname] = {"error": str(exc)}

    total = sum(v for c in summary.get("clusters", {}).values()
                for v in c.values() if isinstance(v, int) and v > 0)
    return {"service": "cce_k8s", "region": region,
            "files": [str(f) for f in files], "count": total}


def main():
    parser = argparse.ArgumentParser(description="Query CCE K8s sub-resources (direct + proxy fallback)")
    parser.add_argument("--region", required=True)
    parser.add_argument("--query-dir", required=True)
    parser.add_argument("--k8s-resources", default=DEFAULT_RESOURCES)
    parser.add_argument("--skip-system-namespaces", action="store_true")
    parser.add_argument("--hcloud-path", default="")
    args = parser.parse_args()

    hcloud = find_hcloud(args.hcloud_path)
    result = run(hcloud, args.region, Path(args.query_dir),
                 k8s_resources=args.k8s_resources, skip_system=args.skip_system_namespaces)
    report_path = Path(args.query_dir) / "CCE" / "temp" / f"cce_k8s_report_{timestamp()}.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Complete; report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
