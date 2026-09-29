# Acceptance Criteria — huawei-cloud-vpc-network-diagnosis-management

## 1. Skill registration (GitCode Skill spec)

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-01 | SKILL.md exists with YAML frontmatter | `grep '^---$' SKILL.md` |
| AC-02 | Frontmatter `name` == directory name `huawei-cloud-vpc-network-diagnosis-management` | read frontmatter |
| AC-03 | Frontmatter `description` includes feature summary + trigger words (中英文触发词) | read frontmatter |
| AC-04 | No `version` field in frontmatter | read frontmatter |
| AC-05 | ≤ 5 tags | read frontmatter |
| AC-06 | SKILL.md ≤ 500 lines | `wc -l SKILL.md` |
| AC-07 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents | grep each heading |
| AC-08 | references/ files use lowercase kebab-case names | `ls references/` |
| AC-09 | references/iam-policies.md exists (Critical) | file existence |
| AC-10 | references/cli-installation-guide.md exists (required with CLI) | file existence |
| AC-11 | All files use allowed extensions (46-type allowlist) | validate-skill.sh |
| AC-12 | No credential hardcoding (AK/SK, passwords) | gitleaks |

## 2. 14 huawei_* actions register and route

All 14 actions are documented in SKILL.md with command templates and parameter tables:

| # | Action | Capability | Risk | hcloud command |
|---|--------|-----------|------|----------------|
| AC-13 | `huawei_list_vpcs` | Query | R3 | `ListVpcs/v3` |
| AC-14 | `huawei_list_subnets` | Query | R3 | `ListSubnets` |
| AC-15 | `huawei_get_vpc` | Query | R3 | `ShowVpc/v3` |
| AC-16 | `huawei_get_subnet` | Query | R3 | `ShowSubnet` |
| AC-17 | `huawei_list_route_tables` | Query | R3 | `ListRouteTables` |
| AC-18 | `huawei_diagnose_network_connectivity` | Diagnose | R3 | composition (VPC/Subnet/RouteTable) |
| AC-19 | `huawei_diagnose_port_connectivity` | Diagnose | R3 | composition (Port/SecurityGroup) |
| AC-20 | `huawei_analyze_subnet_cidr_conflict` | Diagnose | R3 | composition (VPC/Subnet CIDRs) |
| AC-21 | `huawei_create_vpc` | Manage | R2 | `CreateVpc` |
| AC-22 | `huawei_create_subnet` | Manage | R2 | `CreateSubnet` |
| AC-23 | `huawei_update_vpc` | Manage | R2 | `UpdateVpc` |
| AC-24 | `huawei_update_subnet` | Manage | R2 | `UpdateSubnet` |
| AC-25 | `huawei_delete_vpc` | Manage | R1 | `DeleteVpc` (pre-check empty) |
| AC-26 | `huawei_delete_subnet` | Manage | R1 | `DeleteSubnet` (pre-check empty) |

Verification: every operation listed in SKILL.md Core Commands resolves to a real
`hcloud VPC <Operation>` that exists in `hcloud VPC --help`, with parameter names verified
against `hcloud VPC <Operation> --help` output.

## 3. CLI dependency declared correctly

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-27 | hcloud CLI declared in Prerequisites with version guidance | grep SKILL.md |
| AC-28 | `--cli-region` present in every concrete CLI command | grep SKILL.md |
| AC-29 | Every CLI command includes all REQUIRED parameters from `--help` | per-operation check |
| AC-30 | Service name `VPC` matches KooCLI metadata (`~/.hcloud/metaOrigin/template/vpc`) | `hcloud VPC --help` |
| AC-31 | Both auth modes (AK/SK env + local profile) documented | references/cli-installation-guide.md |

## 4. Risk-level behavior

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-32 | Query/Diagnose (R3) marked auto-execute | SKILL.md capability table |
| AC-33 | Manage R2 actions marked preview + explicit confirmation | SKILL.md `[W]` markers + confirmation gates |
| AC-34 | Manage R1 delete actions include pre-checks (empty VPC/subnet) + irreversible warning + explicit confirmation | SKILL.md delete sections |
| AC-35 | No write command runs without confirmation text | grep SKILL.md confirmation gates |

## 5. Diagnosis correctness

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-36 | Network connectivity diagnosis covers: subnet-in-VPC, CIDR overlap, default route, association, gateway | references/verification-method.md §4 |
| AC-37 | Port connectivity diagnosis covers: existence, status, admin state, device owner, SG rules | references/verification-method.md §4 |
| AC-38 | CIDR conflict analysis handles overlap/containment/adjacency | synthetic test cases in verification-method.md §4 |

## 6. Delivery requirements

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-39 | One PR changes only this skill directory | git diff --name-only |
| AC-40 | scripts/skill_quality_sdk.py or scripts/cli/ vendored quality reporting present | file existence |
| AC-41 | validate-skill.sh passes with FAIL: 0 (after __pycache__ cleanup) | script output |
| AC-42 | Security audit (skillcheck / markdownlint / hwcloud-spec / gitleaks) has no ERROR/CRITICAL | audit report |
| AC-43 | Phase 1-6 summaries exist before cleanup (pipeline completeness) | creator pipeline check |