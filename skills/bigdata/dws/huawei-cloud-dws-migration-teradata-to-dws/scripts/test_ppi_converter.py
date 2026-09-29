#!/usr/bin/env python3
"""Test PPI converter against actual Teradata PPI DDLs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppi_converter import convert_ppi_ddl, is_ppi_table, get_distribute_clause

# Test DDLs from Teradata
test_ddls = {
    "app_sales.fact_cust_daily_snapshot": """CREATE SET TABLE app_sales.fact_cust_daily_snapshot ,FALLBACK ,
     NO BEFORE JOURNAL,
     NO AFTER JOURNAL,
     CHECKSUM = DEFAULT,
     DEFAULT MERGEBLOCKRATIO,
     MAP = TD_MAP1
     (
      snapshot_date DATE FORMAT 'YYYY-MM-DD' NOT NULL,
      cust_id INTEGER NOT NULL,
      daily_orders INTEGER DEFAULT 0 ,
      daily_spend DECIMAL(12,2) DEFAULT 0.00 ,
      accum_spend_mtd DECIMAL(12,2) DEFAULT 0.00 )
PRIMARY INDEX ( cust_id )
PARTITION BY RANGE_N(snapshot_date  BETWEEN DATE '2025-01-01' AND DATE '2026-12-31' EACH INTERVAL '1' DAY );""",

    "app_sales.fact_cust_snapshot_partitioned": """CREATE MULTISET TABLE app_sales.fact_cust_snapshot_partitioned ,FALLBACK ,
     NO BEFORE JOURNAL,
     NO AFTER JOURNAL,
     CHECKSUM = DEFAULT,
     DEFAULT MERGEBLOCKRATIO,
     MAP = TD_MAP1
     (
      cust_id BIGINT NOT NULL,
      snapshot_date DATE FORMAT 'YYYY-MM-DD' NOT NULL,
      cust_level VARCHAR(20) CHARACTER SET LATIN NOT CASESPECIFIC,
      total_orders_mtd INTEGER,
      total_amount_mtd DECIMAL(12,2))
PRIMARY INDEX ( cust_id )
PARTITION BY RANGE_N(snapshot_date  BETWEEN DATE '2026-01-01' AND DATE '2026-12-31' EACH INTERVAL '1' MONTH ,
 NO RANGE, UNKNOWN);""",

    "test_migration.trade_multi_ppi": """CREATE MULTISET TABLE test_migration.trade_multi_ppi ,FALLBACK ,
     NO BEFORE JOURNAL,
     NO AFTER JOURNAL,
     CHECKSUM = DEFAULT,
     DEFAULT MERGEBLOCKRATIO,
     MAP = TD_MAP1
     (
      trade_id BIGINT NOT NULL,
      region_id INTEGER NOT NULL,
      amount DECIMAL(15,2),
      trade_date DATE FORMAT 'YYYY-MM-DD' NOT NULL)
PRIMARY INDEX ( trade_id )
PARTITION BY ( RANGE_N(trade_date  BETWEEN DATE '2026-01-01' AND DATE '2026-12-31' EACH INTERVAL '1' MONTH ,
 UNKNOWN),CASE_N(
region_id =  1 ,
region_id =  2 ,
region_id =  3 ,
 NO CASE OR UNKNOWN) );""",
}

for name, ddl in test_ddls.items():
    print(f"\n{'='*80}")
    print(f"Table: {name}")
    print(f"{'='*80}")
    print(f"Is PPI: {is_ppi_table(ddl)}")
    print(f"Distribute: {get_distribute_clause(ddl)}")
    result = convert_ppi_ddl(ddl)
    if result:
        # Count partitions
        part_count = result.count('PARTITION p_')
        print(f"Partition count: {part_count}")
        # Print first 500 chars
        print(f"\nDWS Partition Clause (first 500 chars):")
        print(result[:500])
        if len(result) > 500:
            print(f"... ({len(result)} total chars)")
    else:
        print("ERROR: No partition clause generated!")
