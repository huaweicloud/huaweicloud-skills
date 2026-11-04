# Verification Method 验证方法

## Specification Compliance Verification 规范合规验证

### Structure Validation 结构验证

```bash
# Verify skill directory structure
ls -la skills/cloudrobo-dataset/
ls -la skills/cloudrobo-dataset/references/
ls -la skills/cloudrobo-dataset/scripts/
ls -la skills/cloudrobo-dataset/templates/
```

### Frontmatter Validation Frontmatter验证

```bash
# Check frontmatter exists
grep '^---$' skills/cloudrobo-dataset/SKILL.md | head -2

# Check name field
grep '^name:' skills/cloudrobo-dataset/SKILL.md

# Check description field with triggers
grep 'Triggers include:' skills/cloudrobo-dataset/SKILL.md

# Check tags field
grep '^tags:' skills/cloudrobo-dataset/SKILL.md
```

### Section Validation 章节验证

```bash
# Required sections (bilingual headers)
grep '##.*概述' skills/cloudrobo-dataset/SKILL.md
grep '##.*前置条件' skills/cloudrobo-dataset/SKILL.md
grep '##.*工作流' skills/cloudrobo-dataset/SKILL.md
grep '##.*核心命令' skills/cloudrobo-dataset/SKILL.md
grep '##.*参数确认' skills/cloudrobo-dataset/SKILL.md
grep '##.*参考文档' skills/cloudrobo-dataset/SKILL.md
```

### File Size Constraint 文件大小约束

```bash
# Total skill directory size must not exceed 40 MB
du -sh skills/cloudrobo-dataset/
```

### File Count Constraint 文件数量约束

```bash
# Total files must not exceed 30
find skills/cloudrobo-dataset/ -type f | wc -l
```

## Functional Testing 功能测试

### CLI Testing CLI测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-dataset/scripts/test-cli-commands.sh -s skills/ai/cloudrobo/huawei-cloud-cloudrobo-dataset -e cli
```

### SDK Testing SDK测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-dataset/scripts/test-cli-commands.sh -s skills/ai/cloudrobo/huawei-cloud-cloudrobo-dataset -e sdk
```

### API Testing API测试

API-level verification is manual — replay the API paths in
[Task Config Reference](task-config-catalog.md) in
[API Explorer](https://console.huaweicloud.com/apiexplorer/) against a live environment;
the test script automates only the CLI and SDK executors.

## Test Case List 测试用例列表

See `templates/test-vars.json` for the full test case list.

## Verification Flow 验证流程

```
Each test case → Try CLI execution
  ├── ✅ Success → Record PASS
  └── ❌ Failure → Check syntax issues
       ├── ✅ Syntax issue → Fix and retry
       └── ❌ Non-syntax issue → Fallback to SDK
            ├── ✅ Success → Record PASS (SDK)
            └── ❌ Failure → Fallback to API
                 ├── ✅ Success → Record PASS (API)
                 └── ❌ Failure → Record FAIL ⛔ requires manual verification
```

## Six-Phase Completeness Check 六阶段完整性检查

```
Check phase-1-summary.json exists → If missing, resume from Phase 1
Check phase-2-summary.json exists → If missing, resume from Phase 2
Check phase-3-summary.json exists → If missing, resume from Phase 3
Check phase-4-summary.json exists → If missing, resume from Phase 4
Check phase-5-summary.json exists → If missing, resume from Phase 5
Check phase-6-summary.json exists → If missing, resume from Phase 6
```

All phases complete → Creation done. Missing phases → Resume from the missing phase.

## Custom Operator Onboarding Verification 自定义算子入驻验证

The following applies to the custom-operator onboarding pipeline (SKILL.md §Custom
Operator Onboarding). It replaces the need for a separate sub-skill verification.

### Functional Testing 功能测试

```bash
bash scripts/test-cli-commands.sh -s . -e cli
bash scripts/test-cli-commands.sh -s . -e sdk
```

- Requires `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` environment variables.
- Read-only test cases (dry-run, failure analysis) run automatically.
- **Mutation test cases (onboard) require explicit user confirmation** — they create
  real assets and push images to SWR.

### API-Level Verification API级验证

Manual verification via the `cloudrobo asset` CLI (equivalent API paths in
`dataflow-diagram.md` §API Path Summary — cloudrobo-asset-manager):

1. `cloudrobo asset create-asset --type image` — image asset registration (first submission)
2. `cloudrobo asset create-asset --type algorithm` — algorithm asset creation (first submission)
3. `cloudrobo asset create-version --asset-id <image-id> --url <url>` — image version (re-submission)
4. `cloudrobo asset update-asset --asset-id <algo-id> --ext-metadata <...>` — algorithm image update (re-submission)
5. `cloudrobo asset show-asset --asset-id <id>` — verify status DRAFT/available

### Post-Onboarding Verification Checklist 上架后验证清单

- [ ] Mode A: `image_asset_id` is non-empty; `algorithm_asset_id` is non-empty
- [ ] `GET /v1/assets/{algorithm_asset_id}` returns `status=available`
- [ ] Mode A: `engine.image_url` in algorithm asset matches the SWR URL from Phase 2
- [ ] Mode A SWR login: auto-generated from AK/SK; on auto-credential/login failure the cause was classified (AK/SK invalid/expired, SWR not enabled / IAM permission missing, region mismatch, network) and fixed before retry; `Login Succeeded` verified before build/push
- [ ] Mode B 空间资产-算法: `engine.image_source` = `custom` + `engine.asset_id` = image asset id + `engine.asset_version_id` = image asset version id (**linked to 空间资产-镜像**) and `code_dir` = customer OBS path (under workspace `default_obs_path`) — 空间资产-算法 only
- [ ] Mode B task-creation way chosen (空间资产-算法 use created algorithm / OBS算法 mount OBS code directly); 空间资产-算法 proc-task `task_config.algo_type=WORKSPACE_ASSETS` with `algo_id` = Phase 3 algorithm `asset_id` + `algo_path` (= asset `code_dir`) + `job_local_path` + absolute `algo_entrance`, OBS算法 `algo_type=OBS_ASSETS` without `algo_id` **and skips Phase 3 asset registration (no `create-asset` calls)**
- [ ] `tags` includes `"Data Processing"`（not `sub_type` — see API constraint）
- [ ] Phase 4 dataset source asked first (① 空间资产-数据-新建 / ② 空间资产-数据-复用 / ③ OBS存储); **Source ③ OBS存储 `obs_path` bucket equals the workspace-bound bucket (`default_obs_path` from `cloudrobo workspace current`) — foreign-bucket paths were rejected & re-asked**
- [ ] Phase 4 proc-task reached `SUCCEEDED`; user log shows `[DONE] Processed N items, success N, failed 0` (legacy Chinese form also OK); output frames non-empty
- [ ] User's original source directory is unmodified (`git status` or `diff`)
- [ ] Work copy exists at `/tmp/custom-operator-work-{timestamp}/` with `entrypoint.py` (contains `os.environ.get("SOURCE_DATASET_PATH")`); Mode A also `Dockerfile` with `COPY requirements.txt` before `COPY ./src`
- [ ] On success: `/tmp/custom-operator-work-*` removed (auto-clean); on failure: retained for `--reuse-workdir`
- [ ] Failure analysis returns JSON with `priority`, `cause`, `fix`, `matched_line`; P0 (ModuleNotFoundError/docker build ERROR), P1 (FileNotFoundError SOURCE_DATASET_PATH), P2 (TypeError/KeyError), unmatched → P3 "contact support"

### Failure Analysis 失败分析验证

Failure analysis patterns (P0/P1/P2/P3) and the log-truncation rule (first 64KB) are
documented in `custom-operator/custom-operator-workflow.md`; the error pattern matrix there is the single
source of truth for diagnosing failed custom-operator proc-tasks.
