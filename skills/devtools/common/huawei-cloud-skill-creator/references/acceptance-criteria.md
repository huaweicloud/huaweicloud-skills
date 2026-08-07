# Acceptance Criteria — Huawei Cloud Skill Creator v2

## Skill Creation Readiness

| # | Criterion | Phase | Status |
|---|-----------|-------|--------|
| 1 | User requirements confirmed via Socratic Q&A | P1 | ⬜ |
| 2 | Requirements summary table presented and confirmed | P1 | ⬜ |
| 3 | CLI/SDK/API availability researched for each function | P2 | ⬜ |
| 4 | Phase 2 summary generated (execution mode per function) | P2 | ⬜ |
| 5 | SKILL.md generated with required sections | P3 | ⬜ |
| 6 | references/iam-policies.md generated | P3 | ⬜ |
| 7 | references/dataflow-diagram.md generated | P3 | ⬜ |
| 8 | Test cases generated and saved to JSON | P4 | ⬜ |
| 9 | All CLI commands executed and verified | P4 | ⬜ |
| 10 | Failed commands properly downgraded (CLI→SDK→API) | P4 | ⬜ |
| 11 | Resource lifecycle tested (if applicable) | P5 | ⬜ |
| 12 | Test resources cleaned up | P6 | ⬜ |
| 13 | Skill spec compliance check passed | P6 | ⬜ |
| 14 | Frontmatter name matches directory, description includes triggers, and version is absent | P3/P6 | ⬜ |
| 15 | CLI-based Skill includes KooCLI format and cli-installation-guide.md | P3/P6 | ⬜ |
| 16 | IAM, verification, and acceptance reference requirements checked | P3/P6 | ⬜ |
| 17 | All concrete CLI commands use valid Service/PascalCase operation names and `--cli-region` | P3/P6 | ⬜ |
| 18 | Total content size ≤40 MB, file count ≤30, and SKILL.md ≤500 lines | P3/P6 | ⬜ |
| 19 | Every file has one of the 46 allowed extensions | P3/P6 | ⬜ |
| 20 | PR diff changes no more than one Skill directory | P6 | ⬜ |
| 21 | Secret, vulnerability, dependency, and insecure-configuration scans passed | P6 | ⬜ |
| 22 | All 6 phases verified complete | P6 | ⬜ |
| 23 | No in-session AK/SK entry forms (`hcloud configure set --cli-*-key=...` or `BasicCredentials(ak=..., sk=...)` literal kwargs) outside NEVER context — SEC-002 in `validate-skill.sh` | P3/P6 | ⬜ |

## Quality Gates

| Gate | Must Pass Before |
|------|------------------|
| Phase 1 complete | Starting Phase 2 |
| Phase 2 complete | Starting Phase 3 |
| Phase 3 complete | Starting Phase 4 |
| Phase 4 complete | Starting Phase 5 |
| Phase 5 complete | Starting Phase 6 |
| 6/6 phases complete | Skill creation declared done |
