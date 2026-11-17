# Acceptance Criteria: huawei-cloud-computing-query

**Scenario**: Huawei Cloud computing resource read-only query (ECS / BMS / IMS / AS / CCE)
**Purpose**: Skill test acceptance criteria

## 1. Scope Criteria

✅ Must hold:
- Only read-only query capabilities are exposed; no create/start/stop/reboot/delete/resize/rescale operations
- Write requests are refused and redirected to the owning skill or the Huawei Cloud console
- Every query targets exactly one region per call; no silent multi-region loops

❌ Must not happen:
- Calling write APIs or substituting KooCLI / `hcloud` / `curl` for a skill subcommand
- Fabricating subcommand names that are absent from the per-service guides (`references/ecs/guide.md`, `references/bms/guide.md`, `references/ims/guide.md`, `references/as/guide.md`, `references/cce/guide.md`)

## 2. Execution Criteria

✅ Correct:

```bash
bash scripts/check_env.sh
```

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_cce.py list_clusters --region cn-north-4 --detail true
```

```bash
.venv/bin/python3 scripts/huawei_ecs.py show_server --region cn-north-4 --server_id "<server_id>" --with_related
```

❌ Incorrect (documentation only, not executable in this skill):

| Incorrect form | Why it is rejected |
|----------------|--------------------|
| A KooCLI (`hcloud`) invocation | KooCLI is not an execution path for this skill; use the Python subcommands above |
| `huawei_ecs.py show_server --region cn-north-4` without `--server_id` | required parameter missing, exit 2 |
| `scripts/ecs/list_servers_details.py` | old per-operation path removed; use the subcommand |

- Documented examples uniformly use the `--region <region>` form; the equivalent `--region=<region>`
  form is also accepted by argparse. This is a writing convention only, not a rejected form
- Scripts run with the skill venv Python (see Execution Method), never with a system interpreter that
  lacks the SDK
- `--region` falls back to `HW_REGION_NAME` (default `cn-north-4`); `--project_id` auto-resolves via IAM
  once per process when omitted

## 3. Response Validation Criteria

✅ Must include:
- List output: a compact table plus `共 N 条，当前返回 M 条`
- Default list fields: `id`, `name`, `status` (service-specific summary fields when those exact keys are absent)
- ECS instance lists: `charging_mode` (`0`→按需, `1`→包周期, `2`→竞价; empty renders `-`), flavor summary
  and optional related-resource columns (`fixed_ips`, `floating_ips`, `security_groups`, `volumes`)
- CCE list rows: cluster/node/node pool `id`, `name`, `status`
- Zero-valued fields (for example disk `0`) render as `0`, not dropped or empty
- 401 / 403 / 404 / timeout / network errors map to actionable Chinese guidance rather than a raw traceback

## 4. Security Criteria

✅ Correct:
- Credentials come from `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN` / `HW_PROJECT_ID`
- Secret values are never echoed, logged, or embedded in output

❌ Incorrect:
- Hard-coded AK/SK in scripts, commands, or test cases
- Printing credential values or asking the user to paste AK/SK into the conversation

## 5. Related-Skills Guidance Criteria

✅ Must hold:
- Cross-category hints in runtime output use neutral wording and point to `SKILL.md` → Related Skills,
  without embedding other skill names in script output
- `SKILL.md` and `references/*.md` list the exact sibling skill names for ECS lifecycle, EVS/OBS storage,
  CCE metrics, CCE cluster management, RDS and VOD

## 6. References

- `SKILL.md` — capability scope, related skills, usage principles
- `references/ecs/guide.md`, `references/bms/guide.md`, `references/ims/guide.md`, `references/as/guide.md`, `references/cce/guide.md`
- `references/iam-policies.md` — required IAM read-only permissions
- `references/verification-method.md` — verification method
- `references/cli-installation-guide.md` — out-of-scope operations and KooCLI boundary
