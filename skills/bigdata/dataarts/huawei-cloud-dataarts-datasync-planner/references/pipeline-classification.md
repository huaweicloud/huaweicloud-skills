# Real-time/Offline Classification Algorithm and Decision Tree

> This document is extracted from SKILL.md Phase 2 and defines the real-time/offline classification standards and algorithm for data sync pipelines.

## 1. Classification Standards

| Dimension | Real-time Integration | Batch Offline Integration | Near Real-time |
|-----------|----------------------|--------------------------|----------------|
| **Latency Requirement** | Seconds/Milliseconds | Hours/Days | Minutes |
| **Trigger Mode** | Event-driven (CDC/streaming) | Scheduled (cron/scheduler) | Mixed (scheduled+event) |
| **Sync Mode** | Incremental CDC/streaming append | Full/Full+incremental | Full+incremental CDC |
| **Data Volume/Time** | MB-KB level (small incremental) | GB-TB level (large batch) | GB level |
| **Frequency** | Continuous/seconds/minutes high-freq | Low-freq (hourly/daily/weekly) | Minutes mid-freq |
| **Typical Tools** | Canal/Debezium/Flink CDC/Kafka Connect | DataX/Sqoop/CDM/Oozie/Airflow | DRS/custom |

## 2. Classification Algorithm (5-Step Method)

```
Input: pipeline = {latency, trigger, mode, volume_gb, frequency, tool}
Output: {result: "real-time integration"|"offline integration"|"near real-time", reason: "...", steps: {...}}

Step1: Latency priority
  IF latency in ["seconds", "milliseconds"]:
    → result = "real-time integration"
    → reason = "Latency requirement is {latency}, classified as real-time integration"
    → RETURN

Step2: Trigger mode determination
  IF trigger == "event-driven" OR mode == "CDC":
    → result = "real-time integration"
    → reason = "Trigger mode is event-driven/CDC, classified as real-time integration"
    → RETURN

Step3: Frequency determination
  IF frequency in ["continuous", "seconds"] OR frequency contains "second":
    → result = "real-time integration"
    → reason = "Sync frequency is {frequency}, classified as real-time integration"
    → RETURN

Step4: Reverse determination (offline)
  IF latency in ["hours", "days"] AND trigger == "scheduled":
    → result = "offline integration"
    → reason = "Latency {latency} + scheduled, classified as offline integration"
    → RETURN

Step5: Mixed scenario (near real-time)
  IF latency == "minutes":
    IF mode contains "CDC" OR trigger contains "event":
      → result = "near real-time"
      → reason = "Latency minutes + contains CDC/event-driven, annotated as near real-time, recommend DRS real-time sync"
    ELSE:
      → result = "offline integration"
      → reason = "Latency minutes + scheduled, classified as offline integration"
    → RETURN

  # Default to offline
  → result = "offline integration"
  → reason = "No real-time conditions matched, default to offline integration"
```

## 3. Decision Tree

```
                    ┌── Latency seconds/milliseconds? ──→ Real-time integration
                    │
                    ├── Trigger event-driven/CDC? ──→ Real-time integration
Pipeline input ──→ classify ──┤
                    ├── Frequency continuous/seconds? ────→ Real-time integration
                    │
                    ├── Latency hours/days + scheduled? ──→ Offline integration
                    │
                    └── Latency minutes?
                         ├── Contains CDC/event? ──→ Near real-time (recommend DRS)
                         └── Scheduled? ────→ Offline integration
```

## 4. Boundary Scenarios

| Scenario | Input Characteristics | Classification | Notes |
|----------|----------------------|----------------|-------|
| Full+incremental with seconds latency | mode=full+incremental, latency=seconds | Real-time integration | Latency priority, seconds → real-time |
| Full+incremental with hours latency | mode=full+incremental, latency=hours | Offline integration | Typical offline data warehouse ETL |
| CDC but days latency | mode=CDC, latency=days | Real-time integration | Trigger mode priority (CDC → real-time), but need to confirm with user if reasonable |
| Minutes + scheduled | latency=minutes, trigger=scheduled | Offline integration | Scheduled → offline |
| Minutes + CDC | latency=minutes, mode=CDC | Near real-time | Recommend DRS real-time sync to replace offline |
| No latency provided | latency=unknown | Offline integration (default) | Must proactively ask user, cannot default skip |

## 5. Typical Tool Mapping

| Existing Tool | Classification Tendency | Huawei Cloud Corresponding Product |
|---------------|------------------------|-------------------------------------|
| DataX / Sqoop | Offline | DataArts Studio offline jobs / CDM jobs |
| CDM (Cloudera) | Offline | DataArts Studio CDM jobs |
| Oozie / Airflow scheduling | Offline | DataArts Studio workflow (DLF) |
| Canal / Debezium | Real-time | DRS / DLI-Flink CDC |
| Flink CDC / Flink Streaming | Real-time | DLI-Flink |
| Kafka Connect | Real-time | DMS Kafka + DLI-Flink |
| Logstash / Flume | Near real-time | DIS + DLI-Flink |
| GoldenGate | Real-time | DRS |
| Kettle / Informatica | Offline | DataArts Studio offline jobs |
