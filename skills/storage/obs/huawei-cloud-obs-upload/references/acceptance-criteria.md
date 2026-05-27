# Acceptance Criteria: huawei-cloud-obs-upload

**Scenario**: Huawei Cloud OBS Object Storage Management
**Purpose**: Skill test acceptance criteria

## Table of Contents

- [Correct CLI Command Patterns](#correct-cli-command-patterns)
- [Correct SDK Code Patterns](#correct-sdk-code-patterns)
- [Response Validation Criteria](#response-validation-criteria)
- [Security Criteria](#security-criteria)
- [Month-over-Month Calculation Criteria](#month-over-month-calculation-criteria)
- [References](#references)

---

## Correct CLI Command Patterns

### 0. Parameter Format — hcloud must use equals sign format

#### ✅ Correct
```bash
hcloud obs ls
hcloud CES ShowMetricData --region=cn-south-1 --namespace=SYS.OBS --metric_name=capacity_total
hcloud version
```

#### ❌ Incorrect
```bash
hcloud obs ls --region cn-south-1  # Incorrect: obsutil mode parameters not applicable
hcloud --version  # Incorrect: hcloud does not support --version; use hcloud version
```

> **⚠️ Key: hcloud OBS module is obsutil**
>
> The hcloud CLI OBS module directly maps to obsutil commands; use lowercase `hcloud obs`, not `hcloud OBS`.
> To list buckets, use `hcloud obs ls`; there is no `ListAllMyBucketsType` command.

### 1. OBS Commands — Use obsutil mode

#### ✅ Correct
```bash
hcloud obs ls                           # List all buckets
hcloud obs ls obs://my-bucket -s        # List objects in bucket
hcloud obs stat obs://my-bucket         # View bucket attributes
```

#### ❌ Incorrect
```bash
hcloud OBS ListAllMyBucketsType         # Incorrect: This command does not exist
hcloud obs list-buckets                 # Incorrect: obsutil command is ls
```

### 2. CES Commands — Query monitoring metrics

#### ✅ Correct
```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=capacity_total \
  --dim.0=bucket_name,my-bucket \
  --period=86400 \
  --filter=average \
  --from=1746057600000 \
  --to=1747612800000
```

#### ❌ Incorrect
```bash
hcloud ces ShowMetricData ...           # Incorrect: CES product name must be uppercase
hcloud CES ShowMetricData \
  --namespace=OBS                       # Incorrect: Should be SYS.OBS
hcloud CES ShowMetricData \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=my-bucket        # Incorrect: hcloud uses --dim.0=key,value format
```

### 3. CES Dimension Parameter Format

#### ✅ Correct
```bash
--dim.0=bucket_name,my-bucket
```

#### ❌ Incorrect
```bash
--dimensions.0.name=bucket_name --dimensions.0.value=my-bucket  # Incorrect: SDK format, not supported by hcloud
--dim.0=bucket,my-bucket                                         # Incorrect: Dimension key should be bucket_name
```

### 4. obsutil Upload Commands

#### ✅ Correct
```bash
obsutil cp /home/user/file.txt obs://my-bucket/path/file.txt -flat    # Single file: -flat is fine
obsutil cp /home/user/data/ obs://my-bucket/data/ -r                   # Directory: preserves structure (default)
obsutil cp /home/user/data/ obs://my-bucket/data/ -r -p=10             # Directory with concurrency
obsutil cp /home/user/data/ obs://my-bucket/data/ -r -flat             # Directory: -flat only if user explicitly requests
```

#### ❌ Incorrect
```bash
obsutil upload /home/user/file.txt obs://my-bucket/  # Incorrect: obsutil upload command is cp, not upload
obsutil cp /home/user/file.txt my-bucket/path/file.txt  # Incorrect: Target must start with obs://
obsutil cp /home/user/data/ obs://my-bucket/ -r -flat  # Incorrect: -flat discards directory structure by default; do not use unless user explicitly requests
```

### 5. CES Namespace and Metric Names

#### ✅ Correct
```bash
--namespace=SYS.OBS
--metric_name=capacity_total
--dim.0=bucket_name,my-bucket
```

#### ❌ Incorrect
```bash
--namespace=OBS              # Incorrect: Should be SYS.OBS
--namespace=SYS.OBJECT_STORAGE  # Incorrect: Should be SYS.OBS
--metric_name=capacityTotal  # Incorrect: Should be capacity_total (snake_case)
--metric_name=download_bytes  # Incorrect: Not used in this skill; capacity_total is the actual metric
--dim.0=bucketName,my-bucket  # Incorrect: Dimension key should be bucket_name
--dim.0=bucket,my-bucket      # Incorrect: Dimension key should be bucket_name
```

### 6. Time Ranges — Millisecond Timestamps

#### ✅ Correct
```bash
--from=1746057600000  # Millisecond timestamp
--to=1747612800000    # Millisecond timestamp
```

#### ❌ Incorrect
```bash
--from=1746057600     # Incorrect: Second-level timestamp; CES requires millisecond-level (13 digits)
--from=2025-05-01     # Incorrect: CES requires Unix timestamp, not date string
```

---

## Correct SDK Code Patterns

### 1. Import Patterns

#### ✅ Correct
```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkobs.v1.client import ObsClient
from huaweicloudsdkces.v1.client import CesClient
from huaweicloudsdkces.v1.region.ces_region import CesRegion
```

#### ❌ Incorrect
```python
from huaweicloudsdkobs import Client  # Incorrect: Missing correct module path
```

### 2. Authentication — Must use BasicCredentials; hardcoded AK/SK prohibited

#### ✅ Correct
```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials

credentials = BasicCredentials() \
    .with_ak(os.getenv("HUAWEICLOUD_SDK_AK")) \
    .with_sk(os.getenv("HUAWEICLOUD_SDK_SK")) \
    .with_project_id(os.getenv("HUAWEICLOUD_SDK_PROJECT_ID"))
```

#### ❌ Incorrect
```python
credentials = BasicCredentials() \
    .with_ak("XXXXXXXXXX")      # Prohibited: Hardcoded AK
    .with_sk("YYYYYYYYYY")      # Prohibited: Hardcoded SK
```

### 3. OBS Client Initialization

#### ✅ Correct
```python
from obs import ObsClient

obs_client = ObsClient(
    access_key_id=os.getenv("HUAWEICLOUD_SDK_AK"),
    secret_access_key=os.getenv("HUAWEICLOUD_SDK_SK"),
    server='obs.cn-south-1.myhuaweicloud.com'
)
```

#### ❌ Incorrect
```python
obs_client = ObsClient(
    access_key_id="XXXXXXXXXX",      # Prohibited: Hardcoded AK
    secret_access_key="YYYYYYYYYY",   # Prohibited: Hardcoded SK
    server='obs.cn-south-1.myhuaweicloud.com'
)
```

---

## Response Validation Criteria

### obs ls response (list buckets)
✅ Must include:
- Bucket name list
- Region information for each bucket

### obs stat response (bucket attributes)
✅ Must include:
- `size` - Total size of objects in the bucket (bytes)
- `objectNumber` - Total number of objects in the bucket

### CES ShowMetricData response
✅ Must include:
- `datapoints` array, each containing `timestamp`, `unit`, and an aggregate value (`sum`/`average`/`max`/`min`)
- `metric_name` (string)

---

## Security Criteria

### ✅ Correct Security Practices
1. Use `hcloud configure list` to verify credentials (do not echo AK/SK)
2. SDK uses BasicCredentials to read from environment variables
3. Sensitive data uses environment variables
4. obsutil credentials configured securely via `obsutil config`

### ❌ Incorrect Security Practices
1. Hardcode access keys in code or commands
2. Print or echo credential values
3. Use `hcloud configure set` to pass plaintext credentials in automation scripts
4. Ask the user to provide AK/SK directly in the conversation

### ⛔ Prohibited Operations (Security Constraints)

> **The following delete operations are strictly forbidden, regardless of user requests:**

#### ❌ Absolutely Prohibited
```bash
hcloud obs rm obs://my-bucket -r           # Prohibited: Recursively delete all objects in bucket
hcloud obs rm obs://my-bucket              # Prohibited: Delete bucket
```

#### ✅ Correct: Refuse delete request and direct to console
```
"Per security constraints, this skill does not allow delete operations (delete bucket/object/batch delete/empty bucket). Please use the Huawei Cloud OBS console or obsutil manually."
```

---

## Month-over-Month Calculation Criteria

### ✅ Correct Calculation
```
MoM (%) = (Current Month Value - Last Month Value) / Last Month Value × 100%

Example:
Current month = 125.3 GB, Last month = 98.7 GB
MoM = (125.3 - 98.7) / 98.7 × 100% = +26.95%
```

### Special Case Handling

| Case | Correct Handling | Incorrect Handling |
|------|-----------------|-------------------|
| Last month=0, Current>0 | Display "New (last month was 0)" | ❌ Display +∞% |
| Last month=0, Current=0 | Display "N/A" | ❌ Display 0% |
| Last month>0, Current>0 | Calculate percentage, rounded to 2 decimal places | ❌ Integer truncation |
| Current<Last month | Display negative (e.g., -15.30%) | ❌ Display 0% |

---

## References

- [OBS API Reference](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [obsutil Documentation](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0001.html)
