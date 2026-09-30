#!/usr/bin/env python3
"""
Discover CCE service dependencies.
Scans Service/ConfigMap/Env/Ingress references to identify services affected by AZ power outage.
"""

import json
import os
import sys
import subprocess
import argparse


def run_kubectl(args):
    """Run a kubectl command and return JSON result."""
    cmd = ["kubectl"] + args + ["-o", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"  [WARN] kubectl command failed: {e}")
        return None


def get_node_zones(node_names):
    """Get the AZ of each node."""
    nodes_data = run_kubectl(["get", "nodes"])
    if not nodes_data:
        return {}
    node_zones = {}
    for item in nodes_data.get("items", []):
        name = item["metadata"]["name"]
        zone = item["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "unknown")
        node_zones[name] = zone
    return node_zones


def get_pods_on_nodes(node_names):
    """Get the list of Pods on specified nodes."""
    pods_data = run_kubectl(["get", "pods", "--all-namespaces"])
    if not pods_data:
        return []
    affected_pods = []
    for item in pods_data.get("items", []):
        node = item.get("spec", {}).get("nodeName", "")
        if node in node_names:
            affected_pods.append({
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "node": node,
                "labels": item["metadata"].get("labels", {}),
            })
    return affected_pods


def get_services_for_pods(pods):
    """Get Services associated with the given Pods."""
    services_data = run_kubectl(["get", "services", "--all-namespaces"])
    if not services_data:
        return []
    related_services = []
    pod_namespaces = {p["namespace"] for p in pods}
    for item in services_data.get("items", []):
        ns = item["metadata"]["namespace"]
        if ns in pod_namespaces:
            selector = item.get("spec", {}).get("selector", {})
            related_services.append({
                "name": item["metadata"]["name"],
                "namespace": ns,
                "selector": selector,
                "type": item.get("spec", {}).get("type", "ClusterIP"),
            })
    return related_services


def get_ingress_for_services(services):
    """Get Ingresses associated with the given Services."""
    ingress_data = run_kubectl(["get", "ingress", "--all-namespaces"])
    if not ingress_data:
        return []
    related_ingress = []
    service_names = {(s["namespace"], s["name"]) for s in services}
    for item in ingress_data.get("items", []):
        ns = item["metadata"]["namespace"]
        rules = item.get("spec", {}).get("rules", [])
        for rule in rules:
            for path in rule.get("http", {}).get("paths", []):
                backend = path.get("backend", {})
                svc_name = backend.get("service", {}).get("name", "")
                if (ns, svc_name) in service_names:
                    related_ingress.append({
                        "name": item["metadata"]["name"],
                        "namespace": ns,
                        "host": rule.get("host", ""),
                    })
    return related_ingress


def get_configmaps_for_namespaces(pods):
    """Get ConfigMaps in relevant namespaces."""
    namespaces = {p["namespace"] for p in pods}
    configmaps = []
    for ns in namespaces:
        cm_data = run_kubectl(["get", "configmaps", "-n", ns])
        if cm_data:
            for item in cm_data.get("items", []):
                configmaps.append({
                    "name": item["metadata"]["name"],
                    "namespace": ns,
                })
    return configmaps


def main():
    parser = argparse.ArgumentParser(description="Discover CCE service dependencies")
    parser.add_argument("--nodes", help="Affected node list (comma-separated)")
    parser.add_argument("--output", default="dependencies.json", help="Output file path")
    args = parser.parse_args()

    node_names = args.nodes.split(",") if args.nodes else []

    print("[1/5] Getting node AZ information...")
    node_zones = get_node_zones(node_names)
    for n in node_names:
        print(f"  {n}: {node_zones.get(n, 'unknown')}")

    print("[2/5] Getting Pods on affected nodes...")
    affected_pods = get_pods_on_nodes(node_names)
    print(f"  Total: {len(affected_pods)} Pods")

    print("[3/5] Getting associated Services...")
    services = get_services_for_pods(affected_pods)
    print(f"  Total: {len(services)} Services")

    print("[4/5] Getting associated Ingresses...")
    ingress = get_ingress_for_services(services)
    print(f"  Total: {len(ingress)} Ingresses")

    print("[5/5] Getting associated ConfigMaps...")
    configmaps = get_configmaps_for_namespaces(affected_pods)
    print(f"  Total: {len(configmaps)} ConfigMaps")

    result = {
        "affected_nodes": node_names,
        "node_zones": node_zones,
        "affected_pods": affected_pods,
        "related_services": services,
        "related_ingress": ingress,
        "related_configmaps": configmaps,
    }
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nDependencies saved: {args.output}")


if __name__ == "__main__":
    main()
