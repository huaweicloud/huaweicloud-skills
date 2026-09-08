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

> **⚠️ Large file automatic multipart upload**
>
> obsutil automatically uses multipart upload for large files, with a default part size of 9MB.
> You can specify concurrency with the `-p` parameter (default 5) and multipart threshold with `-threshold`.

## Error handling

上传失败时，根据 obsutil 命令输出判断错误类型，并按下表用标准友好话术回复用户。

| 错误类型 | obsutil 输出特征 | 标准话术 |
|---------|------------------|---------|
| 本地路径不存在 | `Error: lstat <path>: no such file or directory` / `No such file or directory` | 未找到本地路径 `<path>`，请确认路径是否正确、文件或目录是否存在且可读取后重试。 |
| 目标地址缺少 obs:// 前缀 | `Error: Missing a valid cloud_url` / `invalid cloud url` | 目标地址格式不正确，OBS 目标必须以 `obs://` 开头（例如 `obs://my-bucket/path/`），请修正后重试。 |
| 目标桶不存在 | `Bucket <bucket> does not exist` / `NoSuchBucket` | 目标桶 `<bucket>` 不存在，请到 OBS 控制台确认桶名称与所属区域是否正确后重试。 |
| 访问被拒绝 / 凭证无效 | `AccessDenied` / `InvalidAccessKeyId` / `SignatureDoesNotMatch` / `Please set ak, sk and endpoint` | OBS 访问被拒绝，凭证可能无效或未配置，请在终端执行 `hcloud obs config -i=<AK> -k=<SK> -e=obs.<Region>.myhuaweicloud.com` 重新配置后重试。 |
| 上传超时 / 网络异常 | `timeout` / `connection reset` / `dial tcp` / `i/o timeout` | 上传过程中出现网络异常或超时，建议降低并发（`-p=1`）或检查网络后重试；大文件可调整分片阈值 `-threshold`。 |
| 其他错误 | 不匹配上述特征的输出 | 上传失败，obsutil 返回：<原始输出摘要>。请将完整错误信息反馈，以便进一步排查。 |

> **使用要求：**
> - 必须根据 obsutil 实际输出匹配错误类型，不得臆测。
> - 回复时使用对应标准话术，并将 `<path>`、`<bucket>` 等占位符替换为实际值。
> - 凭证类错误不得要求用户在对话中提供 AK/SK，引导其在终端自行配置。

