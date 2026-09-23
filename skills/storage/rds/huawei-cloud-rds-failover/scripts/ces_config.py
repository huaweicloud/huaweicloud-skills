"""
共享 CES 引擎配置模块 — RDS 不同引擎的 CES 监控维度与指标名映射。

execute.py 和 risk.py 共用此模块，保证倒换期间监控采集与 prepare 阶段风险检测
使用同一套引擎映射，避免维度/指标错配导致的假阴性。

引擎映射已实测验证（2026-09-22，五引擎均 ACTIVE）：
  - MySQL / TaurusDB:  dim=rds_instance_id,        value=节点 ID
  - MariaDB:            dim=mariadb_cluster_id,     value=实例 ID
  - PostgreSQL:         dim=postgresql_cluster_id,  value=实例 ID
  - SQLServer:          dim=rds_cluster_sqlserver_id, value=实例 ID
"""

# ---------------------------------------------------------------------------
# 公共指标映射 — MySQL / MariaDB / TaurusDB 三引擎完全相同的 8 项指标
# 提取为常量复用，避免三份相同配置漂移（修改公共指标时只需改一处）。
# ---------------------------------------------------------------------------
_MYSQL_LIKE_METRIC_MAP = {
    "rds_cpu_util": "rds001_cpu_util",
    "rds_mem_util": "rds002_mem_util",
    "rds_disk_util": "rds039_disk_util",
    "rds_connections_count": "rds006_conn_count",
    "rds_in_flow": "rds004_bytes_in",
    "rds_out_flow": "rds005_bytes_out",
    "rds_iops": "rds003_iops",
    "rds_replication_delay": "rds073_replication_delay",
}

# MySQL 与 TaurusDB 的 CES 配置完全一致：维度名 rds_instance_id，维度值用节点 ID
# 共享同一份配置对象，避免重复维护
_MYSQL_CES_CONFIG = {
    "dim_key": "rds_instance_id",
    "dim_value_source": "node_id",  # 维度值用节点 ID
    "metric_map": _MYSQL_LIKE_METRIC_MAP,
}

# 不同 RDS 引擎的 CES 监控指标存在差异：
#   - 维度名不同：MySQL/TaurusDB 用 rds_instance_id（值为节点 ID），
#     PostgreSQL 用 postgresql_cluster_id（值为实例 ID），
#     SQL Server 用 rds_cluster_sqlserver_id（值为实例 ID），
#     MariaDB 用 mariadb_cluster_id（值为实例 ID）。
#   - 大部分指标名相同（rds001_cpu_util 等），但连接数和复制延迟不同。
#
# 新增引擎只需在 ENGINE_CES_CONFIG 中添加一行映射配置。
ENGINE_CES_CONFIG = {
    "MySQL": _MYSQL_CES_CONFIG,
    # TaurusDB (GaussDB for MySQL) — CES 配置与 MySQL 完全一致
    # 共享 _MYSQL_CES_CONFIG，避免重复维护导致行为漂移
    "TaurusDB": _MYSQL_CES_CONFIG,
    "PostgreSQL": {
        "dim_key": "postgresql_cluster_id",
        "dim_value_source": "instance_id",  # 维度值用实例 ID
        "metric_map": {
            "rds_cpu_util": "rds001_cpu_util",
            "rds_mem_util": "rds002_mem_util",
            "rds_disk_util": "rds039_disk_util",
            "rds_connections_count": "rds042_database_connections",
            "rds_in_flow": "rds004_bytes_in",
            "rds_out_flow": "rds005_bytes_out",
            "rds_iops": "rds003_iops",
            "rds_replication_delay": "rds046_replication_lag",
        },
    },
    # SQL Server — 已实测 (2026-09-22, rds-4af7, SQLServer 2025_SE)
    # 维度名 rds_cluster_sqlserver_id，维度值用实例 ID
    # 6 个通用指标名与 MySQL 相同，连接数和复制延迟不同
    "SQLServer": {
        "dim_key": "rds_cluster_sqlserver_id",
        "dim_value_source": "instance_id",
        "metric_map": {
            "rds_cpu_util": "rds001_cpu_util",
            "rds_mem_util": "rds002_mem_util",
            "rds_disk_util": "rds039_disk_util",
            "rds_connections_count": "rds054_db_connections_in_use",
            "rds_in_flow": "rds004_bytes_in",
            "rds_out_flow": "rds005_bytes_out",
            "rds_iops": "rds003_iops",
            "rds_replication_delay": "rds077_replication_delay",
        },
    },
    # MariaDB — 已实测 (2026-09-22, rds-1662, MariaDB 10.11)
    # 维度名 mariadb_cluster_id，维度值用实例 ID
    # 指标名与 MySQL 完全相同，复用 _MYSQL_LIKE_METRIC_MAP
    "MariaDB": {
        "dim_key": "mariadb_cluster_id",
        "dim_value_source": "instance_id",
        "metric_map": _MYSQL_LIKE_METRIC_MAP,
    },
}


def get_engine_ces_config(engine_str):
    """从引擎字符串（如 'PostgreSQL 18'）提取引擎类型，返回对应 CES 配置。

    引擎字符串格式为 '<Type> <Version>'（如 'MySQL 8.0'、'PostgreSQL 18'），
    取空格前的部分匹配 ENGINE_CES_CONFIG 的 key。

    未知引擎（拼写错误、新引擎未映射、空字符串）时抛出 ValueError，
    由调用方决定是报错还是回退——共享配置模块不应内置业务 fallback，
    否则 execute 与 risk 会在未知引擎上使用错误的 CES 维度/指标，
    导致监控数据错配或风险检测假阴性。
    """
    s = (engine_str or "").strip()
    if not s:
        raise ValueError("引擎字符串为空，无法确定 CES 配置")

    # 关键字归一化：先在原始引擎串上做大小写不敏感关键字匹配，
    # 覆盖所有含空格/括号的变体（如 "GaussDB(for MySQL)"、"GaussDB for MySQL" 等），
    # 避免依赖 split()[0] 切片导致 "GaussDB(for" 漏配。
    s_lower = s.lower()
    if "gaussdb" in s_lower or "taurusdb" in s_lower:
        engine_type = "TaurusDB"
    elif "mariadb" in s_lower:
        engine_type = "MariaDB"
    elif "postgresql" in s_lower or "postgres" in s_lower:
        engine_type = "PostgreSQL"
    elif "sqlserver" in s_lower or "sql server" in s_lower or "mssql" in s_lower:
        engine_type = "SQLServer"
    elif "mysql" in s_lower:
        engine_type = "MySQL"
    else:
        # 非关键字命中的引擎，用首 token 兜底匹配（如 "Redis 7.0" 等未覆盖引擎）
        engine_type = s.split()[0] if s.split() else s

    config = ENGINE_CES_CONFIG.get(engine_type)
    if not config:
        raise ValueError(
            f"未知引擎 '{engine_type}'（原始输入: '{s}'），无对应 CES 配置。"
            f"已知引擎: {', '.join(sorted(ENGINE_CES_CONFIG.keys()))}"
        )
    return config


# ---------------------------------------------------------------------------
# 公共 CES 指标查询 helper — execute.py 与 risk.py 共用同一实现
# 消除维度值选择 + ShowMetricData 参数拼接的重复逻辑，避免维护漂移
# ---------------------------------------------------------------------------

def resolve_ces_dim_value(engine, instance_id, node_id):
    """根据引擎解析 CES 维度名和维度值。

    返回 (dim_key, dim_value)；未知引擎抛 ValueError。
    node_id 驱动引擎（MySQL/TaurusDB）缺失 node_id 时抛 ValueError，
    不静默回退 instance_id——CES 以错误维度查询返回空数据不报错，
    会导致监控假阴性。
    """
    cfg = get_engine_ces_config(engine)
    dim_key = cfg["dim_key"]
    if cfg["dim_value_source"] == "node_id":
        if not node_id:
            raise ValueError(
                f"引擎 '{engine}' 需要 node_id 作为 CES 维度值，但 node_id 为空。"
                f"请确保 prepare/execute 传入了主节点 ID。"
            )
        dim_value = node_id
    else:
        dim_value = instance_id
    return dim_key, dim_value


def query_ces_metric(run_hcloud_fn, region, metric_name, dim_key, dim_value,
                     from_ms=None, to_ms=None, period=300):
    """调用 CES ShowMetricData 查询单个指标。

    run_hcloud_fn: 由调用方传入的 run_hcloud 函数（config.run_hcloud 或其他包装）。
    metric_name: 华为云实际指标名（如 rds001_cpu_util）。
    dim_key: CES 维度名（如 rds_instance_id）。
    dim_value: CES 维度值（节点 ID 或实例 ID）。
    from_ms/to_ms: 时间范围（毫秒）；不传则不附加时间过滤参数。
    period: 聚合周期（秒），默认 300。

    返回 {"available": bool, "error": str|None, "datapoints": list}。
    """
    extra_args = [
        f"--metric_name={metric_name}",
        "--namespace=SYS.RDS",
        f"--dim.0={dim_key},{dim_value}",
        f"--period={period}",
        "--filter=average",
    ]
    if from_ms and to_ms:
        extra_args.append(f"--from={from_ms}")
        extra_args.append(f"--to={to_ms}")
    resp = run_hcloud_fn("CES", "ShowMetricData", region, extra_args)
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "datapoints": []}
    datapoints = resp.get("datapoints", [])
    return {"available": True, "error": None, "datapoints": datapoints}
