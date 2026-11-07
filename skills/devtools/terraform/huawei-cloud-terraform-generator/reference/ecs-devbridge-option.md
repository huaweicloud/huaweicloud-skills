# DevBridge SSH tunnel option for ECS (AI DevSpace)

This file contains the full DevBridge setup flow for ECS creation. Referenced by SKILL.md section 4.3.2.

## Part 0: DevBridge 是什么、有什么好处、何时该装

### 它是什么

DevBridge 是华为云的安全中继隧道：ECS 主动**出站**连到中继，SSH/RDP 再从隧道反向接入。因此 ECS 的**安全组入方向可以全关**，公网上没有任何可被扫描的端口。

### 好处（按价值排序）

1. **零暴露（核心价值）**：没有公网 IP 暴露、没有入站端口，杜绝 SSH 爆破与端口扫描。这是装它最根本的理由，与机器台数无关。
2. **省公网资源（规模越大越明显）**：
   - 不需要每台 ECS 各绑一个 EIP → 省下 N 个公网 IP 及对应配额/费用；
   - 没有公网入向流量 → 省入向带宽；
   - 多台共用一条出站通道（NAT 网关 + 1 个 EIP），而不是每台单独一个 EIP。
3. **连接稳定方便**：开机自动连隧道、重启不断线；本地 `ssh root@localhost -p <端口>` 直连，无需记公网 IP。

### 代价（是「复杂度」，不是「钱」）

DevBridge 的前置资源——FunctionGraph 函数、IAM 委托/自定义角色、DevBridge API Key、DevStage 环境——**基本不产生费用**：

- 函数在免费额度内（100 万次/月），转发 Key 只在开机跑几次，约等于免费；
- IAM 委托/自定义角色、DevBridge API Key：免费；
- DevStage 环境：只要「存在但不启动」就不产生运行费，仅占用配额（配额≠钱）；只有真把它开机才有运行费。

真正的代价是**组件多、链路长**：每多一环就多一个失败点，destroy 时也要一起清干净。

另外 ECS 仍需一条出站通道（NAT 或 EIP）供隧道出站——但这**不是 DevBridge 独有**（传统 SSH 也要 EIP），而且多台能共用一条，规模大反而更省。

### 决策规则（装 / 不装）

- **推荐装**：要「零暴露/安全合规」（核心价值，与规模无关）；或规模大到省 N 个 EIP 值得为之加复杂度；或账号已有 DevStage 环境与 devbridge CLI。
- **不推荐装**：一次性测试、测完就删、且不在乎暴露 22；规模小（省不到钱还白加复杂度）；只想省 EIP（跳板机复杂度更低、更省事）。

> 一句话：DevBridge 加的是复杂度，换的是「零暴露 + 规模化的省 EIP」；它只在规模大时才"省钱"，但任何规模下都"买安全"。

## Part 1: Always ask (before generating Terraform)

When creating ECS instances from within AI DevSpace, always ask the user whether to install DevBridge. Do NOT force it, do NOT skip the question.

After confirming the basic ECS plan (region, flavor, image, etc.), ask the user:

```
要不要给这台 ECS 预装 DevBridge SSH 隧道？

  DevBridge 是华为云的安全中继隧道，装了之后：
    - 安全组入方向全关，公网不暴露任何端口，零攻击面
    - SSH 走隧道进来，不需要开 22 端口，不需要知道公网 IP
    - 开机自动连隧道，重启不断线
    - 从本地直接 ssh root@localhost -p <端口> 就能连

  省钱的好处：
    - 省一台跳板机/堡垒机：传统「不开公网 SSH」要单独买跳板机或堡垒机服务，DevBridge 自带中继隧道，省下这笔钱
    - 纯后台机器不用每台配公网 EIP：SSH 走隧道、出网共享 NAT 网关即可，比每台绑一个独立 EIP 更省
    - 零入站攻击面，免去被爆破/入侵的隐性成本（突发流量费、被拿来挖矿产生的超额账单）

  安装方式（唯一 — B1，FunctionGraph 代理）：
    用户凭证不进 user_data，ECS 通过 FunctionGraph 代理获取 DevBridge API Key
    Key 在沙箱里预先创建并落盘，函数只转发、不创建 Key

  不装的话：正常创建，安全组按你的要求配置
```

- If user says **yes / 装 / 要** → proceed to Part 2 (condition check).
- If user says **no / 不装 / 不要** → skip DevBridge, use normal template.

## Part 2: Condition check (only if user wants DevBridge)

### Step 0: Check for existing sandbox DevBridge API Key (DO THIS FIRST)

Before any other checks, look for an existing DevBridge API Key in the sandbox. If one exists and works, it will be passed to the FunctionGraph function (B1 mode) so the function can return it directly without calling DevStage API.

1. **Collect keys from ALL locations** (they can diverge — the CLI cache under `~/.huawei` may hold a stale/disabled key while the sandbox holds the authoritative one):
   - `~/.huawei/devbridge/config.yaml` (devbridge CLI cache, `credentials.api_key`)
   - **Sandbox config (AUTHORITATIVE)**: `~/job-envs/sandboxes/devbridge-*/.huawei/devbridge/config.yaml`
   - Environment variable `DEVBRIDGE_API_KEY` (if set)

   Collect each distinct key value into a candidate list.

2. **Verify EVERY candidate, prefer the authoritative source**:
   ```bash
   devbridge auth login --api-key="<candidate-key>" && devbridge list
   ```
   - Do NOT trust a single location — a key that was valid minutes ago may already be disabled.
   - If exactly one candidate is valid → use it.
   - If multiple are valid → prefer the **sandbox config key** (`~/job-envs/sandboxes/devbridge-*/.huawei/devbridge/config.yaml`), which is the authoritative source.
   - If none is valid → fall through to step 4 (create a new key in the sandbox).

3. **If key is valid** → set `devbridge_api_key = "<existing-key>"` and inform the user:
   ```
   ✅ 检测到沙箱已有可用的 DevBridge API Key，将传递给 FunctionGraph 函数直接复用
      函数不会调用 DevStage API，不会创建新 Key
   ```
   Continue to Step 1 below (still need to check OS type, quota, EIP, etc.), but skip Step 6 (DevStage env check) and Step 7 (B1 permissions for DevStage API — AK/SK still needed for FunctionGraph creation, but not for DevStage API call).

4. **If key is invalid or not found** → create a new key **in the sandbox** via DevStage API (`POST /open-api-public/v1/relay/api-key`) using the sandbox's user-level AK/SK (which DevStage accepts), persist it to disk, then set `devbridge_api_key = "<new-key>"`. The FunctionGraph function does NOT create keys — it only forwards a pre-created key. Continue to Step 1 below.

   ```bash
   # 在沙箱里创建新 DevBridge API Key（用沙箱的用户级 AK/SK，DevStage 接受）
   # 调 POST /open-api-public/v1/relay/api-key 拿到新 key 后落盘：
   #   ~/.huawei/devbridge/config.yaml  (credentials.api_key)
   #   ~/.devbridge_api_key
   ```

### Step 1+: Standard condition checks

Check the following conditions. If any fails, tell the user what failed and why.

1. **Detect OS type** — both Linux and Windows are supported:
   - Linux image → bash user_data, tunnel SSH port 22
   - Windows image → PowerShell user_data, tunnel RDP port 3389
2. **Tunnel quota available?** Run `devbridge list` to count existing tunnels. If >= 10 → fail.
3. **ECS count fits quota?** If remaining quota < N ECS → fail with exact numbers.
4. **EIP or NAT for outbound?** DevBridge needs outbound internet. If no EIP and no NAT gateway → fail: offer to add EIP (~¥0.02/hour).
5. **Egress security group allows TCP 443?** DevBridge tunnel connects out on TCP 443. If user wants zero egress → fail: ask to allow at least TCP 443 egress.
6. **DevStage development environment exists?** (Skip if sandbox key is valid — no DevStage API call needed.) Call `GET /open-api-public/v2/devenvs` via DevStage API. If empty → do NOT fail immediately; go to **Step 6a** to offer creating an environment. Only if the user declines or creation fails, use the old hard failure: "账号下无 DevStage 开发环境，无法创建 DevBridge API Key".
### Step 6a: Create a DevStage environment when none exists (run when Step 6 returns empty)

When `GET /open-api-public/v2/devenvs` returns an empty list, do NOT fail immediately. Tell the user and offer to create one:

```
⚠️ 账号下没有 DevStage 开发环境，DevBridge API Key 的创建以环境存在为前提。

   要不要我帮你自动创建一个开发环境？

   创建前需要确认：
     - 账号已签署开发者服务协议 / 生态隐私政策 / 开发者空间协议
     - 账号已完成实名认证
     - 你能提供一个模板 ID（template_id），在控制台「云开发环境」页面可查

   创建开发环境会占用账号配额、可能产生资源费用；创建后只需「环境存在」即可继续，无需开机。
```

- User says **no / 不要** → use the original hard failure: "账号下无 DevStage 开发环境，无法创建 DevBridge API Key". DevBridge flow stops.
- User says **yes / 要** → run the checks below in order. Any failed check stops the flow with an explanation.

**(1) Agreement sign check** — `GET /open-api-public/v1/agreements`, check each `sign_status`:
- all `1` (signed latest) → skip.
- any `2` (outdated) or `3` (unsigned) → `POST /open-api-public/v1/agreements` with those entries in `sign_info_list`.

**(2) Real-name (实名) check** — `GET /open-api-public/v1/realnames`:
- `realname_status = "2"` → pass.
- otherwise → fail: "账号未完成实名认证，请先到控制台完成实名后再试". Stop.

**(3) Get template_id (manual — no list API)**:

⚠️ The open API Wiki provides NO "list templates" endpoint, so `template_id` cannot be auto-fetched. Guide the user to the console 云开发环境 page to read an available template ID, or ask them to provide one directly. If unavailable → fail. Stop (a Container environment cannot be created without it).

**(4) Query available specs** — `GET /open-api-public/v1/specs?template_id=<template_id>`:
- prefer `is_default = true`; record `flavor_id`, `env_cpu_size`, `env_mem_size` (→ map to `cores` / `memory`).
- note: the response does NOT return `arch`; default to `ARM` (matches the Ascend spec examples). If creation fails on arch, retry with `X86`.

**(5) Create the environment** — `POST /open-api-public/v2/devenvs`:

```json
{
    "source": "CLI",
    "type": "Container",
    "name": "ecs-devbridge-auto-<timestamp>",
    "cores": <env_cpu_size>,
    "arch": "<ARM|X86>",
    "memory": <env_mem_size>,
    "flavor_id": "<flavor_id>",
    "template_id": "<template_id>"
}
```

- `error_code = "0000"` + `devstage_id` returned → success. Step 6 now passes; continue to Step 7.
- `HD.97420468` (数量上限) / `HD.98320022` (容器上限) → fail: ask user to clean up unused environments first, then retry.
- other codes → follow the doc's 处理建议.

**(6) Boundary reminder** — creating an environment only fixes the "environment exists" precondition. It does NOT grant permission to call `POST /open-api-public/v1/relay/api-key`; that permission is independent. If key creation later fails with a permission error, treat it as a Key-API-permission issue (not "no environment").

7. **B1 mode permissions?** Check FunctionGraph + IAM permissions:

   a. **FunctionGraph available?** FunctionGraph is available by default on Huawei Cloud accounts — no separate activation needed. Free tier: 1 million invocations/month.

   b. **IAM permissions?** Two sub-modes supported:

      - **Custom role mode** (`use_custom_role = true`, default): creates a custom IAM role with only `functiongraph:invokeFunction` permission. Requires: IAM agency creation + custom role creation + FunctionGraph function creation permissions.
      - **Predefined role mode** (`use_custom_role = false`): uses a predefined role (default `FunctionGraph Administrator`). Requires: IAM agency creation + FunctionGraph function creation permissions (NO custom role creation needed).

   | Sandbox key | DevStage env | FunctionGraph | IAM agency | Custom role | Outcome |
   |-------------|-------------|---------------|------------|-------------|---------|
   | ✅ valid | any | ✅ | ✅ | ✅ | **B1 mode** with custom role, function returns existing key |
   | ✅ valid | any | ✅ | ✅ | ❌ | **B1 mode** with predefined role, function returns existing key |
   | ✅ valid | any | ✅ | ❌ | any | **不可用** — 缺 IAM 委托，引导用户手动安装（指南见下方） |
   | ✅ valid | any | ❌ | any | any | **不可用** — 缺 FunctionGraph，引导用户手动安装（指南见下方） |
   | ❌ | ✅ | ✅ | ✅ | ✅ | **B1 mode** with custom role, function creates new key |
   | ❌ | ✅ | ✅ | ✅ | ❌ | **B1 mode** with predefined role, function creates new key |
   | ❌ | ✅ | ✅ | ❌ | any | **不可用** — 缺 IAM 委托权限，引导用户手动安装（指南见下方） |
   | ❌ | ✅ | ❌ | any | any | **不可用** — 缺 FunctionGraph 权限，引导用户手动安装（指南见下方） |
   | ❌ | ❌ | any | any | any | **ERROR** — no DevStage environment, cannot create API Key |

### Mode selection

自动预装只支持 **B1 模式**（FunctionGraph 代理）。一切把 DevBridge API Key 直接写进 ECS user_data 的降级方案均已移除（安全部门禁用）。

- **条件满足**（FunctionGraph 可用 + IAM 委托可用）：ECS user_data 中不含任何凭证。进入 Part 3A。
- **条件不满足**（缺 FunctionGraph 或 IAM 委托/权限）：
  ```
  ⚠️ 当前账号不满足 B1 模式的前置条件，无法通过本 skill 自动预装 DevBridge SSH 隧道。

     请参考一键安装指南手动安装：
     👉 https://gitcode.com/anruostyle/devbridge-ssh-setup/blob/main/安装指导.md
  ```

  不要降级到把 Key 写进 user_data 的方案，也不要静默跳过预装。

## Part 3A: Generate Terraform with DevBridge (B1: FunctionGraph proxy)

1. **Read the template** at `assets/ecs/instance-with-devbridge/` as the starting point.
2. **Set variables**: set `devbridge_api_key = "<key>"`. The key MUST already exist — pre-created in the sandbox in Step 0 (reused if valid, or newly created via DevStage API there). There is no "null → function creates the key" path.
3. **FunctionGraph function**: Terraform creates a FunctionGraph function (`huaweicloud_fgs_function.key_creator`) with:
   - Python runtime
   - **Only the pre-created DevBridge API Key** in `user_data` as JSON (`jsonencode({EXISTING_API_KEY = var.devbridge_api_key})`). No AK/SK, no security token — the function holds no user credentials.
   - Function code reads the key via `context.getUserData('EXISTING_API_KEY')` and returns it directly.
   - The function does NOT call DevStage API — the key is pre-created in the sandbox (Step 0), where the sandbox's user-level AK/SK is accepted by DevStage.
4. **IAM role + agency**: Terraform creates:
   - A custom IAM role with `functiongraph:invokeFunction` permission
   - An IAM agency (`op_svc_ecs` delegation) with that role, attached to the ECS
5. **Security group**: zero inbound rules, egress limited to TCP 443 + TCP 80 + UDP 53.
6. **EIP**: for outbound access.
7. **user_data (cloud-init)**: generates an OS-aware script that:
   - Gets STS credentials from metadata service (`169.254.169.254`) — NOT from user_data
   - Invokes the FunctionGraph function with those STS credentials
   - Receives the DevBridge API Key from the function
   - Installs DevBridge CLI, creates tunnel, encrypts key to disk
   - Unsets all env vars

### Security measures (B1)

- **ECS user_data contains NO credentials** — only function URN, region, project_id (all non-sensitive)
- **Function user_data contains NO AK/SK** — only a pre-created DevBridge API Key (revocable, tunnel-only scope). User AK/SK never enters Terraform artifacts (tfstate / user_data / metadata / logs).
- **ECS uses agency STS from metadata service** — service-level credentials that don't appear in tfstate or user_data
- **Function only returns the DevBridge API Key** — it holds no AK/SK to leak
- **IAM agency restricts invocation** — only the designated ECS can invoke the function
- `.gitignore` must include `terraform.tfstate` and `terraform.tfvars`

### What's in tfstate (B1)

The FunctionGraph function's `user_data` contains **only the DevBridge API Key** (as `EXISTING_API_KEY`). No AK/SK, no security token.

- **AK/SK never enter tfstate** — they are used only (a) in the sandbox to create the key via DevStage API, and (b) for the Terraform provider's apply-time authentication; neither path writes them into the function `user_data`.
- The only sensitive value in tfstate is the DevBridge API Key, which is **revocable and tunnel-only** (it cannot touch OBS/ECS/RDS).

Mitigation:
- `sensitive = true` on `devbridge_api_key` (masked in plan output)
- `.gitignore` for tfstate
- Remote backend with encryption (recommended for production)
- The FunctionGraph function is kept until `terraform destroy` (it holds only the revocable DevBridge key, no AK/SK) — no urgent cloud-side removal step (see Part 4)

## Part 4: Post-apply connection guidance (after terraform apply succeeds)

The DevBridge tunnel is created by cloud-init on the ECS first boot. Expected wait time depends on the OS:
- **Linux**: 1-3 minutes after apply completes (the image ships python3; only the DevBridge CLI is downloaded and the tunnel created).
- **Windows**: 15-20 minutes after apply completes (the clean image has no python3/hcloud — cloudbase-init must download embedded Python 3.11 + the DevBridge CLI + OpenSSH-Win64 before creating the tunnel). Do NOT treat a missing tunnel within the first 10 minutes as a failure.

1. **Wait for tunnel to appear** — poll `devbridge list` every 15-20s. Linux budget: 5 minutes. Windows budget: 25 minutes.
2. **Show connection instructions** — once the tunnel is found, display:

```
✅ ECS 创建完成，DevBridge 隧道已就绪

从你的本地电脑连接这台 ECS：

  devbridge auth login --api-key <你的key>
  devbridge connect <tunnel-id>
  ssh root@localhost -p <port>     # Linux
  # 或 远程桌面 → localhost:<port>  # Windows

  隧道 ID: <tunnel-id>
  ECS 名称: <ecs-name>
  安全组: 入方向 0 条规则（全关），SSH/RDP 走 DevBridge 隧道
```

3. **B1 mode: keep the FunctionGraph function until `terraform destroy`** — do NOT destroy it separately. The function's `user_data` holds only a revocable DevBridge API Key (no AK/SK — see Part 3A), so there is no high-risk credential requiring urgent removal. Keeping the function eliminates the Windows slow-boot race entirely: there is no "destroy the function too early → the ECS never gets the key → tunnel never appears" hazard, and no timing rule to obey.

   The function is destroyed together with the ECS/VPC/etc. via a plain `terraform destroy` (Part 5).

4. **B1 mode: the key was pre-created in the sandbox (Step 0)** — no post-apply persistence is needed; the key already lives in `~/.huawei/devbridge/config.yaml` and can be reused for future ECS creations:
   - The key is already stored (encrypted) on the ECS disk via cloud-init.
   - Optionally, the agent can query the DevStage API `GET /open-api-public/v1/relay/api-key` to list keys, find the one created for this ECS, and save it to `~/.huawei/devbridge/config.yaml` for sandbox reuse.
   - If the agent cannot retrieve the key, inform the user: "DevBridge API Key 已在 ECS 上创建。下次创建 ECS 时如需复用，可手动将 Key 保存到 ~/.huawei/devbridge/config.yaml"

5. **If tunnel doesn't appear within the OS budget** (Linux ~5 min, Windows ~25 min) — warn that cloud-init may still be running or failed. The FunctionGraph function is kept (it is only destroyed at `terraform destroy`), so the ECS can retry the invocation on reboot. Tell the user: "隧道未出现，可手动检查 ECS cloud-init 日志。B1 模式下 FunctionGraph 函数保留（destroy 时才清理）。"

## Part 5: terraform destroy cleanup

When the user runs `terraform destroy`, after destroy completes:
1. List DevBridge tunnels, offer to clean up orphans: `devbridge list` → find tunnels for destroyed ECS → `devbridge delete <id>`
2. The DevBridge API Key (pre-created in the sandbox) can be cleaned up via DevStage API: `DELETE /open-api-public/v1/relay/api-key/{id}` (endpoint 4.13.2 in API docs)
3. B1 mode: The FunctionGraph function is kept until `terraform destroy` and destroyed together with the other resources (no separate `-target` cleanup). No special handling needed.
