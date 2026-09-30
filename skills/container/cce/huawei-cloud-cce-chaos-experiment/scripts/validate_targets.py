#!/usr/bin/env python3
"""
Validate CCE AZ power outage experiment targets.

Checks:
1. All target nodes are Ready
2. Cross-AZ capacity: other AZs have enough resources to reschedule pods
3. PDB constraints: PodDisruptionBudgets allow eviction
4. Workload replicas >= 2 (single-replica workloads will experience downtime)
5. Single-AZ cluster risk warning
"""

import argparse
import json
import os
import shlex
import subprocess
import sys



def parse_cpu(value):
    """Parse CPU value like '1930m' or '2' to float cores."""
    if isinstance(value, (int, float)):
        return float(value)
    if not value or value == '0':
        return 0.0
    s = str(value).strip()
    if s.endswith('m'):
        return float(s[:-1]) / 1000.0
    return float(s)

def parse_memory(value):
    """Parse memory value like '2455352Ki' to float MB."""
    if isinstance(value, (int, float)):
        return float(value)
    if not value or value == '0':
        return 0.0
    s = str(value).strip().replace('Ki', '').replace('Mi', '').replace('Gi', '')
    return float(s)

def kubectl_cmd(args):
    """Run a kubectl command and return parsed JSON."""
    cmd = ["kubectl"] + shlex.split(args) + ["-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def kubectl_cmd_text(args):
    """Run a kubectl command and return text output."""
    cmd = ["kubectl"] + shlex.split(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def check_nodes_ready(target_nodes):
    """Rule 1: All target nodes must be Ready."""
    results = []
    all_ready = True
    for node in target_nodes:
        passed = node.get("ready", False)
        results.append({
            "node": node["name"],
            "rule": "node_ready",
            "passed": passed,
            "message": f"Node {node['name']} is {'Ready' if passed else 'NotReady'}"
        })
        if not passed:
            all_ready = False
    return all_ready, results


def check_cross_az_capacity(all_nodes, target_az, target_nodes):
    """Rule 2: Other AZs have enough resources to reschedule pods."""
    # Calculate total allocatable resources in target AZ
    target_cpu = sum(parse_cpu(n.get("allocatable_cpu", 0)) for n in target_nodes)
    target_memory = sum(parse_memory(n.get("allocatable_memory", "0")) for n in target_nodes)

    # Calculate total allocatable resources in other AZs
    other_cpu = 0
    other_memory = 0
    other_ready_count = 0
    for node in all_nodes:
        if node["az"] != target_az and node.get("ready", False):
            other_cpu += parse_cpu(node.get("allocatable_cpu", 0))
            other_memory += parse_memory(node.get("allocatable_memory", "0"))
            other_ready_count += 1

    passed = other_ready_count > 0 and other_cpu >= target_cpu
    message = (
        f"Target AZ {target_az}: {len(target_nodes)} nodes, {target_cpu} CPU. "
        f"Other AZs: {other_ready_count} ready nodes, {other_cpu} CPU. "
        f"{'Sufficient capacity' if passed else 'Insufficient cross-AZ capacity!'}"
    )
    return passed, [{
        "rule": "cross_az_capacity",
        "passed": passed,
        "message": message,
        "target_az_cpu": target_cpu,
        "other_az_cpu": other_cpu,
        "other_az_ready_nodes": other_ready_count,
    }]


def check_pdb_constraints(target_nodes):
    """Rule 3: PDB constraints allow eviction of all pods on target nodes."""
    # Get all PDBs
    pdb_data = kubectl_cmd("get pdb --all-namespaces")
    if not pdb_data:
        return True, [{
            "rule": "pdb_constraints",
            "passed": True,
            "message": "No PDBs found or kubectl unavailable — skipping PDB check"
        }]

    results = []
    all_passed = True

    for pdb in pdb_data.get("items", []):
        pdb_name = pdb["metadata"]["name"]
        namespace = pdb["metadata"]["namespace"]

        # Get current status
        status = pdb.get("status", {})
        allowed_disruptions = status.get("disruptionsAllowed", 0)
        desired_healthy = status.get("desiredHealthy", 0)
        current_healthy = status.get("currentHealthy", 0)

        if allowed_disruptions == 0:
            passed = False
            all_passed = False
            message = (f"PDB {namespace}/{pdb_name}: 0 disruptions allowed "
                      f"(desired={desired_healthy}, current={current_healthy}). "
                      f"Pod eviction will be blocked!")
        else:
            passed = True
            message = (f"PDB {namespace}/{pdb_name}: {allowed_disruptions} disruptions allowed "
                      f"(desired={desired_healthy}, current={current_healthy})")

        results.append({
            "rule": "pdb_constraints",
            "passed": passed,
            "message": message,
            "pdb": f"{namespace}/{pdb_name}",
            "allowed_disruptions": allowed_disruptions,
        })

    return all_passed, results


def check_workload_replicas(target_nodes, discovery_data):
    """Rule 4: Workload replicas >= 2."""
    workloads = discovery_data.get("workloads", [])
    if not workloads:
        return True, [{
            "rule": "workload_replicas",
            "passed": True,
            "message": "No workload info available — skipping replica check"
        }]

    results = []
    all_passed = True
    warnings = []

    for wl in workloads:
        replicas = wl.get("replicas", 1)
        if replicas < 2:
            passed = False
            all_passed = False
            message = (f"{wl['kind']} {wl['namespace']}/{wl['name']}: "
                      f"{replicas} replica(s) — will experience downtime during AZ outage")
            warnings.append(message)
        else:
            passed = True
            message = (f"{wl['kind']} {wl['namespace']}/{wl['name']}: "
                      f"{replicas} replicas — safe for AZ outage")

        results.append({
            "rule": "workload_replicas",
            "passed": passed,
            "message": message,
            "workload": f"{wl['namespace']}/{wl['name']}",
            "replicas": replicas,
        })

    return all_passed, results


def check_single_az_risk(all_nodes, target_az):
    """Rule 5: Single-AZ cluster risk warning."""
    az_set = set(n["az"] for n in all_nodes)

    if len(az_set) <= 1:
        return False, [{
            "rule": "single_az_cluster",
            "passed": False,
            "message": f"Cluster has nodes in only {len(az_set)} AZ(s): {az_set}. "
                      f"No cross-AZ redundancy — AZ outage will cause total outage!"
        }]
    elif len(az_set) == 2:
        return True, [{
            "rule": "single_az_cluster",
            "passed": True,
            "message": f"Cluster spans {len(az_set)} AZs: {az_set}. "
                      f"Minimal cross-AZ redundancy."
        }]
    else:
        return True, [{
            "rule": "single_az_cluster",
            "passed": True,
            "message": f"Cluster spans {len(az_set)} AZs: {az_set}. "
                      f"Good cross-AZ redundancy."
        }]


def main():
    parser = argparse.ArgumentParser(description="Validate CCE AZ power outage targets")
    parser.add_argument("--discovery-file", required=True, help="Path to discovery JSON file")
    parser.add_argument("--cluster-id", help="CCE cluster ID")
    parser.add_argument("--az", required=True, help="Target availability zone")
    parser.add_argument("--region", default=os.environ.get("HW_REGION_NAME", "cn-north-4"))
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    # Load discovery data
    with open(args.discovery_file) as f:
        discovery = json.load(f)

    target_nodes = discovery.get("target_nodes", [])
    all_nodes = discovery.get("all_nodes", [])

    if not target_nodes:
        print(json.dumps({
            "all_compatible": False,
            "error": f"No nodes found in AZ {args.az}",
            "recommendation": "Check that the AZ is correct and nodes exist in the cluster"
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    # Run all validation checks
    all_checks = []
    all_errors = []
    all_warnings = []

    # Rule 1: Nodes Ready
    passed, checks = check_nodes_ready(target_nodes)
    all_checks.extend(checks)
    if not passed:
        all_errors.append("Some target nodes are not Ready")

    # Rule 2: Cross-AZ capacity
    passed, checks = check_cross_az_capacity(all_nodes, args.az, target_nodes)
    all_checks.extend(checks)
    if not passed:
        all_errors.append("Insufficient cross-AZ capacity for pod rescheduling")

    # Rule 3: PDB constraints
    passed, checks = check_pdb_constraints(target_nodes)
    all_checks.extend(checks)
    if not passed:
        all_warnings.append("PDB constraints may block pod eviction")

    # Rule 4: Workload replicas
    passed, checks = check_workload_replicas(target_nodes, discovery)
    all_checks.extend(checks)
    if not passed:
        all_warnings.append("Some workloads have single replica — will experience downtime")

    # Rule 5: Single-AZ risk
    passed, checks = check_single_az_risk(all_nodes, args.az)
    all_checks.extend(checks)
    if not passed:
        all_errors.append("Single-AZ cluster — no cross-AZ redundancy")

    all_compatible = len(all_errors) == 0

    result = {
        "az": args.az,
        "target_node_count": len(target_nodes),
        "all_compatible": all_compatible,
        "error_count": len(all_errors),
        "warning_count": len(all_warnings),
        "checks": all_checks,
        "errors": all_errors,
        "warnings": all_warnings,
        "recommendation": (
            "All checks passed. Proceed with experiment preparation." if all_compatible and not all_warnings
            else "Compatible with warnings. Review warnings before proceeding." if all_compatible
            else "Not compatible. Fix errors before proceeding."
        ),
    }

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Validation result written to {args.output}")
    else:
        print(output_json)

    sys.exit(0 if all_compatible else 1)


if __name__ == "__main__":
    main()
