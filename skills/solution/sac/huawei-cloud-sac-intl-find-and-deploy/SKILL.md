---
name: huawei-cloud-sac-intl-find-and-deploy
description: |
  1. Find and deploy any Huawei Cloud international SAC (Solution as Code) solution end-to-end via Terraform using a public catalog lookup.
  2. Find capability: search the live SAC catalog by business term or product name (concept-aware), present matching solutions first, then ALL regions for the picked solution.
  3. Deploy capability: after the user confirms solution, variant and region, collect temporary credentials (env vars, never in chat) and run the corresponding Terraform template through plan/apply/verify/destroy.
  4. Triggers include: SAC, 一键部署, 华为云, 解决方案实践, retrieve SAC catalog, deploy SAC solution, one-click solution deploy, 检索华为云部署方案, sac方案, 一键部署方案, 帮我部署xx sac方案, 部署Dify, 部署SQLBot, 部署YOLO, 模型网关方案, agent方案, 知识库方案.
  5. Usage: concept search → user picks solution+variant → list ALL regions → pick region → recap + confirm → credentials check → download template → normalize → confirm vars → plan/apply → verify → cleanup.
  6. Requires Python 3.8+, Terraform 1.5+, cloud credentials via env vars (never in chat).
tags: [huawei-cloud, sac, terraform, solution-as-code]
---

# SAC Intl Find and Deploy

## Overview

Two capabilities, one skill:

1. **Find** — the user describes a business outcome (e.g. 模型网关, agent方案, 知识库, Dify). The skill searches the live public catalog, shows matching **solution names first**, then lists **every region** for the picked solution. The solution count is whatever the catalog currently holds (never hardcode it — the script reports `total_solutions`).
2. **Deploy** — after the user explicitly confirms solution + variant + region, the skill checks credentials, downloads the template, and provisions resources via Terraform with confirmation gates.

**Architecture:** Per-solution ECS/VPC/Subnet/Security Group/EIP pattern defined by the downloaded `.tf/.tf.json` template. Provider sources normalized to `huaweicloud/huaweicloud` and `hashicorp/kubernetes`.

**Tool chain:** Python 3.8+ (helper scripts) + Terraform 1.5+ (declarative deployment). No KooCLI. The catalog is always fetched fresh from the public OBS `sac_intl.json` (3 retries, never falls back to stale local data). The script reports the catalog's `generated_at` timestamp — always relay it to the user.

**Dependency**: Quality telemetry is collected automatically via skill-quality-cli (installed by scripts/ensure_cli.sh if absent).

## Prerequisites

- Python 3.8+, Terraform 1.5+ — see [CLI Installation Guide](references/cli-installation-guide.md)
- Huawei Cloud temporary credentials (AK/SK/SecurityToken) via environment variables — see Credential Gate below
- IAM user with sufficient permissions — see [IAM Policies](references/iam-policies.md)
- **skill-quality-cli** — ensured by bash scripts/ensure_cli.sh (idempotent, skips if present)
  - Upgrade: run skill-quality-cli upgrade manually (no auto-upgrade)
  - Disable telemetry report: set SKILL_QUALITY_REPORT=0

### Security

- 🚫 Never expose AK/SK/Token in conversation or output
- 🚫 Never ask user to paste AK/SK/Token in chat; prefer env vars or manual tfvars edit
- 🚫 Never read or display `terraform.auto.tfvars.json` in conversation context (contains credentials)
- ✅ Only temporary credentials with SecurityToken, least privilege, shortest TTL
- ✅ Modification ops (`apply`, `destroy`) require explicit user confirmation

## Core Commands

> **⚠️ Mandatory: every hcloud command in this skill MUST be wrapped with `skill-quality-cli run --skill-name sac-intl-find-and-deploy-skill -- ` — bare hcloud calls are strictly forbidden.** (No hcloud commands in this skill; Terraform-only.)

Placeholder values (see Parameter Confirmation for per-OS resolution):

| Placeholder | Linux / macOS | Windows PowerShell |
| ----------- | ------------- | ------------------ |
| `<python>` | `python3` | `python` |
| `<script_dir>` | `./scripts` | `./scripts` |
| `<temp_dir>` | `/tmp` | `$env:TEMP` |
| `<workdir>` | `sac-workdir` | `sac-workdir` |

```bash
# 1a. Find (Stage A): concept search -> distinct solution+variant rows (NOT truncated)
<python> <script_dir>/query_catalog.py --keyword "<business term>" --group --out <temp_dir>/sac_solutions.json

# 1b. Find (Stage B): after user picks solution+variant -> list ALL regions for it
<python> <script_dir>/query_catalog.py --solution "<solution_name>" --variant "<variant>" --out <temp_dir>/sac_candidates.json

# 2. Download template
<python> <script_dir>/download_tf_template_file.py --url "<template_url>" --out-dir <temp_dir>/<workdir>

# 3. Normalize providers (reads HW_* env vars; writes terraform.auto.tfvars.json with 600)
<python> <script_dir>/normalize_tf_providers.py <temp_dir>/<workdir> --region "<console_region>"

# 4. List variables for review
<python> <script_dir>/list_tf_variables.py <temp_dir>/<workdir>

# 5. Deploy
terraform -chdir=<temp_dir>/<workdir> init
terraform -chdir=<temp_dir>/<workdir> plan
# ⛔ STOP — Review the plan output above. Do NOT auto-apply.
# Confirm with the user (AskUserQuestion or equivalent) before proceeding.
# Only after explicit user confirmation:
terraform -chdir=<temp_dir>/<workdir> apply

# 6. Verify
terraform -chdir=<temp_dir>/<workdir> state list
terraform -chdir=<temp_dir>/<workdir> output -json

# 7. Cleanup
terraform -chdir=<temp_dir>/<workdir> destroy
# Only after terraform destroy succeeds, remove local credential residue:
rm -f <temp_dir>/<workdir>/terraform.auto.tfvars.json <temp_dir>/<workdir>/*.tfstate <temp_dir>/<workdir>/*.tfstate.backup <temp_dir>/<workdir>/*.tfplan
```

## Workflow

### Part 1 — Find

#### 1. Collect input

Business term or desired outcome (e.g. 模型网关, agent方案, 知识库方案, Dify, SQLBot). Region only matters at step 3.

#### 2. Stage A — show matching solutions

Run Core Commands step 1a. The script does concept-aware matching (模型网关→New API+LiteLLM, 知识库→RAGFlow, agent→Hermes/Dify/OpenClaw/n8n…) over solution names, URLs **and `solution_describe` text**, and prints distinct `solution | variant | N regions` rows with a describe snippet. If nothing matches it prints the FULL catalog — show that to the user.

**Freshness announcement (mandatory):** the script prints `catalog data as of: <generated_at>` on stderr and includes `catalog_generated_at` / `total_solutions` in its JSON output. When presenting results, always start with a line like:

> 以下是截至 {catalog_generated_at} 的最新 SAC 方案目录（共 {total_solutions} 个方案），供您选择。

If the fetch fails entirely, the script exits with an explicit error — tell the user the fetch failed and retry later; do NOT improvise with old output. Offline debug only: `--catalog <local json>` override, or `--insecure` / `--ca-bundle <pem>` when a self-signed cert / MITM proxy breaks TLS.

#### 3. Stage B — pick solution, then show ALL regions

Wait for the user to pick exactly one solution+variant. Then run Core Commands step 1b: it lists **every** region for that variant (no truncation, no hidden cuts). Present rows as `solution_name | variant | region_label (console_region)` with `template:` and `deploy:` lines. Wait for the user to explicitly pick one region. Never auto-pick. Mention the `deploy_link` supports console self-service without credentials.

### Part 2 — Deploy

Enter Part 2 only after the user has picked one solution + variant + region.

#### 4. Recap and confirm (deploy gate)

⛔ Before touching any infrastructure, restate the full selection and get explicit confirmation:

> 即将部署：
> - 方案：{solution_name}
> - 版本：{variant}
> - 区域：{region_label} ({console_region})
> - 模板：{template_url}
>
> 确认开始部署吗？

Proceed only after the user says yes. If anything is off, go back to Part 1.

#### 5. Credential gate

Check whether the three environment variables are set — **existence only, never read or print the values**:

```bash
[ -n "$HW_ACCESS_KEY" ] && [ -n "$HW_SECRET_KEY" ] && [ -n "$HW_SECURITY_TOKEN" ] && echo CREDENTIALS_SET || echo CREDENTIALS_MISSING
```

If `CREDENTIALS_MISSING`, tell the user plainly how to configure them — the user runs these **in their own terminal environment**, never pastes values into the chat:

**Linux / macOS（用户在自己的终端里执行）:**

```bash
export HW_ACCESS_KEY="替换成你的AK"
export HW_SECRET_KEY="替换成你的SK"
export HW_SECURITY_TOKEN="替换成你的STS临时Token"
```

**Windows PowerShell（用户在自己的终端里执行）:**

```powershell
$env:HW_ACCESS_KEY = "替换成你的AK"
$env:HW_SECRET_KEY = "替换成你的SK"
$env:HW_SECURITY_TOKEN = "替换成你的STS临时Token"
```

并提醒：AK/SK/Token 属于敏感凭据，⚠️ 不要粘贴到对话中；建议使用最小权限的临时凭据（含 SecurityToken），用完即失效。

If the agent's shell session cannot see the user's env vars (or the user prefers files), fall back to manual edit: after running Core Commands step 3, tell the user to open `<temp_dir>/<workdir>/terraform.auto.tfvars.json` in an editor and fill in `access_key` / `secret_key` / `security_token` themselves. ⛔ The skill must never read or display that file — only confirm with the user whether it has been filled.

Block `plan`/`apply` until the user confirms credentials are in place.

#### 6. Download and normalize template

Run Core Commands steps 2–3. `normalize_tf_providers.py` unifies provider sources and writes `<workdir>/terraform.auto.tfvars.json` (`600`, `sensitive=true`). If env vars were absent at this point, the credential fields stay empty — apply the fallback from step 5.

#### 7. Confirm variables

Run Core Commands step 4. User must confirm login passwords, flavors, billing, and region variables. Sensitive names (key/secret/password/token) display as `********` only. Block `apply` on empty/weak secrets.

#### 8. Deploy, verify, cleanup

⛔ **STOP** — review `terraform plan`, confirm with user, then `apply`. Verify per [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md). On cleanup, `destroy` first, then delete tfvars/state/plan residue and confirm.

## Parameter Confirmation

| Parameter | Required | Default | Constraint |
| --------- | -------- | ------- | ---------- |
| `keyword` (stage A) | Yes* | — | Business term or name; concept expansion applies (模型网关/agent方案/知识库方案…) |
| `group` (stage A) | Yes* | — | Stage A always uses `--group`; lists solution+variant rows |
| `solution` (stage B) | Yes* | — | Exact solution name picked from stage A |
| `variant` (stage B) | Yes* | — | Variant picked from stage A, e.g. 单机版部署 |
| `limit` (stage B) | No | `500` | Safety cap; catalog never reaches this — ALL regions listed |
| `region-filter` (stage B) | No | `""` | Only if the user names a region up front; otherwise list all |
| `console_region` | Yes | — | Taken from picked region row, e.g. `ap-southeast-1` |
| `template_url` | Yes | — | Taken from picked row; must end `.tf` / `.tf.json` |
| `access_key` | Yes | `<NO_DEFAULT>` | From env `HW_ACCESS_KEY`; never print in chat |
| `secret_key` | Yes | `<NO_DEFAULT>` | From env `HW_SECRET_KEY`; never print in chat |
| `security_token` | Yes | `<NO_DEFAULT>` | From env `HW_SECURITY_TOKEN`; missing token aborts normalize |

\* Exactly one of `keyword`+`group` (stage A) or `solution`+`variant` (stage B) is required per invocation.

## Post-Deploy Output

- `terraform output -json` — includes per-template outputs (EIPs, URLs, access instructions)
- Service URL pattern: `http://<EIP>[:port]` after cloud-init settles (~10 min)

## Output Format

All script outputs are JSON-compatible: `query_catalog.py` stage A writes `{keyword, mode: "group", no_match, count, total_solutions, catalog_generated_at, candidates[]}` (each with `region_count` and `solution_describe`), stage B writes `{keyword, mode: "regions", no_match, count, total_solutions, catalog_generated_at, candidates[]}` (each with full `template_url`/`deploy_link`); `list_tf_variables.py` prints `name=default` lines with sensitive masking.

## Verification

1. **Concept search** — stage A returns solution+variant rows for business terms (模型网关→New API+LiteLLM etc., 微服务→Nacos, 语音转写→VibeVoice via describe); no-match prints full catalog with `no_match: true`
2. **Freshness announcement** — stage results carry `catalog_generated_at` / `total_solutions` and the agent announces "以下是截至 … 的最新 SAC 方案目录" before asking the user to pick
3. **Region completeness** — stage B returns ALL regions for the picked variant and the row count matches the `region_count` reported in stage A for that solution+variant; never truncate
4. **Recap gate** — before deploy, the agent restated solution/variant/region/template_url and got explicit confirmation
5. **Credential gate** — env presence checked without printing values; user either exported env vars or manually edited tfvars; skill never read/displayed credentials
6. **Template download** — `.tf/.tf.json` exists under workdir and `terraform validate` passes
7. **Variable confirmation** — secrets non-empty, user confirmed overrides
8. **Deployment** — `plan` clean, user confirmed, `state list` shows expected resources after `apply`
9. **Service reachability** — per-template access URL responds after cloud-init

See [Verification Method](references/verification-method.md) and [Acceptance Criteria](references/acceptance-criteria.md).

## Best Practices

- Always `plan` before `apply`; never auto-apply
- Prefer env vars over pasted credentials; shortest TTL and least privilege
- Keep one workdir per deployment; do not reuse across regions
- Allow ~10 min post-deploy for cloud-init before curl/ssh checks

## Reference Documents

| Document | Description |
| -------- | ----------- |
| [CLI Installation Guide](references/cli-installation-guide.md) | Install Python, Terraform, skill-quality-cli |
| [IAM Policies](references/iam-policies.md) | Permissions and least-privilege guidance |
| [Verification Method](references/verification-method.md) | Step-by-step verification per workflow step |
| [Acceptance Criteria](references/acceptance-criteria.md) | Full deployment acceptance checklist |
| [Related Commands](references/related-commands.md) | Scripts and Terraform quick reference |
| [Dataflow Diagram](references/dataflow-diagram.md) | Mermaid data flow |

## Notes

- The solution catalog size is dynamic — never hardcode a count; use `total_solutions` from script output
- `<workdir>/terraform.auto.tfvars.json` is sensitive — never commit to VCS; never read in context
- `normalize_tf_providers.py` enforces temporary credentials (missing token aborts)
- Tool chain: Python + Terraform only — no KooCLI
