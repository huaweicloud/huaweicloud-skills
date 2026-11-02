# Verification Method 验证方法

## Specification Compliance Verification 规范合规验证

### Structure Validation 结构验证

```bash
# Verify skill directory structure
ls skills/security/config/huawei-cloud-config-helper/
ls skills/security/config/huawei-cloud-config-helper/references/
ls skills/security/config/huawei-cloud-config-helper/references/service/
ls skills/security/config/huawei-cloud-config-helper/scripts/
ls skills/security/config/huawei-cloud-config-helper/scripts/config/
```

### Frontmatter Validation Frontmatter验证

```bash
# Check frontmatter exists
grep '^---$' skills/security/config/huawei-cloud-config-helper/SKILL.md | head -2

# Check name field
grep '^name:' skills/security/config/huawei-cloud-config-helper/SKILL.md

# Check description field with triggers
grep 'Triggers include:' skills/security/config/huawei-cloud-config-helper/SKILL.md

# Check tags field
grep '^tags:' skills/security/config/huawei-cloud-config-helper/SKILL.md
```

### Section Validation 章节验证

```bash
# Required sections (bilingual headers)
grep '##.*概述' skills/security/config/huawei-cloud-config-helper/SKILL.md
grep '##.*前置条件' skills/security/config/huawei-cloud-config-helper/SKILL.md
grep '##.*工作流' skills/security/config/huawei-cloud-config-helper/SKILL.md
grep '##.*核心命令' skills/security/config/huawei-cloud-config-helper/SKILL.md
grep '##.*参数确认' skills/security/config/huawei-cloud-config-helper/SKILL.md
grep '##.*参考文档' skills/security/config/huawei-cloud-config-helper/SKILL.md
```

### File Size Constraint 文件大小约束

```bash
# Total skill directory size must not exceed 40 MB
du -sh skills/security/config/huawei-cloud-config-helper/
```

### File Count Constraint 文件数量约束

```bash
# Total files must not exceed 30
find skills/security/config/huawei-cloud-config-helper/ -type f | wc -l
```

## Functional Testing 功能测试

### Prerequisite 前置

```bash
# Environment variables must be set (never print their values)
pip install -r skills/security/config/huawei-cloud-config-helper/requirements.txt
```

### Test Cases 测试用例

| # | Case | Command (inside skill venv) | Expected |
|---|------|-----------------------------|----------|
| T-01 | Resource summary (all) | `python scripts/config/query_Config_resource_summary.py` | JSON array with `provider/type/region_id/cnt` |
| T-02 | Resource summary (filtered) | `python scripts/config/query_Config_resource_summary.py --provider=obs --region_id=cn-north-4` | JSON array, only obs/cn-north-4 rows |
| T-03 | Resource schema | `python scripts/config/query_Config_resource_schema.py --resource_type=obs.buckets` | JSON with schema fields of `obs.buckets` |
| T-04 | SQL query | `python scripts/config/query_Config_resource_by_sql.py --sql="select id, name, provider, type, region_id from resources where provider = 'obs' and type = 'buckets'"` | JSON array of buckets |
| T-05 | SQL query with properties | `python scripts/config/query_Config_resource_by_sql.py --sql="select id, properties.pwd_status from resources where provider = 'iam' and type = 'users'"` | JSON array of IAM users |
| T-06 | Builtin rules | `python scripts/config/query_Config_builtin_rule.py --keyword=obs --limit=5` | JSON array, ≤5 obs-related rules |
| T-07 | Empty result | SQL with a non-existent provider | prints `没有找到数据`, exit code 0 |
| T-08 | Missing args | `python scripts/config/query_Config_resource_schema.py` | argparse error, exit code 2 |
| T-09 | Invalid AK/SK | Run with wrong credentials | error message with error code, exit code 1, **no credential leakage** |

### Execution Method 执行方式

Scripts must be executed via `skill action=exec` with the skill venv Python:

```bash
# Windows
skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/config/<script>.py [OPTIONS]
# Linux / macOS
skill action=exec: skill://.venv/bin/python3 skill://scripts/config/<script>.py [OPTIONS]
```

## Verification Flow 验证流程

```
Environment vars set → pip install -r requirements.txt
  → T-01 connectivity check
      ├── ✅ Success → run T-02..T-06, record PASS/FAIL
      └── ❌ Failure → check AK/SK validity, proxy config (PROXY_URL), network
  → T-07..T-09 negative cases
  → Cross-check a known resource in the console to confirm field accuracy
```

## Security Verification 安全验证

1. No script prints AK/SK/proxy credential values (grep for `HUAWEICLOUD_AK` usage — only `os.getenv`)
2. All API calls are read-only (list/get/run_query); no create/update/delete calls exist
3. Failure messages contain error code/message only, not credentials

