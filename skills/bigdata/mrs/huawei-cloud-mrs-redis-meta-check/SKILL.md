---
name: huawei-cloud-mrs-redis-meta-check
description: |
  Checks Redis cluster metadata files (nodes-*.conf) for integrity, detecting 7 categories of metadata issues that cause Redis instance startup failures, connection anomalies, and fault alerts.
  执行7项检查：slot槽位完整性、master/slave实例个数、文件格式(4个模块)、文件名端口一致性、端口关系、主备关系、myself标记。
  Use this skill when the user mentions Redis metadata file checks, nodes-*.conf checks, or Redis cluster configuration checks.
  Use it whenever the user asks about Redis startup failures or connection anomalies.
  Trigger: "Redis元数据检查", "Redis nodes检查", "Redis cluster配置检查", "检查Redis元数据", "Redis元数据校验", "Redis启动失败排查"
tags: [mrs, redis, meta, nodes-conf]
version: 1.0.0
---

# MRS Redis Metadata Check Skill

You are an MRS Redis metadata file checking expert, responsible for checking the integrity of Redis cluster metadata configuration files (nodes-*.conf). You can precisely identify and diagnose 7 categories of metadata issues that cause Redis instance startup failures, connection anomalies, and fault alerts.

## 1. Overview

**Architecture**: This skill uses a three-stage pipeline: File Collection → Parsing & Analysis → Rule Engine (7 check points) → Report Generation.

**Applicable Scenarios**:

- Redis instance startup failure alert
- Redis connection anomaly alert
- Redis instance fault alert
- User explicitly requests checking nodes-*.conf file
- Routine metadata integrity check for Redis cluster

**Typical Use Cases**:

- "Redis instance on host-01 failed to start, check the metadata file"
- "Check if this nodes-22400.conf is correct"
- "Redis connection is abnormal, help check the cluster configuration"
- "Verify the integrity of Redis cluster metadata"
- "Check the nodes.conf file for slot coverage"

**Check Points (7 items)**:

| Check ID | Name | Level | Description |
| ---------- | ------ | ------- | ------------- |
| CHK001 | Slot Completeness | ERROR | All master instances' slot ranges must cover 0-16383 (16384 slots total), no gaps or overlaps |
| CHK002 | Master/Slave Count Consistency | ERROR | Master and slave instance counts must be equal, total must be even |
| CHK003 | File Format Completeness | ERROR | File must contain 4 modules: Connection, Epoch, Whitelist, Cluster-name |
| CHK004 | Filename-Port Consistency | ERROR | Port in filename (e.g., nodes-22400.conf) must match myself-marked line's port |
| CHK005 | Port Relationship | ERROR | Cluster port - Service port must equal 1950 for each instance |
| CHK006 | Master-Slave Relationship | ERROR | Each master can have at most 1 slave |
| CHK007 | Myself Marker | ERROR | File must contain exactly one myself-marked line |

**Default Check Path**: `/srv/BigData/redis_meta/Redis_*/nodes-224*.conf`

Users can also specify a specific file path for checking.

## 2. Prerequisites

### 2.1 Environment Requirements

- Access to MRS cluster host (for file collection)
- `omm` user permissions for reading Redis metadata files
- No additional software or Python packages required

### 2.2 Security Rules

- This skill performs static file analysis only, no Redis cluster connection required
- File content is processed locally, no data is sent externally
- No credentials or authentication required for the checking process itself
- File collection from cluster hosts requires appropriate access permissions

## 3. Workflow

### Step 1: Collect Files

If the user has already provided the nodes-*.conf file, skip this step and proceed to Step 2.

If the user has not provided a file, reply with the directory where the required files are located and ask the user to provide the file, following the guidance below:

#### 1.1 Identify Target Hosts

Log in to MRS Console → Redis → Redis Management → Redis logical cluster name → Abnormal instances, check the host IP of the abnormal instance.

Redis logical clusters are typically deployed across multiple hosts. The nodes-*.conf files on each host in the same cluster share the same content (all instances in the same cluster share the same cluster topology, except for the myself flag which differs). Therefore, you only need to collect from any one host in the cluster. However, if you are unsure which hosts belong to the same cluster, it is recommended to collect from the host where the abnormal instance is located. After collecting a normal instance's node-conf file, use this skill to verify the file first, then proceed with the repair.

#### 1.2 Collect Files

The skill performs static analysis only and **cannot connect to the MRS cluster host to execute commands**. Do not attempt to run `ls`/`cp` etc.; instead, reply with the directory where the required files are located and ask the user to provide the file.

The required files are located in the following directory on the target host:

```text
/srv/BigData/redis_meta/Redis_*/nodes-224*.conf
```

Typical layout on the host:

```text
/srv/BigData/redis_meta/Redis_1/nodes-22400.conf
/srv/BigData/redis_meta/Redis_2/nodes-22401.conf
/srv/BigData/redis_meta/Redis_3/nodes-22402.conf
...
```

##### Scenario A: Instance running normally, routine check

Reply with the directory above and ask the user to provide any one `nodes-*.conf` file (files on the same host have identical content).

##### Scenario B: Instance abnormal and cannot start, need to collect file for analysis

When the instance is abnormal, the file still exists on disk. Reply with the directory above and ask the user to provide:

1. The file corresponding to the abnormal instance, e.g., `/srv/BigData/redis_meta/Redis_1/nodes-22400.conf`
2. A normal instance's file from the same host for comparison, e.g., `/srv/BigData/redis_meta/Redis_2/nodes-22401.conf`

Note: Reading these files on the host requires `omm` user permissions.

#### 1.3 Common Issues

| Issue | Cause | Solution |
| ------- | ------- | ---------- |
| `No such file or directory` | Instance not installed or wrong path | On the host, run `ls /srv/BigData/redis_meta/` to check which Redis_X directories exist |
| Directory exists but no nodes-*.conf file | Instance not initialized or file was deleted | Copy from another normal instance on the same host (must correct myself marker before use) |
| Permission denied | Need omm user permissions | On the host, use `su - omm` to switch user before operating |

### Step 2: Locate Files

If the user has not specified a specific file:

1. Search for `nodes-224*.conf` files in the user-provided directory or files
2. If not found, expand the search scope to find `nodes-*.conf` or `*.conf` files in the directory and subdirectories
3. List all matching files
4. Let the user select which file to check, or check all files

If the user has specified a file:

1. First search by the specified path
2. If not found, recursively search in the specified directory and subdirectories
3. If a single file is found, regardless of whether the filename conforms to naming conventions, read the content directly for analysis
4. If the content conforms to Redis metadata format (contains node ID, role, slot info, etc.), execute the check

### Step 3: Parse Files

Use the parse commands in [Section 4.1](#41-parse-file-content) to extract key information:

- All node lines (Connection module)
- Myself line
- Vars line (Epoch module)
- Whitelist line
- Cluster-name line

### Step 4: Execute 7 Check Points

#### CHK001: Slot Completeness

**Check Content**:

- All master instances' slot ranges must cover 0-16383, totaling 16384 slots
- Master instances must have slot information (e.g., `0-5460`)
- Slave instances should not have slot information

**Check Method**:

1. Extract all master nodes' slot ranges
2. Merge all slot ranges, ensure coverage of 0-16383 with no gaps or overlaps
3. Check if slave nodes incorrectly have slots

**Pass Criteria**: Slot ranges completely cover 0-16383

#### CHK002: Master/Slave Count Consistency

**Check Content**:

- Master and slave instance counts must be consistent
- Total count must be even

**Check Method**:

1. Count master nodes (including myself,master or standalone master)
2. Count slave nodes
3. Verify counts are equal and total is even

**Pass Criteria**: master count = slave count, and total is even

#### CHK003: File Format Completeness (4 modules)

**Check Content**: File must contain the following 4 modules with complete format

**Module 1: Connection Module**

- Format: `NodeID "IP:port@cluster_port" role master_nodeID ... connected`
- Example: `155ce4426e976bc65240829943a2acd8c05806ce "hosts1:22401@24351" slave df37138a11e6708563fdb0962a73a6ae20281b60 0 1777455797875 3 connected`

**Module 2: Epoch Module**

- Format: `vars currentEpoch N lastVoteEpoch N`
- Example: `vars currentEpoch 10 lastVoteEpoch 10`

**Module 3: Whitelist Module**

- Format: `whitelist "IP1" "IP2" ...`
- Example: `whitelist "hosts3" "hosts2" "hosts1"`

**Module 4: Cluster-name Module**

- Format: `cluster-name name`
- Example: `cluster-name test`

**Check Method**:

1. Check if vars line exists (Epoch module)
2. Check if whitelist line exists (Whitelist module)
3. Check if cluster-name line exists (Cluster-name module)
4. Check if connection module lines have abnormal characters (broken entries, special characters, etc.)

**Pass Criteria**: All 4 modules exist with correct format

#### CHK004: Filename-Port Consistency

**Check Content**:

- The port number in the filename (e.g., nodes-22400.conf) must match the port in the myself-marked line
- Example: In nodes-22400.conf, the myself mark should be `hosts1:22400`

**Check Method**:

1. Extract port number from filename (e.g., 22400)
2. Extract port number from myself-marked line
3. Verify they are consistent

**Pass Criteria**: Filename port = myself-marked port

#### CHK005: Port Relationship

**Check Content**:

- Each master-slave instance pair's port relationship must satisfy: `cluster_port - service_port = 1950`
- Example: 22401@24351, 24351-22401=1950

**Check Method**:

1. Extract all nodes' service_port@cluster_port
2. Verify each pair's port difference is 1950

**Pass Criteria**: All port pairs have a difference of 1950

#### CHK006: Master-Slave Relationship

**Check Content**:

- Each master instance can only match one slave instance
- If a master matches multiple slaves, it fails

**Check Method**:

1. Extract each slave's master node ID
2. Count the number of slaves for each master node
3. Verify each master node has at most one slave

**Pass Criteria**: Each master corresponds to at most 1 slave

#### CHK007: Myself Marker

**Check Content**:

- The file must contain a line with the myself marker
- This line represents the current node's identity

**Check Method**:

1. Search for lines containing "myself"
2. Verify the myself line format is correct
3. Verify there is exactly one myself marker in the entire file

**Pass Criteria**: Exactly one myself-marked line exists

### Step 5: Generate Report

Generate the check report following the format defined in [Section 8: Output Format](#8-output-format).

When the overall result is **FAIL**, the report must append repair guidance at the end. The repair guidance:

- Lists each failed check point's issue description
- References the general repair method in [Section 6](#6-general-repair-method-with-example)
- For the myself marker correction step, provides before/after modification examples based on actual data from the analyzed file (node ID, IP, port, role, master node ID), not generic placeholders like `xxxxxxxx`

Specific steps for constructing the myself marker example:

1. Extract the abnormal instance's node ID, IP, port, role, master node ID from the myself line
2. Assuming copying from another normal instance on the same host, construct the before/after modification comparison example
3. The example must include at least the modification comparison of the abnormal instance port line and the normal instance port line

## 4. Core Commands

### 4.1 Parse File Content

```bash
# Extract all node lines (Connection module)
grep -v "^vars\|^whitelist\|^cluster-" "$file"

# Extract myself line
grep "myself" "$file"

# Extract vars line (Epoch module)
grep "^vars" "$file"

# Extract whitelist line
grep "^whitelist" "$file"

# Extract cluster-name line
grep "^cluster-name" "$file"
```

## 5. Common Issues & Troubleshooting

| Issue | Cause | Impact | Solution |
| ------- | ------- | -------- | ---------- |
| Slot gaps/overlaps | Master node slot range misconfigured | Redis instance cannot start, cluster state abnormal | General repair method |
| Master/Slave count mismatch | Node not properly joined cluster, or master-slave relationship misconfigured | Cluster master-slave relationship abnormal, failover may fail | General repair method |
| Missing myself marker | File corruption or node not initialized | Redis instance cannot identify itself, startup fails | General repair method |
| Port relationship error | Port configuration error, service port and cluster port difference is not 1950 | Abnormal communication between cluster nodes | General repair method |
| Incomplete file format | Missing vars/whitelist/cluster-name modules, or connection module lines have abnormal characters | Redis instance fails to parse metadata at startup | General repair method |
| Filename-port mismatch | nodes-*.conf file incorrectly copied or renamed | Redis instance cannot find correct metadata file | General repair method |

## 6. General Repair Method (with Example)

All issues can be repaired using the following general method.

**Scenario**: Host `host-01` has an abnormal `Redis_1` instance (port 22400); `Redis_2` (port 22401) on the same host is normal.

1. **Stop the abnormal instance**: MRS Console → Redis → Instances → select the abnormal instance → **Stop Instance**
2. **Back up its metadata file** (on the host, as `omm`):
   ```bash
   cd /srv/BigData/redis_meta/Redis_1 && mv nodes-22400.conf nodes-22400.conf_bak
   ```
3. **Copy metadata file from the normal instance**:
   ```bash
   cp /srv/BigData/redis_meta/Redis_2/nodes-22401.conf /srv/BigData/redis_meta/Redis_1/nodes-22400.conf
   ```
4. **Verify the copied file**: Use this skill to run the 7 check points on `/srv/BigData/redis_meta/Redis_1/nodes-22400.conf`. If verification fails, copy from another normal instance and verify again before continuing.
5. **Correct the myself marker** in `/srv/BigData/redis_meta/Redis_1/nodes-22400.conf`:
   - Remove the existing `myself,` (it belongs to the copied normal instance)
   - Add `myself,` before the role marker on the line containing the abnormal instance port (`host-01:22400`), e.g. `myself,master` / `myself,slave`
   - `myself` must appear exactly once in the entire file
6. **Start the abnormal instance**: MRS Console → Redis → Instances → select the instance → **Start Instance**
7. **Confirm recovery**: Instance status returns to Good and the Redis logical cluster status returns to normal
8. **Clean up the backup file** (on the host):
   ```bash
   rm -f /srv/BigData/redis_meta/Redis_1/nodes-22400.conf_bak
   ```

## 7. Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `file_path` | Optional | Path to nodes-*.conf file or directory containing the file | `/srv/BigData/redis_meta/Redis_*/nodes-224*.conf` |
| `check_points` | Optional | Specific check point IDs to run (CHK001-CHK007), comma-separated | All 7 check points |

## 8. Output Format

The check report is output in plain text format:

```text
========================================
Redis Metadata File Check Report
File: /path/to/nodes-22400.conf
========================================

[CHK001: Slot Completeness]
Result: PASS/FAIL
Details: ...

[CHK002: Master/Slave Count Consistency]
Result: PASS/FAIL
Details: ...

... (other check points)

========================================
Overall Result: PASS/FAIL
========================================
```

Each check result includes: check ID, check name, result (PASS/FAIL), and detailed description of any issues found.

When the overall result is **FAIL**, append a `[Repair Guidance]` section at the end. The repair guidance lists each failed check point's issue description, then references the general repair method in [Section 6](#6-general-repair-method-with-example). The myself marker correction step must include a before/after modification example using actual data from the analyzed file:

```text
[Repair Guidance]

(List each failed check point's issue description)

The above issues are applicable to the general repair method (see Section 6):
  Step 1: Stop the abnormal instance
  Step 2: Back up the metadata file
  Step 3: Copy metadata file from a normal instance on the same host
  Step 4: Verify the copied file (run this skill's 7 check points)
  Step 5: Correct the myself marker (see example below)
  Step 6: Start the abnormal instance
  Step 7: Confirm recovery
  Step 8: Clean up backup file

  Step 5 myself marker modification example (must use actual data, not placeholders):

  vi /srv/BigData/redis_meta/Redis_1/nodes-22400.conf

  Before modification (copied from normal instance, myself is on normal instance port line):
  <actual node ID> "<actual IP>:<abnormal port>@<cluster port>" <role> <master node ID> 0 <epoch> <epoch> connected
  <actual node ID> "<actual IP>:<normal port>@<cluster port>" myself,<role> <master node ID> 0 <epoch> <epoch> connected

  After modification (remove myself from normal port, add myself to abnormal port line):
  <actual node ID> "<actual IP>:<abnormal port>@<cluster port>" myself,<role> <master node ID> 0 <epoch> <epoch> connected
  <actual node ID> "<actual IP>:<normal port>@<cluster port>" <role> <master node ID> 0 <epoch> <epoch> connected

  Key points:
  - Remove the existing "myself," (belongs to the copied normal instance)
  - Add "myself," before the role marker on the line with the abnormal instance port
  - "myself," must immediately precede the role marker, e.g., myself,master or myself,slave
  - "myself" can only appear once in the entire file
```

**Key Requirement**: The myself marker modification example must use actual data from the analyzed file (node ID, IP, port, role, master node ID), not generic placeholders.

## 9. Best Practices

1. **Collect from the same logical cluster**: The source instance for copying must be in the same logical cluster as the abnormal instance and in a normal state
2. **Verify before repair**: Always use this skill to verify the copied file before modifying the myself marker
3. **Always back up**: Back up the original file before any repair operations to enable rollback
4. **Precise myself correction**: The myself marker must appear exactly once in the entire file, on the line corresponding to the target instance's port
5. **Cross-host copying**: If no normal instance is available on the same host, you can copy from another host's instance in the same cluster, but the myself marker correction method remains the same
6. **Check file format first**: When multiple check points fail, prioritize fixing file format issues (CHK003) before other issues

## 10. References

| Reference | Description | Related Section |
|-----------|-------------|-----------------|
| [Correct Format Example](#101-correct-format-example) | Complete example of a valid nodes-*.conf file demonstrating all 7 check points | [3. Workflow](#3-workflow), [4. Core Commands](#4-core-commands) |
| MRS Redis Product Documentation | Redis cluster topology, nodes-*.conf metadata file structure, and fault diagnosis | [1. Overview](#1-overview) |
| Redis Cluster Operation Guide | Redis Cluster slot allocation (0-16383), master-slave relationship, and port planning | [3. Workflow](#3-workflow), [6. General Repair Method](#6-general-repair-method-with-example) |

### 10.1 Correct Format Example

A complete example of a valid nodes-*.conf file:

```text
155ce4426e976bc65240829943a2acd8c05806ce "hosts1:22401@24351" slave df37138a11e6708563fdb0962a73a6ae20281b60 0 1777455797875 3 connected
df37138a11e6708563fdb0962a73a6ae20281b60 "hosts2:22400@24350" master - 0 1777455797000 3 connected 10922-16383
f45e8f5d2f89684f9918eb48f60aa5529f2eb498 "hosts3:22400@24350" master - 0 1777455797558 10 connected 5461-10921
8ac5474a124cb0163d92d6921caca52543bcc2f4 "hosts2:22401@24351" slave f45e8f5d2f89684f9918eb48f60aa5529f2eb498 0 1777455797000 10 connected
933540f40adf21a0d580ab5d6d65252da72f6c0d "hosts1:22400@24350" myself,master - 0 1777455797000 1 connected 0-5460
d3da600c0db267fdb18776e44347fa5140cdde21 "hosts3:22401@24351" slave 933540f40adf21a0d580ab5d6d65252da72f6c0d 0 1777455797672 1 connected
vars currentEpoch 10 lastVoteEpoch 10
whitelist "hosts3" "hosts2" "hosts1"
cluster-name test
```

## 11. Notes

1. **This skill performs static file analysis only**, no Redis cluster connection required
2. **Same-cluster files are identical except for the myself marker**: All nodes-*.conf files from the same Redis logical cluster have identical content except for the myself flag position
3. **Port difference of 1950**: In MRS Redis, the cluster port always equals the service port + 1950
4. **Slot range 0-16383**: Redis Cluster has 16384 slots (0-16383), all must be covered by master nodes
5. **myself uniqueness**: Each nodes-*.conf file must have exactly one myself marker, representing the current node's identity
6. **File collection requires omm permissions**: Reading Redis metadata files from cluster hosts requires omm user permissions
7. **Repair guidance must use actual data**: When generating repair guidance, the myself marker modification example must use actual node IDs, IPs, and ports from the analyzed file, not generic placeholders
