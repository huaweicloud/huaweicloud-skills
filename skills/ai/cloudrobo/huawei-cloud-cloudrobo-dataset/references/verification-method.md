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
Check phase-1-summary.json exists → If missing, restart from Phase 1
Check phase-2-summary.json exists → If missing, restart from Phase 2
Check phase-3-summary.json exists → If missing, restart from Phase 3
Check phase-4-summary.json exists → If missing, restart from Phase 4
Check phase-5-summary.json exists → If missing, restart from Phase 5
Check phase-6-summary.json exists → If missing, restart from Phase 6
```

All phases complete → Creation done. Missing phases → Restart from the missing phase.
