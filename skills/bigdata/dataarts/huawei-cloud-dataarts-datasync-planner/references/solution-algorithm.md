# Solution Design Algorithm and Pipeline Topology Templates

> This document is extracted from SKILL.md Phase 4 and defines the design algorithm and topology templates for Huawei Cloud-side sync solutions.

## 1. Solution Design Algorithm (7-Step Method)

```
Input: pipeline (classified + product matched)
Output: solution = {topology, config, prerequisites, notes, alternatives}

Step1: Determine integration mode → determine product candidate set
  mode = pipeline.classification.result
  candidates = product_selection_decision_tree(mode, source, target)

Step2: Read/write matrix validation → filter unsupported products
  FOR each product in candidates:
    check = read_write_validation(source, target, product)
    IF NOT check.matrix_check:
      product.constraints += check.constraints
      mark as unsupported but retain (annotate constraint)

Step3: Sort candidate products by priority
  Sort criteria: 1) matrix check ✓ 2) optimal latency 3) lowest complexity
  primary = candidates[0], alternatives = candidates[1:3]

Step4: Design pipeline topology
  topology = topology_template(mode, source, target, primary_product)

Step5: Annotate constraint conditions
  constraints = constraint_list(source, target, product)
  (Kerberos/decoupled storage-compute/Ranger/version/network/permissions)

Step6: Instance spec derivation (mandatory, see instance-specs.md Section 3 selection algorithm)
  IF mode == offline:
    spec = CDM_spec_selection(single_batch_volume V, migration_window T, concurrent_jobs N, dedicated_line_bandwidth)
    → cdm.large(base 0.8Gbps/concurrency 16) / cdm.xlarge(base 4Gbps/concurrency 32) / cdm.4xlarge(base 36Gbps/concurrency 128)
    → Note: cross-IDC scenario actual throughput capped by dedicated line bandwidth
  ELIF mode == real-time:
    spec = migration_resource_group_selection(real-time_task_count M, max_tables_per_task, HA_requirement)
    → Validate: single task ≤ 200 tables (split if exceeded), single job minimum 2CU
    → Small 16CU(7 jobs, no HA, test only) / Medium 64CU(32) / Large 96CU(48) / Extra Large 128CU(64)
    → Spec cannot be changed after creation, production recommended one tier higher for reserve

Step7: Output solution
  solution.topology = topology
  solution.config = config_recommendations(mode, volume, frequency) + spec conclusion(spec + selection rationale, format see instance-specs.md Section 5)
  solution.prerequisites = prerequisites(source, target)
  solution.notes = constraints + notes + spec hard constraints(migration single job ≤ 200 tables/spec cannot be changed/network mask ≤ 19 bits)
```

## 2. Pipeline Topology Templates

### Offline Integration Topology

```
# Template 1: DB → Data Warehouse/Hadoop (offline jobs)
Source DB → [Network: VPN/dedicated line/DCS] → DataArts Studio offline jobs → Target (MRS Hive/DWS/DLI)

# Template 2: DB → DB (CDM whole-database migration)
Source DB → [Network] → CDM cluster → Target DB

# Template 3: File → Lake (CDM table/file migration)
FTP/SFTP → [Network] → CDM cluster → MRS HDFS/OBS

# Template 4: OBS → OBS (OMS)
Source OBS → OMS → Target OBS

# Template 5: Any source → Any target (offline jobs, read-write separation)
Source → [Network] → DataArts Studio offline jobs → Target
```

### Real-time Integration Topology

```
# Template 6a: DB → DB (DRS, between OLTP or to Kafka)
Source DB → [Network: VPN/dedicated line] → DRS → Target DB/Kafka

# Template 6b: DB → Data Warehouse (DataArts Studio real-time jobs migration)
#         —— Only official channel for DWS real-time ingestion, DRS to DWS discontinued (2025-08-31)
Source DB → [Network: VPN/dedicated line] → DataArts Studio real-time jobs (migration) → DWS

# Template 7: Kafka → Real-time Data Warehouse (DLI-Flink)
Source Kafka → [Network] → DLI-Flink → Target (DLI/Kafka/DB/HBase/ES)

# Template 8: DB CDC → Real-time Data Warehouse (DLI-Flink CDC)
Source DB → [Network] → DLI-Flink CDC → Target (DLI/Kafka/DB)

# Template 9: Local Collection → Cloud (DIS + Flink)
Local data → DIS Agent → DIS → DLI-Flink → Target

# Template 10: Message Bus → Multi-target (DMS Kafka + Flink)
Source → DMS Kafka → DLI-Flink → Multi-target (DB/data warehouse/cache/search)
```

### Near Real-time Topology

```
# Template 11: DB → DB (DRS, satisfies minutes-level)
Source DB → DRS → Target DB

# Template 12: DB → Data Warehouse (migration + CDM/offline jobs, hybrid)
Source DB → DataArts Studio real-time jobs (migration) (full initialization + real-time incremental) → DWS
Source DB → CDM / offline jobs (full initialization/batch fallback) → DWS
```

## 3. Configuration Recommendation Templates

| Integration Mode | Sync Mode | Scheduling Config | Spec Recommendation |
|-----------------|-----------|-------------------|---------------------|
| Offline | Full | Scheduled (daily/hourly) | CDM instance package spec per instance-specs.md Section 3.1: single batch volume + migration window → base bandwidth validation, concurrent job count validation (16/32/128), dedicated line bandwidth cap; experience: <100GB/4h → cdm.large, 500GB~2TB → cdm.xlarge, >2TB or concurrency>32 → cdm.4xlarge |
| Offline | Full+incremental | Scheduled + incremental extraction | Full uses CDM, incremental uses SQL condition filter (watermark/timestamp); spec derived from full batch peak |
| Offline | Whole-database | One-time or low-freq | CDM whole-database migration, configure concurrency by table count; concurrent job count constrained by cluster limit (16/32/128) |
| Real-time | CDC | Continuous running | Target DB/Kafka: DRS by source spec; Target DWS: migration (DataArts real-time jobs, requires region enabled + whitelist); DLI-Flink by CU (data volume/computation complexity) |
| Real-time | Streaming append | Continuous running | DLI-Flink by throughput config CU, Kafka by partition count config instances |

### 3.1 migration Resource Group Instance Package Specs (Mandatory check for real-time ingestion, see instance-specs.md)

| Spec | CU | Job Limit | HA | Scenario |
|------|----|-----------|----|----------|
| Small | 16 | 7 | ❌ | Test only, not recommended for production |
| Medium | 64 | 32 | ✓ | Common production starting |
| Large | 96 | 48 | ✓ | — |
| Extra Large | 128 | 64 | ✓ | — |

Hard constraints: single job minimum 2CU; single job ≤ 200 tables (split if exceeded and re-select tier by new job count); **spec cannot be changed after creation**; network segment no overlap with source/target and mask ≤ 19 bits; region limited to Beijing-4/Shanghai-1/Guangzhou + whitelist.

## 4. Prerequisites Templates

| Condition Type | Description |
|----------------|-------------|
| Network connectivity | Source and Huawei Cloud need VPN/dedicated line/public internet connectivity; target needs VPC internal connectivity |
| Permission requirements | Source: read permission; Target: write permission; Network: security group rules |
| Version requirements | Refer to version constraints in source-target-matrix.md |
| Kerberos | MRS cluster needs Kerberos disabled or compatible encryption type |
| Decoupled storage-compute | If MRS uses decoupled storage-compute, confirm target component supports (only Hive/Hudi) |
| CDM cluster | Need to create CDM cluster (prerequisite for offline jobs/CDM jobs); spec cdm.large/xlarge/4xlarge per instance-specs.md Section 3.1 (single batch volume/window/concurrency/dedicated line bandwidth); basic package CDM for test only |
| DRS task | Need to create DRS sync task (prerequisite for real-time sync) |
| migration resource group | Need to purchase DataArts Studio data integration resource group/instance package (prerequisite for real-time ingestion to DWS); spec per instance-specs.md, survey needs to confirm real-time task count/max tables per task/HA requirement; hard constraints: single job ≤ 200 tables, spec cannot be changed after creation, network mask ≤ 19 bits and no overlap with source/target |
| Flink queue | Need to create DLI-Flink queue (prerequisite for streaming jobs) |

## 5. Common Scenario Solutions

### Scenario A: Oracle → Hive Offline Full+Incremental (DataX)

```
Pipeline: Oracle 12c (self-built) → Hive 3.1 (CDH), daily 2:00, 50GB, full+incremental
Classification: Offline integration (latency hours + scheduled)
Product: DataArts Studio offline jobs (Oracle ✓ read, MRS Hive ✓ write)
Topology: Oracle → [dedicated line] → DataArts Studio offline jobs → MRS Hive
Config: Full job (daily 2:00) + incremental job (filter by timestamp, daily 2:30)
Spec: Instance package CDM (cdm.large, base 0.8Gbps: single batch 50GB/2h window needs 0.1Gbps with redundancy; concurrency 2 < 16)
Constraints: MRS Hive Kerberos encryption type must be aes256-sha1,aes128-sha1
Alternative: CDM jobs (Oracle → MRS Hive table/file migration)
```

### Scenario B: MySQL → Kafka → Flink → ClickHouse Real-time CDC

```
Pipeline: MySQL 8.0 → Kafka 2.4 → Flink 1.13 → ClickHouse 21.3, CDC, seconds
Classification: Real-time integration (latency seconds + event-driven CDC)
Product: DMS Kafka + DLI-Flink (MySQL JDBC CDC → ClickHouse)
Topology: MySQL → [dedicated line] → DLI-Flink CDC → DMS Kafka (optional) → DLI-Flink → MRS ClickHouse
Config: Flink CDC connector reads MySQL binlog → writes ClickHouse
Constraints: Need to enable MySQL binlog; DLI-Flink queue by CU (recommended 8CU starting)
Alternative: DRS (if only MySQL → ClickHouse without streaming computation, but DRS does not directly support ClickHouse target)
```

### Scenario C: PostgreSQL → DWS Seconds Latency

```
Pipeline: PostgreSQL 12 → DWS, seconds latency, incremental CDC
Classification: Real-time integration (latency seconds)
Product: DataArts Studio real-time jobs (migration) (primary) —— DRS to DWS pipeline discontinued 2025-08-31, cannot use DRS
Topology: PostgreSQL → [dedicated line] → DataArts Studio real-time jobs (migration) → DWS
Config: migration real-time sync task (full initialization + incremental CDC), source wal_level=logical, target DWS 8.1.3/8.2.0+ (excluding 3.0)
Spec: Instance package migration resource group (Medium 64CU: task count per survey, single task ≤ 200 tables, HA → exclude Small 16CU; spec cannot be changed after creation, need reserve); network mask ≤ 19 bits and no overlap with source
Constraints: Need region enabled for real-time jobs + whitelist; only syncs tables with primary keys (views/triggers/stored procedures not synced)
Alternative: CDM/offline jobs high-freq incremental (minutes, if migration does not cover this source) / DLI-Flink CDC (if streaming transformation needed)
```

### Scenario D: FTP → OBS File Ingestion

```
Pipeline: FTP → OBS, hourly 1x, 10GB/time, binary files
Classification: Offline integration (latency hours + scheduled)
Product: DataArts Studio CDM jobs (FTP ✓ read, OBS ✓ write)
Topology: FTP → [public internet/dedicated line] → CDM cluster → OBS
Config: CDM table/file migration, hourly scheduling, binary mode
Constraints: FTP → OBS only supports binary files
Alternative: obsutil tool (if only FTP → OBS, recommend directly using obsutil)
```

### Scenario E: Multi-pipeline Mixed (5 pipelines unified planning)

```
Pipeline 1: Oracle → Hive, offline, daily, 50GB → DataArts offline jobs
Pipeline 2: MySQL → Kafka, real-time CDC, seconds → DRS (MySQL → Kafka)
Pipeline 3: PG → ES, near real-time, 5 minutes → DRS (PG → ES not supported, use offline jobs 5-minute scheduling)
Pipeline 4: FTP → OBS, offline, hourly, 10GB → CDM jobs
Pipeline 5: Kafka → ClickHouse, real-time, seconds → DLI-Flink

Shared: Pipeline 1+4 share 1 CDM cluster; Pipeline 2+5 share 1 DLI-Flink queue
```
