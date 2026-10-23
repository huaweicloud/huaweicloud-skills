---
name: huawei-cloud-activity-submit
description: 直连华为云开放能力线上闯关挑战（activity_code=open-capability-2026-1024）的 Agent 提交接口（POST {base}/submit-activity-work），用 AK/SK 请求头（X-HW-AK / X-HW-SK / X-HW-Security-Token）把活动生成的作品链接/公网地址自动提交到“沙箱部署”（milestone=beginner）与“ECS 持久化部署”（milestone=intermediate）两步，并在成功后回报预计可得积分（以成长体系实际发放为准，仅发放一次）；沙箱部署（beginner）完成后**始终**询问用户是否（可选）将作品发布到开发者作品展览馆的闯关活动；若此时未发布则在 ECS（intermediate）完成后再询问一次，若已发布则 ECS 阶段不再询问（npx skills add ... publish-work-to-gallery）。Use when the user asks to 提交作品、提交闯关成果、自动提交活动成果、提交沙箱链接/公网地址, or when a generated sandbox URL needs to be submitted for the 华为云开放能力闯关挑战。本 skill 固定使用**生产环境**（现网）接口，无需也**不要**切换环境。仅用于调用接口，不涉及任何页面/浏览器操作.
---

# 华为云开放能力闯关 · 作品提交 Skill（生产环境）

让 Agent 直接调用活动 **Agent 提交接口**（AK/SK 鉴权）完成成果提交（**不做任何页面/浏览器操作**），提交成功后向用户提示预计可得的对应步骤积分。

## Overview

本 Skill 让 Agent 直接调用华为云"开放能力闯关挑战"（`activity_code = open-capability-2026-1024`）的 **Agent 提交接口**（AK/SK 鉴权），将活动生成的作品链接自动提交到对应步骤，并在成功后回报预计可得的积分。

**核心特点**：

- **纯 API 调用**：不涉及任何页面/浏览器操作，直接 POST 提交接口。
- **固定生产环境**：本 skill 固定使用生产环境接口，不切换环境。
- **两步独立提交**：`beginner`（沙箱部署，100 分）与 `intermediate`（ECS 持久化部署，400 分），两步相互独立、无强制先后。
- **AK/SK 鉴权**：通过请求头 `X-HW-AK` / `X-HW-SK` / `X-HW-Security-Token` 认证，不依赖 hcloud CLI。
- **附加请求头（两步均需）**：`beginner` 与 `intermediate` 提交时均携带 `X-HW-PROJECT-ID` / `X-HW-REGION`。
- **纯 Node.js 脚本**：`submit.mjs`（Node ≥ 18，无外部依赖），不使用 KooCLI。
- **可选展览馆发布**：沙箱部署后始终询问；若未发布则 ECS 后再问一次；已发布则不再询问。
- **资源清理提醒**：ECS 提交成功后提醒用户清理按量付费资源。

## 何时使用

- 用户说“把作品/成果/沙箱链接提交到活动” “帮我提交闯关成果” “提交沙箱域名/公网地址” 等。
- 活动已生成沙箱作品链接（前端站点）和/或 ECS 公网地址，需要提交到对应步骤。
- 仅针对活动 `activity_code = open-capability-2026-1024`。

## 提交接口

| 项 | 值 |
|----|----|
| 基地址（生产，固定） | `https://open-dataset.huaweicloud.com/api/v1/hdopenservice/agent` |
| 提交 | `POST {base}/submit-activity-work` |

> 前端页面走 `/user/...`（SSO 登录会话）；Agent 走 `/agent/...`（AK/SK 请求头），两者**请求体与响应一致**。本 skill **固定使用生产环境**基地址，不切换环境。

**鉴权（AK/SK 请求头）**：

- `X-HW-AK`（必填）：华为云 Access Key
- `X-HW-SK`（必填）：华为云 Secret Key
- `X-HW-Security-Token`（可选）：使用 STS 临时凭证时必填

**附加请求头（两步均需）**：

- `X-HW-PROJECT-ID`：Project ID
- `X-HW-REGION`：region（如 `cn-north-4`）

> 凭证优先级：命令行参数 > 环境变量（`HW_ACCESS_KEY`/`HW_SECRET_KEY`/`HW_SECURITY_TOKEN`，兼容 `HUAWEICLOUD_SDK_AK`/`HUAWEICLOUD_SDK_SK`/`HUAWEICLOUD_SDK_SECURITY_TOKEN`、`HW_AK`/`HW_SK`）。**切勿把凭证写入仓库。**

**提交请求体**（`Content-Type: application/json`，与 `/user/submit-activity-work` 一致）：

```json
{
  "activity_code": "open-capability-2026-1024",
  "milestone": "beginner | intermediate",
  "work_link": "https://xxx.devbridge-s2.hwtunnel.com",
  "api_link": "http://<ECS_EIP>/hc-activity/index.html",
  "summary": "作品说明（可选，≤500 字）"
}
```

按步骤取字段：

- `beginner`（沙箱部署）：只传 `work_link`（沙箱站点链接）
- `intermediate`（ECS 持久化部署）：只传 `api_link`（ECS 公网访问地址，**需含 `index.html`**，如 `http://<EIP>/hc-activity/index.html`）

**响应**：`{ "code": "success", "message": "..." }`；`code === "success"` 即提交成功。

## 步骤、字段对应、校验与积分

两步相互独立、**无强制先后**：`beginner`（沙箱部署）与 `intermediate`（ECS 持久化部署）可分别单独提交，不要求先沙箱后 ECS。

> **字段/取值对应（重要）**：后端 `milestone` 取值**沿用旧版** `beginner` / `intermediate`（页面文案已改名为“沙箱部署 / ECS 持久化部署”）；旧 `advanced` 步骤**已取消**，不存在。
>
> | 页面步骤 | `milestone` 取值 | 提交字段 |
> |---|---|---|
> | 沙箱部署 | `beginner` | `work_link` |
> | ECS 持久化部署 | `intermediate` | `api_link` |
>
> `--milestone` 同时接受别名：`sandbox`→`beginner`、`ecs`→`intermediate`（脚本自动归一化）。

沙箱域名正则（同前端 `SANDBOX_RE`）：`^https:\/\/[^/]*devbridge-s2\.hwtunnel\.com(\/|$)`

| 步骤 | milestone | 需提交 | 校验 | 成功后积分 |
|------|-----------|--------|------|-----------|
| 沙箱部署 | `beginner` | 沙箱站点链接（`work_link`） | 沙箱域名（另需 Project ID / region 请求头） | 100 分（¥10） |
| ECS 持久化部署 | `intermediate` | 公网访问地址（`api_link`） | `http(s)://` 开头**且含 `index.html`**（如 `http://<EIP>/hc-activity/index.html`） | 400 分（¥40） |

## Workflow（工作流 / 操作步骤）

1. **收集链接**：沙箱步骤用公开沙箱域名（`https://xxx.devbridge-s2.hwtunnel.com`，部署后先 `curl -sI <URL>` 验证 200）；ECS 步骤用 ECS 公网 HTML 地址（`http://<EIP>/`）。
2. **确定当前步骤**：两步相互独立、无强制先后；按用户本次要提交的成果选择对应步骤（沙箱→`beginner`，ECS→`intermediate`），一次提交一个步骤。
3. **校验链接格式**：脚本会在提交前自动校验（沙箱域名、`http(s)://` 前缀与 `index.html`、说明 ≤500 字）；不通过时会打印原因，修正后再提交。
4. **执行提交**：运行 `submit.mjs`（见下）。参数与步骤字段对应（**两步均需 `--project-id` 与 `--region`**；本 skill 固定使用生产环境接口）。
5. **回报用户**：
   - 成功：提示“提交成功。**预计可得**{沙箱部署 / ECS 持久化部署}对应积分 {100 / 400} 分。”，并**另行单独提示**“注意：积分以华为云成长体系实际发放为准；同一活动积分仅可获得一次，重复提交不再加分。”，并说明该步骤已完成、可继续下一步。
   - 失败：原样反馈接口返回的 `message`（如 `里程碑参数不合法`、`当前里程碑需提交接口地址`、`作品链接无效`、`缺少请求头 X-HW-AK`）。
6. **发布到作品展览馆（用户可选，见下节）**：`beginner`（沙箱部署）提交成功后**始终询问**用户是否将作品发布到**开发者作品展览馆的闯关活动**（脚本在此时把发布状态**重置为 false**）；若用户**未发布**，则在 `intermediate`（ECS 持久化部署）提交成功后**再询问一次**；若沙箱阶段**已发布**（`galleryPublished=true`）则 ECS 阶段**不再询问**。发布成功后**运行 `node submit.mjs --gallery-published` 记录状态**。
7. **资源清理（ECS 提交后）**：`intermediate`（ECS 持久化部署）提交成功后，**必须**用 `question` 工具询问用户是否清理本次活动创建的**按量付费资源**（选项：全部清理 / 仅删 ECS / 暂不清理），按用户选择执行或跳过；脚本也会在成功输出中打印清理提醒。

## 脚本用法

脚本位于本 skill 目录：`submit.mjs`（纯 Node，Node ≥ 18，无需额外依赖）。

```bash
# 1) 沙箱部署：提交沙箱域名 URL（milestone=beginner；两步均需带 Project ID / region）
node submit.mjs --milestone beginner \
  --work-link https://abcd1234-3000.devbridge-s2.hwtunnel.com \
  --project-id <PROJECT_ID> --region cn-north-4 \
  --summary "2048 单文件小游戏"

# 2) ECS 持久化部署：提交公网访问地址（milestone=intermediate；链接需含 index.html；带 Project ID / region）
node submit.mjs --milestone intermediate \
  --api-link http://<ECS_EIP>/hc-activity/index.html \
  --project-id <PROJECT_ID> --region cn-north-4
```

凭证可通过命令行参数或环境变量提供：

```bash
# PowerShell
$env:HW_ACCESS_KEY = "<AK>"
$env:HW_SECRET_KEY = "<SK>"
$env:HW_SECURITY_TOKEN = "<使用 STS 临时凭证时填写>"   # 可选
# 或直接：node submit.mjs --ak <AK> --sk <SK> [--security-token <token>]
```

成功输出示例（实际为多行 JSON）：

```
{
  "ok": true,
  "milestone": "intermediate",
  "label": "ECS 持久化部署",
  "points": 400,
  "message": "...",
  "ecsSubmitted": true
}

提交成功。预计可得ECS 持久化部署对应积分 400 分。
注意：积分以华为云成长体系实际发放为准；同一活动积分仅可获得一次，重复提交不再加分。
```

## 发布到开发者作品展览馆的闯关活动展示（用户可选）

**询问时机**：

- `beginner`（沙箱部署）提交成功后**始终询问**用户是否发布到作品展览馆（脚本在此时把 `galleryPublished` **重置为 false**）；
- 沙箱阶段**已发布**（运行过 `node submit.mjs --gallery-published`，即 `galleryPublished=true`）→ `intermediate`（ECS 持久化部署）阶段**不再询问**；
- 沙箱阶段**未发布**（仍为 false）→ `intermediate`（ECS）提交成功后**再询问一次**。

**是否发布由用户决定**——同意才发布，拒绝则跳过、不勉强。发布成功后**运行 `node submit.mjs --gallery-published` 记录状态**。

> **默认直接提交到此活动**：作品默认提交到作品展览馆的「**闯关活动**」，**跳过训练营选择**，不再让用户挑营地。
> - 活动名：`闯关活动`
> - `trainingCampId`：`47d6ba99-fca0-4797-947d-a8776f506df1`

1. **询问用户**（用 `question` 工具）：是否将作品提交到**开发者作品展览馆的闯关活动**展示？（**用户可选**，明确同意才继续；不同意就结束，不要勉强）
2. **用户同意后**，执行：
   ```bash
   npx skills add https://gitcode.com/Lingxi-HandsOn/gallery.git --skill publish-work-to-gallery -y 2>&1
   ```
3. 该命令会安装 `publish-work-to-gallery` skill；随后**按该 skill 的指引**，收集并将用户本地做闯关任务产生的代码（前端、后端等项目的实际目录）推送至开发者作品展览馆的闯关活动。发布时**默认使用 `trainingCampId=47d6ba99-fca0-4797-947d-a8776f506df1`（闯关活动），无需再选择训练营**。**代码目录名不固定**，以用户本次实际生成/使用的目录为准，不要假定某个固定仓库名。
4. 用户不同意则跳过本步骤，直接结束。

**注意事项**：
- **询问时机**：`beginner`（沙箱部署）提交成功后**始终询问**；若用户**未发布**，则 `intermediate`（ECS 持久化部署）提交成功后**再询问一次**；沙箱阶段**已发布**（`galleryPublished=true`）则 ECS 阶段**不再询问**（与操作步骤第 6 步、上方「询问时机」一致）。
- 是否提交展览馆**完全由用户决定**，用户拒绝则跳过，不得代替用户决定。
- 执行前先与用户确认或识别闯关任务实际产生的代码目录（前端、后端项目，**目录名不固定**），只推送相关代码，避免带上无关文件。可由用户指定，或扫描本次工作区中生成的项目目录来确定。
- 如 `npx skills add` 需要联网/安装，失败时如实反馈错误并让用户决定是否重试。

## Prerequisites

- **Node.js ≥ 18**：本 skill 的提交脚本 `submit.mjs` 使用原生 `fetch()`，需 Node 18 或以上版本。
- **华为云 AK/SK**：需要有效的 Access Key 和 Secret Key，用于接口鉴权请求头。可选 STS 临时凭证的 SecurityToken。
  - 凭证来源优先级：命令行参数 > 环境变量（`HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN`，兼容 `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` / `HW_AK` / `HW_SK`）。
- **额外参数（两步均需）**：`beginner` 与 `intermediate` 提交均需提供 `--project-id` 和 `--region`（或环境变量 `HW_PROJECT_ID` / `HW_REGION`，或 hcloud 配置）。
- **网络访问**：需能访问提交接口基地址（`https://open-dataset.huaweicloud.com`）。
- **作品链接**：
  - 沙箱部署步骤（`beginner`）：需已部署的沙箱域名（`https://xxx.devbridge-s2.hwtunnel.com` 格式）。
  - ECS 持久化部署步骤（`intermediate`）：需 ECS 公网访问地址（含 `index.html`，如 `http://<EIP>/hc-activity/index.html`）。
- **不使用 KooCLI**：本 skill 直接通过 HTTP 请求头鉴权调用活动 API，不依赖 hcloud CLI，因此不需要 `--cli-region` 参数。


## 注意事项

- **只调接口，不做页面操作**：不要驱动浏览器、不要模拟点击页面表单。
- **固定环境、不切换**：本 skill 始终使用**生产环境**；传入 `--env` / `--base` 等环境参数会被**忽略**（不报错、无效果），不会切到其它环境。
- **无顺序要求**：两步相互独立，可任意先后单独提交（接口不校验先后顺序）。
- **附加请求头（两步均需）**：`beginner` 与 `intermediate` 提交时均需携带 `X-HW-PROJECT-ID`（Project ID）与 `X-HW-REGION`（region）；脚本通过 `--project-id`/`--region`（或环境变量 `HW_PROJECT_ID`/`HW_REGION`，或 hcloud 配置）取值，缺失会报错。**后端已对两步均强制校验** `X-HW-PROJECT-ID`/`X-HW-REGION`；此前仅 ECS 要求，遵循旧提示词/旧安装的 Agent 提交沙箱步骤时需补传 `--project-id`/`--region`，否则会被“缺少 Project ID”拦截。
- **沙箱域名强校验**：`beginner` 步骤的链接必须是 `https://xxx.devbridge-s2.hwtunnel.com` 形式的沙箱域名；`intermediate` 步骤提交的公网地址必须 `http(s)://` 开头（如 `http://<EIP>/hc-activity/index.html`），缺 `index.html` 时脚本会自动补全。
- **凭证安全**：AK/SK（及临时凭证的 SecurityToken）仅用于本次会话，不要写入仓库或提交到版本库；优先用环境变量传入，避免明文出现在命令行历史。
- **SK 明文传输说明**：`X-HW-SK` 以请求头明文传递是**活动 API 自身设计**（`/agent/*` 接口要求 AK/SK 头），依赖 **HTTPS 传输加密**；请勿将 SK 写入仓库、日志或对外分享。
- **提交不可重复使用**：同一地址提交后即与该账户绑定，勿重复提交相同链接。

## Reference Documents

- [references/iam-policies.md](references/iam-policies.md) — IAM 权限说明（本 skill 使用 AK/SK 请求头鉴权，不依赖 IAM 策略）
- [references/verification-method.md](references/verification-method.md) — 验证方法（如何端到端验证提交功能）
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — 验收标准（生产就绪的客观验收条件）
