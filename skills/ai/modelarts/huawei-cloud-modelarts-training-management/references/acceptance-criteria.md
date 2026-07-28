# Acceptance Criteria

> Checklist for validating the ModelArts training management skill.

---

## 1. Skill Structure

| # | Criterion | Status |
|---|-----------|--------|
| 1.1 | SKILL.md exists and has valid frontmatter (name, description) | ☐ |
| 1.2 | references/ directory exists with all reference files | ☐ |
| 1.3 | No hardcoded credentials (AK/SK) in any file | ☐ |
| 1.4 | No hardcoded region — uses `{region}` placeholder | ☐ |

## 2. API Coverage

| # | Criterion | Status |
|---|-----------|--------|
| 2.1 | All 52 APIs documented in SKILL.md reference table | ☐ |
| 2.2 | All 52 APIs have CLI examples in cli-command-examples.md | ☐ |
| 2.3 | API numbering is sequential 1-52 | ☐ |
| 2.4 | 8 functional domains clearly separated | ☐ |

## 3. CLI Command Format

| # | Criterion | Status |
|---|-----------|--------|
| 3.1 | All commands use `hcloud ModelArts <Operation>` format | ☐ |
| 3.2 | All commands include `--cli-region={region}` | ☐ |
| 3.3 | Complex params use `--cli-jsonInput` with JSON file | ☐ |
| 3.4 | JSON file format uses `{"body": {...}}` envelope | ☐ |
| 3.5 | project_id omitted (auto-resolved) | ☐ |

## 4. Write Operation Safety

| # | Criterion | Status |
|---|-----------|--------|
| 4.1 | All write ops marked with ⚠️ warning | ☐ |
| 4.2 | Write ops require user confirmation before execution | ☐ |
| 4.3 | Delete operations clearly identified as irreversible | ☐ |
| 4.4 | Stop operation documents valid states | ☐ |

## 5. Documentation Quality

| # | Criterion | Status |
|---|-----------|--------|
| 5.1 | Each API has description in Chinese and English | ☐ |
| 5.2 | Required vs optional parameters clearly marked | ☐ |
| 5.3 | JSON examples provided for complex operations | ☐ |
| 5.4 | Error handling documented | ☐ |
| 5.5 | Known issues documented in known-issues.md | ☐ |
| 5.6 | IAM policies documented in iam-policies.md | ☐ |

## 6. Reference Files

| # | Criterion | Status |
|---|-----------|--------|
| 6.1 | cli-command-examples.md covers all 52 APIs | ☐ |
| 6.2 | iam-policies.md has least-privilege and read-only policies | ☐ |
| 6.3 | verification-method.md has test steps and success criteria | ☐ |
| 6.4 | dataflow-diagram.md has Mermaid diagrams | ☐ |
| 6.5 | api-paths.md has REST API paths from SDK | ☐ |
| 6.6 | known-issues.md documents CLI bugs and workarounds | ☐ |
| 6.7 | acceptance-criteria.md (this file) is complete | ☐ |

## 7. Test Readiness

| # | Criterion | Status |
|---|-----------|--------|
| 7.1 | Read-only test commands identified | ☐ |
| 7.2 | Dependent resource IDs parameterized | ☐ |

## 8. Compliance

| # | Criterion | Status |
|---|-----------|--------|
| 8.1 | No secrets in any file | ☐ |
| 8.2 | No PII in any file | ☐ |
| 8.3 | File sizes within reasonable limits | ☐ |
| 8.4 | Markdown formatting is valid | ☐ |
| 8.5 | All internal links resolve | ☐ |
| 8.6 | Description in frontmatter matches skill scope | ☐ |

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Skill Author | | | ☐ Pass / ☐ Fail |
| Reviewer | | | ☐ Pass / ☐ Fail |
