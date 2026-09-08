# Task 3: Schedule Periodic Upload of Local Directory to Target Bucket

> **⚠️ Key: Scheduled upload is based on OS-level scheduled task mechanisms**
>
> This skill implements periodic uploads via OS-level scheduled tasks (Linux: crontab / macOS: crontab / Windows: Task Scheduler)
> and **does not depend on additional daemon processes**.

> **⚠️ Key: Required parameters must be provided by the user; do not guess**

| # | Prompt | Description |
|---|--------|-------------|
| 1 | **Local directory path** | The local directory to upload periodically; must exist |
| 2 | **Target bucket name** | The target OBS bucket name for upload |
| 3 | **Target path prefix (optional)** | The target path prefix within the bucket; defaults to bucket root |
| 4 | **Schedule period** | The execution period, e.g., hourly, daily at 8:00, every 30 minutes |
| 5 | **Crontab expression (optional)** | If the user is familiar with cron expressions, they can provide one directly |

## Implementation (Linux/macOS)

> **⚠️ Key: Script and log file location**
>
> - If the user specifies a storage path, use the user-specified path
> - If the user does not specify, scripts and logs are stored in the **user's home directory** (`$HOME`); do not use `/tmp` (may be lost on reboot)
> - Script path: `$HOME/obs-scheduled-upload-<BucketName>.sh`
> - Log path: `$HOME/obs-scheduled-upload-<BucketName>.log`

**Step 1: Ask the customer whether to preserve the source directory structure**

> **⚠️ MUST ask the customer first before generating the upload script**
>
> Before generating the scheduled upload script, you **must** ask the customer:
> "Do you need the source directory itself to be uploaded as a directory layer to OBS (i.e., preserve the directory structure)?"
>
> Decide whether to use `-flat` based on the customer's explicit answer:
> - **Customer answers "Yes" (preserve directory structure)** → do NOT use `-flat`
> - **Customer answers "No" (do not preserve directory structure, flatten files)** → use `-flat`
>
> **Do NOT assume or default. You must ask the customer and decide based on their explicit answer.**
> If the answer is ambiguous, clarify with the customer before generating the script.

**Step 2: Generate obsutil upload script**

Create the upload script `$HOME/obs-scheduled-upload-<BucketName>.sh`. Pick the command variant based on the customer's answer in Step 1.

**Option A — preserve directory structure (no `-flat`, customer answered "Yes"):**

```bash
#!/bin/bash
# OBS scheduled upload script
# Bucket: <BucketName>
# Local directory: <LocalDirPath>
# Generated at: <Timestamp>

LOG_FILE="$HOME/obs-scheduled-upload-<BucketName>.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting scheduled upload" >> "$LOG_FILE"

obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -f -u >> "$LOG_FILE" 2>&1

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload succeeded" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload failed, exit code: $RESULT" >> "$LOG_FILE"
fi
```

**Option B — flatten files (with `-flat`, customer answered "No"):**

```bash
#!/bin/bash
# OBS scheduled upload script
# Bucket: <BucketName>
# Local directory: <LocalDirPath>
# Generated at: <Timestamp>

LOG_FILE="$HOME/obs-scheduled-upload-<BucketName>.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting scheduled upload" >> "$LOG_FILE"

obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -f -u >> "$LOG_FILE" 2>&1

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload succeeded" >> "$LOG_FILE"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload failed, exit code: $RESULT" >> "$LOG_FILE"
fi
```

> **⚠️ Key: `-flat` is decided by the customer's answer in Step 1**
>
> - Without `-flat`: `obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -f -u` (preserves directory structure, `-u` enables incremental upload)
> - With `-flat`: `obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -f -u` (flattens files, directory structure lost)
> - **Never default to either option**; always follow the customer's explicit answer from Step 1.

**Step 3: Set crontab scheduled task**

```bash
# Run every hour
(crontab -l 2>/dev/null; echo "0 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# Run daily at 8:00
(crontab -l 2>/dev/null; echo "0 8 * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# Run every 30 minutes
(crontab -l 2>/dev/null; echo "*/30 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -
```

**Step 4: Verify scheduled task is set**

```bash
crontab -l
```

## Implementation (Windows - Task Scheduler)

> **⚠️ Same as Linux/macOS: ask the customer first (Step 1) whether to preserve the source directory structure, then pick the corresponding command.**

**Option A — preserve directory structure (no `-flat`, customer answered "Yes"):**

```powershell
# Create a scheduled task (run daily at 8:00)
schtasks /create /tn "OBS-ScheduledUpload-<BucketName>" /tr "obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -u" /sc daily /st 08:00 /f
```

**Option B — flatten files (with `-flat`, customer answered "No"):**

```powershell
# Create a scheduled task (run daily at 8:00)
schtasks /create /tn "OBS-ScheduledUpload-<BucketName>" /tr "obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat -u" /sc daily /st 08:00 /f
```

> **⚠️ Important: Notes on scheduled uploads**
>
> 1. **Incremental upload (-u)**: The `-u` flag enables incremental upload mode — obsutil compares each local file's size and last-modified time against the remote object, and skips files that are already up-to-date. Combined with `-f` (auto-overwrite without prompting), this ensures that only new or modified files are actually transferred.
> 2. **Idempotency**: With `-u`, repeated executions of the scheduled task do not create duplicates or re-upload unchanged files
> 3. **Logs**: Upload logs are recorded in `$HOME/obs-scheduled-upload-<BucketName>.log`
> 4. **Deletes are not synced**: Scheduled upload only syncs new/modified files; **objects deleted locally will not be deleted from the bucket** (user must clean up manually)
> 5. **Crontab environment**: The crontab execution environment differs from an interactive shell; ensure obsutil is in PATH, and recommend using the full path to obsutil in the script
> 6. **Directory structure**: Whether the local directory structure is preserved in OBS is decided by the customer's answer in Step 1 (without `-flat` → preserved; with `-flat` → flattened). Never default; always ask first.

## Managing Scheduled Tasks

```bash
# List current user's scheduled tasks
crontab -l

# Remove a specific scheduled task
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -
```
