# Acceptance Criteria: huawei-cloud-computing-query

**Scenario**: Huawei Cloud computing resource read-only query (ECS / BMS / IMS / AS / CCE)
**Purpose**: Skill test acceptance criteria

## 1. Scope Criteria

✅ Must hold:
- Only read-only query capabilities are exposed; no create/start/stop/reboot/delete/resize/rescale operations
- Write requests are refused and redirected to the owning skill or the Huawei Cloud console
- Every query targets exactly one region per call; no silent multi-region loops

❌ Must not happen:
- Calling write APIs or KooCLI/hcloud/curl as a substitute for the skill scripts
- Fabricating script names that are absent from `references/<service>/guide.md`

## 2. Execution Criteria

✅ Correct:
```bash
bash scripts/check_env.sh                 # once per session, cached 30 minutes
python3 scripts/ecs/list_servers_details.py --region=cn-north-4
python3 scripts/cce/list_clusters.py --region=cn-north-4 --detail true
python3 scripts/ecs/show_server.py --region=cn-north-4 --server_id=<id> --with_related
```

❌ Incorrect:
```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4             # prohibited fallback in this skill
python3 scripts/ecs/show_server.py --region=cn-north-4              # rc=2: --server_id is required
```

- Documented examples uniformly use the `--region=<region>` form; the equivalent `--region <region>` form is also accepted by argparse. This is a writing convention only, not a rejected or failing form
- Scripts are executed with the skill venv Python (see Execution Method), never with a system interpreter that lacks the SDK
- `--region` falls back to `HW_REGION_NAME` (default `cn-north-4`); `--project_id` auto-resolves via IAM when omitted

## 3. Response Validation Criteria

✅ Must include:
- CLI output layer (what the scripts print): a human-readable table plus a summary line in the form `共 N 条 ECS，当前返回 M 条`; columns as listed in the ECS bullet below
- API response layer (what the underlying list APIs return): `count` plus the list of items (ECS; some services expose `total_count` instead), each carrying id/name/status where the API provides them — these fields belong to the API response and are not promised as literal keys in the CLI text output
- ECS lists: `charging_mode` (`0`→按需, `1`→包周期, `2`→竞价; empty renders `-`), `flavor_id` / `flavor_name` / `vcpus` / `memory(GiB)` / `disk` / `gpus`
- ECS `--with_related`: `fixed_ips`, `floating_ips`, `security_groups`, `volumes` (single-server view printed as a `关联资源` section)
- CCE `list_nodes.py --all`: auto-paginated, `--verify` cross-checks against node-pool `current_node`
- Zero-valued fields (for example disk `0`) are rendered as `0`, not dropped or rendered as empty
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
- Cross-category hints in runtime output use neutral wording and point to `SKILL.md` → Related Skills, without embedding other skill names in script output
- `SKILL.md` and `references/*.md` list the exact sibling skill names for ECS lifecycle, EVS/OBS storage, CCE metrics, CCE cluster management, RDS and VOD

## 6. References

- `SKILL.md` — capability scope, related skills, usage principles
- `references/ecs/guide.md`, `references/bms/guide.md`, `references/ims/guide.md`, `references/as/guide.md`, `references/cce/guide.md`
- `references/iam-policies.md` — required IAM read-only permissions
- `references/verification-method.md` — verification method