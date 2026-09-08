# Verification Method 验证方法

## Specification Compliance Verification 规范合规验证

### Structure Validation 结构验证

```bash
# Verify skill directory structure
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/references/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/scripts/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/templates/
```

### Frontmatter Validation Frontmatter验证

```bash
# Check frontmatter exists
grep '^---$' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md | head -2

# Check name field
grep '^name:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md

# Check description field with triggers
grep 'Triggers include:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md

# Check tags field
grep '^tags:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
```

### Section Validation 章节验证

```bash
# Required sections (bilingual headers)
grep '##.*概述' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
grep '##.*前置条件' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
grep '##.*工作流' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
grep '##.*核心命令' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
grep '##.*参数确认' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
grep '##.*参考文档' skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/SKILL.md
```

### File Size Constraint 文件大小约束

```bash
# Total skill directory size must not exceed 40 MB
du -sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/
```

### File Count Constraint 文件数量约束

```bash
# Total files must not exceed 30
find skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/ -type f | wc -l
```

## Functional Testing 功能测试

### CLI Testing CLI测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/scripts/test-cli-commands.sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset --executor cli
```

### SDK Testing SDK测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset/scripts/test-cli-commands.sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-asset --executor sdk
```

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
