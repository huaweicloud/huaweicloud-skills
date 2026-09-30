#!/usr/bin/env python3
"""
Discover CCE clusters and nodes in a specified AZ for AZ power outage experiment.

Usage:
    python3 discover_cce.py --region cn-north-4
    python3 discover_cce.py --region cn-north-4 --cluster-id <id> --az cn-north-4a
    python3 discover_cce.py --region cn-north-4 --cluster-id <id> --az cn-north-4a --include-pods
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys


# Only pass required environment variables to subprocess (avoid bulk env harvesting)
_ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL",
    "HW_ACCESS_KEY", "HW_SECRET_KEY", "HW_REGION_NAME",
    "KUBECONFIG",
)


def _build_env(region=None):
    """Build a minimal environment dict with only needed variables."""
    env = {k: os.environ[k] for k in _ENV_WHITELIST if k in os.environ}
    if region and "HW_REGION_NAME" not in env:
        env["HW_REGION_NAME"] = region
    return env


def find_kubectl():
    """Find kubectl binary path. Searches PATH first, then common install locations."""
    path = shutil.which("kubectl")
    if path:
        return path
    for candidate in [
        "/usr/local/bin/kubectl",
        "/root/bin/kubectl",
        "/usr/bin/kubectl",
        os.path.expanduser("~/.local/bin/kubectl"),
    ]:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def run_cmd(cmd, check=True, region=None):
    """Run a command (list or string) and return stdout.

    Uses shell=False with list args to prevent shell injection.
    If cmd is a string, it is split with shlex.split().
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    env = _build_env(region)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout.strip()


def hcloud_cmd(args, region=None):
    """Run an hcloud CLI command and return parsed JSON.

    Note: hcloud KooCLI may append diagnostic table text after the JSON
    output (e.g. "获取终端宽度失败" + table). Use raw_decode to extract
    only the JSON portion and avoid json.loads "Extra data" errors.
    """
    cmd = shlex.split(args) if isinstance(args, str) else list(args)
    cmd = ["hcloud"] + cmd + ["--cli-output=json"]
    if region:
        cmd.append(f"--cli-region={region}")
    output = run_cmd(cmd, region=region)
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(output)
        return obj


def get_ecs_instance_map(region):
    """Query hcloud ECS ListServersDetails and build a private-IP → ECS-server-ID map.

    In CCE, the Kubernetes node name is the node's private IP. However,
    spec.providerID contains a CCE-internal node ID, NOT the ECS server ID
    needed by ECS BatchStopServers/BatchStartServers. This function builds
    the correct mapping by querying the ECS API directly.
    """
    ip_to_id = {}
    try:
        result = hcloud_cmd("ECS ListServersDetails", region)
        servers = result.get("servers", []) if isinstance(result, dict) else result
        if not isinstance(servers, list):
            servers = []
        for server in servers:
            ecs_id = server.get("id", "")
            if not ecs_id:
                continue
            # Extract private IPs from addresses
            addresses = server.get("addresses", {})
            for net_name, net_list in addresses.items():
                for addr in net_list:
                    if isinstance(addr, dict):
                        ip = addr.get("addr", "")
                        if ip:
                            ip_to_id[ip] = ecs_id
    except Exception as e:
        print(f"Warning: Failed to query ECS server details: {e}", file=sys.stderr)
    return ip_to_id


def list_cce_clusters(region):
    """List all CCE clusters in the region."""
    try:
        result = hcloud_cmd("CCE ListClusters", region)
        clusters = result.get("items", result) if isinstance(result, dict) else result
        if not isinstance(clusters, list):
            clusters = []
        return clusters
    except Exception as e:
        print(f"Warning: Failed to list CCE clusters: {e}", file=sys.stderr)
        return []


def check_kubeconfig():
    """Check that KUBECONFIG environment variable is set.

    The user is responsible for providing the kubeconfig file path via
    the KUBECONFIG environment variable before running this script.
    This script does NOT obtain or create kubeconfig files.
    """
    kubeconfig = os.environ.get("KUBECONFIG", "")
    if not kubeconfig:
        default_path = os.path.expanduser("~/.kube/config")
        if os.path.exists(default_path):
            return True
        print("Error: KUBECONFIG environment variable is not set.", file=sys.stderr)
        print("       Set it before running this script, e.g.:", file=sys.stderr)
        print('       Set the KUBECONFIG env var to point to your file.', file=sys.stderr)
        return False
    if not os.path.exists(kubeconfig):
        print(f"Error: KUBECONFIG file not found: {kubeconfig}", file=sys.stderr)
        return False
    return True



def kubectl_cmd(args):
    """Run a kubectl command and return parsed JSON."""
    kubectl_path = find_kubectl()
    if not kubectl_path:
        print("Error: kubectl not found in PATH or common locations", file=sys.stderr)
        return None
    arg_list = shlex.split(args) if isinstance(args, str) else list(args)
    cmd = [kubectl_path] + arg_list + ["-o", "json"]
    output = run_cmd(cmd, check=False)
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def get_nodes_by_az(az, region=None, ecs_instance_map=None):
    """Get all Kubernetes nodes in a specific AZ.

    Args:
        az: Target availability zone.
        region: Huawei Cloud region (for building ECS instance map if not provided).
        ecs_instance_map: Pre-built private-IP → ECS-server-ID map. If not
            provided and region is given, the map is built here.
    """
    if ecs_instance_map is None and region:
        ecs_instance_map = get_ecs_instance_map(region)
    if ecs_instance_map is None:
        ecs_instance_map = {}

    data = kubectl_cmd("get nodes")
    if not data:
        return [], []

    nodes_in_az = []
    all_nodes = []

    for item in data.get("items", []):
        node_name = item["metadata"]["name"]
        labels = item["metadata"].get("labels", {})

        # Determine AZ from node labels
        node_az = (
            labels.get("topology.kubernetes.io/zone")
            or labels.get("failure-domain.beta.kubernetes.io/zone")
            or "unknown"
        )

        # Get node status
        conditions = item.get("status", {}).get("conditions", [])
        ready = False
        for cond in conditions:
            if cond.get("type") == "Ready":
                ready = cond.get("status") == "True"

        # Get allocatable resources
        allocatable = item.get("status", {}).get("allocatable", {})
        capacity = item.get("status", {}).get("capacity", {})

        # Get ECS instance ID.
        # NOTE: spec.providerID contains a CCE-internal node ID, not the ECS
        # server ID. Use the private-IP → ECS-ID map from the ECS API instead.
        # In CCE, the Kubernetes node name IS the node's private IP.
        instance_id = ecs_instance_map.get(node_name, "")

        node_info = {
            "name": node_name,
            "az": node_az,
            "ready": ready,
            "instance_id": instance_id,
            "allocatable_cpu": allocatable.get("cpu", "0"),
            "allocatable_memory": allocatable.get("memory", "0"),
            "capacity_cpu": capacity.get("cpu", "0"),
            "capacity_memory": capacity.get("memory", "0"),
            "roles": [k.replace("node-role.kubernetes.io/", "") for k, v in labels.items()
                      if k.startswith("node-role.kubernetes.io/") and v == ""],
        }

        all_nodes.append(node_info)
        if node_az == az:
            nodes_in_az.append(node_info)

    return nodes_in_az, all_nodes


def get_pods_on_node(node_name):
    """Get all pods running on a specific node."""
    data = kubectl_cmd(f"get pods --all-namespaces --field-selector spec.nodeName={node_name}")
    if not data:
        return [], []

    pods = []
    for item in data.get("items", []):
        pod_info = {
            "name": item["metadata"]["name"],
            "namespace": item["metadata"]["namespace"],
            "phase": item.get("status", {}).get("phase", "Unknown"),
            "node": node_name,
        }

        # Get owner reference (workload)
        owners = item["metadata"].get("ownerReferences", [])
        if owners:
            pod_info["workload_kind"] = owners[0].get("kind", "")
            pod_info["workload_name"] = owners[0].get("name", "")

        pods.append(pod_info)

    return pods


def get_workloads(namespaces=None):
    """Get all deployments, statefulsets, and daemonsets."""
    workloads = []

    for kind in ["deployment", "statefulset"]:
        cmd = f"get {kind} --all-namespaces"
        data = kubectl_cmd(cmd)
        if not data:
            continue
        for item in data.get("items", []):
            spec = item.get("spec", {})
            workloads.append({
                "kind": kind.capitalize(),
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "replicas": spec.get("replicas", 1),
                "selector": spec.get("selector", {}).get("matchLabels", {}),
            })

    return workloads


def main():
    parser = argparse.ArgumentParser(description="Discover CCE clusters and AZ nodes")
    parser.add_argument("--region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"))
    parser.add_argument("--cluster-id", help="CCE cluster ID")
    parser.add_argument("--az", help="Availability zone to filter nodes")
    parser.add_argument("--include-pods", action="store_true", help="Include pod and workload info")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    result = {"region": args.region}

    # Step 1: List CCE clusters
    clusters = list_cce_clusters(args.region)
    cluster_list = []
    for c in clusters:
        cluster_list.append({
            "id": c.get("metadata", {}).get("uid", c.get("id", "")),
            "name": c.get("metadata", {}).get("name", c.get("name", "")),
            "status": c.get("status", {}).get("phase", c.get("status", "")),
            "flavor": c.get("spec", {}).get("flavor", c.get("flavor", "")),
            "version": c.get("spec", {}).get("version", c.get("version", "")),
        })
    result["clusters"] = cluster_list
    result["cluster_count"] = len(cluster_list)

    if not args.cluster_id:
        # Just list clusters
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Step 2: Get cluster info and discover nodes
    selected_cluster = None
    for c in cluster_list:
        if c["id"] == args.cluster_id:
            selected_cluster = c
            break

    result["selected_cluster"] = selected_cluster or {"id": args.cluster_id}

    # Verify that KUBECONFIG is available (user must set it externally)
    if not check_kubeconfig():
        sys.exit(1)

    # Get nodes
    if args.az:
        nodes_in_az, all_nodes = get_nodes_by_az(args.az, region=args.region)
        result["az"] = args.az
        result["target_nodes"] = nodes_in_az
        result["target_node_count"] = len(nodes_in_az)
        result["all_nodes"] = all_nodes
        result["all_node_count"] = len(all_nodes)

        # Group nodes by AZ
        az_summary = {}
        for n in all_nodes:
            az = n["az"]
            if az not in az_summary:
                az_summary[az] = {"count": 0, "ready": 0}
            az_summary[az]["count"] += 1
            if n["ready"]:
                az_summary[az]["ready"] += 1
        result["az_summary"] = az_summary

        if args.include_pods:
            # Get pods on target nodes
            for node in nodes_in_az:
                node["pods"] = get_pods_on_node(node["name"])
                node["pod_count"] = len(node["pods"])

            # Get all workloads
            result["workloads"] = get_workloads()

            # Summarize pods to be rescheduled
            all_pods = []
            for node in nodes_in_az:
                all_pods.extend(node.get("pods", []))
            result["pods_to_reschedule"] = len(all_pods)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Discovery result written to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
