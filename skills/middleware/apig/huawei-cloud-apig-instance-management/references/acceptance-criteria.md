# Acceptance Criteria

The huawei-cloud-apig-instance-management skill is accepted when all of the following hold:

## A. Structural (GitCode Skill 注册规范)

- [ ] `SKILL.md` exists with YAML frontmatter (`name: huawei-cloud-apig-instance-management`, `description` including trigger words, `tags` ≤ 5, no `version` field)
- [ ] Directory is `skills/{category}/{subcategory}/huawei-cloud-apig-instance-management/` and frontmatter `name` matches the directory name
- [ ] `references/iam-policies.md` and `references/cli-installation-guide.md` exist (CLI-based skill)
- [ ] `references/verification-method.md`, `references/dataflow-diagram.md`, `references/acceptance-criteria.md` present
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; extensions in the allowlist
- [ ] No hardcoded credentials anywhere in the skill

## B. Repo rules

- [ ] PR changes only the `huawei-cloud-apig-instance-management` skill directory (one skill per PR)
- [ ] No named cross-skill references (no calls to other skill directories)
- [ ] Commit message contains `Fixes #738`

## C. Functional coverage (17 `huawei_*` actions)

- [ ] Query R3 (5): list instances / get instance / list API groups / list APIs / list throttling policies — all read-only, executable automatically
- [ ] Analyze R3 (2): public access (`eip_address` vs `sl_domain`), publish chain analysis — read-only
- [ ] Manage R2 (7): create instance (async poll to Running), add ingress EIP,
      create API group, create API, update API, publish API (`--apis.1`),
      create throttling policy — preview + confirmation before execution
- [ ] Manage R1 (3): delete instance, delete API (must precede group deletion — see below), delete API group — all preview + explicit confirmation

## D. Correctness of CLI operations

- [ ] Every operation name matches `hcloud APIG --help` enumeration — verified names:
      `ListInstancesV2`, `CreateInstanceV2`, `DeleteInstancesV2`, `AddIngressEipV2`,
      `CreateApiGroupV2`, `ListApiGroupsV2`, `DeleteApiGroupV2`, `CreateApiV2`,
      `UpdateApiV2`, `ListApisV2`, `BatchPublishOrOfflineApiV2`,
      `CreateRequestThrottlingPolicyV2`, `ListRequestThrottlingPolicyV2`
      (throttling uses `RequestThrottlingPolicyV2` naming, NOT `ThrottlingPolicyV2`)
- [ ] Required parameters present for each operation (verified against `--help`, KooCLI 7.2.12)
- [ ] Every concrete command includes `--cli-region`

## E. Safety

- [ ] 9 Critical Warnings documented (region lock, per-API throttle default, CORS explicit,
      BASIC no public IP, 5-15 min async creation, sl_domain from group & internal-only,
      API name no hyphens, VPC param prefix, AddIngressEipV2 elb-only)
- [ ] Write/delete actions are not executed without user confirmation
- [ ] AK/SK read from environment or local profile; never hardcoded

## F. Verification evidence

- [ ] At least the read-only commands executed against a real authenticated KooCLI and returned valid JSON (or a documented empty result)
- [ ] Mutating commands validated via `--help` parameter checks (execution requires a live environment + user confirmation)

## G. Quality reporting (CLI)

- [ ] `scripts/ensure_cli.sh` exists and is executable (idempotent `skill-quality-cli` installer).
- [ ] `scripts/cli/cli_entry.py` + `scripts/cli/cli_reporting.py` are bundled (zero-dependency in-skill carrier).
- [ ] `SKILL.md` contains the "Quality Reporting (Unified CLI)" section with Mode 1 (`run` wrap) / Mode 2 (`report`) and the mandatory
      `skill-quality-cli run` wrapping rule for hcloud commands.
- [ ] Every executable `hcloud` command in `SKILL.md` is wrapped with
      `skill-quality-cli run --skill-name huawei-cloud-apig-instance-management -- ...`
      (including the async-polling loop and the environment-ID discovery step).
- [ ] E2E verified: `python3 scripts/cli/cli_entry.py --no-auto-upgrade report --skill-name huawei-cloud-apig-instance-management --status success --json <cfg>` returns `[quality-report] OK trace_id=...`.
- [ ] No `skill_quality_sdk` remnants in the skill directory (scripts, SKILL.md, references).