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

**Upload an entire directory (preserves directory structure by default):**

```bash
obsutil cp <LocalDirPath> obs://<BucketName>/<Prefix> -r
```

**Example:**

```bash
obsutil cp /home/user/data/ obs://my-bucket/data/ -r
```

> The above command preserves the full directory structure:
> `/home/user/data/sub/file.txt` → `obs://my-bucket/data/sub/file.txt`

> **⚠️ `-flat` parameter — use only when explicitly needed**
>
> `-flat` discards the local directory structure and uploads only the files (flattened).
> - **For directory uploads: Do NOT use `-flat` by default.** The user specified a directory, so the entire directory should be uploaded as-is.
> - **For single file uploads: `-flat` can be used** (a single file has no directory structure to preserve).
> - With `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/file.txt` (directory structure lost)
> - Without `-flat`: `/home/user/data/sub/file.txt` → `obs://bucket/prefix/sub/file.txt` (directory structure preserved)
>
> Only add `-flat` for directory uploads if the user **explicitly requests** flattening (e.g., "upload all files without directory structure").

> **⚠️ Large file automatic multipart upload**
>
> obsutil automatically uses multipart upload for large files, with a default part size of 9MB.
> You can specify concurrency with the `-p` parameter (default 5) and multipart threshold with `-threshold`.

**Error handling**
1. If "bucket not exist" is reported, prompt the user to confirm the bucket name
2. If "access denied" is reported, prompt the user to check obsutil configuration and bucket permissions
3. If the local path does not exist, prompt the user to confirm the path
4. If upload times out or network error occurs, suggest using `-p` to reduce concurrency or retry
