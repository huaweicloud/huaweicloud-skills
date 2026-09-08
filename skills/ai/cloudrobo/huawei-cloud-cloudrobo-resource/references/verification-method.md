# Verification Method 验证方法

## Specification Compliance Verification 规范合规验证

### Structure Validation 结构验证

```bash
# Verify skill directory structure
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/references/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/scripts/
ls -la skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/templates/
```

### Frontmatter Validation Frontmatter验证

```bash
# Check frontmatter exists
grep '^---$' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md | head -2

# Check name field
grep '^name:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md

# Check description field with triggers
grep 'Triggers include:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md

# Check tags field
grep '^tags:' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
```

### Section Validation 章节验证

```bash
# Required sections (bilingual headers)
grep '##.*概述' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*前置条件' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*工作流' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*核心命令' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*参考文档' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*边界情况' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*验证方法' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
grep '##.*最佳实践' skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/SKILL.md
```

### File Size Constraint 文件大小约束

```bash
# Total skill directory size must not exceed 40 MB
du -sh skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/
```

### File Count Constraint 文件数量约束

```bash
# Total files must not exceed 30
find skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/ -type f | wc -l
```

## Functional Testing 功能测试

### CLI Testing CLI测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/scripts/test-cli-commands.sh -s skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource -e cli
```

### SDK Testing SDK测试

```bash
bash skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource/scripts/test-cli-commands.sh -s skills/ai/cloudrobo/huawei-cloud-cloudrobo-resource -e sdk
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
            └── ❌ Failure → Record FAIL ⛔ requires manual verification
```

## Verification Checklist 验证清单

- Verify `list-quotas` returns `domain_quotas` with CCE `npu=0` and ModelArts `cpu/memory/gpu=0`
- Verify `list-quotas` supports `--workspace-id` and `--resource-type` filtering
- Verify `list-pools` returns `resources` with `page_info`
- Verify `show-pool` returns node-level details including `labels`
- Verify `list-quotas` and `list-pools` support pagination (`--limit`, `--offset`)
