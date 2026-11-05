# Acceptance Criteria

## Functional Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-01 | Returns the total size of a single bucket | `python3 scripts/query_obs_total_size.py --bucket <bucket>` prints a single non-negative integer (bytes) |
| AC-02 | Returns the total size across all buckets | `python3 scripts/query_obs_total_size.py --all` prints a single non-negative integer |
| AC-03 | CLI and SDK agree for the same bucket | `--executor cli` and `--executor sdk` return the same byte count for the same bucket |
| AC-04 | Unit conversion works | `--unit mb` returns `value / 2^20` with two decimals |
| AC-05 | Human readable output works | `--human` returns a readable size like `4.77MB` |
| AC-06 | Empty bucket returns 0 | A bucket with no objects returns `0` |
| AC-07 | Only the size value is on stdout | stdout carries the single size value only; warnings/errors are written to stderr |
| AC-08 | Read-only guarantee | No create/update/delete operation is invoked by this skill |

## Security Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-S1 | No AK/SK hardcoded in skill files | grep for `AK=`, `SK=`, `access.key=`, `secret.key=` on the skill directory returns nothing |
| AC-S2 | No KooCLI `configure set` credential command | SKILL.md and references never include KooCLI `configure set` with credential flags |
| AC-S3 | Least-privilege IAM policy | `references/iam-policies.md` grants only `obs:bucket:ListAllMyBuckets`, `obs:bucket:ListBucket`, `obs:object:List` |
| AC-S4 | No cross-skill calls | SKILL.md does not reference other skill names |

## Quality Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-Q1 | SKILL.md follows the Huawei Cloud Skill Specification | All Critical sections (frontmatter, Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents) present and zero hardcoded credentials |
| AC-Q2 | Script runs without syntax errors | `python3 scripts/query_obs_total_size.py --help` exits 0 |
| AC-Q3 | SKILL.md <= 500 lines, total files <= 30 | `wc -l SKILL.md` reports line count; `find . -type f` reports file count |
