# Component Mapping and Cluster Type Matching

> Extracted from SKILL.md Phase 1.3 + Phase 2. See main document for details.

## 1. Component Mapping to MRS

Map investigated components to MRS 3.x supported components:

| User Component | MRS Component | Notes |
|---------------|---------------|-------|
| HDFS | Hadoop (HDFS) | Mandatory in analysis/hybrid clusters |
| YARN | Hadoop (YARN) | Resource manager, mandatory with Hadoop |
| Spark | Spark2x | MRS 3.x uses Spark2x |
| Flink | Flink | Depends on ZooKeeper, KrbServer, DBService, Hadoop |
| Hive | Hive | Depends on Hadoop, DBService |
| HBase | HBase | Depends on Hadoop |
| Kafka | Kafka | Depends on ZooKeeper |
| ZooKeeper | ZooKeeper | Foundation service |
| Presto/Trino | HetuEngine | Huawei's enhanced Presto derivative |
| ClickHouse | ClickHouse | Depends on ZooKeeper |
| Doris | Doris | Available in MRS 3.3.0+ |
| Ranger | Ranger | Depends on DBService |
| Oozie | Oozie | Depends on Hadoop, DBService, ZooKeeper |
| Hue | Hue | Depends on DBService |
| Flume | Flume | Standalone |
| Loader/Sqoop | Loader | Depends on Hadoop, DBService |
| Tez | Tez | Depends on Hadoop, DBService, ZooKeeper |
| Hudi | Hudi | Bundled with Spark/Hive |
| IoTDB | IoTDB | Depends on KrbServer |
| Kudu | Kudu | Available in MRS 3.1.0 |

## 2. MRS Cluster Types

| Cluster Type | API Value | Description | Use Case |
|-------------|-----------|-------------|----------|
| **Analysis** | ANALYSIS | Hadoop ecosystem components | Offline batch processing, ETL, data warehouse |
| **Streaming** | STREAMING | Streaming components only | Real-time stream processing |
| **Hybrid** | MIXED | Both analysis + streaming components | Mixed workloads (batch + real-time) |
| **Custom** | CUSTOM | User-defined topology (MRS 3.x only) | Flexible deployment, large clusters |

## 3. Cluster Type Selection Logic

```
IF user uses ONLY streaming components (Kafka, Flume, Flink streaming)
  -> Recommend: Streaming Cluster
ELSE IF user uses ONLY batch/analytics components (Hadoop, Spark, Hive, HBase)
  -> Recommend: Analysis Cluster
ELSE IF user uses BOTH batch + streaming
  -> Recommend: Hybrid Cluster
ELSE IF user needs custom topology OR >500 nodes OR component separation
  -> Recommend: Custom Cluster
```

## 4. MRS Version Selection

| Version | Key Features | Recommendation |
|---------|-------------|----------------|
| MRS 3.1.0-LTS | Stable, Impala/Kudu/Presto support | Legacy migration with Impala/Kudu |
| MRS 3.2.0-LTS | ClickHouse, HetuEngine, Guardian | General purpose, ClickHouse workloads |
| MRS 3.3.0-LTS | Doris, JobGateway, Guardian | Latest LTS, Doris/data warehouse |

**Default recommendation**: MRS 3.3.0-LTS (latest LTS with most component support)

## 5. Component Dependency Resolution

When a user selects components, automatically resolve dependencies:

```
Hadoop -> requires ZooKeeper
Hive -> requires Hadoop + DBService
HBase -> requires Hadoop
Spark/Spark2x -> requires Hadoop + Hive + ZooKeeper
Flink -> requires ZooKeeper + KrbServer + DBService + Hadoop
Kafka -> requires ZooKeeper
ClickHouse -> requires ZooKeeper
HetuEngine -> requires Hadoop + DBService + Hive + ZooKeeper + KrbServer + YARN + HDFS
Oozie -> requires Hadoop + DBService + ZooKeeper
Loader -> requires Hadoop + DBService
Ranger -> requires DBService
Tez -> requires Hadoop + DBService + ZooKeeper
```

**Rule**: Always include ZooKeeper as a foundation service. DBService is auto-included when needed.
