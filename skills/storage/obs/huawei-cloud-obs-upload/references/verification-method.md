# Verification Method - Huawei Cloud OBS Object Storage Management

## Table of Contents

- [Verify Bucket List Query](#verify-bucket-list-query)
- [Verify File Upload](#verify-file-upload)
- [Verify Scheduled Upload](#verify-scheduled-upload)
- [Verify Traffic Query](#verify-traffic-query)
- [Verify Request Query](#verify-request-query)
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

```bash
# Delete test object via OBS console, or manually via obsutil
obsutil rm obs://<BucketName>/test/obs-upload-test.txt -flat
```

> **⚠️ Note**: This cleanup step is a necessary operation in the verification process, not a skill feature; it must be executed manually.

---

## Verify Scheduled Upload

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

### Step 2: Set crontab (every 5 minutes, for testing only)

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /bin/bash $HOME/obs-scheduled-upload-test.sh") | crontab -
```

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

### Step 4: Clean up scheduled task

```bash
crontab -l | grep -v "obs-scheduled-upload-test" | crontab -
rm $HOME/obs-scheduled-upload-test.sh $HOME/obs-scheduled-upload-test.log
```

---

## Verify Traffic Query

### Step 1: Calculate time range

```bash
# Current month start timestamp (ms)
FROM_TS=$(($(date -d "$(date +%Y-%m-01)" +%s) * 1000))
# Current timestamp (ms)
TO_TS=$(($(date +%s) * 1000))
# Last month start timestamp (ms)
LAST_MONTH_FROM_TS=$(($(date -d "$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-01)" +%s) * 1000))
# Last month end timestamp (ms)
LAST_MONTH_TO_TS=$(($(date -d "$(date +%Y-%m-01) -1 second" +%s) * 1000))
```

### Step 2: Query current month external download traffic

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \

```

**Expected result:**
- Returns datapoints array
- Each datapoint contains timestamp and sum value

### Step 3: Query last month external download traffic

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$LAST_MONTH_FROM_TS \
  --to=$LAST_MONTH_TO_TS \

```

### Step 4: Verify month-over-month calculation

```
MoM (%) = (Current Month Value - Last Month Value) / Last Month Value × 100%
```

**Verification items:**
- ✅ Traffic value returned in Bytes, needs to be converted to GB for display
- ✅ MoM percentage rounded to 2 decimal places
- ✅ Special handling when last month value is 0

---

## Verify Request Query

### Step 1: Query current month total request count

```bash
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \

```

**Expected result:**
- Returns datapoints array, sum value is the request count

### Step 2: Query request count by type

```bash
# GET request count
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=get_request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \


# PUT request count
hcloud CES ShowMetricData \
  --region=cn-south-1 \
  --namespace=SYS.OBS \
  --metric_name=put_request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=<BucketName> \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \

```

### Step 3: Verify aggregation

**Verification items:**
- ✅ request_count >= get_request_count + put_request_count
- ✅ All request counts >= 0
- ✅ MoM calculation is correct

---

## End-to-End Verification Script

```bash
#!/bin/bash
# OBS management skill end-to-end verification script

REGION="${1:-cn-south-1}"
BUCKET_NAME="${2}"

if [ -z "$BUCKET_NAME" ]; then
  echo "Usage: $0 <region> <bucket_name>"
  exit 1
fi

echo "=========================================="
echo "OBS Management Skill End-to-End Verification"
echo "Region: $REGION"
echo "Bucket: $BUCKET_NAME"
echo "=========================================="

# 1. Verify hcloud
echo -e "\n[1/6] Verifying hcloud version..."
hcloud version

# 2. Verify obsutil
echo -e "\n[2/6] Verifying obsutil version..."
obsutil version

# 3. Verify bucket list
echo -e "\n[3/6] Verifying bucket list query..."
hcloud obs ls

# 4. Verify bucket capacity
echo -e "\n[4/6] Verifying bucket capacity query..."
hcloud OBS GetBucketStorageInfo \
  --region=$REGION \
  --bucket=$BUCKET_NAME \


# 5. Verify CES traffic metrics
FROM_TS=$(($(date -d "$(date +%Y-%m-01)" +%s) * 1000))
TO_TS=$(($(date +%s) * 1000))

echo -e "\n[5/6] Verifying CES external download traffic query..."
hcloud CES ShowMetricData \
  --region=$REGION \
  --namespace=SYS.OBS \
  --metric_name=download_bytes \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=$BUCKET_NAME \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \


# 6. Verify CES request metrics
echo -e "\n[6/6] Verifying CES total request count query..."
hcloud CES ShowMetricData \
  --region=$REGION \
  --namespace=SYS.OBS \
  --metric_name=request_count \
  --dimensions.0.name=bucket_name \
  --dimensions.0.value=$BUCKET_NAME \
  --period=86400 \
  --filter=sum \
  --from=$FROM_TS \
  --to=$TO_TS \


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
