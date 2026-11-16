# Verification Method

How to verify `huawei-cloud-computing-query`, from offline checks to live read-only queries.
All queries use the skill venv Python and the per-service entry scripts; this skill performs **no write
operations**, so every live check below is read-only.

## 1. Static verification (no credentials, no network)

Compile every entry script:

```bash
.venv/bin/python3 -m py_compile scripts/_common.py scripts/config.py scripts/ensure_env.py scripts/huawei_ecs.py scripts/huawei_bms.py scripts/huawei_ims.py scripts/huawei_as.py scripts/huawei_cce.py
```

Every subcommand must accept `-h` and exit 0 before any credential check:

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details -h
.venv/bin/python3 scripts/huawei_bms.py list_bare_metal_servers -h
.venv/bin/python3 scripts/huawei_ims.py list_images -h
.venv/bin/python3 scripts/huawei_as.py list_scaling_groups -h
.venv/bin/python3 scripts/huawei_cce.py list_clusters -h
```

List every subcommand of one service:

```bash
.venv/bin/python3 scripts/huawei_cce.py -h
```

Expected: exit code 0 and a readable help page on a host without AK/SK and without the SDK installed.

## 2. Platform-specific venv interpreter path (Windows regression check)

`scripts/ensure_env.py` selects the venv interpreter by platform:

| Platform | Expected interpreter |
|----------|----------------------|
| Windows (`os.name == "nt"`) | `.venv\Scripts\python.exe` |
| Linux / macOS (`posix`) | `.venv/bin/python3` |

Offline check (no venv, no credentials):

```bash
.venv/bin/python3 -c "import os,sys; sys.path.insert(0,'scripts'); import ensure_env; p=ensure_env._venv_python_path('.venv'); print(os.name, p); assert ('Scripts' in p and p.endswith('python.exe')) if os.name=='nt' else p.endswith('bin/python3')"
```

On Windows the printed path must contain `Scripts\python.exe`. If it contains `bin/python3`, the fix
has regressed: the interpreter was previously hard-coded to `bin/python3`, which made the whole
environment self-check fail on Windows with `FileNotFoundError`.

When the running interpreter must be switched to the venv one, the script starts it as a child
process and exits with the child's exit code instead of replacing its own process image, so callers
that wrap the script (for example `check_env.sh`) still see the real exit code.

## 3. Environment self-check

```bash
bash scripts/check_env.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_env.ps1
```

Expected: the script first checks `HW_ACCESS_KEY` / `HW_SECRET_KEY`, then Python, dependencies, SDK
and service availability. Missing credentials fail fast with exit code 2 and a readable hint. A
passing run writes `.env_check_cache`; a second run within 30 minutes prints `命中环境检查缓存` and
skips dependency and API checks. Force a full run with `--force` / `HW_ENV_CHECK_FORCE=1`.

Required environment variables: `HW_ACCESS_KEY`, `HW_SECRET_KEY`
(optional: `HW_REGION_NAME` default `cn-north-4`, `HW_PROJECT_ID`, `HW_SECURITY_TOKEN`).

## 4. Failure behaviour

| Situation | Expected result |
|-----------|-----------------|
| `-h` / `--help` with no credentials | exit 0, no traceback |
| Query with no `HW_ACCESS_KEY` / `HW_SECRET_KEY` | exit 2, `missing AK/SK` hint on stderr |
| SDK not installed | exit 3, `run scripts/check_env.sh first` hint |
| API or network error | exit 3, readable cause and suggestion |
| Required parameter missing | exit 2 with the parser's usage message |

Verify the credential path:

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details --region cn-north-4
```

## 5. Read-only live verification (needs valid credentials)

Start from a narrow query to avoid large result sets:

```bash
.venv/bin/python3 scripts/huawei_ecs.py list_servers_details --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_bms.py list_bare_metal_servers --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_ims.py list_images --region cn-north-4 --os_type Linux --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_as.py list_scaling_groups --region cn-north-4 --limit 20
```

```bash
.venv/bin/python3 scripts/huawei_cce.py list_clusters --region cn-north-4 --limit 20
```

Expected: a compact table plus `共 N 条，当前返回 M 条`. Cross-check one known resource against the
console (id / name / status must match). `--project_id` may be omitted; it is resolved once through IAM
and reused for the rest of the process.

## 6. Pagination and output trimming

- Default list output shows at most 20 rows and only the summary fields.
- `--all` walks every page and displays all rows.
- `--fields id,name,status` selects display columns without changing the query.
- `--json` prints the raw rows for downstream processing.

Verify full pagination on a cluster with more than one page of nodes:

```bash
.venv/bin/python3 scripts/huawei_cce.py list_nodes --region cn-north-4 --cluster_id "<cluster_id>" --all
```

## 7. Result interpretation

- Every count in the output must come from an API response (`count` / `total_count` / `total_number`),
  never be estimated.
- If a query returns nothing, report "no matching resources" together with the region and filters used
  instead of guessing.
- Do not treat a successful script exit as proof of correct data: cross-check at least one known
  resource against the console.
