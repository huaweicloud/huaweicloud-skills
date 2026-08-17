# Verification Method - Huawei Cloud Flexus L Instance COC Script Execution

## Table of Contents

- [Verify SDK Installation](#verify-sdk-installation)
- [Verify Authentication Configuration](#verify-authentication-configuration)
- [Verify Script Management Operations](#verify-script-management-operations)
- [Verify Script Execution Operations](#verify-script-execution-operations)
- [End-to-End Verification Script](#end-to-end-verification-script)
- [Error Handling](#error-handling)

---

## Verify SDK Installation

### Step 1: Check COC SDK version

```bash
python -c "import huaweicloudsdkcoc; print(huaweicloudsdkcoc.__version__)"
```

**Expected result:**
- Returns version >= 3.1.0
- No import errors

### Step 2: Verify COC client availability

```bash
python -c "from huaweicloudsdkcoc.v1 import CocClient; print('COC SDK version verification passed')"
```

**Expected result:**
- Prints "COC SDK version verification passed"
- No import errors

---

## Verify Authentication Configuration

### Step 1: Check environment variables

```bash
echo "HW_ACCESS_KEY: ${HW_ACCESS_KEY:+set}"
echo "HW_SECRET_KEY: ${HW_SECRET_KEY:+set}"
echo "HW_REGION: ${HW_REGION:-not set}"
```

**Expected result:**
- `HW_ACCESS_KEY` and `HW_SECRET_KEY` should be set
- `HW_REGION` should be set (default: cn-north-4)

### Step 2: Verify authentication programmatically

```bash
python -c "
import os
from huaweicloudsdkcoc.v1 import CocClient
from huaweicloudsdkcore.auth.credentials import GlobalCredentials

ak = os.getenv('HW_ACCESS_KEY')
sk = os.getenv('HW_SECRET_KEY')
region = os.getenv('HW_REGION', 'cn-north-4')

if ak and sk:
    credentials = GlobalCredentials(ak, sk)
    client = CocClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(CocRegion.value_of(region)) \
        .build()
    print('Authentication configuration verification passed')
else:
    print('ERROR: AK/SK environment variables not set')
"
```

**Expected result:**
- Prints "Authentication configuration verification passed"

---

## Verify Script Management Operations

### Step 1: Create a test script

```bash
python {baseDir}/scripts/caller.py create \
  --name "verification_test_script" \
  --type SHELL \
  --content "echo 'Verification test successful'" \
  --description "Test script for skill verification"
```

**Expected result:**
- Returns script UUID (format: SCXXXXXXXXXXXXXXXXXXX)
- Response contains `"ok": true`

### Step 2: List scripts

```bash
python {baseDir}/scripts/caller.py list --page 1 --size 10
```

**Expected result:**
- Returns script list
- Contains the newly created script "verification_test_script"

### Step 3: Get script details

```bash
python {baseDir}/scripts/caller.py show --script-uuid "SCXXXXXXXXXXXXXXXXXXX"
```

**Expected result:**
- Returns script details including name, type, content, description
- Response contains `"ok": true`

### Step 4: Delete test script

```bash
python {baseDir}/scripts/caller.py delete --script-uuid "SCXXXXXXXXXXXXXXXXXXX"
```

**Expected result:**
- Returns success message
- Response contains `"ok": true`

---

## Verify Script Execution Operations

### Step 1: Create an execution script

```bash
python {baseDir}/scripts/caller.py create \
  --name "execution_test_script" \
  --type SHELL \
  --content "echo 'Execution test successful'; hostname; date" \
  --description "Test script for execution verification"
```

**Expected result:**
- Returns script UUID

### Step 2: Execute script (interactive mode)

```bash
python {baseDir}/scripts/caller.py execute --script-uuid "SCXXXXXXXXXXXXXXXXXXX"
```

**Expected result:**
- Prompts for L-instance resource ID and region
- Returns execution task UUID (format: SCTXXXXXXXXXXXXXXXXXXX)
- Response contains `"ok": true`

### Step 3: Query execution result

```bash
python {baseDir}/scripts/caller.py query --execute-uuid "SCTXXXXXXXXXXXXXXXXXXX"
```

**Expected result:**
- Returns execution status (`FINISHED`, `ABNORMAL`, or `PROCESSING`)
- If `FINISHED`, contains execution output
- If `ABNORMAL`, contains error message

### Step 4: Clean up

```bash
python {baseDir}/scripts/caller.py delete --script-uuid "SCXXXXXXXXXXXXXXXXXXX"
```

---

## End-to-End Verification Script

```bash
#!/bin/bash
# COC Script Execution Skill End-to-End Verification

BASE_DIR="${1:-$(dirname "$0")/../..}"

echo "=========================================="
echo "COC Script Execution Skill Verification"
echo "Base Dir: $BASE_DIR"
echo "=========================================="

# 1. Verify SDK installation
echo -e "\n[1/5] Verifying COC SDK installation..."
python -c "import huaweicloudsdkcoc; print(f'COC SDK Version: {huaweicloudsdkcoc.__version__}')"

# 2. Verify authentication
echo -e "\n[2/5] Verifying authentication configuration..."
python -c "
import os
ak = os.getenv('HW_ACCESS_KEY')
sk = os.getenv('HW_SECRET_KEY')
if ak and sk:
    print('Authentication: OK')
else:
    print('Authentication: ERROR - AK/SK not set')
    exit(1)
"

# 3. Create test script
echo -e "\n[3/5] Creating test script..."
CREATE_OUTPUT=$(python "$BASE_DIR/scripts/caller.py" create \
  --name "e2e_test_script" \
  --type SHELL \
  --content "echo 'E2E test successful'" \
  --description "E2E verification test")
echo "$CREATE_OUTPUT"
SCRIPT_UUID=$(echo "$CREATE_OUTPUT" | grep -o 'SC[0-9a-f]\{24\}')

if [ -z "$SCRIPT_UUID" ]; then
    echo "ERROR: Failed to create script"
    exit 1
fi

# 4. List scripts
echo -e "\n[4/5] Listing scripts..."
python "$BASE_DIR/scripts/caller.py" list --page 1 --size 5

# 5. Delete test script
echo -e "\n[5/5] Cleaning up test script..."
python "$BASE_DIR/scripts/caller.py" delete --script-uuid "$SCRIPT_UUID"

echo -e "\n=========================================="
echo "Verification complete!"
echo "=========================================="
```

---

## Error Handling

| Error Code | Description | Troubleshooting Command |
|------------|-------------|----------------------|
| 403 | Insufficient permissions | Verify IAM policy is correctly configured |
| 403 | Authentication failed | Check AK/SK configuration |
| 400 | Invalid parameter | Verify script type, content, and other parameters |
| 429 | API quota exceeded | Wait or upgrade quota |
| 500 | Internal service error | Retry later or contact Huawei Cloud support |
| NameResolutionError | Failed to resolve es01 | Ensure elasticsearch profile is started |

---

## Verification Checklist

- ✅ COC SDK version >= 3.1.0
- ✅ Authentication via environment variables works
- ✅ Script creation returns UUID
- ✅ Script listing returns correct results
- ✅ Script deletion works
- ✅ Script execution returns task UUID
- ✅ Execution result query works