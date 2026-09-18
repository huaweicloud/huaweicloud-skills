# Acceptance Criteria

## Skill Creation Readiness

| # | Criterion | Phase | Status |
|---|-----------|-------|--------|
| 1 | User requirements confirmed via Socratic Q&A | P1 | ⬜ |
| 2 | Requirements include: policy CRUD + 9 rule types + JSON import | P1 | ⬜ |
| 3 | All 14 CLI commands verified (5 policy + 9 rule) | P2 | ⬜ |
| 4 | Phase 2 summary generated with command details | P2 | ⬜ |
| 5 | SKILL.md generated with all required sections | P3 | ⬜ |
| 6 | references/iam-policies.md generated | P3 | ⬜ |
| 7 | references/cli-installation-guide.md generated | P3 | ⬜ |
| 8 | references/verification-method.md generated | P3 | ⬜ |
| 9 | references/dataflow-diagram.md generated | P3 | ⬜ |
| 10 | references/acceptance-criteria.md generated | P3 | ⬜ |
| 11 | Test cases generated for all commands | P4 | ⬜ |
| 12 | Policy CRUD commands executed and verified | P4 | ⬜ |
| 13 | Rule creation commands executed and verified | P4 | ⬜ |
| 14 | JSON import workflow tested | P5 | ⬜ |
| 15 | Resource lifecycle tested (create → verify → delete) | P5 | ⬜ |
| 16 | Test resources cleaned up | P6 | ⬜ |
| 17 | Skill spec compliance check passed | P6 | ⬜ |
| 18 | Frontmatter name matches directory | P3/P6 | ⬜ |
| 19 | Description includes trigger words | P3/P6 | ⬜ |
| 20 | All CLI commands use valid Service/Operation names | P3/P6 | ⬜ |
| 21 | All CLI commands include --cli-region | P3/P6 | ⬜ |
| 22 | Total content size ≤40 MB | P3/P6 | ⬜ |
| 23 | File count ≤30 | P3/P6 | ⬜ |
| 24 | SKILL.md lines ≤500 | P3/P6 | ⬜ |
| 25 | All files use allowed extensions | P3/P6 | ⬜ |
| 26 | No hardcoded AK/SK | P3/P6 | ⬜ |
| 27 | All 6 phases verified complete | P6 | ⬜ |

## Quality Gates

| Gate | Must Pass Before |
|------|------------------|
| Phase 1 complete | Starting Phase 2 |
| Phase 2 complete | Starting Phase 3 |
| Phase 3 complete | Starting Phase 4 |
| Phase 4 complete | Starting Phase 5 |
| Phase 5 complete | Starting Phase 6 |
| 6/6 phases complete | Skill creation declared done |

## Command Coverage

### Policy Management (5 commands)
- [ ] CreatePolicy
- [ ] ListPolicy
- [ ] ShowPolicy
- [ ] UpdatePolicy
- [ ] DeletePolicy

### Rule Creation (9 commands)
- [ ] CreateCustomRule
- [ ] CreateCcRule
- [ ] CreateWhiteblackipRule
- [ ] CreateGeoipRule
- [ ] CreateIgnoreRule
- [ ] CreateAnticrawlerRule
- [ ] CreatePrivacyRule
- [ ] CreateAntiTamperRule
- [ ] CreateAntileakageRule

## JSON Integration

- [ ] Can read huawei-cloud-waf-policy-query export format
- [ ] Can map JSON fields to CreatePolicy parameters
- [ ] Can map JSON fields to UpdatePolicy parameters
- [ ] Can batch create rules from rule_details
- [ ] Handles missing optional fields gracefully
- [ ] Validates JSON structure before import
