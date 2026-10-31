# Verification Method

## Specification Compliance Verification

```bash
# Validate skill structure manually (no auto-validator script in this skill)
[ -f SKILL.md ] && echo "SKILL.md exists"
```

Checks against the Huawei Cloud Skill Specification:
- SKILL.md exists with valid frontmatter
- Required sections present (Overview, Prerequisites, Workflow, Core Commands, etc.)
- No hardcoded credentials
- File naming conventions (kebab-case)
- Package size and file count limits

## Functional Testing

### CLI Priority (Default)

```bash
bash scripts/test-cli-commands.sh -s {absolute-or-relative-skill-path} -e cli [-r {region}]
# e.g. bash scripts/test-cli-commands.sh -s /path/to/huawei-cloud-hss-query -e cli -r cn-north-4
# 不传 -r 时回退使用环境变量 HUAWEI_REGION
```

> ⚠️ 测试用例命令中的 `{region}` 占位符会在执行前被替换为 `-r` 传入的区域（或 `$HUAWEI_REGION`）；
> 未提供区域时含 `{region}` 的用例直接判 FAIL（不会静默执行失败命令）。

### Test Flow

```
Each test case → Replace {region} → Execute hcloud HSS command (argument array, no eval)
  ├── Exit code != 0 → FAIL
  ├── Output contains error markers (error_code/error_msg/USE_ERROR/APIGW./HSS.) → FAIL
  │    ├── Auth error → Check credentials
  │    ├── Param error → Fix and retry
  │    └── Service error → Record for investigation
  └── Exit code == 0 AND no error markers → PASS
```

> ⚠️ hcloud 对部分 USE_ERROR / 服务端错误返回码为 0，判定必须同时检查退出码与输出内容（含
> `error_code`/`error_msg`/`USE_ERROR`/`APIGW.`/`HSS.` 等错误标记即 FAIL），仅看退出码会把失败误判为 PASS。

## Manual Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| CLI authenticated | `hcloud configure list` | Valid profile shown |
| HSS available | `hcloud HSS ListHostStatus --cli-region={region} --limit=1` | No service error |
| Host list works | `hcloud HSS ListHostStatus --cli-region={region} --limit=1` | JSON with host data |
| Vul list works | `hcloud HSS ListVulnerabilities --cli-region={region} --limit=1` | JSON with vul data |
| Baseline works | `hcloud HSS ShowBaselineOverview --cli-region={region}` | JSON with baseline stats |
| Events work | `hcloud HSS ListEventHandleHistory --cli-region={region} --limit=1 --offset=0` | JSON with event data |
| Login audit works | `hcloud HSS ListLoginCommonIp --cli-region={region}` | JSON with login IP data |
