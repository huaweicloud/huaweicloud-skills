# Large File Upload (Multipart) — obsutil

> Applies to `obsutil cp` when a single file is large (hundreds of MB to TB) or when a whole-file
> upload keeps timing out. The same obsutil tool and the same command are used; only a few
> multipart parameters and two config-file timeout values differ.

## Table of Contents

- [When to Use Multipart Upload](#when-to-use-multipart-upload)
- [Three Facts You Must Know](#three-facts-you-must-know)
- [Parameter Matrix](#parameter-matrix)
- [Config File: Timeout and Retry](#config-file-timeout-and-retry)
- [Examples: 200MB / 1GB / 10GB](#examples-200mb--1gb--10gb)
- [Resume After Interruption](#resume-after-interruption)
- [Part-Level Retry](#part-level-retry)
- [Verification](#verification)
- [Error Code Reference](#error-code-reference)
- [Diagnostic Order for Timeouts](#diagnostic-order-for-timeouts)

---

## When to Use Multipart Upload

Use multipart upload when any of the following is true:

- The file is about 100MB or larger (for example, the reported 200MB case).
- A whole-file upload repeatedly reports `timeout`, `i/o timeout`, `connection reset`, or
  `dial tcp ... i/o timeout`.
- The network is unstable and the upload must be resumable.
- The file exceeds 5GB (a single non-multipart upload is limited to 5GB; multipart supports up to
  48.8TB per object).

For small files (a few MB) keep the default behavior. Multipart adds request overhead and is not
useful when the whole file fits in one request.

## Three Facts You Must Know

1. **`-threshold` must be smaller than the file size.**
   `-threshold` is the switch between direct upload and multipart upload. If the file is smaller
   than or equal to the threshold, obsutil uses **direct upload**, which **does not create a
   checkpoint file and cannot resume**. For a 200MB file, set `-threshold=9MB` (or any value below
   200MB), never `-threshold=500MB`.
2. **Resume = rerun the exact same command.**
   Every multipart task writes a checkpoint under the `-cpd` directory (default
   `~/.obsutil_checkpoint`, files under its `upload/` subdirectory). After a failure or `Ctrl-C`,
   rerunning the **same** source path, target URL, `-threshold`/`-ps`, and `-cpd` resumes from the
   completed parts and uploads only the remaining parts. A successful task deletes its checkpoint
   automatically.
3. **`-t` is the security token, not a timeout.**
   `-t` supplies the `securitytoken` for temporary AK/SK. It has nothing to do with timeouts.
   Upload timeouts are controlled by the config file keys `connectTimeout` and `socketTimeout`
   (`socketTimeout` defaults to 310s).

## Parameter Matrix

### Command-line parameters

| Parameter | Default | Valid values | Meaning | When to change |
|-----------|---------|--------------|---------|----------------|
| `-threshold` | `defaultBigfileThreshold` (50MB in recent versions; older clients 9MB) | Bytes, or units such as `9MB` | File size at which multipart upload starts. Must be **less than** the file size to enable multipart | Set `9MB` for a 200MB file; lower it when a whole-file upload times out |
| `-ps` | `defaultPartSize` (`auto` in recent versions; older clients 9MB) | `100KB` to `5GB`, or `auto` | Size of each part | 200MB: `9MB`; 1GB: `16MB`; 10GB: `64MB`; keep the part count at or below 10000 |
| `-p` | `defaultParallels` (5) | >= 1 | Maximum number of parts uploaded concurrently **per object** | 200MB: `5`; unstable network: `1` to `3`; high bandwidth: `8` to `10` |
| `-j` | `defaultJobs` (5) | >= 1 | Maximum number of concurrent **batch tasks** for directory/multi-file uploads | Directory upload only; it does not change part concurrency for a single file |
| `-cpd` | `~/.obsutil_checkpoint` | Existing writable directory | Directory for checkpoint files. A checkpoint is created per multipart task under `upload/` | Keep the same value across retries so the task can resume |
| `-fr` | off | Flag | Generate a result manifest for a single-file upload | Diagnostics only; **it does not enable resume** |
| `-f` | off | Flag | Force operation without an interactive prompt | Recommended for non-interactive retries |
| `-flat` | off | Flag | Drop the local directory structure for a single file | Single-file upload |
| `-t` | - | String | **Security token** for temporary AK/SK. **Not a timeout** | Only when temporary credentials are used |

### Config-file equivalents

| Config key | Default | Meaning |
|------------|---------|---------|
| `defaultBigfileThreshold` | 52428800 bytes (50MB) | Same as `-threshold` |
| `defaultPartSize` | `auto` | Same as `-ps` |
| `defaultParallels` | 5 | Same as `-p` |
| `defaultJobs` | 5 | Same as `-j` |

> `-p` and `-j` are different: `-p` controls parts of one object; `-j` controls parallel files or
> directories in a batch task.

## Config File: Timeout and Retry

`obsutil cp` timeouts are controlled by `~/.obsutilconfig`, not by `-t` and not by any `cp` flag.
Add or update these keys in the existing config file (keep the AK/SK/endpoint lines unchanged):

```ini
# ~/.obsutilconfig (only the timeout/retry keys are shown)
connectTimeout=60
socketTimeout=600
maxRetryCount=5
```

| Key | Default | Unit | Meaning | Suggested value for unstable networks |
|-----|---------|------|---------|---------------------------------------|
| `connectTimeout` | 30 | Seconds | Timeout for establishing a connection | `60` |
| `socketTimeout` | 310 | Seconds | Socket read/write timeout; **this is the real upload timeout knob**. Valid range `[5, 600]` | `600` (the upper limit) |
| `maxRetryCount` | 3 | Count | Maximum retries for a failed request/part | `5` |

> Keep every value inside the range the tool accepts, otherwise obsutil rejects the config:
> `connectTimeout` `[5, 120]`, `socketTimeout` `[5, 600]`, `maxRetryCount` `[0, 5]`.

> Run `obsutil config -help` after upgrading obsutil to confirm the supported keys and units for
> the installed version.

## Examples: 200MB / 1GB / 10GB

All examples use `-flat` for a single file and `-f` to avoid an interactive overwrite prompt.
Replace the bucket, paths, and object key with the user-confirmed values.

### 200MB file (the reported case)

```bash
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

- `-threshold=9MB` is below 200MB, so multipart is used and a checkpoint is created.
- About 23 parts of 9MB, with 5 parts in flight.
- If the network is unstable, use `-p=3`; if it keeps timing out, raise `socketTimeout` to
  `600`.

### 1GB file

```bash
obsutil cp /data/archive-1gb.tar \
  obs://my-bucket/datasets/archive-1gb.tar \
  -flat -threshold=16MB -ps=16MB -p=8 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

- 1GB / 16MB = 64 parts, well below the 10000-part limit.
- Use `-p=4` to `-p=6` on a shared or unstable link.

### 10GB file

```bash
obsutil cp /data/backup-10gb.tar \
  obs://my-bucket/backups/backup-10gb.tar \
  -flat -threshold=32MB -ps=64MB -p=8 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

- 10GB / 64MB = 160 parts.
- Keep `ceil(file_size / part_size) <= 10000`; for example, 10GB with `-ps=1MB` would need 10240
  parts and is invalid.
- For very large files, `-ps=auto` lets obsutil choose the part size.

## Resume After Interruption

Resume is native to multipart upload. There is no `-resume` switch. Two recovery paths:

- **Rerun the exact same command** (the normal case for a single file): the part records under
  `-cpd` are reused, so only the remaining parts are uploaded.
- **`obsutil cp -recover=<TaskId>`**: replays the failed-record files that obsutil wrote for a
  previous task whose `Task id:` was printed (typically a batch/multi-file task). Add `-clear` to
  delete those failure records once the task is resumed.

```bash
# 1) Start the upload and let it fail or stop it with Ctrl-C / kill.
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f

# 2) Read-only check: the interrupted task's checkpoint is present.
ls -lh "$HOME/.obsutil_checkpoint/upload/"

# 3) Rerun the SAME command. Completed parts are reused; only the remaining parts are uploaded.
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

Rules for a successful resume:

- The **local file must not change** (path, size, and content) between runs.
- The **target URL, `-threshold`, `-ps`, and `-cpd` must stay the same**. Changing them creates a
  different task and starts over.
- Do not delete the checkpoint unless a fresh full upload is explicitly intended.
- The default checkpoint location is per-user. If the upload runs as a different user (for example,
  from crontab), pass an explicit shared `-cpd` path.

## Part-Level Retry

Within one run, obsutil retries failed parts automatically according to `maxRetryCount` in
`~/.obsutilconfig` (default 3). A part that still fails after the retries ends the task; the
checkpoint is kept, so the next run resumes from the completed parts.

```ini
# ~/.obsutilconfig
connectTimeout=60
socketTimeout=600
maxRetryCount=5
```

If the failure is a server-side throttle (`SlowDown`, HTTP 503), reduce `-p` before raising
`maxRetryCount` further.

## Verification

```bash
# List the uploaded object and confirm its size.
obsutil ls obs://my-bucket/datasets/ -limit=10
obsutil stat obs://my-bucket/datasets/records-200mb.tar.gz

# The upload command itself ends with a status line such as:
# Upload successfully, 200.00MB, ... status [200], request id [...]
```

A successful multipart task removes its checkpoint automatically. An empty or shrinking
`~/.obsutil_checkpoint/upload/` after the run is expected.

## Error Code Reference

| Error code / output | Meaning | Action |
|---------------------|---------|--------|
| `NoSuchBucket` / `Bucket ... does not exist` | Bucket name or region/endpoint mismatch | Confirm the bucket name and that the configured endpoint belongs to the bucket's region |
| `AccessDenied` / `403 Forbidden` | IAM user or bucket policy lacks write permission | Grant `obs:object:PutObject` (covers UploadPart and CompleteMultipartUpload) and check bucket policy/ACL |
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` | AK/SK wrong, temporary credentials missing `-t`, or endpoint mismatch | Reconfigure credentials in the terminal; for temporary AK/SK pass the security token with `-t` (not a timeout) |
| `RequestTimeTooSkewed` | Local clock differs too much from the server | Sync the system clock (for example, with NTP) and retry |
| `SlowDown` / HTTP 503 | Server-side throttling | Lower `-p` (for example, to `3`), wait, and retry |
| `RequestTimeout` / `i/o timeout` / `dial tcp ... i/o timeout` | Network timeout or too-small `socketTimeout` | Raise `socketTimeout`, lower `-p`, and confirm the bandwidth/firewall/proxy |
| `Connection reset by peer` | Connection broken by the network or a middlebox | Retry (resume is automatic), lower `-p`, check the proxy/MTU |
| `InvalidPart` / `InvalidPartOrder` / `NoSuchUpload` | Multipart state is inconsistent, often after a very long interruption or a changed source file | Rerun the same command first; if `NoSuchUpload` persists, remove that task's checkpoint and upload again |
| `EntityTooLarge` | A part exceeds the 5GB limit | Increase the part count by lowering `-ps` (but keep it above `100KB`) |
| `InvalidArgument` on `-threshold`/`-ps` | Value out of range or wrong unit | Use units such as `9MB`; `-ps` must be between `100KB` and `5GB` |

## Diagnostic Order for Timeouts

When a 200MB-or-larger upload times out, check in this order:

1. **Is multipart actually enabled?** Confirm `-threshold` is smaller than the file size. If the
   threshold is larger, obsutil silently uses direct upload, creates no checkpoint, and cannot
   resume. This is the most common cause of repeated whole-file timeouts.
2. **Is a checkpoint being created?** After an interruption, check
   `~/.obsutil_checkpoint/upload/`. No checkpoint means the task ran in direct-upload mode.
3. **Network bandwidth and stability.** Observe the reported speed. A 200MB file on a 1Mbps link
   needs about 27 minutes before overhead; if the link is that slow, raise `socketTimeout` and
   lower `-p`, or upload from a host with better bandwidth.
4. **Part size and concurrency.** For unstable links, use `-ps=9MB` and `-p=1` to `-p=3`. Too many
   concurrent parts on a weak link increases timeouts.
5. **Region and endpoint match.** Run `obsutil ls` and confirm the bucket's `Location` matches the
   endpoint configured in `~/.obsutilconfig` (for example, `cn-north-4` needs
   `obs.cn-north-4.myhuaweicloud.com`).
6. **AK/SK and permissions.** Confirm the credential is valid and has `obs:object:PutObject`. For
   temporary credentials, confirm the security token is passed with `-t`; never use `-t` as a
   timeout.
7. **Clock and server-side throttling.** `RequestTimeTooSkewed` means clock skew; `SlowDown` means
   reduce `-p`.
8. **Local disk space for checkpoints.** Checkpoint files are small but must be writable; confirm
   the `-cpd` directory exists and is writable by the current user.
