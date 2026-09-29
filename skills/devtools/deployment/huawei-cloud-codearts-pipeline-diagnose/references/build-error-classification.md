# Build Log Error Classification Catalog

This catalog backs `huawei_diagnose_build_failure` and
`huawei_extract_build_log_errors`. Match error lines (regex, case-insensitive)
against the patterns below to classify the root cause. Pattern → category →
evidence → next action.

## 1. Network (网络)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `connection refused` / `connect timed out` | Build host cannot reach endpoint | Check network ACL/security group and endpoint availability |
| `could not resolve host` / `未知的名称或服务` / `Name or service not known` | DNS resolution failed | Verify DNS/proxy config; check scm repo host name |
| `network is unreachable` / `no route to host` | Route missing | Check VPC route/egress; build host subnet |
| `502` / `503` / `504` (as http status) | Upstream service unavailable | Retry; check the dependency service status |
| `ssl.*error` / `certificate verify failed` / `unable to get local issuer` | TLS handshake failed | Update CA bundle; verify endpoint certificate |
| `timed out` / `timeout` (download/fetch) | Artifact/dependency download timeout | Retry; enlarge build timeout; check repo size |

## 2. Parameter / Configuration (参数)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `missing parameter` / `缺少参数` / `undefined variable` / `未定义变量` | Build parameter not passed | Check `RunJob --parameter.N.*` values and job config |
| `No such file or directory` / `找不到文件` / `not found` (file path) | Working dir/script path wrong | Check scm checkout path, working directory, build script path |
| `parse error` / `invalid syntax` / YAML/JSON error | Config/script syntax bad | Fix the build script or `--definition` JSON |
| `no such branch` / `分支不存在` / `commit not found` | scm ref invalid | Verify `--scm.build_commit_id` / `--scm.build_tag` / branch |
| `invalid.*argument` / `参数.*错误` / `invalid parameter` | Parameter value rejected | Re-check parameter format against API help |

## 3. Load / Resource (负载/资源)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `OutOfMemoryError` / `GC overhead limit` / `heap space` / `内存不足` | Memory exhausted | Increase build flavor (`--flavor`) or optimize build |
| `no space left on device` / `disk quota` / `磁盘空间不足` | Disk full | Clean cache; enlarge build disk/flavor |
| `killed` / `cgroup.*limit` / `process was terminated` | Build killed by resource limit | Check flavor limits; reduce parallel steps |
| `build.*timeout` / `执行超时` / `job timed out` | Total build time exceeded | Extend timeout; split the build; optimize steps |
| `too many.*open files` / `cannot allocate memory` | Per-process limits | Adjust ulimit; reduce concurrency |

## 4. Code / Compile (代码/编译)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `error:` (compiler, e.g. `error: cannot find symbol`, `BUILD FAILURE`) | Compile error | Fix source code; check missing dependency import |
| `failed to compile` / `compilation failed` | Compile step failed | Review the failing module in stage log |
| `test.*failed` / `tests failed` / `BUILD FAILURE` (test phase) | Unit/integration test failure | Inspect failing test report |
| `Cannot resolve symbol` / `package .* does not exist` | Missing dependency in build | Check dependency repo/config (maven/gradle/npm) |

## 5. Dependency (依赖)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `Could not resolve dependencies` / `Failed to collect dependencies` | Dependency not downloadable | Check dependency mirror/repo reachability and credentials |
| `Cannot find module` / `require.resolve` errors | JS/Node module missing | Run install step; check lockfile |
| `403` / `401` (dependency fetch) | Repo credentials expired | Refresh artifact repo token/credentials |
| `checksum mismatch` / `sum verification failed` | Corrupted artifact | Clear cache and re-fetch |

## 6. Permission (权限)

| Pattern (regex fragment) | Evidence | Next action |
|--------------------------|----------|-------------|
| `permission denied` / `AccessDenied` / `无权限` | File/API permission rejected | Check IAM roles and repo/bucket permissions |
| `not authorized` / `Unauthorized` / `403` (API call) | Service credentials insufficient | Verify AK/SK scope; add missing IAM policy |
| `fatal: could not read Username` / `Authentication failed` (git) | Git credentials wrong | Update repo credentials/deploy key in job config |

## 7. Other / Unknown

Any line not matching the categories above → mark `other`, keep the original
line, and include the surrounding 5 lines as context for the user.

## Categorization Workflow

1. Fetch the log (`DownloadBuildLog --record_id={record_id} --log_level=INFO` or
   `DownloadBuildRealTimeLog` for a running build).
2. Extract lines matching `error|fail|exception|错误|失败|异常` (case-insensitive),
   deduplicate, keep timestamps.
3. Match each line against categories 1–6 (first match wins; aggregate counts).
4. Report: dominant category, top error lines (≤ 10), first failing step (from
   `ShowBuildRecordFullStages` stage order), and the matching "Next action".
5. If no pattern matches 2+ distinct lines, report as `other` with context rather
   than guessing.