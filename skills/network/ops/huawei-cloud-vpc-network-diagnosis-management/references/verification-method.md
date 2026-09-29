# Verification Method — huawei-cloud-vpc-network-diagnosis-management

This document describes how to verify each capability group of the skill before delivery,
and how to validate the written commands against the real KooCLI.

## 1. Prerequisites verification

```bash
hcloud version                          # KooCLI 7.2.x or later
hcloud configure list                   # a valid AKSK profile with real accessKeyId
hcloud VPC --help                       # service 'VPC' reachable, operations list shown
```

Two supported authentication modes:

| Mode | Setup | Verify |
| ---- | ----- | ------ |
| AK/SK env | `export HUAWEICLOUD_SDK_AK=<your-access-key-id>` / `export HUAWEICLOUD_SDK_SK=<your-secret-access-key>` | `hcloud VPC ListVpcs/v3 --cli-region={region} --limit=1` succeeds |
| Local profile | `hcloud configure set --cli-profile=default --cli-mode=AKSK --cli-region=cn-north-4` (keys configured out-of-band, see guide) | `hcloud configure list` shows `mode: AKSK` |

If neither is configured, run `hcloud configure` interactively.

## 2. Command syntax verification (no credentials needed)

Every operation parameter name used in SKILL.md must exist in `--help` output:

```bash
hcloud VPC ListVpcs/v3 --cli-region=cn-north-4 --help 2>&1 | grep -E -- '--(limit|marker|name|cidr|id)'
hcloud VPC CreateSubnet --cli-region=cn-north-4 --help 2>&1 | grep -E -- '--(subnet.vpc_id|subnet.name|subnet.cidr|subnet.gateway_ip)'
hcloud VPC UpdateSubnet --cli-region=cn-north-4 --help 2>&1 | grep -E -- '--(vpc_id|subnet_id|subnet.name)'
hcloud VPC DeleteSubnet --cli-region=cn-north-4 --help 2>&1 | grep -E -- '--(vpc_id|subnet_id)'
```

All 14 actions' parameter names were verified this way during development.

## 3. Query verification (R3)

Run with a real authenticated profile:

```bash
hcloud VPC ListVpcs/v3 --cli-region={region} --limit=5          # expect vpcs array
hcloud VPC ListSubnets --cli-region={region} --limit=5          # expect subnets array
hcloud VPC ShowVpc/v3 --cli-region={region} --vpc_id={vpc_id}   # expect vpc object
hcloud VPC ShowSubnet --cli-region={region} --subnet_id={subnet_id}
hcloud VPC ListRouteTables --cli-region={region} --limit=5
hcloud VPC ShowRouteTable --cli-region={region} --routetable_id={routetable_id}
hcloud VPC ListPorts/v3 --cli-region={region} --limit=5
hcloud VPC ShowPort/v3 --cli-region={region} --port_id={port_id}
hcloud VPC ShowSecurityGroup --cli-region={region} --security_group_id={security_group_id}
```

Pass criteria: HTTP 200, JSON with the expected top-level key, non-empty data when the
account has resources.

## 4. Diagnosis verification

The three diagnose actions are **local composition** of the read-only queries above:

- `huawei_diagnose_network_connectivity` = list VPCs + list subnets + list route tables +
  show each route table, then evaluate the 5 checks (subnet-in-VPC, no overlap, default
  route, association, valid gateway). Verify the evaluation logic with a small synthetic
  dataset (e.g. two overlapping CIDRs must be reported).
- `huawei_diagnose_port_connectivity` = list/show ports + show bound security groups, then
  evaluate the 5 checks (exists, ACTIVE, admin_state_up, device owner, SG rules).
- `huawei_analyze_subnet_cidr_conflict` = list VPCs/subnets, compute overlap/containment/
  adjacency with Python's `ipaddress` module. Verify with synthetic CIDR pairs:
  - `192.168.1.0/24` vs `192.168.1.128/25` → overlap must be flagged
  - `10.0.0.0/16` contains `10.0.1.0/24` → containment must be flagged
  - `192.168.1.0/24` vs `192.168.2.0/24` → adjacent, not a conflict

## 5. Manage verification (R2/R1 — requires explicit user confirmation)

Write operations must be previewed and confirmed by the user, then executed:

1. `huawei_create_vpc` → confirm name/cidr → run → `ShowVpc/v3` to verify creation.
2. `huawei_create_subnet` → check CIDR inside VPC first → confirm → run → `ShowSubnet` to verify.
3. `huawei_update_vpc` / `huawei_update_subnet` → confirm changed fields → run → query to verify.
4. `huawei_delete_subnet` → verify no ports (`ListPorts/v3 --subnet_id`) → confirm → run → query to verify absence.
5. `huawei_delete_vpc` → verify no subnets (`ListSubnets --vpc_id`) → confirm → run → query to verify absence.

Every resource created during testing must be cleaned up afterwards (see Phase 6 of the
creation pipeline); the final report records created/modified/deleted resources.

## 6. Quality telemetry verification

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh
printf '{"session_id":"verify-vpc","trigger_type":"workflow"}' > /tmp/qcfg.json
SKILL_QUALITY_REPORT_VERBOSE=1 python3 scripts/cli/cli_entry.py --no-auto-upgrade \
  report --skill-name huawei-cloud-vpc-network-diagnosis-management --status success --json /tmp/qcfg.json 2>&1 | tail -1
# Expect: "[quality-report] OK trace_id=..."
```

If the endpoint is unreachable, the business flow still works — telemetry is best-effort.