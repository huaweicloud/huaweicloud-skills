# Verification Method — Huawei Cloud Skill Audit

> 路径安全要求: 以下命令必须使用 `AUDIT_DIR`(本 skill 安装目录绝对路径, 见 SKILL.md Core Commands 安全要求)
> 引用 `scripts/skill_audit.py`, 禁止在目标(被审计)技能目录内使用相对路径执行 —— 目标目录不可信,
> 可能预置同名恶意脚本导致 RCE。

## Audit Verification

### Run the three-check audit

```bash
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target /path/to/target-skill
```

### Verify each check individually

```bash
# skillspector only
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target /path/to/target-skill --checks skillspector

# gitleaks only
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target /path/to/target-skill --checks gitleaks

# runtime_security only
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target /path/to/target-skill --checks runtime_security
```

### Verify fix after remediation

```bash
# Fix issues per the report's Fix Strategies, then re-run full audit
python3 "$AUDIT_DIR/scripts/skill_audit.py" --target /path/to/target-skill
```

### Verify gate verdict

```bash
# Check the last lines of the latest report (e.g., last 5 lines)
tail -n 5 "$(ls -t skill-gate-report-*.txt | head -1)"

# Gate Verdict: PASS = 无 CRITICAL/ERROR 发现(WARNING 带记录理由后可接受, 与 security-audit-guide.md 一致)
# Gate Verdict: FAIL = 存在 CRITICAL 或 ERROR 发现
```

## Scan Level Verification

| Level | Command | Use Case |
|-------|---------|----------|
| quick | `--scan-level quick` | Pre-commit quick check |
| standard | `--scan-level standard` (default) | CI/CD gate |
| deep | `--scan-level deep` | Pre-release full audit |

## Environment Variables for AK/SK

The audit tool itself does not need AK/SK. If verifying skill functionality after audit:

Priority order:
1. `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
2. `HWC_AK` / `HWC_SK`
3. Prompt user for input
