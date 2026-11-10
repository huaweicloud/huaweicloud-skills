---
name: huawei-cloud-oa-risk-inspection
description: |
  Huawei Cloud tenant risk inspection SKILL for OA, Config and SecMaster services.
  Use this skill when the user wants to inspect risk from OA, Config and SecMaster services, and generate inspection report in form of HTML and Excel
  Trigger: User mentions "风险巡检", "风险检查", "资源合规"，"基线检查"
tags: [ risk inspection ]
version: 1.1.0
license: MIT
---

# Huawei Cloud OA Service Risk Inspection

## Overview

Fetch tenant resource inspection results from the Huawei Cloud Optimization Advisor (OA), Config and SecMaster services, and generate an inspection analysis report.

## Cloud service scope

Decide the scope before Step 2:

* **IF** the user named one or more cloud services to inspect (for example "查看 ECS 的巡检风险" or "我想查看 ECS 和 CCE 的巡检风险"), the run is **scoped**: first check the support set, then pass the user's own words as `--cloud-services` to **Step 2** and **Step 5**
  * **MUST** run the support-set probe once before **Step 2**: `python scripts/cloud_service_filter.py --cloud-services "<user's wording>"`. It prints JSON with `supported` / `unsupported` / `available` — **MUST NOT** read the alias table yourself and reason about it
  * **WHEN** every named service is supported, continue without any extra notice
  * **WHEN** only some named services are supported, tell the user which ones are not inspectable yet, then continue with only the supported ones
  * **WHEN** no named service is supported, tell the user none of them can be inspected, list the services from `available`, and terminate the workflow — **MUST NOT** run Steps 2-8 and **MUST NOT** fall back to a full-tenant inspection
  * The value passed to **Step 2** and **Step 5** **MUST** contain only supported services; when all are supported, keep the user's wording verbatim (`--cloud-services "ECS,CCE"`, `--cloud-services 弹性云服务器`)
  * Pass the wording verbatim — the scripts translate names and abbreviations into service codes through [references/cloud_services.json](references/cloud_services.json); **MUST NOT** translate them yourself
  * **MUST NOT** ask the user to confirm or restate the service list
* **IF** the user named no cloud service (for example "执行风险巡检"), the run is **full-tenant**: **MUST NOT** pass `--cloud-services`; Steps 2 and 5 then behave exactly as before
* The scope **MUST NOT** narrow **Step 3** or **Step 4**: neither script accepts a cloud-service option, and skipping or trimming those steps because the user named a service would make the report's sources disagree with each other
* **WHEN** Step 5 exits non-zero because the scope matched no record, record the reason and the available service codes from its log, then terminate — **MUST NOT** re-run as a full-tenant inspection
* The alias table is the single authority on what can be inspected: a service missing from it is reported as unsupported rather than silently matched, so a newly launched service needs a table entry before it can be named

## Workflow

Copy the following checklist and track progress:

```markdown
- [ ] Step 1: Environment check
- [ ] Step 2: Fetch OA risk inspection results
- [ ] Step 3: Fetch Config resource compliance results
- [ ] Step 4: Fetch SecMaster baseline check results
- [ ] Step 5: Convert raw results
- [ ] Step 6: Generate report
- [ ] Step 7: Archive deliverables and clean up temporary files
- [ ] Step 8: Workflow summary
```

**Step 1: Environment check**

* **MUST** Check whether the Python programming language is installed
* **MUST** Check the Python third-party library dependencies, refer to [requirements.txt](requirements.txt)
  * Refer to the command `pip install --dry-run -r requirements.txt`
  * Expect all packages to output `Requirement already satisfied`
  * **IF** `Would install` appears, install the third-party library dependencies listed in [requirements.txt](requirements.txt)
* **MUST** Check whether the hcloud command-line tool is installed
* **MUST** Check whether the hcloud command-line tool has authentication information configured
* If any check fails, **MUST** report the missing items and fix guidance to the user, and terminate the workflow

**Step 2: Fetch OA risk inspection results**

Call the [oa_risk_inspection.py](scripts/oa_risk_inspection.py) script to fetch raw risk inspection results from the Optimization Advisor (OA), with the following requirements:

* **MUST** run the script with its default command-line options, unless the user specifies different values for them or the run is scoped
* **WHEN** the run is scoped, **MUST** pass `--cloud-services` with the user's own wording restricted to the supported services from the support-set probe; this only reduces the number of triggered check items — the merge in **Step 5** decides the final report scope
* **MUST** branch on the exit code:
  * `0` → collection completed; record the artifact's absolute path from the log output and continue to **Step 3**
  * non-zero → record the failure reason and continue to **Step 3** — **MUST NOT** abort the workflow

**Step 3: Fetch Config resource compliance results**

Call the [config_compliance_inspection.py](scripts/config_compliance_inspection.py) script to fetch raw resource compliance check results from the Config service, with the following requirements:

* **MUST** run the script with its default command-line options, unless the user specifies different values for them
* **MUST** branch on the exit code:
  * `0` → collection completed; record the artifact's absolute path from the log output and continue to **Step 4**
  * non-zero → record the failure reason and continue to **Step 4** — **MUST NOT** abort the workflow

**Step 4: Fetch SecMaster baseline check results**

Call the [secmaster_baseline_inspection.py](scripts/secmaster_baseline_inspection.py) script to fetch raw baseline check results from SecMaster, with the following requirements:

* **MUST** run the script with its default command-line options — it takes **no region parameter**: the scan scope is the region list built into the script, so **MUST NOT** pass a region, narrow the scan to a region mentioned in the triggering context, or ask the user which region holds the SecMaster instance
* **MUST** branch on the exit code:
  * `0` → at least one instance was inspected; record the artifact's absolute path from the log output and continue to **Step 5**
  * `1` → every verified region was reachable and the account holds no SecMaster instance; record this source as having **no data** and continue to **Step 5**
  * `2` → the scan is incomplete (a verified region failed, or no instance produced results); record the failure reason and continue to **Step 5**
* **MUST NOT** re-run the script or ask the user anything because of a non-zero exit code
* **MUST** read `meta` from the produced artifact so that failed regions and failed instances are recorded in **Step 8**'s Remarks

**Step 5: Convert raw results**

Call the [merge_inspection_results.py](scripts/merge_inspection_results.py) script to convert the raw results of the Config and SecMaster services into the OA inspection result format, and generate the merged data file, with the following requirements:

* Run [merge_inspection_results.py](scripts/merge_inspection_results.py) with `--help` to view its help manual
* **SHALL** Derive `--oa-file` / `--config-file` / `--secmaster-file` from the absolute paths of the artifacts actually produced by **Step 2** through **Step 4**, as recorded in each step's log output
* **WHEN** the run is scoped, **MUST** pass `--cloud-services` with the same value used in **Step 2** — this step is the authoritative scope filter: it drops the records outside the scope and the records whose cloud service is unknown, and records the outcome in `meta.cloud_service_filter`
  * The value **MUST** contain only the services the support-set probe reported as supported; a service missing from the alias table no longer falls back to its own literal code, so passing it would be rejected instead of silently matching nothing
* **MUST** Run the script directly once the parameters are derived — **MUST NOT** ask the user to confirm the command line
* **MUST** branch on the exit code:
  * `0` → continue to **Step 6**
  * non-zero → when the log reports that the cloud service scope matched no record, record the reason and the available service codes it lists, then terminate the workflow — **MUST NOT** re-run as a full-tenant inspection
* **WHEN** a source failed in **Step 2** / **Step 3** / **Step 4** and produced no artifact, **MUST** omit that source's option and still run the merge — the merge treats an omitted source as an empty result set and records it in `meta.sources`; **MUST NOT** fabricate a placeholder file and **MUST NOT** abort the workflow
* **WHEN** **Step 4** exited non-zero (`1` or `2`), **MUST** omit `--secmaster-file` even though the artifact exists — a non-zero exit means the SecMaster data is absent or incomplete, and passing the file would record `meta.sources.secmaster` as `ok` with zero records, hiding the gap; **MUST** only pass `--secmaster-file` when Step 4 exited `0`
* **MUST** read `meta.sources` from the merged output to confirm each source's status (`ok` / `missing` / `unreadable`), and record any non-`ok` status in **Step 8**'s Remarks
* After the merge run, **MUST** review the merge log for `Blacklist filtered out` lines
  * **WHY**: the merge deduplicates Config / SecMaster items against OA via the blacklists under `references/blacklists`; filtered items do not appear in the final report, so without the log the page check items would seem to differ from the report
  * **MUST** Count the filtered-out items per source for the single-line summary in **Step 8** — the final report excludes those Config rules / SecMaster baselines by design

**Step 6: Generate report**

Call the [merge_report_generator.py](scripts/merge_report_generator.py) script to generate the tenant inspection analysis report, with the following requirements:

* Run [merge_report_generator.py](scripts/merge_report_generator.py) with `--help` to view its help manual
* **SHALL** Derive `--input` from the absolute path of the merged JSON produced by **Step 5: Convert raw results**, as recorded in that step's log output
* **MUST** Run the script directly once the parameters are derived — **MUST NOT** ask the user to confirm the command line
* **MUST** Record the absolute path of the timestamped output directory from the generated artifacts listed in the log output — **Step 7** uses it as `--report-dir`
* **WHEN** the run is scoped, the script also writes `merge_inspection_report_<timestamp>_risk_items.json` into the same directory and logs its absolute path — **MUST** record that path for **Step 8**

**Step 7: Archive deliverables and clean up temporary files**

Call the [archive_artifacts.py](scripts/archive_artifacts.py) script to archive this run's final deliverables under the user home directory, then delete the temporary JSON files, with the following requirements:

* Run [archive_artifacts.py](scripts/archive_artifacts.py) with `--help` to view its help manual
* **SHALL** Derive `--report-dir` from the timestamped output directory recorded in **Step 6**'s log output
* **MUST** Run the script directly once the parameter is derived — **MUST NOT** ask the user to confirm the command line
* The archived deliverables are the HTML report, the Excel workbook and, on scoped runs, the risk-item JSON — the archive step matches them itself, so it needs no extra parameter
* **MUST** branch on the exit code:
  * `0` → the deliverables are archived; **MUST** then delete exactly these **absolute paths recorded for this run** in each step's log output — never a pattern, never a directory:
    * `oa_risk_inspection_results_<this run's timestamp>.json` (from Step 2)
    * `config_compliance_inspection_results_<this run's timestamp>.json` (from Step 3)
    * `secmaster_baseline_inspection_results_<this run's timestamp>.json` (from Step 4)
    * `secmaster_baseline_inspection_stats_<this run's timestamp>.json` (from Step 4)
    * `merge_inspection_results_<this run's timestamp>.json` (from Step 5)
  * non-zero → **MUST** leave the unarchived deliverables in place, record the failure reason, skip the deletion phase, and continue to **Step 8** — **MUST NOT** delete an unarchived deliverable and **MUST NOT** abort the workflow
* **MUST NOT** delete the risk-item JSON: it is a deliverable, not a temporary file, and it is never part of the deletion list above
* **MUST NOT** delete the archived deliverables or any file that was not produced by this run; **WHEN** a listed path does not exist (because that source failed), **MUST** skip it — **MUST NOT** widen the deletion scope to compensate
* **MUST NOT** ask the user to confirm the archive or the deletion

**Step 8: Workflow summary**

Summarize the run with the following requirements:

* **MUST** Present the completion status of **Step 1** through **Step 8** in a table, whose header **SHALL** include: No., Step, Status, Remarks
* **MUST** Check the logs of each step's scripts before writing the summary — this information is authoritative
* **WHEN** a source produced no data (its script failed, or **Step 4** exited `1` because the account holds no SecMaster instance), **MUST** mark that step in Remarks as "无数据" (no data) with the reason and state that the final report lacks that source — **MUST NOT** present the missing source as "0 risks"
* **WHEN** **Step 4** exited `0` but `meta.failed_regions` or `meta.failed_instances` is greater than 0, **MUST** list the failed regions and instances in Step 4's Remarks
* **MUST** record the degradation explicitly in the summary table: an OA, Config or SecMaster collection failure **SHALL NOT** abort the workflow — the remaining steps still run and the failure is reported as a failed step with its reason
* **MUST** Describe the final deliverables: list the archive directory's absolute path and the full absolute paths of every archived file (the HTML report, the Excel workbook and, on scoped runs, the risk-item JSON), read from `archive_manifest.json`. **MUST** list the artifacts that **actually exist** after the run, and **MUST NOT** fabricate artifacts
* **WHEN** the archive step exited non-zero, **MUST** list the unarchived deliverables' full absolute paths in the local report directory, mark them as "not archived" with the failure reason, and **MUST NOT** claim they were archived
* **MUST** Summarize the items filtered out by the blacklist during **Step 5: Convert raw results** in a single line carrying the Config and SecMaster counts, read from the `Blacklist filtered out` log lines — **MUST NOT** list them item by item
* **MUST NOT** report per-source collection scope or counts in the summary, and **MUST NOT** list the temporary JSON files deleted in **Step 7**
* **MUST NOT** ask the user to confirm the summary

**Scoped runs — present the risk-item JSON**

**WHEN** the run is scoped and `merge_inspection_report_<timestamp>_risk_items.json` exists, **MUST** present the inspection result from that JSON as the single data source — **MUST NOT** read the numbers back out of the HTML report, and **MUST NOT** only give the file path and leave the user to open it:

* **MUST** present a risk-item table whose columns include the cloud service, dimension, check item name, risk level, source and risk resource count
* **WHEN** `totals.items` ≤ 20 and `totals.resources` ≤ 50, **MUST** expand each item's resource details below the table
* **WHEN** either limit is exceeded, **MUST** present the item-level table only and state the absolute path of the JSON that holds the complete resource details
* **MUST** state the cloud services covered by `services`
* **WHEN** the merge log reports cloud services that matched no record, **MUST** state that those services are outside this report's scope — **MUST NOT** present them as "no risk"
* **WHEN** `totals.items` is `0` and `totals.records` is greater than `0`, **MUST** phrase it as "已匹配 N 条检查记录，未发现风险项" — **MUST NOT** phrase it as "0 风险"
* **MUST** summarize the records excluded because their cloud service is unknown in a single line, using `meta.cloud_service_filter.excluded_unclassified` from the merge log or merged JSON

**WHEN** the run is full-tenant, **MUST NOT** present the risk-item table; the summary stays exactly as before.

## Prerequisites

- Python >= 3.9
- hcloud >= 7.2.2

## References

- [Huawei Cloud Config Service Documentation](https://support.huaweicloud.com/rms/index.html)
- [Huawei Cloud OA Service Documentation](https://support.huaweicloud.com/productdesc-oa/oa_01_0002.html)
- [Huawei Cloud SecMaster Service Documentation](https://support.huaweicloud.com/secmaster/index.html)
- [Huawei Cloud KooCLI Installation](https://support.huaweicloud.com/qs-hcli/hcli_02.html)
- [IAM Authentication Guide](https://support.huaweicloud.com/api-iam/iam_01_0001.html)
- [CLI Installation Guide](references/cli-installation-guide.md) — Local reference: hcloud CLI setup steps
- [IAM Authentication Guide](references/iam-policies.md) — Local reference: AK/SK and region configuration
- [Verification Method](references/verification-method.md) — Local reference: environment and feature verification procedures
- [Acceptance Criteria](references/acceptance-criteria.md) — Local reference: acceptance gate checklist
