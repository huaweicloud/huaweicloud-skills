# Verification Method - huawei-cloud-skill-creator-skill

> Read this file when verifying that a generated Skill complies with the specification.

## Automated Verification

Use `scripts/validate-skill.sh` for automated checks:

```bash
bash scripts/validate-skill.sh {generated-skill-path}
```

Verification covers: SKILL.md structure, Frontmatter completeness, naming conventions, AK/SK security, references links, body line count, etc.

## Manual Verification Checklist

### Structural Verification

1. Directory structure complete: SKILL.md + references/ + scripts/ (as needed) + templates/ (as needed)
2. SKILL.md YAML Frontmatter format correct
3. All referenced files in references/ exist

### Content Verification

1. description contains 5 structured points
2. Each step has CLI commands
3. Provides 3-5 usage examples
4. AK/SK not hardcoded
5. iam-policies.md contains minimum privilege policy JSON

### Functional Verification

1. CLI command syntax correct (verify via CLI help output)
2. Parameter names match CLI help output
3. Region parameter uses valid values

## Verification Scoring

| Grade | Condition | Description |
|-------|-----------|-------------|
| A | All required pass, WARN ≤ 2 | Ready for official release |
| B | All required pass, WARN ≤ 5 | Publishable, needs improvement |
| C | All required pass, WARN > 5 | Publishable, quality needs improvement |
| D | Required checks failed | Not publishable |
