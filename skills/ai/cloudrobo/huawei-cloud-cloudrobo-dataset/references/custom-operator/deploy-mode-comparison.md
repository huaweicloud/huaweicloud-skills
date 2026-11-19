> Part of the custom-operator guide. Index: [custom-operator-reference.md](custom-operator-reference.md)

## Deploy Mode Comparison: 把代码打进镜像 vs 代码放 OBS、运行时挂载 部署方式对比

### Contents 目录

- Overview 概述
- Side-by-Side Comparison 逐项对比
- Image Build & Push Differences 构建镜像差异（重点）
- Asset Registration Differences 资产注册差异
- Runtime Verification Differences 运行时验证差异
- Decision Guide 决策指南（对话话术）
- Image Slimming 镜像瘦身（把代码打进镜像与预设镜像通用）

### Overview 概述

自定义算子上云支持**两种部署路线**，在阶段 0 由用户选定。本参考从代码交付、镜像构建推送、
资产注册到运行时验证逐项对比，说明**为什么**不同，并给出何时选哪条的决策指引。也记录影响推荐结果的**生产环境注意事项**
（权限模型、`/tmp` 只读等）。

> 快速对照：
> - **把代码打进镜像**（内部代号 image-inbuilt，`custom`）—— 算子代码和依赖一起打进 Docker
>   镜像。每次提交都会**重建并推送一个新镜像**（时间戳 tag）。适合依赖重、难以在预设镜像上
>   复现的算子，或镜像本身就是交付物的情况。
> - **代码放 OBS、运行时挂载**（内部代号 OBS-mounted，`preset`）—— 算子代码上传到 OBS，运行时
>   使用一个**已有的运行时镜像**（运行时和依赖已预装）。**不构建、不推送镜像**。适合快速迭代
>   （只改代码）、小体量或纯标准库算子，或已有合适镜像的情况。

### Side-by-Side Comparison 逐项对比

| Dimension | 把代码打进镜像 — image-inbuilt (`custom`) | 代码放 OBS、运行时挂载 — OBS-mounted (`preset`) |
|-----------|----------------------------------|---------------------------------|
| `engine.image_source` | `custom` | `custom` (空间资产-算法 — algorithm links the image asset via `engine.asset_id` + `engine.asset_version_id`); `preset` only for OBS算法 (`OBS_ASSETS`, no assets) |
| Code location | baked into the image (`/app/src`) | customer OBS path (`code_dir` / `algo_path`), mounted at `{job_local_path}/src` at runtime |
| Image build/push | **yes — EVERY run**, new timestamp tag (old tags never overwritten) | **never** — uses a preset runtime image (registered as an image asset) |
| Docker login / SWR push | required (auto-generated login from AK/SK) | not required |
| `code_dir` (algorithm asset) | `""` (empty) | customer OBS path (must start with workspace `default_obs_path`) |
| Task type (`algo_type`) | `WORKSPACE_ASSETS` (+ `algo_id`) | **空间资产-算法** — `WORKSPACE_ASSETS` (+ `algo_id` = Phase 3 asset id; runtime resolves asset `code_dir`/`image`); **OBS算法** — `OBS_ASSETS` (+ `algo_path` + `job_local_path`, `algo_name` required, **no `algo_id`**, Phase 3 asset registration skipped) |
| `algo_entrance` | `python entrypoint.py` (runs via image ENTRYPOINT as root) | **absolute** `python3 {job_local_path}/entrypoint.py` for **both** 空间资产-算法 and OBS算法 (relative `python entrypoint.py` fails: `//entrypoint.py` no such file) |
| First submission (assets) | `create-asset` image + `create-asset` algorithm | `create-asset` preset image + `create-asset` algorithm |
| Re-submission (assets) | `create-version` (image) + `update-asset` (algorithm) | preset **changed** → `create-version` + `update-asset`; preset **unchanged** → single `update-asset` |
| Code change cycle | rebuild image (minutes, depends on deps) + push (large images can take a long time) + version/update | re-upload changed files to the SAME OBS dir (seconds) + re-run task; 空间资产-算法 additionally `update-asset` the algorithm `code_dir` if the path changed |
| Where deps live | installed into the image at build time | pre-installed in the preset image (or missing → runtime `ModuleNotFoundError`) |
| Image size impact | heavy deps inflate the image (e.g. torch+lerobot ≈ 10 GB); every push transfers the delta | no image transfer; code upload is tiny (KB–MB) |
| Failure fix loop | rebuild + re-push + re-register (slow) | fix code on OBS + re-run task (fast); 空间资产-算法: `update-asset` the algorithm `code_dir` when the OBS path changed |

### Image Build & Push Differences 构建镜像差异（重点）

| Aspect | 把代码打进镜像 | 代码放 OBS、运行时挂载 |
|--------|--------|--------|
| Dockerfile | **generated** (Phase 1) from `../../templates/Dockerfile` | **none** (no image build) |
| Build frequency | every submission (timestamp tag, old tags kept) | never |
| SWR login | auto-generated from AK/SK (`docker login -u {region}@{AK} -p <hmac-secret> swr.{region}.myhuaweicloud.com`) | none |
| Push duration | depends on image size & changed layers — **a 10 GB image can take 10–60+ min**; must keep the customer informed (see [progress-feedback.md](progress-feedback.md)) | none (code upload only) |
| Image size optimization | **must keep the image as small as reasonable** — see "Image Slimming" below | only the preset image matters (already built once) |
| Permission pitfalls | image runs as root via ENTRYPOINT — `/opt/cloud/3rdComponent` (750, `service:servicegroup`) is reachable | **platform runs `algo_entrance` as a NON-root user** — if the preset image's Python lives under a 750 directory (e.g. HCE Python `/opt/cloud/3rdComponent`), `stdbuf: Permission denied` — fix the preset image permissions once (see lessons below) |

#### Build Network 构建网络（内网 vs 外网）

`docker build` 的网络行为**取决于构建主机所在网络**，先探测再选策略——不要盲目套用
代理参数或默认直连：

**探测命令（Phase 2 开始前执行）：**
```bash
# 外网可达性
timeout 10 curl -s -o /dev/null -w "%{http_code}" https://pypi.org/simple/ 2>&1   # 200 = 外网直连可达
timeout 10 curl -s -o /dev/null -w "%{http_code}" https://download.pytorch.org/whl/cpu/ 2>&1
# 是否存在本机/daemon 代理（daemon 代理见 docker.service.d/*.conf 的 Environment=HTTP_PROXY）
env | grep -i proxy
cat /etc/systemd/system/docker.service.d/*.conf 2>/dev/null | grep -i proxy
```

**分支选择：**

| 探测结果 | 构建策略 |
|----------|----------|
| pypi/pytorch **直连 200**（外网） | 正常 `docker build`，用生成的 Dockerfile，`pip install` 无需额外参数 |
| 仅 **代理可达**（内网/代理前置网络，如华为内部） | `docker build` 传 `--build-arg HTTP_PROXY/HTTPS_PROXY` + `NO_PROXY`（见 lesson 4）；必要时补齐编译工具链（lesson 5） |
| pypi 不可达且无代理 | 无法在线装依赖——提示客户提供离线 wheel 或镜像，或改用已有预设镜像 |

> 探测结果可能因容器与宿主网络策略不同而有差异（宿主可达不等于构建容器内可达）。
> 以**实际能通的方式**为准，向客户说明所采用的网络路径（直连/代理/离线）。

#### Production lessons 生产环境注意事项

1. **Non-root platform user cannot reach 750 dirs.** HCE Python images keep the
   bundled interpreter at `/opt/cloud/3rdComponent/python` with mode `750`
   (`service:servicegroup`). 代码放 OBS、运行时挂载 tasks run `algo_entrance` as an arbitrary
   non-root user, so both a relative `python3` (resolves to `/usr/bin/python3`,
   Python 3.9, no site-packages) and an absolute `/opt/cloud/3rdComponent/.../python3`
   fail. Fix (once, on the preset image):
   ```dockerfile
   RUN chmod o+rx /opt/cloud  \
    && chmod -R o+rX /opt/cloud/3rdComponent \
    && chmod o+x /opt/cloud/3rdComponent/python/bin/python3.12
   ```
   Verify as the most restrictive user before pushing:
   ```bash
   docker run --rm --user 65534:65534 --entrypoint /bin/bash <image> -c \
     "/opt/cloud/3rdComponent/python/bin/python3 -V && stdbuf -oL -eL /opt/cloud/3rdComponent/python/bin/python3 -c 'print(1)'"
   ```
2. **Platform may mount `/tmp` read-only.** In 代码放 OBS、运行时挂载 the OBS code is mounted under
   `/tmp/cloudrobo/...`; Python `tempfile` then fails with
   `[Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', ...]`.
   The generated entrypoint **first probes the system `/tmp`** and uses it as-is when
   writable (so **no junk `.cloudrobo-tmp` folder appears in the output dataset**);
   only when `/tmp` is read-only does it redirect `TMPDIR` to the guaranteed-writable
   output dir as a fallback, and it **removes that fallback folder at exit**:
   ```python
   _tmpdir_fallback = os.path.join(os.environ.get("TARGET_DATASET_PATH", "/output"), ".cloudrobo-tmp")
   os.makedirs(_tmpdir_fallback, exist_ok=True)
   os.environ["TMPDIR"] = _tmpdir_fallback
   tempfile.tempdir = _tmpdir_fallback
   # ... finally: shutil.rmtree(_tmpdir_fallback, ignore_errors=True)
   ```
   (already baked into `../../templates/entrypoint.py`)
3. **代码放 OBS、运行时挂载 absolute `algo_entrance` is mandatory.** A relative `python entrypoint.py`
   fails with `stdbuf: failed to run command 'python': Permission denied`. Use
   `python3 {job_local_path}/entrypoint.py` (or the full interpreter path once
   permissions allow) — see [onboarding-phase-4.md](onboarding-phase-4.md) Step 4.1.
4. **`docker build` RUN steps do NOT inherit the daemon's proxy env (intranet/proxy
   networks only).** The daemon proxy (`HTTP_PROXY`/`HTTPS_PROXY` in
   `docker.service.d/*.conf`) applies only to `docker pull`/`push`, not to build-time
   `RUN`. On proxy-fronted networks (e.g. Huawei internal), to install dependencies
   during `docker build`, pass the proxy explicitly:
   ```bash
   docker build \
     --build-arg HTTP_PROXY=http://<proxy>:<port>/ \
     --build-arg HTTPS_PROXY=http://<proxy>:<port>/ \
     --build-arg 'NO_PROXY=*.huawei.com,*.huawei.net,*.huawei.org,<swr-registry>,localhost,127.0.0.1' \
     -t <image>:<tag> .
   ```
   - **`NO_PROXY` must include `*.huawei.com` etc.** for `dnf`/`yum` to reach the
     intranet RPM repo directly (otherwise `Curl error (56)` / `504 from proxy`).
   - Alternatively set `ENV HTTP_PROXY/HTTPS_PROXY/NO_PROXY` inside the Dockerfile,
     or `unset` the proxy before `dnf` commands that must hit the intranet.
   - **External-network environments skip all of this** — plain `docker build` works.
   - This only matters for the **one-off preset-image build** (代码放 OBS、运行时挂载) and **把代码打进镜像**
     image builds — the pre-built images used at runtime are unaffected.
5. **HCE base images may lack the full compile toolchain.** On
   `registry-cbu.huawei.com/cloudrobo/hce-python:*`, `dnf install binutils gcc make`
   alone is **not enough** to build `evdev` (a `pynput` dependency of `lerobot`):
   `binutils` on HCE ships **without `ld`** (it lives in `binutils-extra`), and
   `linux/input.h` comes from `kernel-headers`. Install all of:
   ```bash
   dnf install -y binutils binutils-extra gcc make kernel-headers python3-devel
   ```
   then `pip install ...` (evdev compiles against kernel headers), then remove the
   compile-only deps for image slimming:
   ```bash
   dnf remove -y binutils binutils-extra gcc gcc-c++ make kernel-headers python3-devel \
     && dnf clean all
   ```
6. **`opencv-python` on a headless container fails to import** (`libxcb.so.1: cannot
   open shared object file`) because the X11 client libs are absent. For CPU-only
   data-processing operators use **`opencv-python-headless`** in `requirements.txt`
   (provides the same `cv2` module without the GUI stack).
7. **Install CPU-only torch for CPU-only workers.** `pip install torch` pulls the
   CUDA build (multi-GB) even on CPU-only nodes. When the worker spec has
   `gpu: 0`, install from the CPU index:
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cpu \
     --extra-index-url https://pypi.org/simple -r requirements.txt
   ```
   (`lerobot==0.5.0` resolves `torch>=2.2.1` and accepts the CPU build.)

### Asset Registration Differences 资产注册差异

> **代码放 OBS 并直接挂载 (mount the OBS code directly) skips asset registration entirely** —
> the runtime task uses `algo_path` + `image` (SWR URL string) and links to **no
> asset**, so creating image/algorithm assets would be redundant. Only 把代码打进镜像 and
> 代码放 OBS 并注册算法资产 register assets.

> **⚠️ MANDATORY ORDERING: image asset FIRST, algorithm asset SECOND.** Both 把代码打进镜像
> and 代码放 OBS 并注册算法资产 create the image asset **before** the algorithm asset. The
> algorithm asset's `engine.image_url` references the SWR image that the image asset
> registers — creating the algorithm asset first (before the image asset exists)
> produces a broken algorithm that references a non-registered image, causing runtime
> image-pull failures. If `create-asset --type image` returns `400 SWR image not
> available`, the image is not in SWR (only local) — `docker login` (auto-generated
> from AK/SK) + `docker push` the image to the SWR URL, then **retry**
> `create-asset --type image` until it succeeds, **THEN** create the algorithm asset.
> **Never proceed to the algorithm asset if the image asset failed.**

- **First submission**: 把代码打进镜像 registers the **built image** as an image asset, then
  the algorithm asset (`image_source=custom`, `code_dir=""`). 代码放 OBS 并注册算法资产 registers
  the **preset image** as an image asset, then the algorithm asset
  (`image_source=custom`, `code_dir=<customer OBS path>`). **⚠️ In both modes the
  algorithm asset's `engine` MUST also carry `asset_id` = image asset id and
  `asset_version_id` = image asset `latest_version_id` — these two fields LINK the
  algorithm to the created image asset (空间资产-镜像). An algorithm asset with only
  `image_url` + `image_source` is NOT linked to the image asset; both fields must be
  set together with `image_source=custom`.** In both modes the image asset MUST
  succeed before the algorithm asset is created.
- **Re-submission**: 把代码打进镜像 always `create-version` (new image URL) + `update-asset`.
  代码放 OBS 并注册算法资产 only does that when the **preset image changed**; if the preset image is
  unchanged, a **single `update-asset`** (`code_dir` may change) suffices. Both
  re-submission `update-asset` calls MUST keep `engine.asset_id` +
  `engine.asset_version_id` (re-point `asset_version_id` to the new image version
  when the image changed).

### Runtime Verification Differences 运行时验证差异

- 把代码打进镜像 task-config: `algo_type=WORKSPACE_ASSETS`, `algo_id` + `algo_name` +
  `algo_entrance` (from `ext_metadata.command`) + `image` (built SWR URL).
- 代码放 OBS、运行时挂载 task-config branches by the **task-creation way** chosen in Phase 0
  (default: 注册成空间里的算法资产后引用; switch only when the customer explicitly asks
  to mount OBS code without registering an asset):
  - **空间资产-算法 — use the created algorithm** (`WORKSPACE_ASSETS`): `algo_id` = the
    Phase 3 algorithm `asset_id` + `algo_name` (**required**) + `algo_path` (= asset
    `code_dir`, **required**) + `job_local_path` (**required**) + **absolute**
    `algo_entrance` (`python3 {job_local_path}/entrypoint.py`) + `image` (preset SWR
    URL). Omitting `algo_path`/`job_local_path` fails (`//entrypoint.py`).
  - **OBS算法 — mount the OBS code directly** (`OBS_ASSETS`): `algo_name` (**required**)
    + `algo_path` + `job_local_path` + absolute `algo_entrance` + `image` (preset SWR
    URL), **no `algo_id`**; **Phase 3 asset registration is skipped** (no assets created).
- Both create the task **without `--wait`**, then poll `show-task` and keep the
  customer informed of progress (see [progress-feedback.md](progress-feedback.md)).
- **Output layout (both modes):** single-dataset conversion writes **flat** into the
  output root (`TARGET_DATASET_PATH`) — the generated entrypoint writes
  `OUTPUT_DIR/<item-stem>.json` and never creates a nested `{output_name}`-named
  subfolder (observed failure: output nested one extra level under
  `lerobot-output-20261021181446` when the operator itself mkdir'ed a folder named
  after the output dataset). Multi-dataset runs use a `{dataset_index}_` prefix only.
  No `.cloudrobo-tmp` junk folder is left in the output (see lesson 2).
- **Re-run after a FAILED verification (把代码打进镜像):** rebuild → **re-submission branch**
  (`create-version` + `update-asset`) → `show-asset` the algorithm asset to confirm it
  points at the NEW image version → fresh `output_name` → create the task. A stray
  **HTTP 500** on the re-run `create-task` almost always means a stale algorithm-linkage
  or a stuck pre-registered output asset from the failed run — see
  [failure-analysis-guide.md](failure-analysis-guide.md) (pattern 5d).

### Decision Guide 决策指南（对话话术）

> **部署方式必须问一次，不能静默决定。** 这是客户的运行时决策，取决于客户自己的镜像与依赖。
> 用一轮问清（推荐值预选）：平台已有镜像资产（客户点名）→ 只查这一个；客户提供镜像 URL →
> 直接填 SWR 地址；本机有 Docker → 打进镜像（依赖随镜像安装，最稳）；
> 代码放 OBS、运行时挂载 → 快，但镜像必须已含依赖。
> 本机没有 Docker 只是需要询问的理由，不是替客户选 OBS 挂载的理由。
> 客户说"都可以"时，按上述推荐顺序选第一个成立的并说明理由。
>
> **不要替客户挑镜像。** 禁止全量扫描 `--type image` 资产、翻历史运行、比对别人用过的镜像来
> "推荐"一个运行时——这类扫描耗时且常选出依赖不全的镜像。只有客户点名某个镜像后，才去查
> 它的地址和版本。

Prefer **把代码打进镜像** when:
- the operator has heavy / custom / hard-to-reproduce dependencies (torch, CUDA,
  lerobot, rosbags, ...) and no suitable preset image exists;
- the image itself is a deliverable (e.g. offline distribution, image asset reuse);
- the customer explicitly wants a fully self-contained environment.

Prefer **代码放 OBS、运行时挂载** when:
- the operator code is small / stdlib-only and the base `hce-python` preset image
  suffices;
- the customer wants **fast iteration** (code-only changes, re-run in seconds, no
  image rebuild);
- a suitable preset image (with the required deps) already exists in SWR;
- image build/push resources are limited (SWR quota, build time, network).

> ⚠️ 代码放 OBS、运行时挂载 still needs the preset image to be **reachable and permission-fixed** (see
> lessons above). If the operator needs deps that are missing from every available
> preset image, 代码放 OBS、运行时挂载 is not free — you would first build + push a suitable preset
> image once, then switch to 代码放 OBS、运行时挂载 for subsequent iterations.
>
> **Preset-image tag rule 预设镜像 tag 规则:** whenever the skill builds (one-off) or
> rebuilds a 代码放 OBS、运行时挂载 preset image, the SWR tag **MUST be a timestamp**
> (`{YYYYMMDDHHMMSS}`, e.g. `swr.{region}.myhuaweicloud.com/{ns}/{repo}:20260924154534`)
> — never the base-image version string (e.g. `:2.0_3.12.10_2605.1`) and never
> `:latest`. Each preset-image rebuild gets a **new timestamp tag**; old tags are kept
> (mirrors the 把代码打进镜像 tag policy, so the algorithm asset can always be re-pointed to a
> specific build and the image asset version history stays traceable).

### Image Slimming 镜像瘦身（把代码打进镜像与预设镜像通用）

Keep the built image as small and reasonable as possible:

- **Layer order for caching**: `COPY requirements.txt` before `COPY ./src`; base image
  + system packages first (rarely change), deps second, source last.
- **Clean package-manager caches in the same `RUN`** (apt/yum/dnf):
  ```dockerfile
  RUN dnf install -y gcc gcc-c++ make ... && dnf clean all && rm -rf /var/cache/dnf
  # or apt: && rm -rf /var/lib/apt/lists/*
  ```
- **pip with `--no-cache-dir`** and clean pip cache:
  ```dockerfile
  RUN python3 -m pip install --no-cache-dir -r requirements.txt && rm -rf ~/.cache/pip
  ```
- **Multi-stage build** when the operator needs build-time-only tools (gcc, headers):
  build wheels in a builder stage, copy only wheels/site-packages into the final
  image, so the final image has no compiler toolchain.
- **Remove intermediate artifacts** in the same layer that created them (logs,
  temp files, `__pycache__`).
- Use a base image whose tag is a **specific pinned version**, not `latest`.
- After successful verification, **only keep useful images** locally — see
  [progress-feedback.md](progress-feedback.md) §Cleanup & Image Housekeeping.

> Typical sizes: a full operator image with lerobot/ray/torch/opencv deps is on the order of
> 10 GB, most of it `pip install` of torch/opencv — unavoidable for 把代码打进镜像, while a
> permission-fix layer adds only KB. If the operator only needs stdlib, the image is just the
> base (~1 GB).

---