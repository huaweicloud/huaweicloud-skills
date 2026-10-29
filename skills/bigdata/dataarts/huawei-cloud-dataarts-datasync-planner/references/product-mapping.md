# Huawei Cloud Product Capability Matrix and Selection Decision Tree

> This document is extracted from SKILL.md Phase 3 and defines Huawei Cloud data sync product capabilities and selection rules.

## 1. Huawei Cloud Data Sync Product Overview

| Product | Integration Mode | Typical Scenario | Latency | Documentation |
|---------|-----------------|------------------|---------|---------------|
| **DataArts Studio offline jobs** | Batch offline | Data ingestion, data to cloud, ETL, cross-source sync | Minutes~Hours | [Offline job data sources](https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_1457.html) |
| **DataArts Studio CDM jobs** | Batch offline | Table/file migration, whole-database migration | Minutes~Hours | [CDM data sources](https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_1630.html) |
| **DataArts Studio real-time jobs (migration)** | Real-time incremental | DB/streaming → data warehouse/lake real-time ingestion, whole-database/sharded-database sync | Seconds | [DataArts real-time jobs](https://support.huaweicloud.com/usermanual-dataartsstudio/dataartsstudio_01_1601.html) |
| **DRS Data Replication Service** | Real-time/batch | DB (between OLTP) real-time sync, disaster recovery, DB migration | Seconds | [DRS product](https://support.huaweicloud.com/product-drs.html) |
| **DLI-Flink** | Real-time streaming | Streaming ETL, real-time data warehouse, CEP | Milliseconds~Seconds | [DLI-Flink](https://support.huaweicloud.com/usermanual-dli/dli_01_0438.html) |
| **DIS Data Ingestion Service** | Real-time collection | Data collection to cloud, log collection | Seconds | [DIS product](https://support.huaweicloud.com/product-dis.html) |
| **DMS Kafka** | Message middleware | Real-time message bus, async decoupling | Milliseconds | [DMS Kafka](https://support.huaweicloud.com/product-dms.html) |
| **OMS Object Migration Service** | Batch one-time | OBS-to-OBS migration, local → OBS | One-time | [OMS product](https://support.huaweicloud.com/product-oms.html) |

## 2. DRS Supported Data Source Matrix

> ⚠️ **Important Change (verified 2026-09-09)**: DRS pipelines with GaussDB(DWS)/CSS(ES) as target database have been discontinued — MySQL/TaurusDB/DDM→GaussDB(DWS) went offline on 2024-10-30, others (Oracle/PG/SQL Server/DB2→GaussDB(DWS), etc.) were **discontinued 2025-08-31**, no longer supporting new task creation (existing tasks/whitelist customers excepted). **Real-time data warehousing to DWS uniformly goes through DataArts Studio real-time jobs (migration)**. The matrix below has removed DWS target rows.

DRS only supports real-time replication between relational databases (OLTP) and sync to Kafka:

| Source | Target | Sync Mode | Notes |
|--------|--------|-----------|-------|
| MySQL | MySQL | Full+incremental CDC | Cloud DB/self-built both supported |
| MySQL | Kafka | Full+incremental CDC | Data ingestion scenario |
| PostgreSQL | PostgreSQL | Full+incremental CDC | |
| Oracle | Oracle | Full+incremental CDC | Disaster recovery scenario |
| Oracle | MySQL | Full+incremental | Heterogeneous migration |
| Oracle | Kafka | Full+incremental CDC | |
| SQL Server | SQL Server | Full+incremental CDC | |
| GaussDB(for MySQL) | GaussDB(for MySQL) | Full+incremental CDC | |
| GaussDB(for openGauss) | GaussDB(for openGauss) | Full+incremental CDC | |
| TaurusDB | TaurusDB | Full+incremental CDC | |
| MongoDB | MongoDB | Full+incremental CDC | Document database |
| DDM | DDM | Full+incremental CDC | Distributed database middleware |

## 3. DLI-Flink Supported Connectors

| Connector | Role | Notes |
|-----------|------|-------|
| Kafka (DMS/Apache/MRS) | Source/Sink | Most common streaming source/target |
| DIS | Source | Huawei Cloud data ingestion service |
| OBS | Source/Sink | Object storage, for batch-stream unification |
| JDBC (MySQL/PG/Oracle/DWS) | Source/Sink | Via JDBC connection, supports CDC |
| DLI | Sink | Write to DLI tables |
| Elasticsearch/CSS | Sink | Write to search service |
| Redis (DCS) | Sink | Write to cache |
| HBase (MRS/CloudTable) | Source/Sink | |
| Hive (MRS) | Sink | Via Hive JDBC |
| ClickHouse (MRS) | Sink | |
| Doris (MRS) | Sink | |
| MongoDB | Source/Sink | |
| Pulsar | Source/Sink | |

## 4. Product Selection Decision Tree

```
Input: pipeline = {integration_mode, source_type, target_type, latency, data_volume}

IF integration_mode == "real-time integration":
    IF source is relational database AND target is DWS/data warehouse:
        → Primary: DataArts Studio real-time jobs (migration) —— DRS to DWS pipeline discontinued 2025-08-31, real-time ingestion uniformly via migration
        → Alternative: DLI-Flink CDC (if streaming computation/transformation needed)
    ELIF source is relational database AND target is [relational DB (OLTP)|Kafka]:
        → Primary: DRS (seconds latency, simplest pipeline, no coding)
        → Alternative: DLI-Flink CDC (if streaming computation/transformation needed)
    ELIF source is Kafka/message system AND streaming computation needed:
        → Primary: DLI-Flink (milliseconds~seconds, supports complex CEP/window computation)
        → Alternative: DRS (if only DB sync)
    ELIF source is local data collection/logs:
        → Primary: DIS + DLI-Flink (collection + computation)
    ELIF message middleware needed for async decoupling:
        → Primary: DMS Kafka + DLI-Flink
    ELSE:
        → Primary: DLI-Flink (most flexible real-time compute engine)

ELIF integration_mode == "offline integration":
    IF source/target need arbitrary combination (read-write separation):
        → Primary: DataArts Studio offline jobs (new architecture, 30+ data sources arbitrary combination)
        → Alternative: CDM jobs (if whole-database migration needed and offline jobs not supported)
    ELIF scenario is table/file migration or whole-database migration:
        → Primary: DataArts Studio CDM jobs (traditional, good whole-database migration support)
        → Alternative: offline jobs (if data source in support list)
    ELIF both source and target are OBS:
        → Primary: OMS (object migration service, optimized for OBS-to-OBS)
    ELIF source is relational database AND full+incremental needed:
        → Primary: DataArts Studio offline jobs
        → Alternative: DRS batch mode (if data volume large and incremental continuous)

ELIF integration_mode == "near real-time":
    IF target is DWS/data warehouse:
        → Primary: DataArts Studio real-time jobs (migration) or CDM/offline jobs short-cycle batch (DRS not applicable for DWS target)
    ELSE:
        → Primary: DRS (seconds, satisfies minutes requirement)
        → Alternative: DataArts Studio offline jobs (if DRS does not support this data source combination)
```

## 5. Product Comparison Matrix

| Dimension | DataArts Offline Jobs | CDM Jobs | DRS | DLI-Flink | DIS |
|-----------|----------------------|----------|-----|-----------|-----|
| Integration Mode | Offline | Offline | Real-time/Batch | Real-time | Real-time collection |
| Latency | Minutes~Hours | Minutes~Hours | Seconds | Milliseconds~Seconds | Seconds |
| Data Source Count | 30+ | 20+ | 10+ | 15+ | Agent |
| Read-Write Separation | ✓ Arbitrary combination | ✗ Fixed combination | ✗ Predefined | ✓ Flexible | ✗ One-way |
| Streaming Computation | ✗ | ✗ | ✗ | ✓ Complex CEP | ✗ |
| CDC | ✗ | ✗ | ✓ | ✓ | ✗ |
| Whole-database Migration | Partial | ✓ | ✗ | ✗ | ✗ |
| Development Complexity | Low (config) | Low (config) | Low (config) | Medium~High (coding) | Low (Agent) |
| Typical Scenario | ETL/ingestion | Table migration | DB (between OLTP) sync | Real-time data warehouse | Data collection |

> **DWS Ingestion Pipeline Product Division (verified 2026-09)**: When DWS is the target — batch offline/whole-database initialization uses **CDM**; offline integration requiring ETL transformation uses **offline jobs**; real-time/incremental continuous sync uses **migration (DataArts Studio data integration real-time jobs)**, supports single-table/whole-database/sharded-database, writes to DWS using UPSERT/COPY mode, target DWS requires 8.1.3/8.2.0+ (excluding DWS 3.0). **DRS does not participate in any pipeline to DWS** (discontinued 2025-08-31). migration real-time jobs are currently available in Beijing-4/Shanghai-1/Guangzhou and require whitelist application; confirm by user region during planning.

## 6. Shared Product Recommendations

Multiple pipelines can share product instances to reduce cost:

| Sharing Scenario | Shared Product | Notes |
|------------------|----------------|-------|
| Multiple offline pipelines | 1 CDM cluster / 1 DataArts Studio instance | Same CDM cluster can run multiple migration jobs |
| Multiple real-time to DWS pipelines | 1 DataArts Studio instance + migration resource group | migration real-time jobs unified management of multi-pipeline whole-database/sharded-database sync |
| Multiple real-time DB pipelines | 1 DRS instance | Same DRS can manage multiple sync tasks |
| Multiple streaming pipelines | 1 DLI-Flink queue | Same queue runs multiple Flink Jobs |
| Multiple message pipelines | 1 DMS Kafka instance | Same Kafka multiple Topics |
