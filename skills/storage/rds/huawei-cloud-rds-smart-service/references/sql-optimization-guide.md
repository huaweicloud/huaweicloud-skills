# SQL Performance Optimization Guide

## Methodology

### Step 1: Identify Slow SQL

```bash
# Query slow logs (last 24 hours)
hcloud RDS ListSlowLogs --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z

# Query TOP SQL by execution time
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=20

# Query historical TOP SQL (last 7 days)
hcloud RDS ListHistoryTopSqls --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-07T23:59:59Z
```

### Step 2: Analyze Wait Events

```bash
# Query wait events to understand bottlenecks
hcloud RDS ListHistoryWaitEvents --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-01T00:00:00Z --end_date=2024-01-01T23:59:59Z
```

**Common Wait Events**:

| Wait Event | Meaning | Optimization |
|------------|---------|--------------|
| `lock_wait` | Row lock contention | Reduce transaction scope, optimize locking |
| `io_wait` | Disk I/O bottleneck | Increase `innodb_buffer_pool_size`, use SSD |
| `cpu_wait` | CPU intensive query | Optimize query, add indexes |
| `memory_wait` | Memory pressure | Increase instance size, optimize sort operations |

### Step 3: Identify Hotspot Objects

```bash
# Show tables/indexes with highest load
hcloud RDS ShowTopObjects --cli-region=cn-north-4 --instance_id={instance_id}
```

### Step 4: Apply Optimizations

#### Index Optimization

- **Missing Index**: Add index on columns used in WHERE/JOIN/ORDER BY
- **Redundant Index**: Remove duplicate or unused indexes
- **Composite Index**: Create multi-column index for frequently co-queried columns
- **Covering Index**: Include all needed columns to avoid table lookup

#### Query Rewrite

| Anti-Pattern | Optimization |
|-------------|--------------|
| `SELECT *` | Select only needed columns |
| `NOT IN (subquery)` | Use `LEFT JOIN ... WHERE ... IS NULL` |
| `OR conditions` | Use `UNION ALL` for non-overlapping sets |
| `LIKE '%pattern%'` | Use full-text index or reverse prefix |
| `COUNT(*)` on large table | Use approximate count or maintain counter |
| Nested subqueries | Rewrite as JOINs |

#### Parameter Tuning for Performance

```bash
# Show current parameters
hcloud RDS ShowInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id}

# Key parameters to tune:
# - innodb_buffer_pool_size: 50-70% of total memory
# - innodb_io_capacity: match disk IOPS (SSD: 2000-10000)
# - innodb_read_io_threads: 4-8 for multi-core
# - innodb_write_io_threads: 4-8 for multi-core
# - sort_buffer_size: 2-4MB per session
# - join_buffer_size: 2-4MB per session
# - max_connections: based on application needs
```

#### SQL Concurrency Control

```bash
# Set SQL limit to control concurrency of specific SQL
hcloud RDS CreateSqlLimit --cli-region=cn-north-4 --instance_id={instance_id} \
  --sql_limit_rule='{"sql_id":"xxx","max_concurrency":10}'
```

### Step 5: Verify Optimization

```bash
# After optimization, re-check TOP SQL
hcloud RDS ListTopSqls --cli-region=cn-north-4 --instance_id={instance_id} --limit=20

# Compare wait events before and after
hcloud RDS ListHistoryWaitEvents --cli-region=cn-north-4 --instance_id={instance_id} \
  --start_date=2024-01-02T00:00:00Z --end_date=2024-01-02T23:59:59Z
```

## Engine-Specific Optimization

### MySQL

- Use `EXPLAIN` to analyze execution plan
- Enable slow query log with `long_query_time = 1`
- Monitor `InnoDB` buffer pool hit ratio (should be > 95%)
- Consider read replicas for read-heavy workloads

### PostgreSQL

- Use `EXPLAIN ANALYZE` for detailed execution plan
- Monitor `pg_stat_activity` for long-running queries
- Tune `shared_buffers` (25% of total memory)
- Use `pg_stat_statements` extension for query statistics

### SQL Server

- Use execution plan analysis via SQL Server Management Studio
- Monitor `sys.dm_exec_requests` for active queries
- Tune `max server memory` (leave 2-4GB for OS)
- Consider indexed views for complex aggregations

## Optimization Checklist

- [ ] Identified TOP 10 slow SQL statements
- [ ] Analyzed wait events for bottleneck type
- [ ] Identified hotspot tables/indexes
- [ ] Added missing indexes on critical columns
- [ ] Rewrote inefficient SQL patterns
- [ ] Tuned database parameters (buffer pool, I/O)
- [ ] Set SQL concurrency limits for problematic queries
- [ ] Verified performance improvement after changes
- [ ] Documented optimization changes for rollback
