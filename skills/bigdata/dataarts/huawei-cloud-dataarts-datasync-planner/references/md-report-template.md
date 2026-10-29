# Markdown Report Template and Data Structure

> This document is extracted from SKILL.md Phase 6 and defines the 3 major section structure and data contract of the MD report.

## 1. MD Document Structure (3 Major Sections)

| Section | Name | Content |
|---------|------|---------|
| 1 | Existing Data Pipeline Topology Diagram | ASCII topology diagram showing all current sync pipelines |
| 2 | Existing Pipeline Description | Each pipeline: data source location (IDC/Alibaba Cloud/Tencent Cloud, etc.), real-time incremental or batch offline, sync frequency, data volume |
| 3 | Huawei Cloud Replacement Solution Topology Diagram and Description | Replacement solution topology diagram + description (directly use CDM/migration/DRS product names, do not repeat DataArts Studio) |

## 2. MD Document Template

```markdown
# Huawei Cloud Data Sync Pipeline Planning Report

> Generated Date: YYYY-MM-DD

---

## I. Existing Data Pipeline Topology Diagram

​```text
<ASCII topology diagram: showing all pipeline source → target topology>
​```

---

## II. Existing Pipeline Description

### Pipeline P001: <source>→<target>

| Item | Description |
|------|-------------|
| Data Source Location | IDC self-built / Alibaba Cloud RDS / Tencent Cloud CVM, etc. |
| Source Data Source | Oracle 11g / MySQL 8.0, etc. (with version) |
| Target Data Source | ClickHouse 21.8 / Hive 3.1, etc. (with version) |
| Sync Mode | Real-time incremental / Batch offline |
| Sync Frequency | Daily 1x / hourly / continuous (CDC), etc. |
| Daily Sync Data Volume | XX GB/day |
| Existing Tool | Kettle / Sqoop / DataX / Canal, etc. |

### Pipeline P002: ...

(same structure)

---

## III. Huawei Cloud Replacement Solution Topology Diagram and Description

### Replacement Solution Topology Diagram

​```text
<ASCII topology diagram: showing Huawei Cloud-side replacement solution topology, directly annotate product names CDM/migration/DRS>
​```

### Solution Description

#### Pipeline P001: <source>→<target>

| Item | Description |
|------|-------------|
| Solution Type | Direct match / Huawei Cloud feasible solution (indirect) / Third-party software solution |
| Replacement Product | CDM / migration / offline jobs / DRS (directly use product names, no DataArts Studio prefix) |
| Pipeline Topology | Source → [dedicated line/VPN] → CDM/migration → Target |
| Configuration Recommendations | Sync mode/scheduling/spec |
| Constraint Conditions | Kerberos/decoupled storage-compute/version requirements |
| Alternative Solution | Secondary product (if any) |
| No Match Explanation | (if applicable) reason + Huawei Cloud feasible solution + third-party solution + pros/cons comparison |

#### Pipeline P002: ...

(same structure)

### Shared Product Recommendations

(description of products that can be shared across multiple pipelines)
```

## 3. Product Name Usage Convention

In solution descriptions, **directly use product/capability names** without repeatedly mentioning DataArts Studio:

| Product/Capability | Correct Notation | Incorrect Notation |
|--------------------|------------------|---------------------|
| CDM | CDM | ~~DataArts Studio CDM~~ |
| migration | migration | ~~DataArts Studio migration~~ |
| Offline Jobs | offline jobs | ~~DataArts Studio offline jobs~~ |
| DRS | DRS | ~~Data Replication Service DRS~~ (full name on first mention, then DRS) |

**Reason**: CDM, migration, and offline jobs are all DataArts Studio capabilities; the document context already explains this, no need to repeat "DataArts Studio" prefix everywhere.

**Important (verified 2026-09-09)**: migration refers to **DataArts Studio data integration real-time jobs/real-time processing integration jobs**, and is the **only official channel for real-time data warehousing to DWS** (DRS pipelines with DWS/CSS as target database stopped sale 2025-08-31; reports **must not** write DRS as the solution for DWS target; offline ingestion to DWS uses CDM/offline jobs).

## 4. report_data Data Structure

> **Excel 脚本契约**：`generate_datasync_report.py` 只读取 `report_data["pipelines"]`。顶层 `generated_at` / `current_topology` / `huawei_topology` 是 Phase 5 Markdown 报告使用的可选拓扑文本，Excel 脚本不消费。字段名必须与下表一致（注意是 `mode` 而非 `sync_mode`，`deploy` 而非 `location`）。

```python
report_data = {
    "generated_at": "2026-08-28",            # 可选,MD 报告生成日期(Excel 脚本不读取)
    "current_topology": "existing topology ASCII text",     # 可选,MD 报告源端拓扑图(Excel 脚本不读取)
    "huawei_topology": "replacement solution topology ASCII text",  # 可选,MD 报告华为云拓扑图(Excel 脚本不读取)
    "pipelines": [
        {
            "id": "P001",                                     # 链路编号
            "name": "Oracle到ClickHouse离线同步",             # 链路名称
            "source": {"type": "Oracle", "version": "11g", "deploy": "IDC self-built"},   # deploy=源端部署
            "target": {"type": "CloudTable ClickHouse", "version": "21.8+", "deploy": "Huawei Cloud"},
            "mode": "全量+增量",              # 同步模式(全量/增量/CDC/流式);字段名是 mode 非 sync_mode
            "daily_volume_gb": 50,            # 日同步数据量(GB)
            "frequency": "daily 1x",
            "latency": "小时级",              # 延迟要求(秒级/小时级等),分类关键
            "tool": "Kettle",
            "huawei_solution": {
                "mode": "离线集成",           # 集成模式(实时集成/离线集成)
                "scheme_type": "直接对标",    # 方案类型,取值见下方对照表(中英文均可)
                "product": "offline jobs",    # 直接用产品名,不加 DataArts Studio 前缀
                "topology": "Oracle → [dedicated line] → offline jobs → CloudTable ClickHouse",
                "config": "incremental extraction; daily 2:00 scheduling",
                "constraints": "CloudTable via JDBC connection (not CDM native support)",
                "alternative": "CDM not supported → DataX on ECS",
            },
            "no_direct_match": {              # 可选,仅当无法直接对标时提供;存在且 scheme_type≠直接对标 时生成 Sheet3
                "reason": "reason text",
                "huawei_feasible": "Huawei Cloud feasible solution (preferred)",
                "huawei_topology": "topology text",
                "third_party": "third-party solution (secondary)",
                "third_party_topology": "topology text",
                "pros_cons": "pros/cons comparison text",
            },
        }
    ],
}
```

### 4.1 scheme_type 取值（脚本同时兼容中文与英文）

脚本 `_normalize_scheme_type` 会将英文取值归一化为中文规范名后再上色与筛选 Sheet3，因此中英文均可填写。**推荐使用中文取值**以与脚本示例数据一致。

| 中文取值（推荐） | 英文取值（兼容） | Sheet2 方案类型列颜色 | 是否进入 Sheet3 |
|------------------|------------------|----------------------|-----------------|
| 直接对标 | Direct match | 浅绿 | 否 |
| 华为云可行方案(间接) | Huawei Cloud feasible solution (indirect) | 浅黄 | 是（需有 no_direct_match） |
| 三方软件方案 | Third-party software solution | 浅橙 | 是（需有 no_direct_match） |

## 5. Generation Rules

- **Excel report file name (Phase 6, script output)**: DataSync_Pipeline_Report_<YYYYMMDD>.xlsx
- **Markdown report file name (Phase 5)**: DataSync_Pipeline_Report_<YYYYMMDD>.md
- **Topology diagram**: use ```text code block, ASCII art
- **Tables**: use standard Markdown tables
- **Product names**: directly use CDM/migration/offline jobs/DRS, do not repeat DataArts Studio
- **Solution type annotation**: each pipeline must explicitly annotate solution type (Chinese or English values accepted, see Section 4.1)
