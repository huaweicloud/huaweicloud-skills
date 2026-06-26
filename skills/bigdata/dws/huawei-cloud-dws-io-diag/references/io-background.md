# I/O Background Knowledge - DWS I/O Overload Diagnosis

## RAID Architecture Background

- **System disks**: 2 disks in RAID1 (mirroring), specifications are already RAID group overall performance
- **Data disks**: 4-6 disks in RAID5 (parity), specifications are already RAID group overall performance
- **Key constraint**: iostat cannot precisely distinguish sequential I/O from random I/O ratio; each sdX device in iostat corresponds to one RAID group, thresholds are RAID group overall performance specifications, compare directly without multiplying by disk count
- **DWS data distribution is disk-based**: Data skew only causes single disk overload, not all disks overloaded simultaneously

## I/O Key Metric Thresholds

| Metric | Meaning | Threshold Judgment |
|--------|---------|-------------------|
| r/s, w/s | Read/Write IOPS | SSD upper limit 8000-20000/s; HDD sequential I/O upper limit 1000-2000/s, HDD random I/O upper limit 300-600/s (per RAID group) |
| rMB/s, wMB/s | Read/Write throughput | SSD upper limit 900-3500MB/s; HDD sequential I/O upper limit 250-800MB/s, HDD random I/O upper limit 130-240MB/s (per RAID group) |
| r_await, w_await | Average response time (ms) | Persistently > 100 indicates I/O bottleneck (occasional spikes are normal) |
| avgrq-sz | Average request size (KB) | Normal ~200; < 30 with high IOPS → highly suspect fragmented I/O |
| avgqu-sz | Average I/O queue depth | Persistently > 100 indicates severe I/O queue backlog, combined with await to judge I/O bottleneck |
| %util | Disk utilization | Only focus on whether persistently 99% or 100% |

## Three Major I/O Scenario Indicator Features

| Scenario | Features |
|----------|----------|
| **I/O Throughput Overload** | rMB/s+wMB/s reaching RAID group upper limit + util persistently 99%/100% + await persistently > 100 |
| **IOPS Overload** | r/s+w/s reaching RAID group upper limit + util persistently 99%/100% + await persistently > 100 |
| **I/O Anomaly** | IOPS and throughput far below minimum specification + await persistently > 100 + avgqu-sz persistently > 100 + util persistently 99%/100% |

## Important Principles

1. **Thresholds based on RAID group**: Each sdX device in iostat corresponds to one RAID group, thresholds are already RAID group overall performance specifications, compare directly, never multiply by disk count
2. **Throughput and IOPS independent judgment**: Both can be overloaded simultaneously, each must be judged independently. Throughput not overloaded but IOPS overloaded → only IOPS overload, not dual overload
3. **Anomaly feature**: Throughput and IOPS occasionally maxed out but await persistently high → prioritize I/O anomaly determination over overload
4. **DWS data distribution is disk-based**: Data skew only causes single disk overload; when encountering single node with all disks overloaded, must prioritize suspicion of node-level anomaly (RAID card read-write strategy degradation, RAID card CC verification, RAID card failure, etc.), rather than business overload
5. **User identity judgment**: Database user is omm or Ruby → system cause (e.g., autovacuum, topsql, log writing); other users → customer-side cause
