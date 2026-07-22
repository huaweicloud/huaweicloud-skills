# -*- coding: utf-8 -*-
"""Regression test suite for MRS Hive SQL checker.

Runs good-SQL (should produce zero violations) and bad-SQL (should trigger
specific rules) cases to validate tokenizer/parser/checker integrity after
the keyword/literal/parser/function updates.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))

from hive_sql_checker import check_sql


# ============================================================
# Good SQL — should produce ZERO violations (or only INFO)
# ============================================================
GOOD_CASES = [
    (
        "simple_select",
        "SELECT id, name FROM db1.users WHERE dt='20260101' AND id > 100 LIMIT 100",
    ),
    (
        "select_with_hive_literals",
        "SELECT 100L, 3.14D, 123.45BD, 256M, 0x1F FROM db1.t1 WHERE dt='20260101' LIMIT 10",
    ),
    (
        "select_cluster_by",
        "SELECT a, b FROM db1.t1 WHERE dt='20260101' CLUSTER BY a LIMIT 10",
    ),
    (
        "select_distribute_sort",
        "SELECT a, b FROM db1.t1 WHERE dt='20260101' DISTRIBUTE BY a SORT BY b LIMIT 10",
    ),
    (
        "select_tablesample",
        "SELECT a FROM db1.t1 TABLESAMPLE(10 PERCENT) WHERE dt='20260101' LIMIT 10",
    ),
    (
        "lateral_view_outer",
        "SELECT a, d FROM db1.t1 LATERAL VIEW OUTER explode(c) t2 AS d WHERE dt='20260101' LIMIT 10",
    ),
    (
        "create_table_full",
        "CREATE TABLE IF NOT EXISTS db1.t1 (id BIGINT, name STRING) "
        "COMMENT 'user table' "
        "PARTITIONED BY (dt STRING) "
        "CLUSTERED BY (id) INTO 10 BUCKETS "
        "STORED AS ORC "
        "LOCATION '/user/hive/warehouse/t1' "
        "TBLPROPERTIES ('orc.compress'='SNAPPY')",
    ),
    (
        "create_table_skewed",
        "CREATE TABLE db1.t1 (id int, region string) "
        "COMMENT 'skewed test' "
        "PARTITIONED BY (dt string) "
        "SKEWED BY (region) ON ('CN', 'US') STORED AS DIRECTORIES "
        "STORED AS ORC",
    ),
    (
        "merge_valid",
        "MERGE INTO db1.target t USING db1.source s ON t.id = s.id "
        "WHEN MATCHED THEN UPDATE SET t.val = s.val",
    ),
    (
        "load_data_valid",
        "LOAD DATA INPATH '/path/to/data' INTO TABLE db1.t1",
    ),
    (
        "load_data_overwrite",
        "LOAD DATA LOCAL INPATH '/path/to/data' OVERWRITE INTO TABLE db1.t1 PARTITION (dt='20260101')",
    ),
    (
        "ctas",
        "CREATE TABLE db1.t2 AS SELECT a, b FROM db1.t1",
    ),
    (
        "insert_overwrite_select",
        "INSERT OVERWRITE TABLE db1.t1 PARTITION (dt='20260101') SELECT a, b FROM db1.t2",
    ),
    (
        "mapjoin_hint",
        "SELECT /*+ MAPJOIN(t2) */ t1.a, t2.b FROM db1.t1 JOIN db1.t2 ON t1.id = t2.id WHERE t1.dt='20260101' LIMIT 100",
    ),
    (
        "backtick_identifier",
        "SELECT `order`, `status` FROM db1.`table` WHERE `order` > 0 AND dt='20260101' LIMIT 10",
    ),
    (
        "cte_with_union",
        "WITH cte AS (SELECT a FROM db1.t1 WHERE dt='20260101') SELECT a FROM cte UNION ALL SELECT a FROM db1.t2 LIMIT 100",
    ),
    # SPEC001 false-positive exclusions: count(*) and multiplication
    (
        "select_count_star",
        "SELECT count(*) FROM db1.t1 WHERE dt='20260101' LIMIT 10",
    ),
    (
        "select_multiply_after_rparen",
        "SELECT sum(price)*100 FROM db1.t1 WHERE dt='20260101' LIMIT 10",
    ),
    (
        "select_multiply_ident_const",
        "SELECT segment*50 AS seg FROM db1.t1 WHERE dt='20260101' LIMIT 10",
    ),
    (
        "select_multiply_div_chain",
        "SELECT cast(a AS DECIMAL(15,4))/cast(b AS DECIMAL(15,4))*100 AS ratio FROM db1.t1 WHERE dt='20260101' LIMIT 10",
    ),
    # ANSI JOIN should NOT trigger SPEC003
    (
        "ansi_join_no_spec003",
        "SELECT t1.a, t2.b FROM db1.t1 JOIN db1.t2 ON t1.id = t2.id WHERE t1.dt='20260101' LIMIT 100",
    ),
]

# ============================================================
# Bad SQL — should trigger specific rule IDs
# ============================================================
BAD_CASES = [
    (
        "merge_missing_when",
        "MERGE INTO t1 USING t2 ON t1.id=t2.id",
        ["SYN014"],
    ),
    (
        "load_data_missing_inpath",
        "LOAD DATA INTO TABLE t1",
        ["SYN015"],
    ),
    (
        "reserved_keyword_with_backtick",
        "SELECT `order` FROM db1.t1 WHERE dt='20260101' LIMIT 10",
        [],  # `order` with backticks should NOT trigger SYN002
    ),
    (
        "create_table_no_partition",
        "CREATE TABLE db1.t1 (id int, name string) COMMENT 'test' STORED AS ORC",
        ["SPEC019"],
    ),
    (
        "create_table_no_columns",
        "CREATE TABLE db1.t1 STORED AS ORC",
        ["SYN012"],
    ),
    (
        "select_star",
        "SELECT * FROM db1.t1 WHERE dt='20260101' LIMIT 10",
        ["SPEC001"],
    ),
    (
        "invalid_stored_as",
        "CREATE TABLE db1.t1 (id int) COMMENT 'test' PARTITIONED BY (dt string) STORED AS INVALIDFORMAT",
        ["SYN007"],
    ),
    # SPEC003: true cartesian product (no join condition) -> ERROR
    (
        "cartesian_product_no_where",
        "SELECT a.id FROM t1, t2",
        ["SPEC003"],
    ),
    # SPEC003: old-style comma join with bare column join -> WARNING (not ERROR)
    (
        "old_style_join_bare_cols",
        "SELECT i_item_id FROM catalog_sales, date_dim WHERE cs_sold_date_sk = d_date_sk",
        ["SPEC003"],
    ),
    # SPEC003: old-style comma join with table.col = bare_col -> WARNING (not ERROR)
    (
        "old_style_join_mixed_cols",
        "SELECT count(*) FROM catalog_sales cs1, date_dim WHERE cs1.cs_ship_date_sk = d_date_sk",
        ["SPEC003"],
    ),
]


def run_good_cases():
    failures = []
    for name, sql in GOOD_CASES:
        result = check_sql(sql)
        # Filter out INFO-level (acceptable)
        real_violations = [
            v for v in result.get("violations", [])
            if v.get("level", "ERROR") in ("ERROR", "WARNING")
        ]
        if real_violations:
            failures.append((name, sql, real_violations))
            print(f"  FAIL  {name}: {len(real_violations)} violations")
            for v in real_violations:
                print(f"        [{v.get('rule_id')}] {v.get('message','')}")
        else:
            print(f"  PASS  {name}")
    return failures


def run_bad_cases():
    failures = []
    for name, sql, expected_rules in BAD_CASES:
        result = check_sql(sql)
        triggered = {v.get("rule_id") for v in result.get("violations", [])}
        missing = [r for r in expected_rules if r not in triggered]
        if missing:
            failures.append((name, sql, missing, triggered))
            print(f"  FAIL  {name}: expected {expected_rules}, missing {missing}")
            print(f"        triggered: {triggered}")
        else:
            print(f"  PASS  {name} (triggered {expected_rules})")
    return failures


def main():
    print("=" * 60)
    print("GOOD SQL CASES (expect zero ERROR/WARNING violations)")
    print("=" * 60)
    good_failures = run_good_cases()

    print()
    print("=" * 60)
    print("BAD SQL CASES (expect specific rule violations)")
    print("=" * 60)
    bad_failures = run_bad_cases()

    print()
    print("=" * 60)
    total_fail = len(good_failures) + len(bad_failures)
    print(f"TOTAL: {len(GOOD_CASES) + len(BAD_CASES)} cases, "
          f"{len(GOOD_CASES) + len(BAD_CASES) - total_fail} passed, "
          f"{total_fail} failed")
    print("=" * 60)
    return 1 if total_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
