# Acceptance Criteria

## Test Pass Criteria

| Phase | Criteria |
|-------|----------|
| Phase 0 | SKILL.md, references/, scripts/, templates/ all exist |
| Phase 1 | Feature points extracted without error |
| Phase 2 | At least one execution mode (CLI/SDK/API) available per feature |
| Phase 3 | Test cases generated for all feature points |
| Phase 4 | All read-only tests pass; write tests require user confirmation |
| Phase 5 | Orchestration scenarios derived and executed |
| Phase 6 | Resource lifecycle verified end-to-end |
| Phase 7 | Consolidated report generated |

## Quality Gates

- All Critical-level spec checks must pass
- Security audit must not have ERROR/CRITICAL findings
- User must confirm before any write/mutating operation
