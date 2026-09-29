# Verification Method - Huawei Cloud EVS Disk Create

## Table of Contents

- [Verify Environment](#verify-environment)
- [Verify Availability Zone Query](#verify-availability-zone-query)
- [Verify Disk Creation](#verify-disk-creation)
- [Verify Disk List Query](#verify-disk-list-query)
- [End-to-End Verification Script](#end-to-end-verification-script)

---

## Verify Environment

### Step 1: Verify hcloud installed

```bash
hcloud version
```

**Expected result:**
- Returns KooCLI version >= 3.2.0

### Step 2: Verify credentials configured

```bash
hcloud configure list
```

**Expected result:**
- Returns credential configuration, no error raised

---

## Verify Availability Zone Query

### Step 1: Query availability zones

```bash
hcloud EVS CinderListAvailabilityZones --cli-region=cn-north-4
```

**Expected result:**
- Returns `availabilityZoneInfo` array
- Each zone contains `zoneName` and `zoneState`
- `zoneState.available` is `true` for usable zones

---

## Verify Disk Creation

### Step 1: Confirm parameters with user before execution

```
Please confirm the disk creation parameters:
  Region: cn-north-4
  Availability Zone: cn-north-4a
  Disk Type: GPSSD
  Size: 40 GB
  Disk Name: test-disk-001
```

### Step 2: Create disk

```bash
hcloud EVS CreateVolume \
  --cli-region=cn-north-4 \
  --volume.availability_zone=cn-north-4a \
  --volume.size=40 \
  --volume.volume_type=GPSSD \
  --volume.name=test-disk-001
```

**Expected result:**
- Returns `volume` object containing `id`, `name`, `status`
- Disk status is `creating` on creation

### Step 3: Verify disk created

```bash
hcloud EVS ListVolumes --cli-region=cn-north-4
```

**Expected result:**
- Disk `test-disk-001` appears in the list
- Disk status is `available`

---

## Verify Disk List Query

```bash
hcloud EVS ListVolumes --cli-region=cn-north-4
```

**Expected result:**
- Returns `volumes` array
- Each volume contains `id`, `name`, `size`, `status`, `volume_type`, `availability_zone`

---

## End-to-End Verification Script

```bash
#!/bin/bash
# EVS disk create skill end-to-end verification script

REGION="${1:-cn-north-4}"
AZ="${2:-cn-north-4a}"
DISK_NAME="${3:-test-disk-verification}"

if command -v hcloud &> /dev/null; then
  echo "[OK] hcloud installed: $(hcloud version)"
else
  echo "[FAIL] hcloud not installed"
  exit 1
fi

echo "=========================================="
echo "[1/4] Verifying availability zone query..."
hcloud EVS CinderListAvailabilityZones --cli-region=$REGION

echo "[2/4] Creating disk $DISK_NAME..."
hcloud EVS CreateVolume \
  --cli-region=$REGION \
  --volume.availability_zone=$AZ \
  --volume.size=40 \
  --volume.volume_type=GPSSD \
  --volume.name=$DISK_NAME

echo "[3/4] Listing volumes..."
hcloud EVS ListVolumes --cli-region=$REGION

echo "[4/4] Verifying disk details..."
hcloud EVS ShowVolume --cli-region=$REGION --volume_id=<volume-id>

echo "=========================================="
echo "Verification complete!"
echo "=========================================="
```

---

## Error Handling

| Error Code | Description | Troubleshooting |
|------------|-------------|----------------|
| Error: Insufficient permissions | Missing EVS permissions | Check IAM policy, add `EVS FullAccess` |
| Error: Specified availability zone is unavailable | Invalid AZ code | Check AZ code, try another zone |
| Error: Quota exceeded for resources | Disk quota exceeded | Check EVS quota, apply for increase |
| Error: Disk name already exists | Duplicate disk name | Use a different name or timestamp suffix |

---

## References

- [EVS API Reference](https://support.huaweicloud.com/api-evs/index.html)
- [KooCLI EVS Command Help](https://support.huaweicloud.com/cli-koocli/koocli_02_0034.html)