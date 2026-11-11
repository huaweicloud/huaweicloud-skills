# Verification Method

How to verify that `huawei-cloud-computing-query` works, from offline checks to live read-only queries.
All queries go through the local Python SDK scripts under `scripts/<service>/`; this skill performs **no write operations**,
so every live check below is read-only.

## 1. Static verification (no credentials, no network)

Compile every script in the skill:

```bash
python3 -m py_compile \
  scripts/config.py scripts/ensure_env.py \
  scripts/ecs/*.py scripts/bms/*.py scripts/ims/*.py scripts/as/*.py scripts/cce/*.py
```

Every script must accept `-h` and exit 0:

```bash
python3 scripts/ecs/list_cloud_servers.py -h
python3 scripts/ecs/list_servers_details.py -h
python3 scripts/bms/list_bare_metal_servers.py -h
python3 scripts/ims/list_images.py -h
python3 scripts/as/list_scaling_groups.py -h
python3 scripts/cce/list_clusters.py -h
python3 scripts/cce/show_node_pool.py -h
python3 scripts/cce/show_cluster_tags.py -h
python3 scripts/cce/list_node_pools_by_tag.py -h
```

> Note: `scripts/as/*.py` imports `huaweicloudsdkas` and `scripts/bms/*.py` imports `huaweicloudsdkbms`
> at module level. If those SDKs are not installed yet, `-h` fails with `ModuleNotFoundError` —
> run the environment check (section 3) first. This is pre-existing behaviour shared by all scripts
> in the same directory.

## 2. Platform-specific venv interpreter path (Windows regression check)

`scripts/ensure_env.py` must select the venv interpreter **by platform**:

| Platform | Expected interpreter |
|----------|----------------------|
| Windows (`os.name == "nt"`) | `.venv\Scripts\python.exe` |
| Linux / macOS (`posix`) | `.venv/bin/python3` |

Offline check (no venv, no credentials):

```bash
python3 -c "import os,sys; sys.path.insert(0,'scripts'); import ensure_env; \
p=ensure_env._venv_python_path('.venv'); print(os.name, p); \
assert ('Scripts' in p and p.endswith('python.exe')) if os.name=='nt' else p.endswith('bin/python3')"
```

On Windows the printed path must contain `Scripts\python.exe`. If it contains `bin/python3`, the fix
has regressed: the interpreter was previously hard-coded to `bin/python3`, which made the whole
environment self-check fail on Windows with `FileNotFoundError` and sent users to fix a non-existent path.

Also confirm the manual fallback hint is platform-aware: temporarily force the venv to be absent
(e.g. rename `.venv`) and re-run the environment check — the printed hint must be
`python -m venv .venv && .venv\Scripts\activate` on Windows and
`python3 -m venv .venv && source .venv/bin/activate` on Linux / macOS.

## 3. Environment self-check

```bash
# Linux / macOS
bash scripts/check_env.sh

# Windows
powershell -ExecutionPolicy Bypass -File scripts/check_env.ps1
```

Expected: Python version check → dependency install → SDK import check → credential check →
service availability check, all `OK`. The first passing run writes `.env_check_cache`; a second run
within 30 minutes must print `命中环境检查缓存` and skip dependency/API checks (no network calls).
Force a full run with `--force` / `HW_ENV_CHECK_FORCE=1`, disable the cache with `--ttl 0`.
The SDK check must cover `huaweicloudsdkcore / ecs / iam / ims / as / bms / cce`
(see `SDK_MODULES` in `scripts/ensure_env.py` and `requirements.txt`).

Required environment variables: `HW_ACCESS_KEY`, `HW_SECRET_KEY`
(optional: `HW_REGION_NAME` default `cn-north-4`, `HW_PROJECT_ID`, `HW_SECURITY_TOKEN`).
`--region` is optional for every script and falls back to `HW_REGION_NAME` — verify one script with
`--region` omitted behaves identically to an explicit region.

## 4. Read-only live verification (needs valid credentials)

Start from a narrow query (`--limit` / filters) to avoid large result sets:

```bash
# Existing services
python3 scripts/ecs/list_cloud_servers.py --region cn-north-4
python3 scripts/bms/list_bare_metal_servers.py --region cn-north-4
python3 scripts/ims/list_images.py --region cn-north-4
python3 scripts/as/list_scaling_groups.py --region cn-north-4

# CCE (added for cluster/node inventory)
python3 scripts/cce/list_clusters.py --region cn-north-4
python3 scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster-id>
python3 scripts/cce/list_node_pools.py --region cn-north-4 --cluster_id <cluster-id>
python3 scripts/cce/show_quota.py --region cn-north-4

# CCE node full pagination / tags / node pool details
python3 scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster-id> --all --verify
python3 scripts/cce/list_node_pools.py --region cn-north-4 --cluster_id <cluster-id> --show_default_node_pool true
python3 scripts/cce/show_node_pool.py --region cn-north-4 --cluster_id <cluster-id> --nodepool_id <nodepool-id>
python3 scripts/cce/show_cluster_tags.py --region cn-north-4 --cluster_id <cluster-id>
python3 scripts/cce/list_node_pools_by_tag.py --region cn-north-4 --cluster_id <cluster-id> --tag env=prod

# ECS flavor details / whole-machine related view
python3 scripts/ecs/list_servers_details.py --region cn-north-4 --with_related
python3 scripts/ecs/show_server.py --region cn-north-4 --server_id <server-id> --with_related
```

Expected: a tab-separated table plus a summary line. Cross-check one known resource against the console
(id / name / status must match). `--project_id` may be omitted; it is resolved via the IAM API.

## 5. Feature-specific checks

### 5.1 AS tag-based resource instances (`scripts/as/list_resource_instances.py`)

Previously this script sent an empty request body and always failed with
`400 / AS.0002 Request body is null`. Verify the body is now built:

```bash
# With a real tag
python3 scripts/as/list_resource_instances.py --resource_type SCALING_GROUP_TAG \
  --region cn-north-4 --tag env=prod

# Filter variants and count
python3 scripts/as/list_resource_instances.py --resource_type SCALING_GROUP_TAG \
  --region cn-north-4 --tag_any env=prod,env=test --not_tag tmp=1 --match resource_name=web
python3 scripts/as/list_resource_instances.py --resource_type SCALING_GROUP_TAG \
  --region cn-north-4 --tag env=prod --count
```

Expected: a `resource_id / resource_name / resource_detail` table with `total_count`
(no `AS.0002`), and `1` row of `total_count` for the `--count` variant.
Malformed values (`--tag env` is allowed as *any value*; `--match web` is not) and
`--count` combined with `--limit/--offset/--marker` must fail fast with a Chinese error message.

### 5.2 ECS tag filtering and export (`scripts/ecs/list_cloud_servers.py`, `list_servers_details.py`)

```bash
# Tag filter (repeatable, AND logic) — maps to the ECS API `tags` parameter
python3 scripts/ecs/list_cloud_servers.py --region cn-north-4 --tag env=prod --tag group=web
python3 scripts/ecs/list_cloud_servers.py --region cn-north-4 --not_tag env=test

# Export the same query result
python3 scripts/ecs/list_cloud_servers.py --region cn-north-4 --tag env=prod \
  --export csv --export_path ./servers.csv
python3 scripts/ecs/list_servers_details.py --region cn-north-4 --export json
```

Expected:
- the returned rows match the tag filter;
- the export prints `已导出 N 条到 <file> (格式: ...)`, CSV opens correctly in Excel
  (UTF-8 with BOM), and the default file name is `<script>_<YYYYmmdd_HHMMSS>.<ext>`;
- `--tag` together with the legacy `--tags` fails fast instead of silently dropping a filter;
- an empty result set creates no file.

### 5.3 Pagination limits

Read the "分页上限与翻页语义" section of `references/ecs/guide.md`. Verify that a query without
`--sort_by` returns at most `PAGE_SIZE` (50) rows and that the summary line prints the
`--marker` value for the next page; `--sort_by` fetches up to `API_LIMIT` (1000) per request.

## 6. Result interpretation

- Every count in the output must come from an API response (`total_count` / `count`), never be estimated.
- If a query returns nothing, report "no matching resources" together with the region and filters used
  instead of guessing.
- Do not treat a successful script exit as proof of correct data: cross-check at least one known
  resource against the console.
