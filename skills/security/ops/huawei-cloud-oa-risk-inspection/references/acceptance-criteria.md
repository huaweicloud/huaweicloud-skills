# Acceptance Criteria — huawei-cloud-oa-risk-inspection

## 1. Registration & Routing

- [ ] `SKILL.md` conforms to the GitCode Skill registration spec (YAML frontmatter with
      `name`, `description` containing feature summary + trigger words, `tags`, `version`).
- [ ] Skill directory follows the `huawei-cloud-oa-risk-inspection` naming convention.
- [ ] `hcloud` CLI dependency correctly declared in Prerequisites section (>= 7.2.2).

## 2. Behavior

- [ ] **Step 1 (Environment check)**: verifies Python >= 3.9, hcloud >= 7.2.2, dependencies,
      and hcloud authentication; terminates with guidance if any check fails.
- [ ] **Cloud service scope resolution**: when the user names one or more cloud services,
      the agent first runs the support-set probe
      (`python scripts/cloud_service_filter.py --cloud-services "<wording>"`) and then passes
      their wording verbatim as `--cloud-services` to Steps 2 and 5, without translating it
      itself; when the user names none, the option is not passed and the run is full-tenant.
      The scope never narrows Step 3 or Step 4. A Step 5 exit caused by the scope matching no
      record terminates the workflow with the available service codes from the log, and is
      never retried as a full-tenant run.
- [ ] **Partially unsupported services**: when only some named services are absent from the
      alias table, the agent tells the user which ones are not inspectable yet and continues
      with only the supported ones — it neither aborts nor passes the unsupported names on.
- [ ] **Fully unsupported services**: when none of the named services is in the alias table,
      the agent states that none can be inspected, lists the codes from the probe's
      `available` field, and terminates before Step 2 without falling back to a full-tenant run.
- [ ] **Alias table scope**: `references/cloud_services.json` contains only services that
      exist in OA / Config / SecMaster, and every service value those three sources report
      resolves to an entry (no unresolved token).
- [ ] **Step 2 (Fetch OA risk inspection)**: runs `oa_risk_inspection.py` with its default
      command-line options; script parameters may be asked about but default values are
      used when unspecified. The region is the script constant `cn-southwest-2` and there
      is no region option. Branches on the exit code: `0` records the produced artifact's
      absolute path from the log output and continues to Step 3; non-zero records the
      failure reason and still continues to Step 3 without aborting. Produces
      `oa_risk_inspection_results_<ts>.json`. On scoped runs it also receives
      `--cloud-services`, narrows the triggered check items only, and records the resolution
      in `meta.cloud_service_filter`.
- [ ] **Step 3 (Fetch Config compliance)**: runs `config_compliance_inspection.py` with its
      default command-line options; script parameters may be asked about but default values
      are used when unspecified. The hcloud region is the script constant `cn-north-4`.
      Branches on the exit code: `0` records the produced artifact's absolute path from the
      log output and continues to Step 4; non-zero records the failure reason and still
      continues to Step 4 without aborting. Produces
      `config_compliance_inspection_results_<ts>.json`.
- [ ] **Step 4 (Fetch SecMaster baseline)**: runs with its default options and takes no
      region parameter — the scan scope is the region list built into the script, so the
      agent never asks about or narrows to a region. Produces
      `secmaster_baseline_inspection_results_<ts>.json` (with a `meta` block covering the
      scanned regions and instances) and `secmaster_baseline_inspection_stats_<ts>.json`.
      Exit codes: `0` at least one instance inspected — records the artifact's absolute path
      from the log output; `1` no instance in the account; `2` incomplete scan. Every branch
      continues to Step 5, and `--secmaster-file` is passed only when the exit code is `0`.
- [ ] **Step 5 (Convert raw results)**: invokes `merge_inspection_results.py` with
      `--oa-file` / `--config-file` / `--secmaster-file` derived from Steps 2-4 outputs,
      without asking for confirmation; a source that produced no artifact is omitted and the
      merge records it as `missing` in `meta.sources`. `--secmaster-file` is also omitted
      when Step 4 exited non-zero, so absent or incomplete SecMaster data is never recorded
      as `ok`. On scoped runs it receives the same `--cloud-services` value as Step 2 and is
      the authoritative filter: out-of-scope and unclassified records are dropped and
      counted in `meta.cloud_service_filter`, `meta.counts` stays equal to the length of
      `results`, and a scope matching no record exits non-zero without writing a file.
- [ ] **Step 6 (Generate report)**: invokes `merge_report_generator.py` with `--input`
      pointing to the Step 5 output, without asking for confirmation; produces both HTML and
      XLSX reports. On scoped runs it additionally writes
      `merge_inspection_report_<ts>_risk_items.json` next to them and logs its absolute path;
      on full-tenant runs that file is absent.
- [ ] **Step 7 (Archive and cleanup)**: invokes `archive_artifacts.py` with `--report-dir`
      from the Step 6 output directory, archiving the HTML report and the Excel workbook —
      plus the risk-item JSON when the run was scoped — to `~/.hcloud-oa-risk/<ts>/` with an
      `archive_manifest.json`; the merged JSON and any other JSON are not archived. Deletes
      exactly the 5 temporary JSON files produced in Steps 2-5 (including the merged JSON) by
      their recorded absolute paths, and only after the archive exits zero; the risk-item
      JSON is a deliverable and is never in that list. An archive failure keeps the
      deliverables in place and continues. Never uses wildcards or directory deletion.
- [ ] **Step 8 (Summary)**: presents a completion table (No./Step/Status/Remarks) covering
      all 8 steps, lists the archive directory and the archived report absolute paths (from
      `archive_manifest.json`), marks unarchived deliverables as "not archived" with the local
      path and reason, summarizes the blacklist-filtered items in a single line carrying the
      Config and SecMaster counts, and marks any absent source as "无数据" in Remarks instead
      of "0 risks". No per-source breakdown section and no list of deleted temporary files.
      On scoped runs it also presents the risk-item JSON as the single data source: an
      item-level table (service / dimension / item name / risk level / source / risk resource
      count), the resource details expanded when `totals.items` <= 20 and `totals.resources`
      <= 50 (otherwise the table only plus the JSON's absolute path), the covered `services`,
      a statement for services that matched no record, the wording "已匹配 N 条检查记录，未发现
      风险项" when `totals.items` is 0 but `totals.records` is not, and one line for the
      records excluded as unclassified. Full-tenant runs present no such table.
- [ ] **No confirmation prompts**: Steps 5, 6, 7 and 8 must not ask the user for parameters
      or confirmation; each script command line is printed before execution without
      blocking. Steps 2 and 3 run with the script default options and may ask about script
      parameters, but never about the region.

## 3. Output Artifacts

- [ ] **HTML report** (`merge_inspection_report_<ts>.html`):
      - Summary cards: risk items / hint items / security items / non-risk items / failed items
      - 5 charts: risk status distribution, product distribution, source distribution,
        risk dimension distribution, Config daily compliance trend
      - Risk item detail table with filtering, sorting, pagination and nested resource detail
      - Hint item overview block and failed item detail block
- [ ] **XLSX report** (`merge_inspection_report_<ts>.xlsx`):
      - Overview sheet ("风险检查总览"): account info and risk item table with source and
        jump-link columns; nothing is appended below the risk item table
      - One detail sheet per risk item with resource details and back-to-overview links
      - Risk resource count equals the resource detail list length
- [ ] **Risk-item JSON** (`merge_inspection_report_<ts>_risk_items.json`, scoped runs only):
      - Contains `services`, `totals` (`items` / `resources` / `records`) and `items[]`
      - Each item carries the same fields the HTML table shows plus its resource details
        (region / id / name / status)
      - `totals.items` equals the number of items and `totals.resources` the total resource
        entries, so the agent can state "matched N records, found no risk" when items is 0
      - Contains no report paths, archive location or account identifiers
      - Absent on full-tenant runs, whose HTML and XLSX remain unchanged

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
| Archive and cleanup | 7 | Reports archived, 5 temp JSON removed | - |
| Summary | 8 | Completion table + archive and artifact paths + one-line blacklist | - |
