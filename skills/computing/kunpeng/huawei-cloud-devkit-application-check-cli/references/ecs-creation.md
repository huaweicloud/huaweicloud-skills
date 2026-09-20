# Network Setup, Architecture Selection, ECS Creation & EIP Binding

## Step 3: Network Setup (VPC + Subnet + Security Group)

### Detection & Reuse Strategy

> 🔴 **CRITICAL — Programmatic Detection Required**: All resource detection steps (VPC, Subnet, Security Group, ECS) MUST use programmatic JSON parsing to filter results by name prefix. **NEVER rely on visual scanning of command output** — when a region has many resources (e.g., 77+ VPCs, 219+ Security Groups), the output will be truncated and visual scanning will miss matching resources. Always parse the complete JSON output (from persisted output file or piped through a JSON parser) using Python `json.loads()` or equivalent.

Before creating new network resources, **always detect existing ones** in the selected region first:

1. Query existing resources using **resource-type-specific naming prefix** (do NOT use a generic wildcard like `*-devkit-*`)
2. If found ? Present to user and ask for confirmation to reuse
3. If user agrees ? Reuse existing resources
4. If user declines or none found ? Create new resources

> **?? CRITICAL**: NEVER reuse existing resources without explicit user consent. Always ask first.

> **?? PARAMETER CONFIRMATION (MANDATORY)**: Before creating ANY network resource (VPC, Subnet, Security Group), AI MUST present all parameters (name, CIDR, rules) to the user for explicit confirmation. NO defaults. NO execution without user approval.

### Detection Prefix Rules

Each resource type uses its **own specific prefix** for detection. Do NOT cross-match or use a generic pattern.

| Resource Type | Detection Prefix | New Resource Name |
|---------------|-----------------|-------------------|
| VPC | `devkit-vpc-*` | `devkit-vpc-{timestamp}` |
| Subnet | `devkit-subnet-*` | `devkit-subnet-{timestamp}` |
| Security Group | `devkit-secgroup-*` | `devkit-secgroup-{timestamp}` |

### Step 3.1: Detect Existing VPC

> ⚠️ **MANDATORY Programmatic Filtering**: When listing resources, ALWAYS parse the complete JSON output programmatically (e.g., Python `json.loads`) to filter by name prefix. Do NOT rely on visual scanning of command output — large outputs may be truncated and cause missed detections. Use the persisted output file or pipe to a JSON parser.

```bash
hcloud VPC ListVpcs --cli-region=${HUAWEI_REGION} --limit=500
```

Filter VPCs with name matching `devkit-vpc-*` **using programmatic JSON parsing** (not visual scanning). Example:

```python
# Parse the full JSON output and filter by prefix
import json
data = json.loads(full_output)  # full_output = complete command output
devkit_vpcs = [v for v in data.get('vpcs', []) if v['name'].startswith('devkit-vpc-')]
for v in devkit_vpcs:
    print(f"Name: {v['name']}, ID: {v['id']}, CIDR: {v['cidr']}")
```

If found:

```
Found existing VPC(s) in region ${HUAWEI_REGION}:
  1. devkit-vpc-20260804 (ID: xxx, CIDR: 192.168.0.0/16)
  2. devkit-vpc-20260805 (ID: yyy, CIDR: 192.168.0.0/16)

Reuse existing VPC? (yes/no)
```

- **User says yes** ? Use selected VPC, proceed to Step 3.2 (detect subnet)
- **User says no or none found** ? Create new VPC

#### Create New VPC

```bash
hcloud VPC CreateVpc --cli-region=${HUAWEI_REGION} --vpc.name=devkit-vpc-{timestamp} --vpc.cidr=192.168.0.0/16
```

### Step 3.2: Detect Existing Subnet

> ⚠️ **MANDATORY Programmatic Filtering**: Always parse the complete JSON output programmatically to filter by name prefix. Do NOT rely on visual scanning — large outputs may be truncated.

```bash
hcloud VPC ListSubnets --cli-region=${HUAWEI_REGION} --vpc_id=${VPC_ID} --limit=500
```

Filter subnets with name matching `devkit-subnet-*` **using programmatic JSON parsing**. If found:

```
Found existing Subnet(s) under VPC ${VPC_ID}:
  1. devkit-subnet-20260804 (ID: xxx, CIDR: 192.168.0.0/24)

Reuse existing Subnet? (yes/no)
```

- **User says yes** ? Use selected Subnet, proceed to Step 3.3 (detect security group)
- **User says no or none found** ? Create new Subnet

#### Create New Subnet

```bash
hcloud VPC CreateSubnet --cli-region=${HUAWEI_REGION} --subnet.name=devkit-subnet-{timestamp} --subnet.cidr=192.168.0.0/24 --subnet.vpc_id=${VPC_ID} --subnet.gateway_ip=192.168.0.1
```

### Step 3.3: Detect Existing Security Group

> ⚠️ **MANDATORY Programmatic Filtering**: Always parse the complete JSON output programmatically to filter by name prefix. Do NOT rely on visual scanning — large outputs may be truncated.

```bash
hcloud VPC ListSecurityGroups --cli-region=${HUAWEI_REGION} --limit=500
```

Filter security groups with name matching `devkit-secgroup-*` **using programmatic JSON parsing**. If found:

```
Found existing Security Group(s) in region ${HUAWEI_REGION}:
  1. devkit-secgroup-20260804 (ID: xxx)

Reuse existing Security Group? (yes/no)
```

- **User says yes** ? Use selected Security Group
- **User says no or none found** ? Create new Security Group

#### Create New Security Group & Add ICMP Rule

> **?? CRITICAL**: Create a security group with **NO ingress rules** initially, then **automatically add one ICMP rule** (all ICMP, 0.0.0.0/0). Do NOT auto-add SSH or other ingress rules ? the user will manually add the SSH (port 22) rule via Console after the ECS is created.

```bash
# 1. Create security group (empty, no ingress rules)
hcloud VPC CreateSecurityGroup --cli-region=${HUAWEI_REGION} --security_group.name=devkit-secgroup-{timestamp}

# 2. Automatically add ICMP ingress rule (all ICMP, 0.0.0.0/0)
hcloud VPC CreateSecurityGroupRule --cli-region=${HUAWEI_REGION} \
  --security_group_rule.direction=ingress \
  --security_group_rule.security_group_id=${SG_ID} \
  --security_group_rule.protocol=icmp \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0
```

After creation, the security group contains:
- ? **ICMP ingress rule**: all ICMP, source 0.0.0.0/0 (automatically added, used for ping connectivity test)
- ? **SSH ingress rule**: not added, user must manually add it via Console (port 22/tcp)

The user must manually add the SSH ingress rule (port 22/tcp) after the ECS is created (see Step 5.5 below).

### Network Setup Summary

| Scenario | Action |
|----------|--------|
| Existing resource found + user consents | Reuse existing |
| Existing resource found + user declines | Create new |
| No existing resource found | Create new |

---

## Step 4: Select Server Type, Flavor & OS & Resolve Credentials

### 4.1 Architecture (Fixed)

Architecture is **fixed to x86_64**. No ARM/aarch64 option. No user selection needed.

| Architecture | Description |
|--------------|-------------|
| x86_64 | x86 architecture (fixed, cannot be changed) |

### 4.2 Flavor (4U8G, ac/C/S/T/X series only, dynamically queried, no default)

**Selection rule**: Query available flavors with AZ filter and include only ac/C/S/T/X series.

```bash
hcloud ECS ListFlavors --cli-region=${HUAWEI_REGION} --availability_zone=${AZ} --limit=2000
```

> ⚠️ **MANDATORY Limit ≥ 2000**: Some availability zones have 700+ flavors. Using `--limit=500` will truncate results and **miss 4U8G flavors** that appear later in the result set. Always use `--limit=2000` or higher, and verify the returned count covers all available flavors.

**Filter criteria**:
- `vcpus` = 4 — ⚠️ **TYPE WARNING**: The hcloud API returns `vcpus` as a **string** (e.g., `'4'`), not an integer. Always convert with `int(f.get('vcpus', 0))` before numeric comparison. Failing to do so will result in **zero matches**.
- `ram` = 8192 (8GiB)
- **ONLY include** flavor id starting with: `ac`, `c`, `s`, `t`, `x`
- **Exclude all other series**: `g`, `p`, `ai`, `pi`, `as`, `at`, `k`, `r`, etc.

**Python filter example**:
```python
import re
pattern = re.compile(r'^(ac|c|s|t|x)')
candidates = [
    f for f in flavors
    if int(f.get('vcpus', 0)) == 4       # ⚠️ int() conversion required!
    and int(f.get('ram', 0)) == 8192
    and pattern.match(f.get('id', ''))
]
```

| Series | Prefix | Description | Example |
|--------|--------|-------------|---------|
| ac | `^ac` | Accelerated Computing x86 | ac7.xlarge.2 |
| C | `^c` | General Computing x86 | c7.xlarge.2, c6.xlarge.2 |
| S | `^s` | General Purpose x86 | s6.xlarge.2, sn3.xlarge.2 |
| T | `^t` | Burstable x86 | t6.xlarge.2, t7.xlarge.2 |
| X | `^x` | Performance x86 | x1.4u.8g |

**Recommendation rule**: When presenting options to user, **include at least 1 flavor from each available series** (ac, C, S, T, X). If a series has no available flavor in the AZ, skip that series.

Present the filtered flavor list to user for selection. **No default.** All selected flavors are x86_64 architecture.

### 4.3 OS Image (2 options, pick 1, no default)

| Option | OS Image | Architecture |
|--------|----------|-------------|
| 1 | CentOS 7.6 | x86_64 |
| 2 | Ubuntu 20.04 | x86_64 |

User must choose one. **No default.** No other OS options.

Query images via **ECS Nova API** (NOT `hcloud IMS ListImages`) to get the correct image ID with architecture and GPU metadata filtering.

> **🔴 CRITICAL**: Use ECS Nova API v2.1 endpoint `GET https://ecs.{region}.myhuaweicloud.com/v2.1/{project_id}/images/detail` to query images. This API returns `metadata.HW_ARCH` field for architecture filtering and image name for GPU keyword exclusion. **NEVER use `hcloud IMS ListImages`** — it does not provide `HW_ARCH` metadata and returns GPU-marked images incompatible with ac/C/S/T/X flavors.

| OS | x86_64 image name pattern | Example image name |
|----|---------------------------|-------------------|
| CentOS 7.6 | `CentOS 7.6 64bit` | CentOS 7.6 64bit |
| Ubuntu 20.04 | `Ubuntu 20.04 server 64bit` | Ubuntu 20.04 server 64bit |

> **🔴 MANDATORY Image Filtering (5-step filter, all in Python)**: After querying images from ECS Nova API, apply these filters **in order**:
>
> 1. **Architecture check**: `metadata.HW_ARCH == "x86_64"` — skip any image where `HW_ARCH` exists and != `"x86_64"`
> 2. **GPU keyword exclusion**: skip images with name (lowercase) containing any of: `gpu`, `with cuda`, `with tesla`, `with graphic`, `vroce`
> 3. **Bare metal/ARM exclusion**: skip images with name (lowercase) containing any of: `baremetal`, `bms`, `arm`, `aarch64`, `kunpeng`, `ai`, `with uniagent`
> 4. **OS name match**: image name contains OS pattern (`CentOS 7.6 64bit` or `Ubuntu 20.04 server 64bit`)
> 5. **Public image preference**: prefer images with `metadata.__image_type == "gold"` (public images)

```bash
# Query images via ECS Nova API (inline Python with AK/SK signing)
py -c "
import requests, json
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.sdk_signer import Signer

region = '${HUAWEI_REGION}'
project_id = '${PROJECT_ID}'
ak = '${HUAWEI_ACCESS_KEY}'
sk = '${HUAWEI_SECRET_KEY}'
url = f'https://ecs.{region}.myhuaweicloud.com/v2.1/{project_id}/images/detail'

# Sign request with AK/SK
creds = BasicCredentials(ak, sk, project_id)
signer = Signer(creds)
# ... sign and send GET request ...
resp = requests.get(url, headers=signed_headers, verify=True)
images = resp.json().get('images', [])

# 5-step filter
exclude_keywords = ['baremetal', 'bms', 'vroce', 'with uniagent', 'gpu', 'ai', 'arm', 'aarch64', 'kunpeng', 'with graphic', 'with cuda', 'with tesla']
os_pattern = '${OS_PATTERN}'  # 'CentOS 7.6 64bit' or 'Ubuntu 20.04 server 64bit'

candidates = []
for img in images:
    name = img.get('name', '')
    name_lower = name.lower()
    metadata = img.get('metadata', {})
    HW_ARCH = metadata.get('HW_ARCH', '')

    # Step 1: Architecture check (HW_ARCH == 'x86_64')
    if HW_ARCH and HW_ARCH != 'x86_64':
        continue

    # Step 2+3: GPU and bare metal/ARM keyword exclusion
    if any(kw in name_lower for kw in exclude_keywords):
        continue

    # Step 4: OS name match
    if os_pattern.lower() not in name_lower:
        continue

    # Step 5: Public image preference (gold = public)
    image_type = metadata.get('__image_type', '')
    if image_type == 'gold':
        candidates.insert(0, img)  # Public images first
    else:
        candidates.append(img)

if candidates:
    selected = candidates[0]
    print(f'Image ID: {selected[\"id\"]}')
    print(f'Image Name: {selected[\"name\"]}')
    print(f'Architecture: {selected.get(\"metadata\", {}).get(\"HW_ARCH\", \"x86_64\")}')
else:
    print('No compatible image found')
"
```

### 4.4 Resolve ECS Login Credentials

> **?? CRITICAL RULE**: Login username and password are obtained **ONLY** from environment variables `DEVKIT_ECS_USER` and `DEVKIT_ECS_PASSWORD` (detected from **User ? Machine** levels, NOT Process level). No additional password is set at any stage. **NEVER** call `hcloud ECS BatchResetServersPassword` or any password reset API. If SSH login fails, re-detect env vars; if still fails, ask user to update/add env vars.

See [Security Rules](rules.md) for credential resolution, password rules, SSH authentication failure handling, and prohibited actions.

---

## Step 5: ECS Creation & EIP Binding

### Detection Prefix Rule

ECS detection uses **only** the `devkit-ecs-*` prefix. Do NOT use generic wildcard patterns like `*-devkit-*`.

| Resource Type | Detection Prefix | New Resource Name |
|---------------|-----------------|-------------------|
| ECS | `devkit-ecs-*` | `devkit-ecs-{timestamp}` |

### Step 5.1: Detect Existing DevKit ECS

> ⚠️ **MANDATORY Programmatic Filtering**: Always parse the complete JSON output programmatically to filter by name prefix. Do NOT rely on visual scanning — large outputs may be truncated.

```bash
hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION} --limit=500
```

Filter servers with name matching `devkit-ecs-*` and status `ACTIVE` **using programmatic JSON parsing**. If found:

- **None found** ? Create new ECS
- **One or more found (N ? 1)** ? List ALL found servers, ask user to select one to reuse or create new:

```
Found N existing DevKit ECS in region ${HUAWEI_REGION}:
  1. devkit-ecs-20260804 (ID: xxx, Flavor: c6.xlarge.2, EIP: x.x.x.x)
  2. devkit-ecs-20260805 (ID: yyy, Flavor: c7.xlarge.2, EIP: y.y.y.y)
  3. devkit-ecs-20260806 (ID: zzz, Flavor: s6.xlarge.2, EIP: z.z.z.z)

Select a server to reuse [1-N], or enter 0 to create a new ECS:
```

- **User selects a number (1-N)** ? Use that ECS, skip creation, proceed to Step 6 (Login & Upload)
- **User enters 0** ? Create new ECS

> **?? CRITICAL**: NEVER reuse existing ECS without explicit user consent. Always ask first.

### Step 5.2: Prepare ECS Creation Parameters

Collect and resolve all required parameters for ECS creation:

- **Region**: From user input or `--cli-region` default
- **Flavor**: From user selection (4U8G ac/C/S/T/X series, dynamically queried)
- **OS Image**: From ECS Nova API query (CentOS 7.6 64bit or Ubuntu 20.04 server 64bit, x86_64 architecture, GPU-filtered)
- **VPC/Subnet**: Detect existing or create new
- **Security Group**: Detect existing `devkit-sg-*` or create new with required ports (22, 80, 443)
- **EIP**: Allocate new EIP with 300 Mbit/s bandwidth (chargemode=traffic)
- **adminPass**: From `DEVKIT_ECS_PASSWORD` environment variable

### Step 5.3: Create ECS

> **?? CRITICAL**: `--server.adminPass` MUST use `DEVKIT_ECS_PASSWORD` env var value. This is NOT "setting an additional password" ? it passes the user's existing env var value to set the server's initial login password. Do NOT hardcode, auto-generate, or derive a password from any other source. After creation, **NEVER** call `hcloud ECS BatchResetServersPassword` or any API to modify the server password. See [Security Rules](rules.md).

> **?? PARAMETER CONFIRMATION (MANDATORY)**: Before executing `CreateServers`, AI MUST present ALL parameters to the user for explicit confirmation:

```
========================================
  ECS Creation Parameter Summary
========================================
  Region:          ${HUAWEI_REGION}
  Instance Name:   devkit-ecs-{timestamp}
  Flavor:          ${FLAVOR_ID}
  OS Image:        ${IMAGE_NAME}
  VPC:             ${VPC_NAME} (ID: ${VPC_ID})
  Subnet:          ${SUBNET_NAME} (ID: ${SUBNET_ID})
  Security Group:  ${SG_NAME} (ID: ${SG_ID})
  Root Volume:     GPSSD 40GB
  EIP Bandwidth:   300 Mbit/s (chargemode=traffic)
  adminPass:       from DEVKIT_ECS_PASSWORD env var (***)
========================================
Confirm the above parameters? (yes/no)
```

- **User says yes** ? Execute CreateServers
- **User says no or no response** ? Do NOT execute; ask user to correct parameters

```bash
hcloud ECS CreateServers --cli-region=${HUAWEI_REGION} \
  --server.name=devkit-ecs-{timestamp} \
  --server.flavorRef=${FLAVOR_ID} \
  --server.imageRef=${IMAGE_ID} \
  --server.vpcid=${VPC_ID} \
  --server.nics.1.subnet_id=${SUBNET_ID} \
  --server.security_groups.1.id=${SG_ID} \
  --server.adminPass=${DEVKIT_ECS_PASSWORD} \
  --server.root_volume.volumetype=GPSSD \
  --server.root_volume.size=40 \
  --server.publicip.eip.bandwidth.size=300 \
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.chargemode=traffic \
  --server.publicip.eip.iptype=5_bgp
```

#### CreateServers Response Format

> ⚠️ CreateServers returns `job_id` and `serverIds`, not a server object:
> ```json
> {"job_id": "ff808081...", "serverIds": ["4d38f254-..."]}
> ```

#### Safe Creation Pattern (MANDATORY)

> 🔴 **NEVER re-run CreateServers if output parsing fails.**
> The first call likely already created the server. Retrying creates a duplicate server, wasting quota and costs.
>
> Correct approach:
> 1. Redirect output to file: `hcloud ECS CreateServers ... --cli-output=json > /tmp/ecs_result.json 2>/dev/null`
> 2. Parse from file: `python3 -c "import json; d=json.load(open('/tmp/ecs_result.json')); ..."`
> 3. If parsing fails, **query existing servers**: `hcloud ECS ListServersDetails --cli-region=${HUAWEI_REGION}` filter by name to find the already-created server
> 4. **NEVER re-run CreateServers**

### Step 5.4: Wait for ECS Ready

Poll: `hcloud ECS ShowServer --cli-region=${HUAWEI_REGION} --server_id=${SERVER_ID}` until status is `ACTIVE`.

### Step 5.5: Output Server Info & Security Group Reminder

```
========================================
  DevKit Server Created
========================================
  Server Name:    devkit-ecs-{timestamp}
  Server ID:      {SERVER_ID}
  EIP:            {DEVKIT_ECS_EIP}
  Flavor:         {FLAVOR_ID}
  OS:             {IMAGE_NAME}
  Region:         {HUAWEI_REGION}
  Security Group: {SG_NAME} (ID: {SG_ID})
  SSH:            ssh ${DEVKIT_ECS_USER}@{DEVKIT_ECS_EIP}
========================================

??  Login credentials come ONLY from DEVKIT_ECS_USER / DEVKIT_ECS_PASSWORD env vars.
    No password reset will be performed. See [Security Rules](rules.md) for auth failure handling.

??  Security group has ICMP rule (0.0.0.0/0) added automatically.
    You MUST manually add SSH ingress rule before you can SSH into the server:

    Huawei Cloud Console ? VPC ? Security Groups ? {SG_NAME} ? Inbound Rules ? Add Rule
      Protocol: TCP | Port: 22 | Source: <your_ip>/32

     OR via hcloud CLI:
       hcloud VPC CreateSecurityGroupRule --cli-region=${HUAWEI_REGION} \
         --security_group_rule.direction=ingress \
         --security_group_rule.security_group_id=${SG_ID} \
         --security_group_rule.protocol=tcp \
         --security_group_rule.multiport=22 \
         --security_group_rule.remote_ip_prefix=<your_ip>/32
```

### Step 5.6: Auto-Proceed to Step 6 (Login, Upload & Install)

> **?? MANDATORY AUTO-PROCEED**: Once ECS status is `ACTIVE` and EIP is bound, **AUTOMATICALLY** proceed to Step 6 without waiting for user confirmation. If SSH login fails (e.g., security group ingress not yet configured), report the error and ask user to add SSH ingress rules, then retry. Do NOT skip Step 6 ? it is mandatory after Step 5 success.

See [DevKit Operations Workflow](devkit-operations-workflow.md) for detailed Step 6 execution (SSH login verify ? upload scripts ? install DevKit + Maven).
