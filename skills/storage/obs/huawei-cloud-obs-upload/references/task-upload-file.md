# Task 2: Upload Local File or Directory to Target Bucket

> **⚠️ Key: Upload operations require obsutil, not hcloud**
>
> hcloud CLI does not support OBS object upload operations (no PutObject/UploadPart CLI commands).
> Uploading files/directories must use the **obsutil** CLI tool.

> **Prerequisites:**
> - obsutil >= 5.5.0 required
> - obsutil must have AK/SK configured: `obsutil config -ak=<AK> -sk=<SK> -e=<Endpoint>`
>   - **Do not ask the user to input AK/SK directly in the conversation**; guide them to configure via obsutil config themselves

> **⚠️ Key: Required parameters must be provided by the user; do not guess**

| # | Prompt | Description |
|---|--------|-------------|
| 1 | **Local file/directory path** | The local path to upload; must exist and be readable |
| 2 | **Target bucket name** | The target OBS bucket name for upload |
| 3 | **Target path prefix (optional)** | The target path prefix within the bucket; defaults to bucket root |

> **⚠️ Confirmation gate before executing an upload**
>
> - **Data transmission notice**: uploading transmits the local file/directory to the remote OBS bucket and persists it in the cloud.
> - Restate the confirmed parameters (local path → bucket/prefix) and obtain the user's explicit approval **before** running the upload command.
> - If the user declines, or the path/bucket is not confirmed, do not execute.

**Upload a single file:**

```bash
obsutil cp <LocalFilePath> obs://<BucketName>/<ObjectKey> -flat
```

**Example:**

```bash
obsutil cp /home/user/data/report.csv obs://my-bucket/reports/report.csv -flat
```

**Upload an entire directory:**

> **⚠️ MUST ask the customer first: whether to preserve the source directory structure**
>
> Before executing a directory upload, you **must** ask the customer:
> "Do you need the source directory itself to be uploaded as a directory layer to OBS (i.e., preserve the directory structure)?"
>
> Decide whether to use `-flat` based on the customer's explicit answer:
>
> - **Customer answers "Yes" (preserve directory structure)** → do NOT use `-flat`:
>   ```bash
>   obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r
>   ```
>   Example: `/home/user/data/sub/file.txt` → `obs://my-bucket/data/sub/file.txt`
>
> - **Customer answers "No" (do not preserve directory structure, flatten files)** → use `-flat`:
>   ```bash
>   obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r -flat
>   ```
>   Example: `/home/user/data/sub/file.txt` → `obs://my-bucket/data/file.txt`
>
> **Do NOT assume or default. You must ask the customer and decide based on their explicit answer.**
> If the answer is ambiguous, clarify with the customer before executing.

> **⚠️ `-flat` parameter semantics**
>
> - With `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/file.txt` (directory structure lost, only filenames kept)
> - Without `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/sub/file.txt` (directory structure preserved)
> - **For single file uploads: `-flat` can be used without asking** (a single file has no directory structure to preserve).

## Large file upload (multipart, 200MB+)

> **When to use:** the file is about 100MB or larger, or a whole-file upload repeatedly reports
> `timeout` / `i/o timeout` / `connection reset`. For a small file, keep the default command.

obsutil uploads a large file with native multipart upload. The command is still `obsutil cp`; only
the multipart parameters and the timeout config change. Full parameter matrix and 200MB/1GB/10GB
samples: [large-file-upload.md](large-file-upload.md).

### Three facts that decide success

1. **`-threshold` must be smaller than the file size.**
   If the file is smaller than or equal to `-threshold`, obsutil uses direct upload. Direct upload
   **creates no checkpoint file and cannot resume**. For a 200MB file, set `-threshold=9MB`, never
   `-threshold=500MB`.
2. **Resume = rerun the same command.**
   A failed or interrupted multipart task keeps a checkpoint under the `-cpd` directory (default
   `~/.obsutil_checkpoint`, files under `upload/`). Rerunning the same source, target,
   `-threshold`/`-ps`, and `-cpd` uploads only the remaining parts.
3. **`-t` is the security token, not a timeout.**
   `-t` passes the temporary-credential `securitytoken`. Timeouts are controlled by
   `connectTimeout` / `socketTimeout` in `~/.obsutilconfig` (`socketTimeout` defaults to 310s).

### 200MB sample (recommended starting point)

```bash
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

| Parameter | Value in this sample | Why |
|-----------|----------------------|-----|
| `-threshold` | `9MB` | Less than 200MB, so multipart is used and a checkpoint is created |
| `-ps` | `9MB` | About 23 parts; keeps each request small enough for an unstable link |
| `-p` | `5` | Five parts in flight; use `1` to `3` on an unstable network |
| `-cpd` | `~/.obsutil_checkpoint` | Keep the same path on retry so the task resumes |
| `-f` | on | No interactive overwrite prompt |

### Resume after interruption

```bash
# Start the upload, then let it fail or stop it with Ctrl-C / kill.
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f

# Read-only check: the interrupted task's checkpoint exists.
ls -lh "$HOME/.obsutil_checkpoint/upload/"

# Rerun the SAME command; completed parts are reused.
obsutil cp /data/records-200mb.tar.gz \
  obs://my-bucket/datasets/records-200mb.tar.gz \
  -flat -threshold=9MB -ps=9MB -p=5 \
  -cpd="$HOME/.obsutil_checkpoint" -f
```

> The local file must not change between runs, and the target URL, `-threshold`, `-ps`, and `-cpd`
> must stay the same. Otherwise obsutil treats it as a new task and starts over.
>
> If the failed run printed a `Task id:`, `obsutil cp -recover=<TaskId>` replays its failed-record
> files (typical for batch/multi-file tasks; add `-clear` to drop them afterwards).

### Part-level retry and timeout tuning

```ini
# ~/.obsutilconfig (keep the existing AK/SK/endpoint lines unchanged)
connectTimeout=60
socketTimeout=600
maxRetryCount=5
```

| Key | Default | Unit | Meaning |
|-----|---------|------|---------|
| `connectTimeout` | 30 | Seconds | Connection establishment timeout |
| `socketTimeout` | 310 | Seconds | Read/write timeout; the real upload timeout knob |
| `maxRetryCount` | 3 | count | Automatic retries for a failed request/part |

Within one run, obsutil retries failed parts according to `maxRetryCount`. A part that still fails
ends the task but keeps the checkpoint, so the next run resumes from the completed parts. For
server-side throttling (`SlowDown`, HTTP 503), lower `-p` before raising `maxRetryCount`.

### Verify

```bash
obsutil ls obs://my-bucket/datasets/ -limit=10
obsutil stat obs://my-bucket/datasets/records-200mb.tar.gz
```

The upload ends with a line such as `Upload successfully, 200.00MB, ... status [200]`. A successful
multipart task removes its checkpoint automatically.

## Error handling

上传失败时，根据 obsutil 命令输出判断错误类型，并按下表用标准友好话术回复用户。

| 错误类型 | obsutil 输出特征 | 标准话术 |
|---------|------------------|---------|
| 本地路径不存在 | `Error: lstat <path>: no such file or directory` / `No such file or directory` | 未找到本地路径 `<path>`，请确认路径是否正确、文件或目录是否存在且可读取后重试。 |
| 目标地址缺少 obs:// 前缀 | `Error: Missing a valid cloud_url` / `invalid cloud url` | 目标地址格式不正确，OBS 目标必须以 `obs://` 开头（例如 `obs://my-bucket/path/`），请修正后重试。 |
| 目标桶不存在 | `Bucket <bucket> does not exist` / `NoSuchBucket` | 目标桶 `<bucket>` 不存在，请到 OBS 控制台确认桶名称与所属区域是否正确后重试。 |
| 访问被拒绝 / 凭证无效 | `AccessDenied` / `InvalidAccessKeyId` / `SignatureDoesNotMatch` / `Please set ak, sk and endpoint` | OBS 访问被拒绝，凭证可能无效或未配置，请在终端执行 `hcloud obs config -i=<AK> -k=<SK> -e=obs.<Region>.myhuaweicloud.com` 重新配置后重试。 |
| 上传超时 / 网络异常 | `timeout` / `connection reset` / `dial tcp` / `i/o timeout` | 上传过程中出现网络异常或超时。大文件请确认 `-threshold` 小于文件大小以启用分段上传，适当降低并发（`-p=1~3`）并在 `~/.obsutilconfig` 调大 `socketTimeout`（默认 310s）后重跑同一命令续传；`-t` 是 securitytoken，不是超时参数。 |
| 其他错误 | 不匹配上述特征的输出 | 上传失败，obsutil 返回：<原始输出摘要>。请将完整错误信息反馈，以便进一步排查。 |

> **使用要求：**
> - 必须根据 obsutil 实际输出匹配错误类型，不得臆测。
> - 回复时使用对应标准话术，并将 `<path>`、`<bucket>` 等占位符替换为实际值。
> - 凭证类错误不得要求用户在对话中提供 AK/SK，引导其在终端自行配置。

