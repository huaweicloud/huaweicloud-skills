# Pre-Migration Technical Checklist for SMS

Before creating an SMS migration task, verify all items below to ensure uninterrupted replication, zero pre-check warnings, and smooth cutover.

---

## 0. Phase 1 Discovery & Registration State Decision Tree

Depending on whether the source server has the SMS Agent already installed, Phase 1 evaluation branches into two scenarios:

```
                      Query SMS Servers:
             hcloud SMS ListServers --limit=10
                             |
             +---------------+---------------+
             |                               |
    [Scenario A: Found]             [Scenario B: Not Found]
             |                               |
    Inspect ShowServer output       Perform Preliminary Offline Checks
    • Automated 14 Pre-Checks       • OS distribution & kernel version
    • Disk partition layout         • Clock drift (NTP ≤ 15 min)
    • Health: "waiting-migrate"     • Outbound TCP 443 to SMS API
             |                      • Target SG: TCP 22, 8899, 8900
    SKIP Phase 2 Agent Deploy                |
             |                      Proceed to Phase 2: Deploy Agent
    Proceed to Phase 3: Templates            |
                                    Poll ListServers until registered
```

- **Scenario A (Agent Already Installed & Registered)**:
  - Locate the host via `hcloud SMS ListServers --cli-region={region}`. All 14 diagnostic check items (`OS_VERSION`, `FIRMWARE`, `CPU`, `MEMORY`, `DISK_INFO`, `PARTITION_STYLE`, `DISK_USED_SIZE`, `FILE_SYSTEM`, `FREE_SPACE`, `OEM_SYSTEM`, `DRIVER_FILE`, `SERVICE`, `ACCOUNT_RIGHTS`, `DISK_PERFORMANCES`) are run **automatically** by the Agent daemon.
  - Review check status via `hcloud SMS ShowServer --cli-region={region} --source_id={source_server_id}`. If all items report `result: "OK"`, **skip Phase 2 (Agent Deployment)**.
- **Scenario B (Fresh Host / Agent Not Yet Installed)**:
  - The server is not yet registered in SMS.
  - Validate preliminary requirements in Sections 1 through 4 manually before downloading and executing the Agent installer. Query `ListServers` post-installation to confirm registration.

---

## 1. Network & Security Group Requirements (Target & Source)

SMS establishes dual-channel communication: a control channel to the Huawei Cloud SMS API and a high-speed replication channel between the source agent and the target ECS.

### 1.1 Target ECS Security Group Inbound Rules

The target ECS security group **must** allow specific inbound traffic from the source host based on the operating system:

| Source OS / Replication Type | Required Inbound Ports | Protocol | Source Address | Function Description |
|---|---|---|---|---|
| **Linux (`MIGRATE_FILE`)** | `22` | TCP | Source Server IP | • **Port 22**: Link initialization and secure rsync data transmission over SSH. |
| **Windows Server (`MIGRATE_BLOCK`)** | `22`, `8899`, `8900` | TCP | Source Server IP | • **Port 22**: Initialization and disk partitioning.<br>• **Port 8899**: Control channel and task state synchronization.<br>• **Port 8900**: Block data streaming channel. |

> [!IMPORTANT]
> - **Default Provisioning**: By default, create a dedicated new security group with minimal inbound rules restricted strictly to the source host IP.
> - **Source IP Selection**: Use the source public egress IP (`{source_public_ip}/32`) for internet migrations. Use the source private IP (`{source_private_ip}/32`) only when private network connectivity (VPN/Direct Connect) is established.
> - **Security Guardrail**: Never set the inbound source address to `0.0.0.0/0`.

### 1.2 Target ECS Security Group Outbound Rules

- **Port 443 (TCP)**: Outbound HTTPS access to Huawei Cloud internal services and SMS API endpoint (China Site: `sms.cn-north-4.myhuaweicloud.com`; International Site Singapore: `sms.ap-southeast-3.myhuaweicloud.com`).
- Allow all outbound within target VPC subnet for communication with DNS and metadata services.

### 1.3 Target Subnet Network ACL

If the target VPC subnet is associated with a Network ACL (NACL), ensure matching inbound rules (ports 22, 8899, 8900) and outbound ephemeral return ports (1024-65535) are permitted.

### 1.4 Source Host Outbound Firewall Rules

The source server must allow the following outbound traffic:
- **TCP 443**: Outbound HTTPS to the regional SMS control plane endpoint.
- **TCP 22, 8899, 8900**: Outbound to Target ECS IP (Public EIP or Private IP via VPN/Direct Connect).
- **Bandwidth**: Minimum 10 Mbps dedicated uplink recommended.

---

## 2. Operating System & Software Dependencies

### 2.1 Supported OS Families

| OS Family | Supported Versions | Prerequisites |
|---|---|---|
| **CentOS / RHEL** | 6.x, 7.x, 8.x, 9.x | `rsync`, `tar`, `nohup`, `python` |
| **Ubuntu** | 14.04, 16.04, 18.04, 20.04, 22.04 | `rsync`, `tar`, `nohup` |
| **Debian** | 8.x, 9.x, 10.x, 11.x | `rsync`, `tar`, `nohup` |
| **EulerOS / openEuler** | 2.x, 20.03, 22.03 | Fully certified native support |
| **Windows Server** | 2008 R2, 2012, 2012 R2, 2016, 2019, 2022 | PowerShell 3.0+, VSS (Volume Shadow Copy) service enabled |

### 2.2 System Time Synchronization (NTP Clock Drift)

- **Requirement**: The system clock on the source server **must not drift by more than 15 minutes** from standard UTC/CST time.
- **Impact**: Excessive time drift causes AK/SK signature verification failures during Agent startup (`SMS.6603`).
- **Fix**: Synchronize via `chrony` or `ntpdate` (`ntpdate pool.ntp.org` or `w32tm /resync`).

### 2.3 Firmware & Boot Mode Constraints (BIOS vs. UEFI)

- **Firmware Verification**: Check the `FIRMWARE` check item in `hcloud SMS ShowServer --source_id={source_id}`.
- **BIOS-boot Hosts & Linux**: Support automated target VM provisioning via SMS migration templates (`CreateTemplate` / `exist_server: false`).
- **UEFI Windows Hosts (Existing Server Mode Mandatory)**:
  - SMS **does not support automated VM provisioning via templates** for UEFI Windows hosts.
  - **Do NOT create a migration template**.
  - **Requirement**: You must pre-create a target ECS instance on Huawei Cloud first, ensuring the target ECS boot firmware is set to UEFI (`hw_firmware_type: "uefi"`) and disk capacities match or exceed the source disks.
  - In task creation, configure `"exist_server": true` and `"target_server.vm_id": "{target_ecs_vm_id}"`.

---

## 3. Storage, Disk & Partition Constraints

- **Free Disk Space**:
  - **Linux**: The root filesystem (`/`) must have at least **200 MB** of free disk space for temporary agent runtime caches.
  - **Windows**: Partitions ≥ 600 MB require at least **320 MB** free space; partitions < 600 MB require at least **40 MB** free space.
- **Maximum Disk Count**: Source server cannot exceed **23 physical disks** (Huawei Cloud ECS supports max 24 disks; 1 disk is temporarily reserved for the migration agent system image).
- **Maximum Disk Size**: Single destination disk on Linux should not exceed **16 TB** due to `mkfs` filesystem formatting limitations.
- **Partition Tables**: Both MBR and GPT partition styles are supported. Disks larger than 2 TB must use GPT.
- **Unsupported Filesystem Configurations**:
  - Nested LVM configurations are not supported.
  - Shared network filesystems (NFS, CIFS, NAS, OCFS2, GlusterFS) cannot be migrated via SMS block/file replication (use OMS or dedicated sync tools).

---

## 4. Hardware Sizing & Quotas

- **Instance Sizing**: Source and destination hosts must each have at least **1 vCPU and 1 GB RAM**.
- **SMS Concurrency**: Single Huawei Cloud account supports registering up to **1000 source servers** and up to **200 concurrent active migration tasks**.

---

## 5. Migration Task & Template Parameter Constraints

- **Task Name (`name`)**: Length must be 4–20 characters (`4 <= length <= 20`). Supported characters: alphanumeric, underscores (`_`), hyphens (`-`), and Chinese characters. Avoid overly long names.
- **Replication Type (`type`)**: Use `"MIGRATE_FILE"` for Linux and `"MIGRATE_BLOCK"` for Windows (do not reboot the source Windows host or restart SMS-Agent during migration).
- **Target OS Image (`image_id`)**: Query IMS via `--__platform` (`--__imagetype="gold"` for Linux; `--__imagetype="market"` with `--__platform="Windows"` for Windows).
- **Target Provisioning Mode (`exist_server` vs. `vm_template_id`)**:
  - **BIOS / Linux (Template Mode)**: Set `exist_server: false` and link `vm_template_id`.
  - **UEFI Windows (Existing Server Mode Mandatory)**: Set `exist_server: true`, specify `target_server.vm_id` pointing to the pre-created UEFI ECS, and omit `vm_template_id` (see Section 2.3).
- **Target Project ID (`project_id`)**: Query via `hcloud IAM KeystoneListProjects --name="{region}" --cli-query="projects[0].id"` (or list all via `hcloud IAM KeystoneListAuthProjects`).

### 5.1 Public vs. Private Network Parameter Comparison Matrix

| Component / Parameter | Public Internet Migration (Default) | Private Intranet Migration (VPN / Direct Connect / Peering) |
|---|---|---|
| **Network Infrastructure** | Source host has outbound internet access; Target ECS requires public EIP | Dedicated intranet connectivity established between source and target VPC |
| **Security Group Ingress (`remote_ip_prefix`)** | Source host's **public egress IP** (`{source_public_ip}/32`) | Source host's **private intranet IP** (`{source_private_ip}/32`) |
| **Template `publicip`** | `{ "type": "5_bgp", "bandwidth_size": 300, "bandwidth_share_type": "PER" }` (allocates pay-per-traffic EIP with 300 Mbit/s bandwidth) | `{}` (empty object; skips EIP creation to avoid public IP charges) |
| **Task `use_public_ip`** | `true` (routes replication traffic via target public EIP) | `false` (routes replication traffic via private intranet VPC routes) |
| **Task `migration_ip`** | `""` (auto-resolves newly allocated EIP) or target EIP if existing ECS | Target ECS private IP (e.g., `"172.16.10.100"`) or `""` if auto-assigned |


