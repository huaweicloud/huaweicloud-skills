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

**Step 1: Generate obsutil upload script**

Create the upload script `$HOME/obs-scheduled-upload-<BucketName>.sh`:

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

> **⚠️ Key: Do NOT use `-flat` for directory uploads**
>
> The user specified a directory to upload, so the entire directory structure should be preserved.
> - Default command: `obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -f -u` (preserves directory structure, `-u` enables incremental upload)
> - Only add `-flat` if the user **explicitly requests** flattening (e.g., "upload all files without directory structure")

**Step 2: Set crontab scheduled task**

```bash
# Run every hour
(crontab -l 2>/dev/null; echo "0 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# Run daily at 8:00
(crontab -l 2>/dev/null; echo "0 8 * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -

# Run every 30 minutes
(crontab -l 2>/dev/null; echo "*/30 * * * * /bin/bash $HOME/obs-scheduled-upload-<BucketName>.sh") | crontab -
```

**Step 3: Verify scheduled task is set**

```bash
crontab -l
```

## Implementation (Windows - Task Scheduler)

```powershell
# Create a scheduled task (run daily at 8:00)
schtasks /create /tn "OBS-ScheduledUpload-<BucketName>" /tr "obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -u" /sc daily /st 08:00 /f
```

> **⚠️ Important: Notes on scheduled uploads**
>
> 1. **Incremental upload (-u)**: The `-u` flag enables incremental upload mode — obsutil compares each local file's size and last-modified time against the remote object, and skips files that are already up-to-date. Combined with `-f` (auto-overwrite without prompting), this ensures that only new or modified files are actually transferred.
> 2. **Idempotency**: With `-u`, repeated executions of the scheduled task do not create duplicates or re-upload unchanged files
> 3. **Logs**: Upload logs are recorded in `$HOME/obs-scheduled-upload-<BucketName>.log`
> 4. **Deletes are not synced**: Scheduled upload only syncs new/modified files; **objects deleted locally will not be deleted from the bucket** (user must clean up manually)
> 5. **Crontab environment**: The crontab execution environment differs from an interactive shell; ensure obsutil is in PATH, and recommend using the full path to obsutil in the script
> 6. **Directory structure preserved**: By default, the full local directory structure is preserved in OBS. Only use `-flat` if the user explicitly requests it.

## Managing Scheduled Tasks

```bash
# List current user's scheduled tasks
crontab -l

# Remove a specific scheduled task
crontab -l | grep -v "obs-scheduled-upload-<BucketName>" | crontab -
```
