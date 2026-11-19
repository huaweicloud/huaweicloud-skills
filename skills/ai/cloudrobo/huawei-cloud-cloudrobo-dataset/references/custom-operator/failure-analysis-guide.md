> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## Failure Analysis Guide 失败分析指南

### Contents 目录

- Overview 概述
- Error Pattern Matrix 错误模式矩阵
- Analysis Algorithm 分析算法
- Priority Ordering 优先级排序
- Log Truncation 日志截断
- Usage Example 使用示例
- Common Failure Scenarios 常见失败场景

### Overview 概述

The skill reads a failed task's
`job-std-output.log`, truncates it to 64KB, and matches error patterns against
a priority-ordered list. The first match determines the root cause and fix
suggestion returned to the user.

### Error Pattern Matrix 错误模式矩阵

#### P0 — Critical (Dependency / Build) 关键错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 3 | `docker build.*ERROR\|COPY failed` | Dockerfile 构建失败 — The Docker build step failed, usually because a `COPY` source path does not exist in the work copy. | 检查 Dockerfile 中 `COPY` 指令的源路径是否存在于工作副本中。确认 `./src` 目录结构正确，`requirements.txt` 位于正确位置。 |
| 3a | `OSError:\s*\[Errno 30\].*Read-only file system` | 输出目录只读 — The container tried to create `output/` inside the **read-only** input dataset mount (`SOURCE_DATASET_PATH`). The platform mounts input datasets read-only. | 将输出目录改为 `TARGET_DATASET_PATH` 环境变量或 `/output/`，绝不要在输入数据集路径内写文件。修复 `entrypoint.py` 后重新构建推送镜像。 |
| 3b | `IsADirectoryError:\s*\[Errno 21\]` | 目录被当作文件 — The dataset asset OBS root contains a `<version_id>/` subdirectory holding the real files; `iterdir()` treated it as a file. | entrypoint 改用递归遍历 `INPUT_DIR.rglob("*")` 并过滤 `is_file()`，保留相对路径写出。 |
| 3c | Task `FAILED` with **no Python traceback** in `job-std-output.log`; log ends mid-operation (e.g. inside video encoding) and `get-events` shows `Warning RequiredProcessAbnormal: The required obs process [/usr/bin/s3fs] is abnormal(missing)` | **OBS 挂载进程异常退出** — the `s3fs` FUSE process mounting the OBS bucket died while the operator streamed large files (video mp4) straight into the mounted output root, so the write aborts and the container exits without a Python traceback. Platform-side mount instability, aggravated by high-throughput streaming writes. | Diagnose with `dataset proc get-events --task-id <id> --job-name <pod name>`. **Real fix: build the dataset on container-local disk (`tempfile.gettempdir()`), then copy the finished tree to the OBS mount root in one sequential pass** — never encode/write large files directly onto the FUSE mount. Re-submit once; if it recurs, also raise the flavor. Not an operator-logic bug. |
| 3d | `PermissionError: \[Errno 13\].*target` when implementing the "build locally then publish" pattern | Removing/reshaping the platform mount point — `TARGET_DATASET_PATH` (e.g. `/tmp/target/dataset`) is a **mount point that cannot be removed** (`rmdir` → Errno 13). | Build under `tempfile.gettempdir()` (never under the target mount), then create/copy into the mount root. Do not `rmdir` the mount, and do not `shutil.move` a directory into an existing directory (it nests and silently drops files, leaving `meta/episodes/` empty). |
| 3e | Downstream reports `ArrowInvalid: Parquet magic bytes not found in footer`, or `FileNotFoundError: .../meta/info.json`, or "not a valid LeRobot v3 dataset"; the parquet starts with `PAR1` but does NOT end with `PAR1` — **including when the file is on local disk, before any OBS copy** | **`LeRobotDataset.finalize()` was never called.** LeRobot buffers parquet footer metadata in its writers; `save_episode()` alone leaves every `.parquet` without a footer, so the dataset is invalid. This looks like truncation but is a missing API call. | After the last `save_episode()`, call **`dataset.finalize()`** (closes the parquet writers of both the dataset and its metadata). Verify any generated `.parquet` starts AND ends with `PAR1` **on the local build** before copying to OBS — if the local file is already broken, the cause is always the missing `finalize()`, not the mount. |
| 3f | Same `PAR1`-footer symptom but only for objects **on the OBS mount**, while the locally built file is valid | **Truncated write to the OBS FUSE mount** — s3fs still had the tail buffered when the container exited. Object size can look correct, so size alone does not prove completeness. | After copying to the mount, `os.fsync` each file, verify **size AND trailing `PAR1`**, retry on mismatch, and sleep a few seconds before exiting to let FUSE flush. |
| 3g | Cleaning fails with `ValueError: Embedded/image-file features need a dedicated curation writer` | The converted dataset mixes storage kinds: some camera keys are `video` while at least one is per-frame `image` (e.g. a depth stream declared `"dtype": "image"`). The preset cleaning operator only accepts all-video (or all-image) feature sets. | In `build_features()`, give **every** camera key the same storage kind (`video` when `use_videos=True`). Do not special-case one stream (e.g. depth) to `image`. |

#### P1 — High (Runtime Environment) 运行时环境错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 4 | `FileNotFoundError.*SOURCE_DATASET_PATH` | 数据集路径未注入 — The platform did not inject `SOURCE_DATASET_PATH`, or the entrypoint is reading it before the env var is set. | 确认 `entrypoint.py` 已正确读取 `SOURCE_DATASET_PATH` 环境变量。检查 `ext_metadata.env` 中是否声明了 `SOURCE_DATASET_PATH`。如果使用自定义 entrypoint，确保使用 `os.environ.get("SOURCE_DATASET_PATH")` 而非硬编码路径。 |
| 5 | `PermissionError.*output` | 输出目录无写权限 — The container cannot write to the output directory, possibly due to volume mount permissions. | 确认 `OUTPUT_DIR` 已通过 `mkdir(parents=True, exist_ok=True)` 创建。检查容器挂载卷是否有写权限。如使用 OBS 挂载，确认 OBS 桶策略允许写入。 |
| 5a | `stdbuf: failed to run command 'python': Permission denied` | OBS 挂载方式 `algo_entrance` 使用了**相对路径** `python entrypoint.py` — The platform runs the command from `/`, so the relative path and the `python` symlink in the preset image fail. | 将 `algo_entrance` 改为**绝对的、已解析的**路径，如 `python3 /opt/operator/entrypoint.py`（`/opt/operator` 即 task_config 的 `job_local_path`）。 |
| 5a-1 | `python3: can't open file '.../{job_local_path}/entrypoint.py': [Errno 2]` | **占位符未替换** — `algo_entrance` 里直接写了文档占位符 `{job_local_path}`，平台不会替换它（`{job_local_path}` 只是给智能体看的占位符） | 把 `{job_local_path}` 替换为 task_config 中 `job_local_path` 的**实际值**，例如 `job_local_path=/opt/operator` ⇒ `algo_entrance="python3 /opt/operator/entrypoint.py"`；算法资产的 `ext_metadata.command` 同样处理 |
| 5a-2 | `ModuleNotFoundError: No module named 'h5py'`（或 numpy/Pillow/lerobot 等） | **镜像缺依赖** — 代码放 OBS、运行时挂载方式只挂代码，不会安装 `requirements.txt` | 改为把代码打进镜像并在 Dockerfile 里 `RUN pip install -r requirements.txt`；或核实用户提供的镜像是否已内置这些依赖。不可假定"运行时镜像"自带算子依赖 |
| 5b | `No module named 'user_operator'` | 代码放 OBS、运行时挂载 entrypoint 硬编码 `/app/src` 导入 — 代码放 OBS、运行时挂载 mounts the code at `{job_local_path}/src`, not `/app/src`. | entrypoint 的 src 导入改为相对 `__file__`：`sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))`；并确认 OBS 代码含 `src/user_operator.py`。 |
| 5c | `SOURCE_DATASET_PATH is not a valid JSON map` (+ `INPUT environment variable is not set`) | task-config 的 `envs` 包含 `SOURCE_DATASET_PATH` 的 fallback `default`（如 `/tmp/source/dataset`）— The literal placeholder in `envs` **overrides/blocks the platform runtime injection** of the dataset mount path (input is `access_method=env`). | 重建任务时从 `envs` 中**移除 `SOURCE_DATASET_PATH`**（及其他 `access_method=env` 输入端口），仅保留业务变量（如 `UMI_PLATFORM`）；无需重建镜像。 |
| 5d | `create-task` 返回 **HTTP 500**（重建镜像后重跑常见） | 算法资产 `engine.image_url` / `engine.asset_version_id` 仍指向**旧镜像版本**（重建后误走 first-submission 分支重复 `create-asset`，或 `update-asset` 未重指到新版本）；或失败运行预注册的 `BUILD_IN_ASSET` 输出资产停在 `DRAFT`/`CREATING`；或平台正重新索引刚更新的资产 | ① `show-asset` 校验算法资产指向**新**镜像版本（未指向则执行 Phase 3 Step 3.2 的 `create-version`+`update-asset`，**绝不重复 `create-asset`**）；② 使用**全新** `output_name`（时间戳后缀，不复用失败运行的）；③ 等待约 30 s 重试一次；④ 仍 500 → 记录 `trace_id` + 系统日志，联系平台支持 |

#### P2 — Medium (Code Logic) 代码逻辑错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 6 | `TypeError:\s*(.+)` | 类型错误 — The `process()` function received an unexpected argument type, or the return value type is unsupported. | 检查 `process()` 入参类型，entrypoint.py 传递的是 `str(item)` 路径字符串。确认返回值为 `str` 或 `bytes`。详情：{0} |
| 7 | `KeyError:\s*'(\w+)'` | 字典键缺失 — The operator code tried to access a dictionary key that doesn't exist. | 检查数据结构，确认键存在后再访问。使用 `.get(key, default)` 替代直接索引。缺失键：'{0}' |

#### P3 — Unknown 未知错误

| # | Pattern | Root Cause | Fix Suggestion |
|---|---------|------------|----------------|
| 8 | (no match) | 未知错误 — The log does not match any known error pattern. | 请查看完整日志并联系平台支持。可使用 `cloudrobo dataset proc download-log --task-id <id>` 下载完整日志。 |

### Analysis Algorithm 分析算法

```python
#!/usr/bin/env python3
"""Failure analysis engine for custom-operator skill."""
import re

ERROR_PATTERNS = [
    # P0 — Critical (Dependency / Build)
    {
        "priority": "P0",
        "pattern": r"ModuleNotFoundError:\s*No module named '(\S+)'",
        "cause": "Python 依赖缺失",
        "fix": "在 requirements.txt 中添加 '{0}' 后重跑 onboard 命令。"
               "Phase 2 docker build 会重新安装依赖。"
    },
    {
        "priority": "P0",
        "pattern": r"ImportError:\s*(.+)",
        "cause": "导入失败",
        "fix": "检查模块路径与 __init__.py，确认 entry.module 配置正确。"
               "错误详情：{0}"
    },
    {
        "priority": "P0",
        "pattern": r"docker build.*ERROR|COPY failed",
        "cause": "Dockerfile 构建失败",
        "fix": "检查 Dockerfile COPY 源路径是否存在于工作副本中。"
               "确认 ./src 目录结构和 requirements.txt 位置。"
    },
    {
        "priority": "P0",
        "pattern": r"OSError:\s*\[Errno 30\].*Read-only file system",
        "cause": "输出目录只读（输入数据集为只读挂载）",
        "fix": "输出目录改为 TARGET_DATASET_PATH 环境变量或 /output/，"
               "绝不在 SOURCE_DATASET_PATH 输入路径内写文件。"
    },
    {
        "priority": "P0",
        "pattern": r"IsADirectoryError:\s*\[Errno 21\]",
        "cause": "数据集资产根目录含 <version_id>/ 子目录，iterdir 将目录当文件",
        "fix": "entrypoint 改用递归遍历 INPUT_DIR.rglob('*') 并过滤 is_file()，"
               "输出保留相对路径。"
    },

    # P1 — High (Runtime Environment)
    {
        "priority": "P1",
        "pattern": r"FileNotFoundError.*SOURCE_DATASET_PATH",
        "cause": "数据集路径未注入",
        "fix": "确认 entrypoint.py 已读取 SOURCE_DATASET_PATH 环境变量。"
               "检查 ext_metadata.env 中是否声明 SOURCE_DATASET_PATH。"
    },
    {
        "priority": "P1",
        "pattern": r"stdbuf: failed to run command 'python': Permission denied",
        "cause": "代码放 OBS、运行时挂载 algo_entrance 使用了相对路径 python entrypoint.py",
        "fix": "将 代码放 OBS、运行时挂载 的 algo_entrance 改为绝对路径："
               "python3 {job_local_path}/entrypoint.py "
               "（如 python3 /tmp/cloudrobo/<operator-name>/entrypoint.py）"
    },
    {
        "priority": "P1",
        "pattern": r"No module named 'user_operator'",
        "cause": "entrypoint 硬编码 /app/src 导入，代码放 OBS、运行时挂载 代码挂载在 {job_local_path}/src",
        "fix": "entrypoint 的 src 导入改为相对 __file__："
               "sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))；"
               "并确认 OBS 代码含 src/user_operator.py"
    },
    {
        "priority": "P1",
        "pattern": r"PermissionError.*output",
        "cause": "输出目录无写权限",
        "fix": "确认 OUTPUT_DIR 已 mkdir(parents=True, exist_ok=True)。"
               "检查容器挂载卷写权限，OBS 桶策略允许写入。"
    },
    {
        "priority": "P1",
        "pattern": r"The asset name is existed",
        "cause": "BUILD_IN_ASSET 输出资产名重复",
        "fix": "创建 proc-task 时 output_name 使用唯一值（如带时间戳后缀）。"
    },
    {
        "priority": "P1",
        "pattern": r"(?i)http\s*500|internal server error|create.?task.*500",
        "cause": "重建镜像后重跑 create-task 平台内部错误（多为算法资产仍指向旧镜像版本 / 失败运行的输出资产未清理）",
        "fix": "① show-asset 校验算法资产 engine.image_url/asset_version_id 指向新镜像版本（未指向则执行 "
               "Phase 3 Step 3.2 create-version+update-asset，绝不重复 create-asset）；"
               "② output_name 使用全新时间戳值；③ 等待约 30s 重试一次；"
               "④ 仍 500 → 记录 trace_id + 系统日志，联系平台支持。"
    },

    # P2 — Medium (Code Logic)
    {
        "priority": "P2",
        "pattern": r"TypeError:\s*(.+)",
        "cause": "类型错误",
        "fix": "检查 process() 入参类型，entrypoint.py 传递 str 路径。"
               "确认返回值为 str 或 bytes。详情：{0}"
    },
    {
        "priority": "P2",
        "pattern": r"KeyError:\s*'(\w+)'",
        "cause": "字典键缺失",
        "fix": "检查数据结构，使用 .get(key, default) 替代直接索引。"
               "缺失键：'{0}'"
    },
]

def analyze_failure(log_path="job-std-output.log"):
    """Analyze a failure log and return root cause + fix suggestion.

    Reads the log file, truncates to 64KB, and matches against ERROR_PATTERNS
    in priority order. Returns the first match.

    Args:
        log_path: Path to the job-std-output.log file.

    Returns:
        dict with keys: priority, cause, fix, matched_line.
        If no pattern matches, returns P3 with "contact support" suggestion.
    """
    try:
        with open(log_path, errors="ignore") as f:
            log = f.read()[:65536]  # Truncate to 64KB
    except FileNotFoundError:
        return {
            "priority": "P3",
            "cause": "日志文件未找到",
            "fix": "确认任务 ID 正确，且任务已产生日志。"
                   "使用 list-log-files 先获取可用日志文件列表。",
            "matched_line": ""
        }

    for p in ERROR_PATTERNS:
        m = re.search(p["pattern"], log)
        if m:
            return {
                "priority": p["priority"],
                "cause": p["cause"],
                "fix": p["fix"].format(*m.groups()),
                "matched_line": m.group(0)[:200]
            }

    return {
        "priority": "P3",
        "cause": "未知错误",
        "fix": "请查看完整日志并联系平台支持。"
               "可使用 download-log 下载完整日志。",
        "matched_line": ""
    }
```

### Priority Ordering 优先级排序

Patterns are evaluated **in order** — the first match wins. This means:

1. **P0 patterns are checked first** — if a dependency or build error exists,
   it is the root cause regardless of other errors in the log (which are
   typically downstream consequences).

2. **P1 patterns are checked next** — environment issues like missing
   `SOURCE_DATASET_PATH` or permission errors indicate a configuration problem
   that must be fixed before code-level debugging.

3. **P2 patterns are checked last** — code logic errors (TypeError, KeyError)
   are surfaced only if no environment or dependency issues are found.

4. **P3 is the fallback** — if no pattern matches, the error is unknown and
   the user should download the full log for manual analysis.

### Log Truncation 日志截断

- Only the **first 64KB** of `job-std-output.log` is read.
- This prevents excessive memory usage on large logs.
- Most critical errors appear early in the log (during initialization or
  first item processing).
- If the user needs full log analysis, suggest `download-log` for the
  complete file.

### Usage Example 使用示例

#### CLI

```bash
# Analyze a failed task
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log

# With a local log file
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log
```

#### Output Format

```json
{
  "priority": "P0",
  "cause": "Python 依赖缺失",
  "fix": "在 requirements.txt 中添加 'torch' 后重跑 onboard 命令。Phase 2 docker build 会重新安装依赖。",
  "matched_line": "ModuleNotFoundError: No module named 'torch'"
}
```

### Common Failure Scenarios 常见失败场景

#### Scenario 1: Missing Python Dependency

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 12, in <module>
    from user_operator import process
  File "/app/src/user_operator.py", line 3, in <module>
    import torch
ModuleNotFoundError: No module named 'torch'
```

**Analysis result:**
```json
{
  "priority": "P0",
  "cause": "Python 依赖缺失",
  "fix": "在 requirements.txt 中添加 'torch' 后重跑 onboard 命令。",
  "matched_line": "ModuleNotFoundError: No module named 'torch'"
}
```

**Action:** Add `torch` to `requirements.txt`, re-run the build (see ../../SKILL.md §Custom Operator Onboarding).

#### Scenario 2: Missing SOURCE_DATASET_PATH

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 20, in <module>
    INPUT_DIR = Path(DATASET_PATH) / "input"
  File "/usr/lib/python3.x/pathlib.py", line 1005, in __new__
    ...
FileNotFoundError: <dataset-path>/input does not exist
```

**Analysis result:**
```json
{
  "priority": "P1",
  "cause": "数据集路径未注入",
  "fix": "确认 entrypoint.py 已读取 SOURCE_DATASET_PATH 环境变量..."
}
```

**Action:** Verify `ext_metadata.env` includes `SOURCE_DATASET_PATH`, re-onboard if needed.

#### Scenario 2a: envs 中 SOURCE_DATASET_PATH 占位值阻断平台注入

**Log excerpt (typical):**
```
[ENTRY] cwd=/app/src cmd=python3 main.py --operator umitolerobotv3 --platform pika --overwrite
SOURCE_DATASET_PATH is not a valid JSON map.
2026-09-28 11:34:56,942 - ERROR - Error during data conversion INPUT environment variable is not set
[DONE] command exit code: 1
```

**Analysis result:**
```json
{
  "priority": "P1",
  "cause": "task-config 的 envs 中包含 SOURCE_DATASET_PATH 的 fallback default（如 /tmp/source/dataset），该字面量覆盖/阻断了平台运行时注入的 JSON map（输入端口 access_method=env）",
  "fix": "重建任务：从 envs 中移除 SOURCE_DATASET_PATH（及其他 access_method=env 输入端口），仅保留业务变量（如 UMI_PLATFORM=pika）。无需重建镜像。",
  "matched_line": "SOURCE_DATASET_PATH is not a valid JSON map."
}
```

**Action:** Re-create the proc-task with `envs` excluding `SOURCE_DATASET_PATH`.

#### Scenario 3: Type Error in process()

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 35, in <module>
    result = process(str(item))
  File "/app/src/user_operator.py", line 15, in process
    data = json.loads(item)
TypeError: the JSON object must be str, bytes or bytearray, not PosixPath
```

**Analysis result:**
```json
{
  "priority": "P2",
  "cause": "类型错误",
  "fix": "检查 process() 入参类型，entrypoint.py 传递 str 路径...",
  "matched_line": "TypeError: the JSON object must be str, bytes or bytearray, not PosixPath"
}
```

**Action:** Fix the `process()` function to handle string path input correctly.

#### Scenario 4: Docker Build Failure

**Log excerpt:**
```
Step 4/7 : COPY ./src ./src
COPY failed: file not found in build context: src
```

**Analysis result:**
```json
{
  "priority": "P0",
  "cause": "Dockerfile 构建失败",
  "fix": "检查 Dockerfile COPY 源路径是否存在于工作副本中...",
  "matched_line": "COPY failed: file not found in build context: src"
}
```

**Action:** Ensure `src/` directory exists in the operator source, re-run onboarding.

---