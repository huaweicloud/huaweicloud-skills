# Acceptance Criteria

> Checklist for validating the Hermes one-click deployment skill.

---

## 1. Skill Structure

| # | Criterion | Status |
|---|-----------|--------|
| 1.1 | SKILL.md exists and has valid frontmatter (name, description) | ☐ |
| 1.2 | references/ directory exists with all reference files | ☐ |
| 1.3 | No hardcoded credentials (AK/SK/Secret) in any file | ☐ |
| 1.4 | All scripts support both long-term and temporary credentials | ☐ |
| 1.5 | PYTHON scripts use `sys.path.insert(0, ...)` for imports | ☐ |

## 2. Deployment Commands

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 2.1 | `deploy` command creates Flexus L instance with valid credentials | `python scripts/caller.py deploy --ak <AK> --sk <SK> --non-interactive` |
| 2.2 | `deploy` command accepts `--name` parameter | `python scripts/caller.py deploy --name my-hermes --non-interactive` |
| 2.3 | `deploy` command accepts `--region` parameter with valid region | `python scripts/caller.py deploy --region cn-north-4 --non-interactive` |
| 2.4 | `deploy` command auto-generates instance name when `--name` not provided | Check output shows timestamp-based name |
| 2.5 | `deploy` command supports `--security-token` for temporary credentials | `python scripts/caller.py deploy --security-token <token>` |

## 3. Model Configuration

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 3.1 | `maas` command runs COC script for MaaS configuration | `python scripts/caller.py maas --resource-id <id> --api-key <key>` |
| 3.2 | `maas` command accepts `--api-base-url` parameter | Check output uses custom URL |
| 3.3 | `maas` command accepts `--timeout` parameter | Check timeout value in confirmation |

## 4. Channel Configuration

| # | Criterion | Verification Method |
|---|-----------|---------------------|
 | 4.1 | `channel` command supports Feishu platform | `python scripts/caller.py channel --bot-platform feishu --feishu-app-id <id>` |
| 4.2 | `channel` command supports WeCom platform | `python scripts/caller.py channel --bot-platform wecom --wecom-bot-id <id>` |
| 4.3 | Channel secrets are not hardcoded in scripts | `grep -r 'SECRET=|' scripts/` (should find zero matches) |

## 5. Gateway Management

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 5.1 | `gateway` command restarts Hermes gateway on remote instance | `python scripts/caller.py gateway --resource-id <id>` |

## 6. Query & Diagnostics

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 6.1 | `query` command retrieves script execution result by UUID | `python scripts/caller.py query --execute-uuid <uuid>` |
| 6.2 | `uniagent` command queries UniAgent status | `python scripts/caller.py uniagent -resource-id <id>` |

## 7. Error Handling

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 7.1 | Missing credentials produces guidance message | Run without --ak/--sk |
| 7.2 | Invalid region produces clear error | Use invalid region value |
| 7.3 | All commands support `--non-interactive` flag | Run with --non-interactive and check output |
| 7.4 | Network timeout handled gracefully for APIs | Simulate unreachable endpoint |

## 8. Security

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 8.1 | No hardcoded AK/SK/secret in any .py file | `grep -r '= \"AK\"\|= \"SK\"' scripts/` |
| 8.2 | No credential values printed to stdout | Review output for masked display `****` |
| 8.3 | Write operations require user confirmation (interactive mode) | Run without --non-interactive and verify prompt |
| 8.4 | Secrets use env var injection via export, not hardcoded assignment | Code review |

## 9. Documentation

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 9.1 | SKILL.md contains `## Overview` section | Check section exists |
| 9.2 | SKILL.md contains `## Core Commands` section | Check section exists |
| 9.3 | SKILL.md contains `## Parameter Reference` section | Check section exists |
| 9.4 | SKILL.md contains trigger words in description | Check frontmatter |
| 9.5 | `references/cli-installation-guide.md` exists | File exists |
| 9.6 | `references/acceptance-criteria.md` exists | File exists |
| 9.7 | `references/iam-policies.md` exists | File exists |

## 10. Integration

| # | Criterion | Verification Method |
|---|-----------|---------------------|
| 10.1 | Skill triggers on "Deploy Hermes", "Install Hermes", etc. | Trigger keyword test |
| 10.2 | Skill supports both long-term and temporary credentials | Test both auth modes |
| 10.3 | Skill falls back to interactive mode when parameters missing | Run without any arguments |

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Skill Author | | | | ☐ Pass / ☐ Fail |
| Reviewer | | | ☐ Pass / ☐ Fail |