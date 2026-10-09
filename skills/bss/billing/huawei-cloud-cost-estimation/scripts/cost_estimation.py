#!/usr/bin/env python3
"""Huawei Cloud cost estimation — read-only pre-purchase price estimation via hcloud.

Quality reporting: vendored skill_quality_sdk (scripts/skill_quality_sdk.py).

Usage (all read-only, no side effects):
  python3 cost_estimation.py auth-projects                     # resolve accessible project_id
  python3 cost_estimation.py period-quote --project_id P --spec c6.2xlarge.2.linux \
      --service-type hws.service.type.ec2 --resource-type hws.resource.type.vm \
      --region cn-north-1 --period-type 2 --period-num 1 --quantity 1
  python3 cost_estimation.py ondemand-quote --project_id P --spec ac3.large.2.linux \
      --service-type hws.service.type.ec2 --resource-type hws.resource.type.vm \
      --region cn-north-1 --factor Duration --usage-value 1 --usage-measure-id 4 --quantity 1

All commands are read-only queries (List*/Show* / POST pricing inquiry that only returns price).
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_quality_sdk import quality_report  # noqa: E402

BSS_REGION = "cn-north-1"


def _hcloud(args, region=BSS_REGION):
    """Run a read-only hcloud command and return parsed JSON.

    hcloud requires `--param=value` (equals) form; pass compound args already
    joined. `args` is a flat list of shell words that may contain `--k=v`.
    """
    cmd = ["hcloud"] + args + [f"--cli-region={region}", "--cli-output=json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout = (proc.stdout or "").strip()
    if proc.returncode != 0:
        err = proc.stderr.strip() or stdout
        raise RuntimeError(f"hcloud {args[0]} failed: {err[:500]}")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"hcloud {args[0]} non-JSON output: {stdout[:200]}") from e


@quality_report(skill_name="huawei-cloud-cost-estimation", skill_version="1.0.0")
def auth_projects():
    """List accessible projects (IAM read-only)."""
    data = _hcloud(["IAM", "KeystoneListAuthProjects"])
    projects = data.get("projects", [])
    rows = [f"{p.get('name')}\t{p.get('id')}" for p in projects]
    print("\n".join(rows))
    return {"count": len(projects)}


@quality_report(skill_name="huawei-cloud-cost-estimation", skill_version="1.0.0")
def period_quote(args):
    """Run BSS/ListRateOnPeriodDetail (read-only)."""
    cmd = ["BSS", "ListRateOnPeriodDetail", f"--project_id={args.project_id}"]
    base = "--product_infos.1."
    cmd += [
        base + "id=1",
        base + "cloud_service_type=" + args.service_type,
        base + "resource_type=" + args.resource_type,
        base + "resource_spec=" + args.spec,
        base + "region=" + args.region,
        base + "period_type=" + str(args.period_type),
        base + "period_num=" + str(args.period_num),
        base + "subscription_num=" + str(args.quantity),
    ]
    if args.size:
        cmd += [base + "resource_size=" + str(args.size), base + "size_measure_id=" + str(args.size_measure_id)]
    data = _hcloud(cmd)
    official = data.get("official_website_rating_result", {})
    amt = official.get("official_website_amount")
    print(json.dumps({"currency": data.get("currency", "CNY"),
                      "official_website_amount": amt,
                      "optional_discount_rating_results": data.get("optional_discount_rating_results", [])}))
    return {"official_website_amount": amt, "currency": data.get("currency", "CNY")}


@quality_report(skill_name="huawei-cloud-cost-estimation", skill_version="1.0.0")
def ondemand_quote(args):
    """Run BSS/ListOnDemandResourceRatings (read-only)."""
    cmd = ["BSS", "ListOnDemandResourceRatings", f"--project_id={args.project_id}"]
    base = "--product_infos.1."
    cmd += [
        base + "id=1",
        base + "cloud_service_type=" + args.service_type,
        base + "resource_type=" + args.resource_type,
        base + "resource_spec=" + args.spec,
        base + "region=" + args.region,
        base + "usage_factor=" + args.factor,
        base + "usage_value=" + str(args.usage_value),
        base + "usage_measure_id=" + str(args.usage_measure_id),
        base + "subscription_num=" + str(args.quantity),
    ]
    if args.size:
        cmd += [base + "resource_size=" + str(args.size), base + "size_measure_id=" + str(args.size_measure_id)]
    if args.precision is not None:
        cmd += [f"--inquiry_precision={args.precision}"]
    data = _hcloud(cmd)
    out = {"currency": data.get("currency", "CNY"),
           "official_website_amount": data.get("official_website_amount"),
           "amount": data.get("amount"),
           "discount_amount": data.get("discount_amount")}
    print(json.dumps(out))
    return out


def main():
    parser = argparse.ArgumentParser(description="Huawei Cloud cost estimation (read-only)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-projects", help="resolve accessible project_id")

    p = sub.add_parser("period-quote", help="BSS/ListRateOnPeriodDetail")
    _add_common(p)
    p.add_argument("--period-type", type=int, required=True)
    p.add_argument("--period-num", type=int, required=True)

    o = sub.add_parser("ondemand-quote", help="BSS/ListOnDemandResourceRatings")
    _add_common(o)
    o.add_argument("--factor", required=True)
    o.add_argument("--usage-value", type=float, required=True)
    o.add_argument("--usage-measure-id", type=int, required=True)
    o.add_argument("--precision", type=int, choices=[0, 1], default=None)

    args = parser.parse_args()
    if args.command == "auth-projects":
        auth_projects()
    elif args.command == "period-quote":
        period_quote(args)
    elif args.command == "ondemand-quote":
        ondemand_quote(args)


def _add_common(p):
    p.add_argument("--project-id", required=True)
    p.add_argument("--service-type", required=True, help="cloud_service_type code")
    p.add_argument("--resource-type", required=True, help="resource_type code")
    p.add_argument("--spec", required=True, help="resource_spec from ListResourceSpecs")
    p.add_argument("--region", required=True, help="resource deploy region")
    p.add_argument("--quantity", type=int, default=1)
    p.add_argument("--size", type=int, default=None, help="linear product size (GB/Mbps)")
    p.add_argument("--size-measure-id", type=int, default=None)


if __name__ == "__main__":
    main()