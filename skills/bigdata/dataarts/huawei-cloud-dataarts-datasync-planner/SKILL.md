---
name: huawei-cloud-dataarts-datasync-planner
description: |
  Huawei Cloud data sync pipeline planning. Identifies existing pipelines, distinguishes real-time/offline, matches DataArts Studio/DRS/DLI-Flink/DIS products, outputs selection plan and multi-sheet Excel report.
  Automatically classifies integration mode, validates read/write matrix, derives instance spec, and generates structured report.
  Applicable to data sync pipeline planning, data integration product selection, data ingestion, data-to-cloud migration, and real-time/offline sync solution design.
  Trigger words: "data sync", "data integration", "data migration pipeline", "sync pipeline planning", "DataArts Studio", "CDM migration", "DRS data replication", "DLI-Flink", "real-time sync", "offline sync", "data ingestion", "data to cloud", "data sync solution", "data integration planning", "batch integration", "real-time integration", "数据同步", "数据集成", "数据迁移链路", "同步链路规划", "CDM迁移", "DRS数据复制", "实时同步", "离线同步", "数据入湖", "数据上云", "数据同步方案", "数据集成规划", "批量集成", "实时集成"
tags:
  - huawei-cloud
  - data-sync
  - product-selection
version: "1.0.0"
license: MIT
---

# Huawei Cloud Data Sync Pipeline Planning and Product Matching

## Trigger Words

**Chinese triggers:** "数据同步", "数据集成", "数据迁移链路", "同步链路规划", "DataArts Studio", "CDM迁移", "DRS数据复制", "DLI-Flink", "实时同步", "离线同步", "数据入湖", "数据上云", "数据同步方案", "数据集成规划", "批量集成", "实时集成"

**English triggers:** "data sync", "data integration", "data migration pipeline", "sync pipeline planning", "DataArts Studio", "CDM migration", "DRS data replication", "DLI-Flink", "real-time sync", "offline sync", "data ingestion", "data to cloud", "data sync solution", "data integration planning", "batch integration", "real-time integration"

## Overview

Identify the user's existing data sync pipelines (source, target, sync mode, data volume, frequency), distinguish **real-time integration** from **batch offline integration**, match Huawei Cloud data sync product capabilities (DataArts Studio/DRS/DLI-Flink/DIS, etc.), and output a complete Huawei Cloud-side data sync pipeline plan and product selection report.

⚠️ **DRS no longer supports new pipelines with GaussDB(DWS)/CSS(ES) as target database** (stopped sale 2025-08-31). All **sync to DWS goes through DataArts Studio data integration**: offline batch uses CDM/offline jobs, real-time incremental uses migration.

## Prerequisites

- Python3 + openpyxl (`pip install openpyxl`) — for generating multi-sheet Excel report
- Huawei Cloud DataArts Studio documentation access — offline job/CDM job data source support status
- Huawei Cloud DRS documentation access — real-time data replication capabilities


## Workflow

| Phase | Content | Output |
|-------|---------|--------|
| Phase 1 | Pipeline Identification: collect source, target, sync mode, data volume, frequency, latency requirement of existing data sync pipelines | Pipeline list |
| Phase 2 | Real-time/Offline Classification: determine whether each pipeline is real-time or offline based on latency requirement, trigger mode, data characteristics | Classification result + rationale |
| Phase 3 | Product Capability Matching: match Huawei Cloud products based on source/target and integration mode | Product selection + read/write matrix validation |
| Phase 4 | Solution Design: design Huawei Cloud-side sync solution for each pipeline | Sync solution |
| Phase 5 | Report Output: structured Markdown report | Markdown format report |
| Phase 6 | Excel Report Generation: multi-sheet report | DataSync_Pipeline_Report.xlsx |

### Phase 1: Pipeline Identification

Collect complete information of the user's existing data sync pipelines. Each pipeline requires: source data source type + **exact version number** + deployment mode, target data source, sync mode, **daily sync data volume**, sync frequency, latency requirement, existing tool. Spec derivation mandatory questions: offline pipeline (single batch data volume/migration window/concurrency/network bandwidth), real-time pipeline (task count/max tables per task/HA requirement), general (usage period).

> Spec derivation survey question checklist: see [references/instance-specs.md](references/instance-specs.md) Section 5

### Phase 2: Real-time/Offline Classification

Determine whether the pipeline belongs to real-time or offline integration based on pipeline characteristics. Core classification criteria: latency requirement (seconds → real-time, hours → offline), trigger mode (event-driven → real-time, scheduled → offline), sync mode, frequency. 5-step classification algorithm.

> Detailed classification algorithm and decision tree: see [references/pipeline-classification.md](references/pipeline-classification.md)

### Phase 3: Product Capability Matching

Match Huawei Cloud products based on source/target data source types and integration mode. Product matrix includes: DataArts Studio offline jobs/CDM jobs/real-time jobs (migration), DRS, DLI-Flink, DIS, DMS Kafka, OMS. After matching, must validate source read capability and target write capability (including version feasibility check).

**Sync to DWS uniformly uses DataArts Studio**: offline uses CDM/offline jobs, real-time uses migration. DRS does not include DWS as target.

> Complete product capability matrix and selection decision tree: see [references/product-mapping.md](references/product-mapping.md)
> Read/write capability matrix: see [references/source-target-matrix.md](references/source-target-matrix.md)

### Phase 4: Solution Design

Design Huawei Cloud-side sync solution for each pipeline, including: recommended product + alternatives, pipeline topology, integration mode, configuration recommendations (including instance spec conclusion), prerequisites, constraints. 7-step solution design algorithm includes instance spec derivation (CDM spec/migration CU tier).

> Solution design algorithm: see [references/solution-algorithm.md](references/solution-algorithm.md)
> Instance spec selection algorithm: see [references/instance-specs.md](references/instance-specs.md)

### Phase 5: Report Output

Generate structured Markdown report with 5 sections: pipeline identification summary, classification results, product matching results, Huawei Cloud-side sync solution, decision summary.

### Phase 6: Excel Report Generation

Agent writes the Phase 1-4 investigation results into `report.json` (schema see [references/md-report-template.md](references/md-report-template.md) Section 4), then runs the script to generate a multi-sheet Excel report. The report contains 3 sheets: source data pipelines (源端数据链路), Huawei Cloud sync pipelines (华为云侧同步链路), and no-direct-match solutions (无法直接对标方案, generated on demand only when pipelines that cannot be directly matched exist).

> Complete MD document template: see [references/md-report-template.md](references/md-report-template.md)
> Python script implementation: see [scripts/generate_datasync_report.py](scripts/generate_datasync_report.py)

## Output Rules

- **MD document 3 major sections**: existing data pipeline topology diagram + existing pipeline description (data source location/real-time or offline/frequency/data volume) + replacement solution topology diagram and description (directly use CDM/migration/DRS product names, do not repeat DataArts Studio)
- **Solution type annotation**: each solution must be annotated: direct match / Huawei Cloud feasible solution (indirect) / third-party software solution
- **DWS target uniformly goes through DataArts Studio**: offline uses CDM/offline jobs, real-time uses migration. Prohibit recommending DRS (this pipeline stopped sale 2025-08-31)
- **Product name usage convention**: directly use CDM, migration, offline jobs, DRS and other product/capability names, do not repeatedly mention DataArts Studio
- **Read/write matrix validation must be executed**: after matching product, must validate source read capability and target write capability; when not supported, annotate and recommend alternative
- **Constraint conditions must be annotated**: Kerberos restrictions, decoupled storage-compute restrictions, version requirements, migration spec constraints must be explicitly annotated
- **Solution must output instance spec conclusion**: CDM: cdm.large/xlarge/4xlarge; migration: 16/64/96/128 CU + selection rationale
- **Source version is required**: must confirm exact source database version number as feasibility judgment basis
- **Daily sync data volume is required**: both real-time and offline scenarios must confirm; affects product selection and spec configuration
- **Latency requirement is classification key**: must proactively ask when user does not specify
- **Functional boundary**: data sync full-process planning (pipeline identification → classification → product matching → solution design → report), excludes sync implementation and operations

## Core Commands

### Report Generation

```bash
# Generate report from investigation results (recommended)
python scripts/generate_datasync_report.py --input report.json

# Generate demo report with built-in example data (no --input)
python scripts/generate_datasync_report.py
```

File naming: `DataSync_Pipeline_Report_<YYYYMMDD>.xlsx`

## Parameter Confirmation

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Source data source type + version + deployment | Required | Exact version number as feasibility judgment basis | N/A |
| Target data source | Required | Target end data source type | N/A |
| Sync mode | Required | Full/incremental/CDC/streaming | N/A |
| Daily sync data volume | Required | Affects product selection and spec configuration | N/A |
| Sync frequency | Required | Continuous/hourly/daily, etc. | N/A |
| Latency requirement | Required | Key basis for real-time/offline classification; must proactively ask when not specified | N/A |
| Existing tool | Required | Current sync tool (DataX/Canal/Kettle, etc.) | N/A |
| Single batch data volume | Conditional | Offline pipeline spec derivation | N/A |
| Migration window | Conditional | Offline pipeline spec derivation | N/A |
| Concurrency | Conditional | Offline pipeline spec derivation | N/A |
| Network bandwidth | Conditional | Offline pipeline spec derivation | N/A |
| Real-time task count | Conditional | Real-time pipeline spec derivation | N/A |
| Max tables per task | Conditional | Real-time pipeline spec derivation | N/A |
| HA requirement | Conditional | Real-time pipeline spec derivation | N/A |
| Usage period | Optional | General spec derivation | N/A |

## Notes

1. **Real-time vs offline core classification criterion is latency requirement**: seconds/milliseconds → real-time, hours/days → offline, minutes require combining trigger mode for comprehensive judgment
2. **DRS suitable for DB→DB (between OLTP) real-time sync**: supports real-time replication between relational databases such as MySQL/PG/Oracle/SQL Server, seconds-level latency. **DRS does not support DWS target pipeline (stopped sale 2025-08-31)**
3. **DLI-Flink suitable for streaming ETL and real-time data warehouse**: supports Kafka/DIS and other sources, milliseconds to seconds latency
4. **DataArts Studio offline jobs are new architecture**: read-write separation, arbitrary combination, more flexible than traditional CDM, recommended first for offline scenarios
5. **DataArts Studio CDM jobs are traditional architecture**: table/file migration, whole-database migration, good compatibility but poor flexibility
6. **Read/write matrix validation is a mandatory step**: after matching product, must confirm source supports read, target supports write
7. **Kerberos restriction**: MRS cluster Kerberos encryption type "aes256-sha2,aes128-sha2" is not supported by CDM
8. **Decoupled storage-compute restriction**: CDM only supports MRS Hive and MRS Hudi for decoupled storage-compute scenarios
9. **Ranger restriction**: CDM only supports MRS Hive for Ranger scenarios
10. **OBS-to-OBS migration recommends OMS**: object storage migration between each other uses OMS instead of CDM
11. **Self-built Doris/StarRocks and other MPP analytical databases ≠ relational database source**: do not apply MySQL→DWS pipeline just because Doris is MySQL-protocol compatible. Self-built Doris→DWS has no official direct path
12. **Instance spec constraints (verified 2026-09-10)**: CDM: cdm.large (8 cores 16G)/xlarge (16 cores 32G)/4xlarge (64 cores 128G); migration: 16CU (7 jobs, no HA)/64CU (32 jobs)/96CU (48 jobs)/128CU (64 jobs); single job minimum 2CU, maximum 200 tables; spec cannot be changed after creation. Complete specs see references/instance-specs.md
13. **Product capability data source**: DataArts Studio <https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_1457.html> ; CDM <https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_1630.html> . Retrieved: 2026-08-26
14. **Multi-pipeline unified planning**: multiple pipelines should be analyzed together to identify shareable products

## References

| Document | Description |
|----------|-------------|
| [Pipeline Classification](references/pipeline-classification.md) | Real-time/offline classification algorithm and decision tree |
| [Product Mapping](references/product-mapping.md) | Huawei Cloud product capability matrix and selection decision tree |
| [Source-Target Matrix](references/source-target-matrix.md) | Data source read/write capability matrix (30+ data sources) |
| [Solution Algorithm](references/solution-algorithm.md) | Solution design algorithm and pipeline topology templates |
| [Instance Specs](references/instance-specs.md) | Instance spec constraints and spec selection algorithm |
| [MD Report Template](references/md-report-template.md) | MD report template and data structure |
| [IAM Policies](references/iam-policies.md) | IAM permission requirements (no API permissions needed for this planning skill) |
| [Verification Methods](references/verification-method.md) | Output verification and validation methods |

## Code Structure

```text
scripts/
└── generate_datasync_report.py          # Excel report generation (multi-sheet: 源端数据链路/华为云侧同步链路/无法直接对标方案)
references/
├── iam-policies.md                      # IAM permission requirements (no API permissions needed)
├── instance-specs.md                    # Instance spec constraints and selection algorithm
├── md-report-template.md                # MD report template and data structure
├── pipeline-classification.md           # Real-time/offline classification algorithm and decision tree
├── product-mapping.md                   # Huawei Cloud product capability matrix and selection decision tree
├── solution-algorithm.md                # Solution design algorithm and pipeline topology templates
├── source-target-matrix.md              # Data source read/write capability matrix
└── verification-method.md               # Output verification and validation methods
```

## Verification

- Execute `python scripts/generate_datasync_report.py --input report.json` to generate report; confirm multi-sheet Excel file output (源端数据链路/华为云侧同步链路/无法直接对标方案)
- Verify each pipeline has completed real-time/offline classification with clear rationale (latency requirement + trigger mode)
- Confirm read/write matrix validation has been executed: after matching product, validate source read capability and target write capability
- Check DWS target solutions uniformly use DataArts Studio (not DRS)

## Best Practices

- Latency requirement is the core criterion for real-time/offline classification: seconds/milliseconds → real-time, hours/days → offline
- Sync to DWS uniformly goes through DataArts Studio: offline uses CDM/offline jobs, real-time uses migration; prohibit recommending DRS
- Source database exact version number is required as feasibility judgment basis
- Multiple pipelines should be analyzed together to identify shareable products and optimize resources
- Instance spec cannot be changed after creation; carefully evaluate concurrency and table count requirements during selection

## Edge Cases

- **Kerberos encryption type restriction**: MRS cluster Kerberos encryption type "aes256-sha2,aes128-sha2" is not supported by CDM; need to downgrade to other encryption types or switch to DataArts Studio offline jobs
- **Decoupled storage-compute scenario restriction**: CDM only supports decoupled storage-compute for MRS Hive and MRS Hudi; other components (such as Spark/HBase) are not supported
- **Ranger permission restriction**: CDM only supports Ranger for MRS Hive; other components do not support Ranger authentication
- **OBS-to-OBS migration**: object storage migration between each other should use OMS instead of CDM; CDM is suitable for structured data migration
- **Self-built MPP database**: self-built Doris/StarRocks and other MPP analytical databases are not relational database sources; even if Doris is MySQL-protocol compatible, MySQL→DWS pipeline cannot be applied
- **Paimon and other emerging data lake formats**: CDM/offline jobs do not support direct read/write of Paimon format; need to read via DLI Spark or query via StarRocks External Catalog zero-copy
- **DRS target restriction**: DRS no longer supports new pipelines with GaussDB(DWS)/CSS(ES) as target database (stopped sale 2025-08-31); sync to DWS uniformly goes through DataArts Studio
- **Read/write matrix uncovered format**: when encountering data formats not listed in the read/write matrix, declare not in known matrix and recommend closest alternative; do not repeatedly search to confirm
- **Instance spec cannot be changed**: CDM and migration specs cannot be modified after creation; fully evaluate concurrency and table count requirements during selection
