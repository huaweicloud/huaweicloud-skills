# Verification Method - Huawei Cloud OBS Object Storage Management

## Table of Contents

- [Verify Bucket List Query](#verify-bucket-list-query)
- [Verify File Upload](#verify-file-upload)
- [Verify Scheduled Upload](#verify-scheduled-upload)
- [End-to-End Verification Script](#end-to-end-verification-script)

---

## Verify Bucket List Query

### Step 1: List buckets

```bash
hcloud obs ls
```

**Expected result:**
- Returns a bucket list, each bucket containing `Name`, `Location`, `CreationDate`
- If no buckets exist, returns an empty list (normal)

### Step 2: Query bucket capacity and object count

```bash
hcloud OBS GetBucketStorageInfo \
  --region=cn-south-1 \
  --bucket=<BucketName>
```

**Expected result:**
- Returns `size` (bytes) and `objectNumber` (object count)
- size >= 0, objectNumber >= 0

### Step 3: Verify output format

```
Bucket               Capacity(GB)  Objects
my-bucket-1          125.3         1024
my-bucket-2          0.5           15
```

**Verification items:**
- ✅ Capacity is in GB, with 1 decimal place
- ✅ Object count is an integer
- ✅ All buckets have been queried

---

## Verify File Upload

### Step 1: Upload test file

```bash
# Create test file
echo "test content" > /tmp/obs-upload-test.txt

# Upload
obsutil cp /tmp/obs-upload-test.txt obs://<BucketName>/test/obs-upload-test.txt -flat
```

**Expected result:**
- Returns upload success message
- Shows uploaded file size and duration

### Step 2: Verify file has been uploaded

```bash
obsutil ls obs://<BucketName>/test/ -limit=10
```

**Expected result:**
- List contains `test/obs-upload-test.txt`
- File size matches local file

### Step 3: Clean up test file

> Delete the test object manually via the OBS console:
> 1. Log in to the Huawei Cloud OBS console and open bucket `<BucketName>`
> 2. Navigate to the `test/` folder under the bucket
> 3. Select the object `obs-upload-test.txt`
> 4. Click **Delete** and confirm in the dialog (the console will prompt for confirmation)

> **⚠️ Note**: This cleanup step is a manual console operation outside this skill's scope. The skill itself never performs delete operations.

---

## Verify Scheduled Upload

> **⚠️ Persistence warning**: A scheduled upload installs a recurring task on the host that keeps pushing local data to the cloud after the session ends. The user must explicitly approve before any crontab entry is written. This section is for test/verification only, and cleanup must follow.

### Step 0: Get explicit user confirmation

- Explain that this test installs a cron job that uploads `/tmp/obs-scheduled-test/` to `obs://<BucketName>/scheduled-test/` every 5 minutes until removed.
- Only proceed after the user explicitly approves.

### Step 1: Create upload script

```bash
# Create test directory and file
mkdir -p /tmp/obs-scheduled-test
echo "test $(date)" > /tmp/obs-scheduled-test/test.txt

# Create upload script
cat > $HOME/obs-scheduled-upload-test.sh << 'EOF'
#!/bin/bash
export PATH=/usr/local/bin:$PATH
LOG_FILE="$HOME/obs-scheduled-upload-test.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting scheduled upload" >> "$LOG_FILE"
obsutil cp /tmp/obs-scheduled-test/ obs://<BucketName>/scheduled-test/ -r >> "$LOG_FILE" 2>&1
EOF
chmod +x $HOME/obs-scheduled-upload-test.sh
```

### Step 2: Write crontab entry (every 5 minutes, for testing only; requires user confirmation first)

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /bin/bash $HOME/obs-scheduled-upload-test.sh") | crontab -
```

> **⚠️ This appends a persistent scheduled task to the user's crontab. Write it only after the user has explicitly confirmed.** Once written, the task runs until it is removed (see Step 4).

### Step 3: Verify scheduled task

```bash
# Check crontab
crontab -l

# Wait 5 minutes then check log
sleep 310
cat $HOME/obs-scheduled-upload-test.log

# Check files in OBS bucket
obsutil ls obs://<BucketName>/scheduled-test/ -limit=10
```

### Step 4: Clean up scheduled task (after explicit confirmation of the user)

```bash
# Remove the test scheduled task (this line must only be executed after the user confirms cleanup)
crontab -l | grep -v "obs-scheduled-upload-test" | crontab -
# Remove the test script and log
rm $HOME/obs-scheduled-upload-test.sh $HOME/obs-scheduled-upload-test.log
```

> **⚠️ Cleanup confirmation**: Removing the crontab entry must also be confirmed with the user, since it modifies the user's crontab.
> **Note**: `crontab -r` clears ALL scheduled tasks and is not used by this skill.

---

## End-to-End Verification Script

```bash
#!/bin/bash
# OBS upload skill end-to-end verification script

REGION="${1:-cn-south-1}"
BUCKET_NAME="${2}"

if [ -z "$BUCKET_NAME" ]; then
  echo "Usage: $0 <region> <bucket_name>"
  exit 1
fi

echo "=========================================="
echo "OBS Upload Skill End-to-End Verification"
echo "Region: $REGION"
echo "Bucket: $BUCKET_NAME"
echo "=========================================="

# 1. Verify hcloud
echo -e "\n[1/5] Verifying hcloud version..."
hcloud version

# 2. Verify obsutil
echo -e "\n[2/5] Verifying obsutil version..."
obsutil version

# 3. Verify bucket list
echo -e "\n[3/5] Verifying bucket list query..."
hcloud obs ls

# 4. Verify bucket capacity & object count
echo -e "\n[4/5] Verifying bucket capacity query..."
hcloud OBS GetBucketStorageInfo \
  --region=$REGION \
  --bucket=$BUCKET_NAME \

# 5. Verify file upload
echo -e "\n[5/5] Verifying file upload..."
echo "test content" > /tmp/obs-upload-verify.txt
obsutil cp /tmp/obs-upload-verify.txt obs://$BUCKET_NAME/test/obs-upload-verify.txt -flat
obsutil ls obs://$BUCKET_NAME/test/ -limit=10

echo -e "\n=========================================="
echo "Verification complete!"
echo "=========================================="
```

---

## Error Handling

| Error Code | Description | Troubleshooting Command |
|------------|-------------|----------------------|
| 403 | Insufficient permissions | `hcloud configure list` to check credentials |
| 404 | Bucket does not exist | `obsutil ls -limit=100` to list buckets |
| 400 | Invalid request parameters | Check region, bucket name, and other parameters |
| 500 | Internal service error | Retry later or contact Huawei Cloud technical support |
| Empty datapoints | No CES data | Check namespace, metric_name, and time range |
