# ELB Monitoring Report Format

## Report Template

```
## ELB Monitoring Report
**Load Balancer**: <loadbalancer-name> (<loadbalancer-id>)
**ELB Type**: <Dedicated/Shared>
**Region**: <region>
**Time Range**: <start-time> to <end-time>

### Key Metrics Summary
- Concurrent Connections: XX (avg), XX (max), XX (min)
- Active Connections: XX (avg), XX (max), XX (min)
- Inbound Bandwidth: XX.XX Mbps (avg)
- Outbound Bandwidth: XX.XX Mbps (avg)
- [Dedicated ELB Only] HTTP 5xx Error Rate: XX.XX% (avg)

### Connection Metrics
| Time | Concurrent Connections | Active Connections | New Connections/sec |
|------|----------------------|-------------------|-------------------|
| ...  | ...                  | ...               | ...               |

### Traffic Metrics
| Time | Inbound Bandwidth | Outbound Bandwidth | Inbound Packets | Outbound Packets |
|------|------------------|-------------------|----------------|-----------------|
| ...  | ...              | ...               | ...            | ...             |

### HTTP Metrics (Dedicated ELB Only)
| Time | HTTP 2xx | HTTP 4xx | HTTP 5xx | 2xx Ratio | 4xx Ratio | 5xx Ratio |
|------|----------|----------|----------|-----------|-----------|-----------|
| ...  | ...      | ...      | ...      | ...       | ...       | ...       |

### Recommendations
1. [If concurrent connections > 80% of limit] Consider scaling up ELB specification
2. [If HTTP 5xx ratio > 1%] Check backend server health and configuration
3. [If bandwidth > 80% of limit] Consider upgrading bandwidth or optimizing traffic
4. [If active connections consistently high] Review connection timeout settings
5. [Dedicated ELB] Consider enabling traffic mirroring for deep packet inspection
```
