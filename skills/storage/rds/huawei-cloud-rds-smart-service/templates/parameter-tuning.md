# RDS Parameter Tuning Template

## MySQL 8.0 Recommended Parameters

### Memory Optimization
| Parameter | Formula | Example (8GB) |
|-----------|---------|---------------|
| innodb_buffer_pool_size | 60-70% of total RAM | 5GB |
| innodb_log_buffer_size | 16-64MB | 32MB |
| sort_buffer_size | 2-4MB per session | 4MB |
| join_buffer_size | 2-4MB per session | 4MB |
| read_buffer_size | 1-2MB per session | 2MB |
| tmp_table_size | 32-128MB | 64MB |
| max_heap_table_size | 32-128MB | 64MB |

### I/O Optimization
| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| innodb_io_capacity | 2000 (SSD) / 200 (HDD) | I/O capacity for background operations |
| innodb_io_capacity_max | 4000 (SSD) / 400 (HDD) | Max I/O capacity |
| innodb_flush_method | O_DIRECT | Avoid double buffering |
| innodb_read_io_threads | 4-8 | Read I/O threads |
| innodb_write_io_threads | 4-8 | Write I/O threads |

### Connection Optimization
| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| max_connections | 500-2000 | Based on application needs |
| wait_timeout | 28800 | Connection idle timeout (seconds) |
| interactive_timeout | 28800 | Interactive connection timeout |
| thread_cache_size | 50-100 | Thread cache size |

### Logging Optimization
| Parameter | Recommended | Description |
|-----------|-------------|-------------|
| slow_query_log | ON | Enable slow query log |
| long_query_time | 1.0 | Threshold for slow query (seconds) |
| log_queries_not_using_indexes | ON | Log queries without indexes |

## PostgreSQL Recommended Parameters

| Parameter | Formula | Example (8GB) |
|-----------|---------|---------------|
| shared_buffers | 25% of total RAM | 2GB |
| effective_cache_size | 75% of total RAM | 6GB |
| work_mem | 4-16MB per session | 8MB |
| maintenance_work_mem | 256-512MB | 512MB |
| max_connections | 100-500 | Based on application needs |
| random_page_cost | 1.1 (SSD) / 4.0 (HDD) | Random page cost |
| effective_io_concurrency | 200 (SSD) / 0 (HDD) | I/O concurrency |

## Applying Parameters

```bash
# Show current parameters
hcloud RDS ShowInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id}

# Update parameters (requires confirmation)
hcloud RDS UpdateInstanceConfiguration --cli-region=cn-north-4 --instance_id={instance_id} \
  --values='{"innodb_buffer_pool_size":"5G","innodb_io_capacity":"2000"}'

# Verify parameter change history
hcloud RDS ListInstanceParamHistories --cli-region=cn-north-4 --instance_id={instance_id}
```

## Important Notes

- Parameter changes may require instance restart
- Some parameters are dynamic (no restart needed), others are static (restart required)
- Always test parameter changes on non-production instances first
- Monitor instance performance after parameter changes
- Keep a record of parameter changes for rollback
