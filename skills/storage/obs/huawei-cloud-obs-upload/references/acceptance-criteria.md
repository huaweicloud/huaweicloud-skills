# Acceptance Criteria: huawei-cloud-obs-upload

**Scenario**: Huawei Cloud OBS Object Storage Management
**Purpose**: Skill test acceptance criteria

## Table of Contents

- [Correct CLI Command Patterns](#correct-cli-command-patterns)
- [Correct SDK Code Patterns](#correct-sdk-code-patterns)
- [Response Validation Criteria](#response-validation-criteria)
- [Security Criteria](#security-criteria)
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

> **⚠️ For directory uploads, ask the customer first whether to preserve the source directory structure, then pick the command. Never default.**

#### ✅ Correct
```bash
obsutil cp /home/user/file.txt obs://my-bucket/path/file.txt -flat    # Single file: -flat is fine (no need to ask)
obsutil cp /home/user/data/ obs://my-bucket/data/ -r                   # Directory: customer chose to preserve structure
obsutil cp /home/user/data/ obs://my-bucket/data/ -r -p=10             # Directory with concurrency (customer chose preserve)
obsutil cp /home/user/data/ obs://my-bucket/data/ -r -flat             # Directory: customer chose to flatten files
```

#### ❌ Incorrect
```bash
obsutil upload /home/user/file.txt obs://my-bucket/  # Incorrect: obsutil upload command is cp, not upload
obsutil cp /home/user/file.txt my-bucket/path/file.txt  # Incorrect: Target must start with obs://
obsutil cp /home/user/data/ obs://my-bucket/ -r -flat  # Incorrect: using -flat without asking the customer first; -flat must follow the customer's explicit answer
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

### 7. Large file upload (200MB+) — multipart assertions

A large-file command must actually enable multipart upload, keep a checkpoint, and use the config
file (not `-t`) for timeout tuning.

#### ✅ Correct
```bash
# 200MB single file: threshold < file size, explicit part size, explicit checkpoint, part concurrency
obsutil cp /data/records-200mb.tar.gz obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 -cpd="$HOME/.obsutil_checkpoint" -f

# Resume: rerun the exact same command after an interruption
obsutil cp /data/records-200mb.tar.gz obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 -cpd="$HOME/.obsutil_checkpoint" -f

# 1GB: larger parts; 10GB: even larger parts (keep ceil(size/ps) <= 10000)
obsutil cp /data/archive-1gb.tar obs://my-bucket/datasets/archive-1gb.tar \
  -flat -threshold=16MB -ps=16MB -p=8 -cpd="$HOME/.obsutil_checkpoint" -f
obsutil cp /data/backup-10gb.tar obs://my-bucket/backups/backup-10gb.tar \
  -flat -threshold=32MB -ps=64MB -p=8 -cpd="$HOME/.obsutil_checkpoint" -f

# Timeout/retry tuning belongs in ~/.obsutilconfig
# connectTimeout=60
# socketTimeout=600
# maxRetryCount=5
```

#### ❌ Incorrect
```bash
# Incorrect: threshold >= file size -> direct upload, no checkpoint, no resume
obsutil cp /data/records-200mb.tar.gz obs://my-bucket/records-200mb.tar.gz -threshold=500MB -p=5

# Incorrect: -t is the security token, not an upload timeout
obsutil cp /data/records-200mb.tar.gz obs://my-bucket/records-200mb.tar.gz -t=600

# Incorrect: -fr only generates a result manifest; it does not enable resume
obsutil cp /data/records-200mb.tar.gz obs://my-bucket/records-200mb.tar.gz -fr

# Incorrect: 10GB with 1MB parts = 10240 parts, above the 10000-part limit
obsutil cp /data/backup-10gb.tar obs://my-bucket/backup-10gb.tar -threshold=1MB -ps=1MB
```

**Assertions for a large-file upload answer:**

- The 200MB sample MUST include `-threshold`, `-ps`, `-p`, and `-cpd`; `-threshold` MUST be less
  than 200MB.
- The answer MUST state that rerunning the same command resumes from the checkpoint; `-fr` MUST NOT
  be presented as a resume switch.
- The answer MUST state that `-t` is the security token, not a timeout; timeout tuning MUST point
  to `socketTimeout` (default 310s) in `~/.obsutilconfig`.
- 200MB / 1GB / 10GB samples MUST keep the part count at or below 10000.
- Multipart failures MUST be diagnosed in the order: `-threshold` vs file size → checkpoint
  presence → bandwidth/part concurrency → Region/Endpoint → AK/SK permission → clock.

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
    .with_ak(os.getenv("HW_ACCESS_KEY")) \
    .with_sk(os.getenv("HW_SECRET_KEY")) \
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
    access_key_id=os.getenv("HW_ACCESS_KEY"),
    secret_access_key=os.getenv("HW_SECRET_KEY"),
    server='obs.cn-south-1.myhuaweicloud.com'
)
```

#### ❌ Incorrect
```python
obs_client = ObsClient(
    access_key_id="XXXXXXXXXX",      # FORBIDDEN: Hardcoded AK
    secret_access_key="YYYYYYYYYY",   # FORBIDDEN: Hardcoded SK
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

> **The following operations are strictly forbidden, regardless of user requests. They are described semantically; the skill never provides executable destructive command examples.**

#### ❌ Absolutely Prohibited
- Recursively deleting all objects in a bucket
- Deleting a bucket

#### ✅ Correct: Refuse delete request and direct to console
```
"Per security constraints, this skill does not allow delete operations (delete bucket/object/batch delete/empty bucket). Please use the Huawei Cloud OBS console or obsutil manually."
```

---

## References

- [OBS API Reference](https://support.huaweicloud.com/api-obs/obs_04_0001.html)
- [obsutil Documentation](https://support.huaweicloud.com/utiltg-obs/obs_11_0001.html)
- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0001.html)
