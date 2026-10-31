# Backup Time Reference for Single-to-HA Conversion (RDS for MySQL)

> This reference supports the SKILL workflow Step 8 backup-handling confirmation. It documents the verified method for telling the user how long one full backup of the instance roughly takes.

## 1. Purpose

Before asking the user whether to keep the pre-conversion manual backup, the SKILL informs them how long one backup roughly takes. The reference time is obtained from the instance's real backup history when available, and from a conservative storage-based estimate otherwise.

## 2. Primary Reference — Latest Automatic Backup

Query the instance's automatic backups:

```bash
hcloud RDS ListBackups \
  --cli-region=<region> \
  --instance_id=<instance_id> \
  --backup_type=auto
```

Verified facts:

- The response is sorted strictly by `begin_time` in descending order, so the first record is the most recent automatic backup.
- The backup duration reference is `end_time - begin_time` of the first record.
- A full backup of the same instance takes a similar time regardless of whether it is automatic or manual (both are full backups).

Verified example (2026-10-21, instance `c29f...in01`, cn-north-4, 40 GB CLOUDSSD): the latest automatic backup ran `17:11:09 → 17:13:10`, i.e. **2 min 1 s (121 s)** for a 6198 KB backup.

## 3. Supplementary Reference — Latest Manual Backup

When the instance has no automatic backup record, query the manual backups:

```bash
hcloud RDS ListBackups \
  --cli-region=<region> \
  --instance_id=<instance_id> \
  --backup_type=manual
```

Use the first record's `end_time - begin_time` the same way.

Verified example (2026-10-22, same instance): the latest manual backup ran `11:39:56 → 11:41:06`, i.e. **1 min 10 s (70 s)**, with the same 6198 KB backup size.

## 4. Fallback — Conservative Storage-based Estimate

When the instance has no backup record at all, estimate the duration from the storage size:

```
estimate_seconds = storage_size_gb * 1024 / 100
```

The 100 MB/s throughput assumption is conservative. Verified against the real 40 GB CLOUDSSD instance, the estimate is `40 * 1024 / 100 = 409.6 s ≈ 6.8 min` versus an actual duration of about 121 s — the estimate is roughly **3.4x larger** than reality, so it is presented as a conservative upper bound with "actual usually shorter".

## 5. Presentation

The reference is informational only. It helps the user decide whether to keep the manual backup; it is not a hard gate on skipping the backup. The number is always framed as approximate.
