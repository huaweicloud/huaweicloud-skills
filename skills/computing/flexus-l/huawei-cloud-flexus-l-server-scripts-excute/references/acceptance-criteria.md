# Acceptance Criteria: huawei-cloud-flexus-l-server-scripts-excute

**Scenario**: Huawei Cloud Flexus L Instance COC Script Management and Execution
**Purpose**: Skill test acceptance criteria

## Table of Contents

- [Correct Command Patterns](#correct-command-patterns)
- [Correct SDK Code Patterns](#correct-sdk-code-patterns)
- [Response Validation Criteria](#response-validation-criteria)
- [Security Criteria](#security-criteria)
- [Parameter Validation Criteria](#parameter-validation-criteria)

---

## Correct Command Patterns

### 1. Create Script

#### ✅ Correct

```bash
# Using environment variables
python {baseDir}/scripts/caller.py create \
  --name "backup_script" \
  --type SHELL \
  --content "echo 'Backup completed'" \
  --description "Data backup script"

# Using command line parameters
python {baseDir}/scripts/caller.py create \
  --ak "your_ak" \
  --sk "your_sk" \
  --name "deploy_script" \
  --type SHELL \
  --content "echo 'Deploy completed'" \
  --description "Deployment script"
```

#### ❌ Incorrect

```bash
# Incorrect: Missing required parameters
python {baseDir}/scripts/caller.py create --name "test"  # Missing --type and --content

# Incorrect: Invalid script type
python {baseDir}/scripts/caller.py create \
  --name "test" \
  --type shell \  # Should be SHELL (uppercase)
  --content "echo test"

# Incorrect: Empty content
python {baseDir}/scripts/caller.py create \
  --name "test" \
  --type SHELL \
  --content ""
```

### 2. List Scripts

#### ✅ Correct

```bash
python {baseDir}/scripts/caller.py list --page 1 --size 10
python {baseDir}/scripts/caller.py list  # Uses defaults
```

#### ❌ Incorrect

```bash
# Incorrect: Negative page number
python {baseDir}/scripts/caller.py list --page -1 --size 10

# Incorrect: Invalid size
python {baseDir}/scripts/caller.py list --page 1 --size 0
```

### 3. Show Script Details

#### ✅ Correct

```bash
python {baseDir}/scripts/caller.py show --script-uuid "SC2023102521413701c4a8a62"
```

#### ❌ Incorrect

```bash
# Incorrect: Missing script-uuid
python {baseDir}/scripts/caller.py show

# Incorrect: Invalid UUID format
python {baseDir}/scripts/caller.py show --script-uuid "invalid-uuid"
```

### 4. Execute Script

#### ✅ Correct

```bash
python {baseDir}/scripts/caller.py execute \
  --script-uuid "SC2023102521413701c4a8a62" \
  --execute-user root \
  --timeout 300

python {baseDir}/scripts/caller.py execute \
  --script-uuid "SC2023102521413701c4a8a62" \
  --execute-user root \
  --timeout 300 \
  --success-rate 100
```

#### ❌ Incorrect

```bash
# Incorrect: Missing script-uuid
python {baseDir}/scripts/caller.py execute

# Incorrect: Invalid timeout
python {baseDir}/scripts/caller.py execute \
  --script-uuid "SC2023102521413701c4a8a62" \
  --timeout 3  # Must be > 5 seconds

# Incorrect: Invalid success rate
python {baseDir}/scripts/caller.py execute \
  --script-uuid "SC2023102521413701c4a8a62" \
  --success-rate 101  # Must be 0-100
```

### 5. Query Execution Result

#### ✅ Correct

```bash
python {baseDir}/scripts/caller.py query --execute-uuid "SCT2023083109562601af694bf"
```

#### ❌ Incorrect

```bash
# Incorrect: Missing execute-uuid
python {baseDir}/scripts/caller.py query
```

### 6. Delete Script

#### ✅ Correct

```bash
python {baseDir}/scripts/caller.py delete --script-uuid "SC2023102521413701c4a8a62"
```

#### ❌ Incorrect

```bash
# Incorrect: Missing script-uuid
python {baseDir}/scripts/caller.py delete
```

---

## Correct SDK Code Patterns

### 1. Import Patterns

#### ✅ Correct

```python
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkcoc.v1.region.coc_region import CocRegion
from huaweicloudsdkcoc.v1 import CocClient
from huaweicloudsdkcoc.v1.model.add_script_model import AddScriptModel
from huaweicloudsdkcoc.v1.model.script_execute_model import ScriptExecuteModel
```

#### ❌ Incorrect

```python
from huaweicloudsdkcoc import Client  # Incorrect: Missing correct module path
```

### 2. Authentication — Must use environment variables; hardcoded AK/SK prohibited

#### ✅ Correct

```python
import os
from huaweicloudsdkcore.auth.credentials import GlobalCredentials

ak = os.getenv("HW_ACCESS_KEY")
sk = os.getenv("HW_SECRET_KEY")
security_token = os.getenv("HW_SECURITY_TOKEN")

if security_token:
    credentials = GlobalCredentials(ak, sk).with_security_token(security_token)
else:
    credentials = GlobalCredentials(ak, sk)
```

#### ❌ Incorrect

```python
# Prohibited: Hardcoded AK/SK
credentials = GlobalCredentials("AKXXXXXXXXXX", "SKXXXXXXXXXX")
```

### 3. COC Client Initialization

#### ✅ Correct

```python
from huaweicloudsdkcoc.v1.region.coc_region import CocRegion

client = CocClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(CocRegion.value_of("cn-north-4")) \
    .build()
```

#### ❌ Incorrect

```python
# Incorrect: Using SDKClient directly
client = CocClient(credentials, region="cn-north-4")  # Incorrect API
```

---

## Response Validation Criteria

### Create Script Response

✅ Must include:
- `"ok": true` on success
- `"text"` containing success message with script UUID
- `"result"` containing raw API response
- `"error": null` on success

### List Scripts Response

✅ Must include:
- `"ok": true` on success
- `"text"` containing total count
- `"result"` with `"scripts"` array and `"total"` count
- Each script contains `script_uuid`, `name`, `type`, `description`, `risk_level`, `version`, `create_time`

### Show Script Response

✅ Must include:
- `"ok": true` on success
- `"text"` indicating success
- `"result"` with complete script details
- Script details include: `script_uuid`, `name`, `type`, `content`, `description`, `risk_level`, `version`, `create_time`

### Execute Script Response

✅ Must include:
- `"ok": true` on success
- `"text"` containing success message with execution UUID
- `"result"` containing raw API response
- Execution UUID format: `SCTXXXXXXXXXXXXXXXXXXX`

### Query Execution Result Response

✅ Must include:
- `"data"` containing execution result
- `batch_index`, `total_instances`, `execute_instances`
- Each instance contains: `id`, `status`, `message`, `target_instance`
- Status values: `FINISHED`, `ABNORMAL`, `PROCESSING`, `READY`

### Error Response

✅ Must include:
- `"ok": false`
- `"error"` containing `code` and `message`
- `"result": null`

---

## Security Criteria

### ✅ Correct Security Practices

1. Use environment variables for credentials (`HW_ACCESS_KEY`, `HW_SECRET_KEY`, `HW_SECURITY_TOKEN`)
2. SDK uses `GlobalCredentials` to read from environment variables
3. Never print or log AK/SK values
4. Use `--non-interactive` flag in automation scripts
5. Set appropriate risk levels for scripts

### ❌ Incorrect Security Practices

1. Hardcode access keys in code or commands
2. Print or echo credential values in conversation
3. Pass AK/SK as plaintext command line parameters in production
4. Ask users to provide AK/SK directly in conversation

---

## Parameter Validation Criteria

### Script Type

#### ✅ Correct

```bash
--type SHELL
--type PYTHON
--type BAT
```

#### ❌ Incorrect

```bash
--type shell  # Must be uppercase
--type Shell  # Must be uppercase
--type SH     # Invalid type
```

### Risk Level

#### ✅ Correct

```bash
--risk-level LOW
--risk-level MEDIUM
--risk-level HIGH
```

#### ❌ Incorrect

```bash
--risk-level low  # Must be uppercase
--risk-level L    # Invalid risk level
```

### Timeout

#### ✅ Correct

```bash
--timeout 300    # Between 5 and 1800
--timeout 60     # Minimum 5 seconds
--timeout 1800   # Maximum 1800 seconds
```

#### ❌ Incorrect

```bash
--timeout 3      # Must be > 5 seconds
--timeout 2000   # Must be <= 1800 seconds
--timeout -1     # Must be positive
```

### Success Rate

#### ✅ Correct

```bash
--success-rate 1
--success-rate 50
--success-rate 100
```

#### ❌ Incorrect

```bash
--success-rate 0     # Must be >= 0.01
--success-rate 101   # Must be <= 100
```

### Region

#### ✅ Correct

```bash
--region cn-north-4
--region ap-southeast-3
--region eu-west-101
```

#### ❌ Incorrect

```bash
--region cn-north4    # Invalid format
--region CN-NORTH-4   # Must be lowercase
```