---
name: huawei-cloud-cce-env-assessment
description: | 
  A skill for huawei cloud container(CCE) assessment. 
  It automatically collects metrics and configurations from containerized application environments on Huawei Cloud to generate a comprehensive assessment report. 
  Use this when users want to evaluate if their Huawei Cloud applications align with cloud-native best practices and identify areas for improvement. 
Triggers: 应用云原生评估, 华为云容器环境评估, huawei cloud cce assessment, huawei cloud container environment assessment, cloud native assessment.
tags: [huawei-cloud, cloud-native, cce, container, assessment]
---

# Huawei Cloud — CCE ENV Assessment Skill

## Overview

Automatically collects evaluation metrics of the huawei cloud container environment, outputs metric scoring tables by dimension, and generates evaluation reports and improvement suggestions.

---

## Prerequisites
> **Prerequisite check: Huawei Cloud CLI (hcloud) >= 7.2.2 required**
> Run `hcloud version` to verify the version is >= 7.2.2, and `hcloud configure list` to confirm a profile exists.
> If it is not installed or the version is too low, see [references/koocli-installation-guide.md](references/koocli-installation-guide.md) for the installation guide.
```bash
hcloud version
hcloud configure list
```
> **Prerequisite check: Python >= 3.6 required**
> Run `python --version` to verify the version is >= 3.6.0
> If it is not installed or the version is too low, The skill execution is interrupted proactively, and the user is prompted to install Python 3.6 or later.
> If the Python version is 3.6.x, run the following command to upgrade pip to the latest version `pip3 install --user --upgrade 'pip<22'`



## ⚠️ Mandatory Execution Rules

### Rule 1: Step-by-step Confirmation
**After each step, you MUST:**

1. Print the completion status of the current step
2. Show the output produced by that step
3. Every Skill run starts from Step 1 — do NOT skip Step 1 and jump into later steps
4. Strictly follow this Skill's rules and wait for user confirmation after every step
5. Strictly follow the described flow; do not perform extra operations. If anything errors, return the error to the user as-is — do not try to fix it yourself
6. All execution rules take precedence over efficiency

**Do NOT chain multiple steps in a single run!**

### Rule 2: Fixed Directories
**After each step, you MUST:**

1. Save all intermediate files under the `data/` directory

### Rule 3: Permission Issues

1. When you hit a permission problem, try `sudo`. If that does not resolve it, error out and abort the Skill flow

### Rule 4: Anti-skip Check

**Before executing each step, verify that its prerequisites are satisfied:**

| Step | Prerequisite |
|------|--------------|
| Step 2: Environment check | Step 1 is complete; Huawei Cloud AK/SK have been obtained |
| Step 3: Container environment collection | Step 2 is complete with no errors; `data/` and `artifacts/` are emptied |
| Step 4: Metric scoring | Step 3 is complete; `data/cloud-native-collection.md` has been generated |
| Step 5: Report generation | Step 4 is complete; `artifacts/cloud-native-summary.xlsx` has been generated |

### Rule 5: Information Collection Method

1. For every piece of information collected, prefer the Huawei Cloud KooCLI tool (`hcloud` commands)

### Rule 6: Status Tracking
```
📋 Cloud-Native Container Assessment — Status Board
├────────────────────────────────────────────┤
│ Step 1: Configuration       [⏳ In progress]│
│ Step 2: Environment check   [○ Pending]     │
│ Step 3: Information collect [○ Pending]     │
│ Step 4: Metric scoring      [○ Pending]     │
│ Step 5: Report generation   [○ Pending]     │
└────────────────────────────────────────────┘
```

**After each step, update the status board:**

```
📋 Cloud-Native Container Assessment — Status Board
├────────────────────────────────────────────┤
│ Step 1: Configuration       [✅ Done]       │
│ Step 2: Environment check   [✅ Done]       │
│ Step 3: Information collect [✅ Done]       │
│ Step 4: Metric scoring      [✅ Done]       │
│ Step 5: Report generation   [⏳ In progress]│
└────────────────────────────────────────────┘
```

## 🔐 Permission Boundary

### The AI is allowed to:
- Follow the SKILL steps exactly
- Invoke only the scripts specified in the SKILL
- Return errors as-is when problems occur

### The AI is forbidden to:
- Temporarily modify or bypass the workflow
- Switch to an alternative approach (e.g. fall back to Markdown when html fails)
- Modify any script or configuration without user consent
- Perform any operation not explicitly listed in the SKILL

### Handling out-of-bounds operations
Any out-of-bounds operation must stop immediately and wait for user confirmation. Continuing is forbidden.

## Core Workflows

### Step 1: Configuration
Prompt the user for the environment configuration.

| Item | Description | Example |
|------|-------------|---------|
| Huawei Cloud AK/SK | Access Key and Secret Key for Huawei Cloud API | AK/SK = HPUAN3EWCG... / 1Bt5sdDU.. |
| Region | Region where the container cluster lives | region = cn-north-4 |
| Cluster name | CCE cluster name (Step 1 only) | cce_name = dify-cce-cluster |
| Dockerfile source | Source code repository (containing the Dockerfile) | Dockerfile = https://github.com/langgenius/dify |

Once the user supplies the configuration, save the values into environment variables `HWC_AK`, `HWC_SK`, `CCE_Region`, `CCE_NAME`, `Dockerfile_REPO_URL` respectively.

Diamond Gate 1: Get user confirmation before Step 2.

### Step 2: Environment Check
Using the configuration provided in Step 1, verify that the environment is reachable and that local runtime dependencies are present.

1. Use `hcloud` with AK/SK to access the Huawei Cloud CCE environment and confirm it is reachable, If it is not installed or the version is too low, see [references/koocli-installation-guide.md](references/koocli-installation-guide.md) for the installation guide.
2. Verify that the local Python environment is working correctly, Python version requirement is greater than 3.6, If the Python version is 3.6.x, run the following command to upgrade pip to the latest version `pip3 install --user --upgrade 'pip<22'`
3. Check whether the Python dependency library is installed. Go to the references directory. If the Python version is 3.6.x, run the command `python3 -m pip install -r requirements.txt`. If the Python version is later than 3.7, Execute commands using a Python virtual environment `pip3 install -r requirements.txt`.
3. Empty any historical files inside `data/`; if `data/` does not exist, create it
4. Empty any historical files inside `artifacts/`; if `artifacts/` does not exist, create it
5. Once the checks complete, return the result to the user and wait for confirmation on whether to install dependencies or to continue

### Step 3: Container Environment Information Collection
For every metric listed in `references/cloud-native-checklist.xlsx`, collect the corresponding environment information.

1. Every collection run MUST be driven by the actual metric items in `references/cloud-native-checklist.xlsx` and MUST invoke `scripts/collect_all.py` to collect fresh data — do NOT reuse historical or cached data
2. **Acceptance metric**: the metric item being assessed
3. **Quantified target**: the reference standard for that metric
4. **Acceptance method**: how the environment information for that metric is collected
5. During collection, if any required piece of information cannot be obtained, explore alternative ways to retrieve it and ask the user for confirmation
6. Once collection is complete for every metric, fill the collection method (including, but not limited to, Python scripts and executed commands) and the collected data into `templates/cloud-native-assessment-template.md`, write the result to `data/cloud-native-collection.md`, and show it to the user

### Step 4: Metric Scoring

Based on the collection data in `data/cloud-native-collection.md`, score each metric:

1. Compare the collected data against the quantified target to derive an **acceptance verdict** (Fully Satisfied / Mostly Satisfied / Partially Satisfied / Not Satisfied; metrics that cannot be compared are recorded as Not Satisfied; "Not Applicable" and "Not Evaluated" both roll up into Not Satisfied, and the basis field must state that the metric is N/A or Not Evaluated) and a **scoring basis** (describe based on the collected data — include the metric's environment information, the collection method used, and the reason for non-satisfaction)
2. Convert the verdict to a score: Fully Satisfied = 3, Mostly Satisfied = 2, Partially Satisfied = 1, Not Satisfied = 0
3. Invoke `scripts/score_and_excel.py` to produce a fresh scoring sheet, output as Excel containing the columns: number, cloud-native dimension, level, acceptance metric, quantified target, acceptance method, description, acceptance verdict, score, full score, scoring basis. Save to `artifacts/cloud-native-summary.xlsx`

### Step 5: Report Generation

Using the contents of the scoring sheet `artifacts/cloud-native-summary.xlsx`, generate the final assessment report:

1. The final report uses `templates/report_template.md` as its base template
2. The report title is fixed as "Cloud-Native Assessment Report"
3. The report contains 4 chapters; Chapter 1 and Chapter 2 reuse the content of `templates/report_template.md` directly
4. Chapter 3 of the final report is populated from the scoring sheet `artifacts/cloud-native-summary.xlsx`
5. Invoke `scripts/make_charts.py` against the `cloud-native-summary.xlsx` produced in Step 4 to generate a radar chart and a staircase chart

   **Chart generation requirements:**
   - **Radar chart**: group metrics by cloud-native dimension. The score for each dimension = (sum of that dimension's metric scores / sum of that dimension's full scores) × 5. The radar has exactly six dimensions: Service-orientation, Security, Automation, Elasticity, Observability, Resilience. If a metric belongs to multiple dimensions (e.g. metric #1 belongs to both Service-orientation and Automation), it contributes to the scoring of every dimension it belongs to.
   - **Staircase chart**: overall score = (sum of all metric scores / sum of all full scores) × 5. Stage thresholds — score ≤ 1: Traditional; 1 < score ≤ 2: Basic Cloud; 2 < score ≤ 3: Service-Oriented; 3 < score ≤ 4: Automated; score > 4: Intelligent. The chart must visually render as stairs.

6. Place the generated radar chart into report section 3.3.3 and the staircase chart into 3.3.4
7. Replace Chapter 4 of the final report with the actual remediation recommendations
8. Based on the assessment results, output remediation recommendations by P0/P1/P2 priority:
   - **P0**: Not Satisfied (0 pts) — mandatory items
   - **P1**: Partially Satisfied (1 pt) — items to fix
   - **P2**: Mostly Satisfied (2 pts) — recommended improvements
9. Invoke `scripts/make_report_html.py` to generate the final report as a html, written to `artifacts/cloud-native-report.html`

## Core Commands

### Get cluster ID and basic info
```bash
hcloud cce ListClusters --cli-region=cn-north-4
```

### Get cluster kubeconfig certificate
```bash
hcloud cce CreateKubernetesClusterCert \
  --cli-region=cn-north-4 \
  --cluster_id=a5659ec8-55b5........ \
  --duration=1
```

### Get detailed cluster info
```bash
hcloud cce ListClusters --cli-region=cn-north-4
```

### Authentication parameters
| Auth mode | Required | Optional |
|-----------|----------|----------|
| **AKSK** | `--cli-access-key`, `--cli-secret-key` | `--cli-security-token` |
| **Profile** | `--cli-profile` | `--cli-mode`, `--cli-region` |

## Output Format

1. The final report is delivered as a html file
2. The scoring sheet is delivered as an Excel file
3. All output files are saved under the `artifacts/` directory

## Verification

### Post-install verification
1. Version check: `hcloud version` MUST return 7.2.2 or higher
2. Help check: `hcloud --help` MUST list the available services

### Authentication verification
1. Profile check: `hcloud configure list` MUST show the configured profile

## Best Practices

1. Evaluate and analyze the container environment running on Huawei Cloud.
2. Harden the configuration of existing container clusters and modify the cluster configuration based on the optimization suggestions.

## References

- `report_template.md` — Final report template
- `cloud-native-checklist.xlsx` — Description of assessment metrics
- `requirements.txt` — Python dependency library

## Scripts

- `collect_all.py` — Main assessment script; integrates all collection modules
- `make_charts.py` — Chart generation script
- `make_report.py` — Report generation script
- `score_and_excel.py` — Scoring sheet generation script

## Templates

- `report_template.md` — Final report template
- `cloud-native-assessment-template.md` — Data collection template

## Notes

1. Make sure the Huawei Cloud container environment is reachable
2. Make sure the Huawei Cloud credentials are valid and not expired
3. If the Huawei Cloud Koocli tool and Python environment cannot be automatically installed using the skill, it is recommended that users install them manually.
4. Currently only public-network access to the container environment is supported
5. Output may be truncated during execution; clearing historical data and re-running the Skill is recommended in that case
