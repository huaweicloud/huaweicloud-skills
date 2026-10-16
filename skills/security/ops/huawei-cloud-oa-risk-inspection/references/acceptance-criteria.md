# Acceptance Criteria — huawei-cloud-oa-risk-inspection

## 1. Registration & Routing

- [ ] `SKILL.md` conforms to the GitCode Skill registration spec (YAML frontmatter with
      `name`, `description` containing feature summary + trigger words, `tags`, `version`).
- [ ] Skill directory follows the `huawei-cloud-oa-risk-inspection` naming convention.
- [ ] `hcloud` CLI dependency correctly declared in Prerequisites section (>= 7.2.2).

## 2. Behavior

- [ ] **Step 1 (Environment check)**: verifies Python >= 3.9, hcloud >= 7.2.2, dependencies,
      and hcloud authentication; terminates with guidance if any check fails.
- [ ] **Step 2 (Fetch OA risk inspection)**: prompts user for parameters of
      `oa_risk_inspection.py` (`--region`, `--X-Language`, `--threads`, `--page-size`,
      `--max-retries`, `--retry-interval`, `--timeout`), produces
      `oa_risk_inspection_results_<ts>.json`.
- [ ] **Step 3 (Fetch Config compliance)**: prompts user for `--cli-region` of
      `config_compliance_inspection.py`, produces `config_compliance_inspection_results_<ts>.json`.
- [ ] **Step 4 (Fetch SecMaster baseline)**: prompts user for `--region_id` of
      `secmaster_baseline_inspection.py`, produces `secmaster_baseline_inspection_results_<ts>.json`
      and `secmaster_baseline_inspection_stats_<ts>.json`.
- [ ] **Step 5 (Convert raw results)**: invokes `merge_inspection_results.py` with
      `--oa-file` / `--config-file` / `--secmaster-file` based on Steps 2-4 outputs,
      produces `merge_inspection_results_<ts>.json`.
- [ ] **Step 6 (Generate report)**: invokes `merge_report_generator.py` with `--input`
      pointing to the Step 5 output, produces both HTML and XLSX reports.
- [ ] **Step 7 (Cleanup)**: removes the 5 temporary JSON files produced in Steps 2-5.
- [ ] **Step 8 (Summary)**: presents a completion table with step/status/notes, lists final
      artifact paths (absolute), written entirely in English.
- [ ] **Parameter confirmation**: each script step (Steps 2-6) must independently ask the
      user to confirm that step's parameter values; answers from previous steps must NOT be
      silently reused.

## 3. Output Artifacts

- [ ] **HTML report** (`merge_inspection_report_<ts>.html`):
      - Summary cards: risk items / hint items / security items / non-risk items / failed items
      - 5 charts: risk status distribution, product distribution, source distribution,
        risk dimension distribution, Config daily compliance trend
      - Risk item detail table with filtering, sorting, pagination and nested resource detail
      - Hint item overview block and failed item detail block
- [ ] **XLSX report** (`merge_inspection_report_<ts>.xlsx`):
      - Overview sheet ("风险检查总览"): account info, risk item table with source and
        jump-link columns, check coverage summary block
      - One detail sheet per risk item with resource details and back-to-overview links
      - Risk resource count equals the resource detail list length

## 4. Structure & Compliance

- [ ] `references/cli-installation-guide.md` present — hcloud CLI setup instructions.
- [ ] `references/iam-authentication-guide.md` present — AK/SK and region configuration.
- [ ] `references/verification-method.md` present — environment and feature verification.
- [ ] `references/acceptance-criteria.md` present — this file.
- [ ] All filenames in `references/` use kebab-case.
- [ ] SKILL.md contains required sections: Overview, Workflow, Prerequisites, References.
- [ ] No hardcoded credentials in any file.
- [ ] All file extensions in the allowlist (.md, .py, .txt, .html, .js).

## 5. Test Result Summary

| Capability | Steps | Expected | Result |
|------------|-------|----------|--------|
| Environment check | 1 | All prerequisites met | - |
| OA data fetching | 2 | JSON with OA check items | - |
| Config data fetching | 3 | JSON with compliance rules/resources | - |
| SecMaster data fetching | 4 | JSON + stats | - |
| Merge | 5 | Merged JSON in OA format | - |
| Report generation | 6 | HTML + XLSX produced | - |
| Risk count accuracy | 6 | Count == resource list length | - |
| Cleanup | 7 | Temp JSON removed | - |
| Summary | 8 | Completion table + artifact paths | - |
