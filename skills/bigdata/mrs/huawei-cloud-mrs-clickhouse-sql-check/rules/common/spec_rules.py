# -*- coding: utf-8 -*-
"""
ClickHouse 24.8 开发规范规则定义

Source: 《MRS 组件开发规范》v01 (2026-07-03) 第1章 ClickHouse 应用开发规范

规则分类:
- SPEC001-SPEC010: DDL 表设计规范
- SPEC011-SPEC020: DDL 操作与物化视图规范
- SPEC021-SPEC030: DML 数据入库规范
- SPEC031-SPEC040: 查询与数据修改规范
"""

# 规则定义: (rule_id, rule_name, level, category, description, fix_suggestion)
SPEC_RULES = [
    # ==================== DDL 表设计规范 ====================
    ("SPEC001", "禁止使用 Buffer 表引擎", "ERROR", "DDL",
     "Buffer 表引擎在重启/进程故障场景下无法保证数据可靠性，存在数据丢失风险",
     "使用 ReplicatedMergeTree 等副本引擎替代 Buffer"),

    ("SPEC002", "建议使用 Replicated 副本引擎", "WARNING", "DDL",
     "为提升数据和服务可靠性，建议使用 Replicated*MergeTree 系列副本引擎",
     "使用 ReplicatedMergeTree / ReplicatedSummingMergeTree 等副本引擎"),

    ("SPEC003", "表名命名不规范", "WARNING", "DDL",
     "表名应以字母开始，可包含 a-z/A-Z/0-9/下划线，在当前数据库内唯一",
     "按命名规范修改表名"),

    ("SPEC004", "禁止用字符类型存放时间/日期数据", "WARNING", "DDL",
     "不允许用字符类型存放时间或日期类数据，字符串过滤效率低于日期类型",
     "使用 Date / DateTime / DateTime64 等日期类型"),

    ("SPEC005", "禁止用字符类型存放数值数据", "WARNING", "DDL",
     "不允许用字符类型存放数值类型数据，字符串过滤效率低于整型",
     "使用 UInt/Int/Float 等数值类型"),

    ("SPEC006", "Nullable 列过多", "INFO", "DDL",
     "不建议表中存储过多 Nullable 列，会消耗更多内存",
     "字符串使用 'NA'，数值型用 0 作为缺省值"),

    ("SPEC007", "数值类型未选择最小满足类型", "INFO", "DDL",
     "建议根据业务场景选择最小满足的数值类型，性能差别较大",
     "如 UInt8 代替 UInt32，Float32 代替 Float64"),

    ("SPEC008", "低基数维度未使用 LowCardinality", "INFO", "DDL",
     "基数<10万 的维度字段建议使用 LowCardinality 修饰符，提升查询性能",
     "使用 LowCardinality(String) 等"),

    ("SPEC009", "单表字段超过5000列", "WARNING", "DDL",
     "单表字段建议不超过5000列，否则插入时易出现内存超限错误",
     "拆分表或调大 min_bytes_for_wide_part"),

    ("SPEC010", "缺少 TTL 生命周期管理", "INFO", "DDL",
     "表设计应考虑数据生命周期管理，需设置 TTL 或定期老化清理分区",
     "添加 TTL create_time + toIntervalMonth(N) 子句"),

    # ==================== DDL 操作与索引规范 ====================
    ("SPEC011", "ORDER BY 字段过多", "WARNING", "DDL",
     "ORDER BY 排序字段建议不超过4个，且不允许为 null",
     "精简 ORDER BY 字段，按访问频率从高到低、基数从小到大排列"),

    ("SPEC012", "PRIMARY KEY 非排序字段前导列", "WARNING", "DDL",
     "PRIMARY KEY 应为 ORDER BY 字段的前导列",
     "调整 PRIMARY KEY 为 ORDER BY 的前缀"),

    ("SPEC014", "DROP/ALTER 未加 NO DELAY", "INFO", "DDL",
     "删除/修改表时建议加 NO DELAY 立即执行，否则等待8分钟",
     "添加 NO DELAY 关键字"),

    ("SPEC015", "单表跳数索引超过5个", "WARNING", "DDL",
     "单表跳数索引总数建议控制在5个以内，避免影响数据导入性能",
     "精简 INDEX 定义"),

    ("SPEC016", "分区数过多风险", "INFO", "DDL",
     "分区数建议控制在一万以内，分区字段使用整型；part 过多会显著降低查询性能",
     "使用 toYYYYMM/toYYYYMMDD 分区，避免过细粒度"),

    # ==================== 物化视图规范 ====================
    ("SPEC017", "物化视图命名不规范", "INFO", "DDL",
     "聚合表建议加 _{type}_agg 后缀，物化视图加 _{type}_mv 后缀",
     "按命名规范修改物化视图/聚合表名"),

    ("SPEC018", "物化视图未显式指定聚合表", "WARNING", "DDL",
     "创建物化视图时建议使用 TO 关键字显式指定聚合表，否则会创建隐式表",
     "使用 TO 关键字指定目标聚合表"),

    ("SPEC019", "禁止使用 POPULATE 创建物化视图", "ERROR", "DDL",
     "POPULATE 期间若有数据插入可能丢失，禁止使用",
     "先创建 MV (WHERE 未来时间) 再 INSERT 历史数据补齐"),

    ("SPEC020", "物化视图缺少 TTL", "INFO", "DDL",
     "TTL 不会从源表同步到物化视图，建议物化视图表也配置 TTL 并与源表一致",
     "为物化视图目标表添加与源表一致的 TTL"),

    # ==================== DML 数据入库规范 ====================
    ("SPEC021", "INSERT 写分布式表", "WARNING", "DML",
     "不建议写分布式表：异步转发有一致性风险、batch size 变小、IO 瓶颈",
     "写本地表，查询分布式表"),

    ("SPEC022", "INSERT 未限定单分区", "INFO", "DML",
     "建议一批插入的数据属于同一个分区，否则 part 文件膨胀",
     "按分区拆分批次插入"),

    ("SPEC023", "禁止使用 Kafka 表引擎", "ERROR", "DML",
     "不建议建 ClickHouse Kafka 表引擎同步数据，存在性能问题",
     "应用侧自己消费 Kafka 攒批写入 ClickHouse"),

    # ==================== 查询规范 ====================
    ("SPEC024", "禁止 SELECT * 查询", "WARNING", "Query",
     "禁止 SELECT * 查询，应明确指定所需列，减少数据扫描量",
     "列出具体字段名替代 *"),

    ("SPEC025", "建议使用 uniqCombined 替代 distinct", "INFO", "Query",
     "uniqCombined 性能优于 countDistinct/distinct，内存占用更小",
     "使用 uniqCombined(col) 替代 countDistinct/distinct"),

    ("SPEC026", "分布式 JOIN 未使用 GLOBAL 关键字", "WARNING", "Query",
     "分布式表 JOIN/IN/NOT IN 建议添加 GLOBAL 关键字，避免查询放大",
     "使用 GLOBAL JOIN / GLOBAL IN / GLOBAL NOT IN"),

    ("SPEC027", "复杂多表 JOIN 未拆分", "INFO", "Query",
     "多表复杂 join 建议拆分为两表 join 或子查询",
     "拆分为多个两表 JOIN 或使用子查询"),

    ("SPEC028", "关联查询未遵循大表 join 小表", "INFO", "Query",
     "关联查询建议大表 join 小表（小表为过滤后千万级以下数据量）",
     "调整 JOIN 顺序，小表在右"),

    ("SPEC029", "慎用 FINAL 查询", "INFO", "Query",
     "FINAL 查询会触发完整 merge，性能较差，建议慎用",
     "考虑在业务低峰执行或改用 argMax 等方案"),

    # ==================== 数据修改规范 ====================
    ("SPEC030", "慎用 DELETE/UPDATE mutation", "WARNING", "DML",
     "DELETE/UPDATE 为 mutation 操作，性能差且阻塞 merge，建议慎用",
     "考虑通过分区替换或 TTL 方式管理数据"),

    ("SPEC031", "禁止修改索引列", "ERROR", "DML",
     "禁止修改 ORDER BY / PRIMARY KEY 索引列的值",
     "避免对索引列执行 UPDATE"),

    ("SPEC032", "谨慎执行 OPTIMIZE 操作", "INFO", "DML",
     "OPTIMIZE 会强制 merge，消耗大量资源，建议慎用",
     "在业务低峰期执行，避免频繁调用"),

    ("SPEC033", "批量数据清理未按分区操作", "INFO", "DML",
     "批量数据清理建议根据分区来操作（DROP PARTITION）",
     "使用 ALTER TABLE ... DROP PARTITION"),

    # ==================== 类型一致性规范 ====================
    ("SPEC034", "类型敏感函数中 Decimal 类型不一致", "WARNING", "Query",
     "coalesce/ifNull/nullIf 等类型敏感函数中使用了不同 scale 或 precision 的 Decimal 类型，"
     "会导致隐式类型转换，可能引起精度丢失或意外行为",
     "统一函数参数中的 Decimal 类型，确保 scale 和 precision 一致"),

    ("SPEC035", "IN/NOT IN 子查询列数不匹配", "ERROR", "Query",
     "IN/NOT IN 操作符左右两侧的列数不一致，会导致运行时错误或逻辑错误",
     "使用元组形式 (col1, col2) IN (SELECT col1, col2 ...) 确保列数匹配"),
]

# 按规则ID索引
SPEC_RULES_MAP = {r[0]: r for r in SPEC_RULES}

# 总规范规则数
TOTAL_SPEC_RULES = len(SPEC_RULES)


def get_rule(rule_id):
    """获取规则定义"""
    return SPEC_RULES_MAP.get(rule_id)


def make_violation(rule_id, line=1, column=1, sql_snippet="", **kwargs):
    """根据规则ID生成违规信息 dict"""
    rule = SPEC_RULES_MAP.get(rule_id)
    if not rule:
        return None
    return {
        "rule_id": rule_id,
        "rule_name": rule[1],
        "level": rule[2],
        "category": rule[3],
        "message": rule[4],
        "line": line,
        "column": column,
        "sql_snippet": sql_snippet,
        "fix_suggestion": rule[5],
    }
