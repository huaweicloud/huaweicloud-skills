# Data Source Read/Write Capability Matrix

> This document is extracted from SKILL.md Phase 3, data source Huawei Cloud official documentation (retrieved 2026-08-26).
> ⚠️ **Important Change (verified 2026-09-09)**: DRS pipelines with GaussDB(DWS)/CSS(ES) as target database have been **discontinued 2025-08-31** (MySQL family → DWS went offline 2024-10-30), not supporting new creation. **All sync to DWS uniformly goes through DataArts Studio data integration**: offline uses CDM/offline jobs (matrix below), real-time uses migration real-time jobs (see Section 2.5). DRS matrix does not include DWS target.

## 1. Offline Jobs Read/Write Capability Matrix (DataArts Studio 24.4.x)

Read-write separation architecture: source only needs to support read, target only needs to support write, arbitrary combination.

> Data sources in the table are from DataArts Studio official data source list. **Doris row refers to cloud MRS Doris / CloudTable Doris**; self-built/open-source Doris has no official data source connector, see Section 2.6 for DWS ingestion specifics.

| Data Source | Single-table Read | Single-table Write | Sharded Read | Sharded Write | Whole-database Read | Whole-database Write |
|-------------|-------------------|---------------------|--------------|---------------|---------------------|----------------------|
| MySQL | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| PostgreSQL | ✓ | ✓ | ✓ (partial region) | ✓ | ✓ | ✗ |
| SQL Server | ✓ | ✓ | ✓ (partial region) | ✓ | ✗ | ✗ |
| Oracle | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| SAP HANA | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Open Gauss | ✓ | ✓ | ✓ (partial region) | ✓ | ✓ | ✗ |
| GBase | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| DWS | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ |
| DLI | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Apache Hive | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ (partial region) |
| MRS Hive | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ (partial region) |
| MRS Hudi | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Doris | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| MRS ClickHouse | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Open ClickHouse | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Fabric SQL | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Lake Formation | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| MRS HBase | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| MongoDB | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Redis | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Elasticsearch | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| DMS Kafka | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| Apache RocketMQ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| LTS | ✓ (partial region) | ✗ | ✗ | ✗ | ✗ | ✗ |
| RestApi | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| OBS | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| FTP | ✓ | ✓ (partial region) | ✗ | ✓ (partial region) | ✗ | ✗ |
| SFTP | ✓ | ✓ (partial region) | ✗ | ✓ (partial region) | ✗ | ✗ |
| Apache HDFS | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |

## 2. CDM Jobs Data Source Support Matrix (24.4.x & 2.10.0.400)

### Table/File Migration Supported Data Sources

| Source Category | Source Data Source | Target Support | Notes |
|-----------------|-------------------|----------------|-------|
| Data Warehouse | DWS | DWS/DLI/MRS ClickHouse/Doris/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/Oracle/ES | Does not support DWS physical machine management |
| | DLI | DWS/DLI/MRS ClickHouse/Doris/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/Oracle/MongoDB/ES | |
| | MRS ClickHouse | MRS ClickHouse/DLI | Recommended version 21.3.4.X |
| | Doris | Doris | Official matrix: Doris (source) → target only Doris, **no Doris → DWS**. DataArts Doris data source only supports MRS Doris/CloudTable Doris, **not self-built/open-source Doris** (see Doris ingestion notes at end) |
| Hadoop | MRS HDFS | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/Oracle/ES | Supports local storage, only Hive/Hudi support decoupled storage-compute |
| | MRS HBase | (same as above) | Recommended version 2.1.X/1.3.X |
| | MRS Hive | DWS/DLI/MRS ClickHouse/Doris/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/Oracle/ES | Does not support 2.x, recommended 1.2.X/3.1.X |
| | MRS Hudi | DWS/MRS HBase | Supports local storage + decoupled storage-compute |
| | Apache HBase | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/OBS/ES | Not supported as target, local storage only |
| | Apache Hive | (same as above) | Does not support 2.x |
| | Apache HDFS | (same as above) | |
| Object Storage | OBS | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/ES | OBS-to-OBS migration recommends OMS |
| File System | FTP/SFTP | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/ES/OBS | To search only CSV, to OBS only binary |
| | HTTP | MRS HDFS | To OBS recommend obsutil |
| Relational DB | Cloud MySQL | DWS/DLI/Doris/MRS HDFS/MRS HBase/MRS Hive/MRS Hudi/OBS/MySQL/PG/SQL Server/ES | OLTP → OLTP recommends DRS |
| | Cloud SQL Server | DWS/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/ES | |
| | Cloud PG/MySQL/PG/Oracle/SQL Server | DWS/MRS HDFS/MRS HBase/MRS Hive/MRS Hudi/OBS/ES | |
| NoSQL | DCS (Redis) | MRS HDFS/MRS HBase/MRS Hive/OBS | NoSQL not supported as target |
| | Redis/MongoDB | | |
| Message System | DIS | CSS (beta) | Not supported as target |
| | Apache/DMS/MRS Kafka | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/ES | MRS Kafka not supported as target |
| Search | Elasticsearch | DWS/DLI/MRS HDFS/MRS HBase/MRS Hive/OBS/MySQL/PG/SQL Server/ES | Non-secure mode only |

### Whole-database Migration Supported Data Sources

| Data Source | Read | Write | Notes |
|-------------|------|-------|-------|
| DWS | ✓ | ✓ | |
| MRS HBase | ✓ | ✓ | Export to HBase only, recommended 2.1.X/1.3.X |
| MRS Hive | ✓ | ✓ | Export to relational DB only, recommended 1.2.X/3.1.X |
| Apache HBase | ✓ | ✗ | Recommended 2.1.X/1.3.X |
| Apache Hive | ✓ | ✗ | Export to relational DB only |
| MRS Hudi | ✓ | ✓ | Supports local storage + decoupled storage-compute |
| Cloud MySQL/PG/SQL Server | ✓ | ✓ | OLTP → OLTP recommends DRS |
| MySQL/PG/SQL Server/Oracle | ✓ | ✗ | |
| DCS | ✗ | ✓ | MRS → DCS only |
| CloudTable | ✓ | ✓ | |
| FusionInsight HBase/Hive | ✓ | ✗ | |
| SAP HANA | ✓ | ✗ | Version 2.00.050.00 only |
| DM (Dameng) | ✓ | ✗ | Export to DWS/Hive only |
| DDS | ✓ | ✓ | Between DDS and MRS only |

## 2.5 DataArts Studio Real-time Jobs (migration) DWS Ingestion Support

> Data source: Huawei Cloud DataArts Studio data integration (real-time jobs) official documentation (updated 2026-07-14, verified 2026-09-09).
> migration = DataArts Studio data integration real-time jobs/real-time processing integration jobs, the **only official channel for DB → DWS real-time ingestion** (DRS to DWS discontinued). Real-time processing integration jobs are currently only available in **Beijing-4/Shanghai-1/Guangzhou** and **require whitelist application**; other regions gradually opening. Supports single-table/whole-database/sharded-database, writes to DWS using UPSERT/COPY mode.

| Source | Target | Sync Scenario | Version Requirements |
|--------|--------|---------------|---------------------|
| MySQL / TaurusDB (self-built/other cloud/RDS, standalone/standby/PXC) | DWS | Whole-database/sharded-database | MySQL 5.6/5.7/8.x; DWS 8.1.3, 8.2.0+ (**excluding DWS 3.0**); source binlog enabled (ROW) |
| PostgreSQL / OpenGauss / GaussDB (centralized/distributed) | DWS | Whole-database | Source wal_level=logical; DWS 8.1.3, 8.2.0+ (excluding DWS 3.0) |
| Other sources (Oracle/SQL Server/Kafka, etc.) → DWS | — | — | Per official "supported data sources" page and user region console actual availability; if not available, offline fallback with CDM/offline jobs |

## 2.6 Doris (including self-built/open-source Doris) DWS Ingestion Specifics

> ⚠️ **2026-09-09 Verification Conclusion (easily misjudged, must follow)**
> 1. **DataArts Studio data integration (CDM/offline jobs) Doris data source only supports Huawei Cloud MRS Doris and CloudTable Doris**, no self-built/open-source Doris data source connector; Doris connector (old CDM manual mentioned connecting open-source Doris) is not applicable in new DataArts Studio data integration.
> 2. Official migration matrix Doris (source) → target **only Doris**, no Doris → DWS; migration real-time jobs Doris is only a **target** (e.g., MySQL → Doris beta), source does not support Doris.
> 3. **Self-built/open-source Doris → DWS has no official direct pipeline**. Feasible paths:
>    - If Doris data source is OLTP DB (MySQL/MariaDB/SQL Server, etc.) → build → DWS pipeline at the **source** directly (migration real-time/CDM offline), avoid secondary transfer;
>    - Need to transfer Doris processed results → Doris side scheduled export file (OBS/local) → CDM/offline jobs file ingestion to DWS;
>    - Or third-party tools (DataX/Flink, etc., third-party software solution, self-evaluation required).
> 4. Do not disguise self-built Doris as MySQL source for official MySQL → DWS pipeline (not in official support list, Doris has no binlog, CDC not feasible).

## 3. Read/Write Validation Algorithm

```
Input: source_type, target_type, product
Output: {read_check, write_check, matrix_check, constraints}

IF product == "DataArts Studio offline jobs":
    read_check = offline_jobs_matrix[source_type].single_table_read
    write_check = offline_jobs_matrix[target_type].single_table_write
    matrix_check = read_check AND write_check

ELIF product == "DataArts Studio CDM jobs":
    targets = CDM_table_file_matrix[source_type].target_support
    read_check = source_type in CDM_table_file_matrix
    write_check = target_type in targets
    matrix_check = write_check

ELIF product == "DRS":
    pair = (source_type, target_type)
    matrix_check = pair in DRS_support_matrix
    IF target_type == "DWS":   # DRS to DWS pipeline discontinued 2025-08-31
        matrix_check = False
        recommend reassign product = "migration (DataArts real-time jobs)"

ELIF product == "migration":
    # DataArts Studio real-time jobs, official channel for DWS real-time ingestion (requires region enabled + whitelist)
    matrix_check = (source_type, target_type) in Migration_support_matrix (Section 2.5)
    IF NOT matrix_check:
        constraints += "⚠️ Recommend verifying migration console availability for this pipeline; if not available, use CDM/offline jobs high-freq batch fallback"

ELIF product == "DLI-Flink":
    read_check = source_type in FlinkConnectorSources
    write_check = target_type in FlinkConnectorSinks
    matrix_check = read_check AND write_check

IF NOT matrix_check:
    constraints += "⚠️ {source_type}→{target_type} not in {product} support matrix"
```

## 4. Common Constraint Conditions

| Constraint | Affected Product | Description |
|------------|-----------------|-------------|
| Kerberos encryption type | CDM | MRS cluster Kerberos type must be "aes256-sha1,aes128-sha1", does not support "aes256-sha2,aes128-sha2" |
| Decoupled storage-compute | CDM | Only MRS Hive, MRS Hudi support decoupled storage-compute; Apache HBase/Hive local storage only |
| Ranger | CDM | Only MRS Hive supports Ranger; Apache HBase/Hive do not |
| ZK SSL | CDM | Does not support ZK with SSL enabled |
| Whole-database write | Offline jobs | Only Hive supports whole-database write (partial region); most data sources whole-database write is ✗ |
| OLTP → OLTP | CDM/DRS | Relational DB migration, real-time recommends DRS, offline recommends CDM |
| OBS-to-OBS migration | CDM | Recommend using OMS instead of CDM |
| FTP → Search | CDM | Only supports CSV and other text files, not binary |
| FTP → OBS | CDM | Only supports binary files |
| DWS physical machine | CDM | Does not support DWS physical machine management mode |
| DWS target real-time pipeline | DRS | **DRS pipelines with DWS/CSS as target discontinued 2025-08-31**, real-time ingestion uses migration (DataArts real-time jobs), requires region enabled + whitelist |
