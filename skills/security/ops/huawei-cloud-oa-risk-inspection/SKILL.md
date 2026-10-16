---
name: huawei-cloud-oa-risk-inspection
description: |
  Huawei Cloud tenant risk inspection SKILL for OA, Config and SecMaster services.
  Use this skill when the user wants to inspect risk from OA, Config and SecMaster services, and generate inspection report in form of HTML and Excel
  Trigger: User mentions "风险巡检", "风险检查", "资源合规"，"基线检查"
tags: [ risk inspection ]
version: 1.0.0
license: MIT
---

# Huawei Cloud OA Service Risk Inspection

## Overview

Fetch tenant resource inspection results from the Huawei Cloud Optimization Advisor (OA), Config and SecMaster services, and generate an inspection analysis report.

## Workflow

Copy the following checklist and track progress:

```markdown
- [ ] Step 1: Environment check
- [ ] Step 2: Fetch OA risk inspection results
- [ ] Step 3: Fetch Config resource compliance results
- [ ] Step 4: Fetch SecMaster baseline check results
- [ ] Step 5: Convert raw results
- [ ] Step 6: Generate report
- [ ] Step 7: Clean up temporary files
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

* Run [oa_risk_inspection.py](scripts/oa_risk_inspection.py) with `--help` to view its help manual
* Use the `question` tool to ask the user how to configure the command-line parameters for running [oa_risk_inspection.py](scripts/oa_risk_inspection.py)
  * **MUST** List the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **MUST** Have the user provide the necessary command-line parameter values, otherwise the script cannot run
  * **MUST** Ask the user to confirm the parameter values for **this** step's script. **MUST NOT** reuse or carry over answers from previous steps without explicit user confirmation for this step

**Step 3: Fetch Config resource compliance results**

Call the [config_compliance_inspection.py](scripts/config_compliance_inspection.py) script to fetch raw resource compliance check results from the Config service, with the following requirements:

* Run [config_compliance_inspection.py](scripts/config_compliance_inspection.py) with `--help` to view its help manual
* Use the `question` tool to ask the user how to configure the command-line parameters for running [config_compliance_inspection.py](scripts/config_compliance_inspection.py)
  * **MUST** List the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **MUST** Have the user provide the necessary command-line parameter values, otherwise the script cannot run
  * **MUST** Ask the user to confirm the parameter values for **this** step's script. **MUST NOT** reuse or carry over answers from previous steps without explicit user confirmation for this step

**Step 4: Fetch SecMaster baseline check results**

Call the [secmaster_baseline_inspection.py](scripts/secmaster_baseline_inspection.py) script to fetch raw baseline check results from SecMaster, with the following requirements:

* Run [secmaster_baseline_inspection.py](scripts/secmaster_baseline_inspection.py) with `--help` to view its help manual
* Use the `question` tool to ask the user how to configure the command-line parameters for running [secmaster_baseline_inspection.py](scripts/secmaster_baseline_inspection.py)
  * **MUST** List the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **MUST** Have the user provide the necessary command-line parameter values, otherwise the script cannot run
  * **MUST** Ask the user to confirm the parameter values for **this** step's script, especially `--region_id`. **MUST NOT** silently reuse the region ID given in **Step 3** (or any answer from a previous step) — ask the user to confirm it again for this step even when the value is identical

**Step 5: Convert raw results**

Call the [merge_inspection_results.py](scripts/merge_inspection_results.py) script to convert the raw results of the Config and SecMaster services into the OA inspection result format, and generate the merged data file, with the following requirements:

* Run [merge_inspection_results.py](scripts/merge_inspection_results.py) with `--help` to view its help manual
* Use the `question` tool to ask the user how to configure the command-line parameters for running [merge_inspection_results.py](scripts/merge_inspection_results.py)
  * **MUST** List the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **SHALL** Based on the outputs of **Step 2: Fetch OA risk inspection results** through **Step 4: Fetch SecMaster baseline check results**, prepare the command-line parameters for [merge_inspection_results.py](scripts/merge_inspection_results.py), and have the user confirm them
  * **MUST** Show the user the complete prepared command line and request confirmation before running, even when parameter values match a previous step
* After the merge run, **MUST** review the merge log for `Blacklist filtered out` lines
  * **WHY**: the merge deduplicates Config / SecMaster items against OA via the blacklists under `references/blacklists`; filtered items do not appear in the final report, so without the log the page check items would seem to differ from the report
  * **MUST** Record the filtered-out items (name + status + blacklist reason) for the workflow summary in **Step 8**, listing them as the reason the final report excludes those Config rules / SecMaster baselines

**Step 6: Generate report**

Call the [merge_report_generator.py](scripts/merge_report_generator.py) script to generate the tenant inspection analysis report, with the following requirements:

* Run [merge_report_generator.py](scripts/merge_report_generator.py) with `--help` to view its help manual
* Use the `question` tool to ask the user how to configure the command-line parameters for running [merge_report_generator.py](scripts/merge_report_generator.py)
  * **MUST** List the command-line parameter details, including: parameter name, required/optional, default value, parameter description, etc.
  * **SHALL** Based on the output of **Step 5: Convert raw results**, prepare the command-line parameters for [merge_report_generator.py](scripts/merge_report_generator.py), and have the user confirm them
  * **MUST** Show the user the complete prepared command line and request confirmation before running, even when parameter values match a previous step

**Step 7: Clean up temporary files**

Delete the temporary JSON files produced by **Step 2: Fetch OA risk inspection results** through **Step 5: Convert raw results**, with the following requirements:

* **MUST** Delete the following temporary JSON files (the 5 files produced in Steps 2-5):
  * `oa_risk_inspection_results_<timestamp>.json` (from Step 2)
  * `config_compliance_inspection_results_<timestamp>.json` (from Step 3)
  * `secmaster_baseline_inspection_results_<timestamp>.json` (from Step 4)
  * `secmaster_baseline_inspection_stats_<timestamp>.json` (from Step 4)
  * `merge_inspection_results_<timestamp>.json` (from Step 5)
* **MUST NOT** delete the final report artifacts (HTML and Excel) generated in **Step 6: Generate report**
* **MUST** List the full absolute paths of all deleted files in the workflow summary (Step 8)

**Step 8: Workflow summary**

Summarize the completion status of the workflow steps from **Step 1: Environment check** through **Step 8: Workflow summary**, with the following requirements:

* **MUST** Present the completion status in a table, whose header **SHALL** include: No., Step, Status, Remarks
* **MUST** Describe the final artifacts: list the full absolute paths of all files generated in **Step 6: Generate report**. **MUST** list the artifacts that **actually exist** after the run, and **MUST NOT** fabricate artifacts
* **MUST** List the full absolute paths of all temporary JSON files deleted in **Step 7: Clean up temporary files**
* **MUST** Check the logs of each step's scripts before writing the summary — this information is authoritative
* **MUST** List the items filtered out by the blacklist during **Step 5: Convert raw results**, read from the `Blacklist filtered out` log lines (item name + status + blacklist reason)
  * **SHALL** Present them as a separate "黑名单过滤项" (Blacklist-filtered items) row or sub-section in the summary table
  * **WHY**: the final report intentionally excludes these Config rules / SecMaster baselines; listing them lets the user reconcile page check items with the report and confirms the difference is by design, not a defect

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
