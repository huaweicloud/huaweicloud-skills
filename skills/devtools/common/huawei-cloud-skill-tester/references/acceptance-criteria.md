# Acceptance Criteria — huawei-cloud-skill-tester

## Pipeline Execution

- [ ] Pipeline runs end-to-end for a single skill without error
- [ ] Pipeline runs end-to-end for multiple skills without error
- [ ] `--all-installed` flag scans and tests all installed skills
- [ ] `--fresh` flag resets all phase outputs and starts from scratch
- [ ] `--phase` flag resumes from a specific phase

## Phase Outputs

- [ ] Each phase generates a valid `phase-N-summary.json` file
- [ ] JSON schema matches the specification in `references/output-schema-spec.md`
- [ ] Summary contains correct `verdict` field

## Chain Verification

- [ ] Phase 2 refuses to run if Phase 1 output is missing
- [ ] Phase 3 refuses to run if Phase 1 or Phase 2 output is missing
- [ ] Phase 4 refuses to run if Phase 3 output is missing
- [ ] Phase 5 refuses to run if Phase 4 output is missing
- [ ] Phase 6/7 refuse to run if Phase 5 was not completed for all tested skills
- [ ] Phase 8 refuses to run if any Phase 0~7 output is missing

## Write Operation Safety

- [ ] Read-only test cases execute automatically without user intervention
- [ ] Write operations (Create/Update/Delete) prompt for user confirmation before execution
- [ ] User can skip write operations with `n` response
- [ ] Skipped operations are recorded as `skip` (user_cancelled)
- [ ] Confirmation is required per-case, not batched

## Error Handling

- [ ] Missing AK/SK triggers user prompt; process terminates if not provided
- [ ] Network interruption preserves already-executed results
- [ ] Resource cleanup retries 3 times before marking as manual
- [ ] Manual cleanup instructions are generated for failed cleanups

## Reporting

- [ ] Phase 8 produces a consolidated report with all phase verdicts
- [ ] Overall statistics include pass/fail/skip counts
- [ ] Resources created and cleaned counts are accurate
- [ ] Manual intervention steps are listed in the report
