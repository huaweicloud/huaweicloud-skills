# 自然语言对话用例（Conversation Examples）

本文件为 `huawei-cloud-ecs-dsh-deploy` 技能提供**自然语言对话用例**：用户以日常中文表述需求时，Agent 应如何识别意图、执行前置确认并驱动部署脚本。供技能测试与 LLM 编排参考。

> ⚠️ **最高优先级规则（所有用例必须遵守）**：
> 1. 部署涉及**实际费用**，执行前必须展示默认配置并向用户确认区域、规格、计费模式；
> 2. 用户必须输入 `CONFIRM`（大写）后，才允许执行部署；
> 3. **禁止编造价格**，价格一律引导至官方价格计算器 https://www.huaweicloud.com/pricing/calculator.html#/hecs；
> 4. 删除服务器必须二次确认；
> 5. 安全组默认留空（无入站规则），部署完成后提醒用户手动配置**仅放行 22 端口（SSH，来源 your_ip/32）**；
> 6. 访问 dsh Web UI **必须先在本机建立 SSH 隧道**。部署成功后的回复中**必须原样包含完整 SSH 隧道命令**（将 `{公网IP}` 替换为脚本输出中的实际公网 IP），**不可省略、不可摘要**——用户需要复制粘贴执行。格式示例：`ssh -L 3080:127.0.0.1:3080 root@121.36.x.x`，然后浏览器访问 `http://127.0.0.1:3080`。

---

## 一、触发词 → 意图映射表

| 用户自然语言（示例） | 识别意图 | 对应命令/动作 |
|---|---|---|
| "部署 DeepSeek Harness" / "部署 dsh" / "帮我装一个 AI 智能体" | `deploy` | `python3 scripts/deploy_dsh.py --ak <AK> --sk <SK>` |
| "部署到华南-广州" / "用新加坡区域" | `deploy`（指定区域） | `--region cn-south-1` / `ap-southeast-3` |
| "用 4 核 8G 的机器" | `deploy`（指定规格） | `--flavor x1.4u.8g` |
| "部署时顺便配好 API key" / "API key 填 sk-xxx" | `deploy`（预置密钥） | `--api-key sk-xxx` |
| "有哪些区域可以用" / "看看支持哪些区域" | `list-regions` | `python3 scripts/deploy_dsh.py --list-regions` |
| "测试一下 AK/SK 对不对" / "验证凭证" | `test` | `python3 scripts/deploy_dsh.py --test --ak <AK> --sk <SK>` |
| "现在有哪些服务器" / "列出已部署的实例" | `list-servers` | `python3 scripts/deploy_dsh.py --list-servers --region <REGION>` |
| "dsh 服务跑着吗" / "检查部署状态" | `status` | `python3 scripts/deploy_dsh.py --status <ID> --region <REGION>` |
| "把那个服务器删掉" / "释放实例" | `delete` | `python3 scripts/deploy_dsh.py --delete <ID> --region <REGION>` |
| "这要花多少钱" / "价格多少" | 费用咨询 | 引导官方价格计算器，禁止自行报价 |

---

## 二、完整对话用例

### 用例 1：首次一键部署（标准流程）

**触发语句：** "帮我在华为云上部署一个 DeepSeek Harness"

**识别意图：** `deploy`（默认配置）

**Agent 响应流程：**

1. 展示默认配置并确认：
   > 好的，即将在华为云 Flexus 云服务器 X 实例上部署 DeepSeek Harness (dsh)。默认配置如下：
   > - **区域**：华北-北京四（cn-north-4）
   > - **规格**：x1.2u.4g（2核4GB）
   > - **系统盘**：40GB，Ubuntu 22.04
   > - **带宽**：100Mbps 按流量计费
   > - **计费模式**：按需付费
   > - **访问方式**：SSH 隧道（本机执行 `ssh -L 3080:127.0.0.1:3080 root@<公网IP>` 后访问 `http://127.0.0.1:3080`）
   >
   > 部署涉及实际费用，价格请以华为云官网为准（[价格计算器](https://www.huaweicloud.com/pricing/calculator.html#/hecs)）。
   > 如需修改请告诉我；确认无误请回复 `CONFIRM`。

2. 用户回复 `CONFIRM` 后：
   - 收集 AK/SK（若此前未提供），执行：
     ```bash
     python3 scripts/deploy_dsh.py --ak <AK> --sk <SK> --region cn-north-4
     ```
   - 脚本自动完成：锁文件检查 → 空安全组创建 → 服务器创建 → 等待 ACTIVE → 等待 UniAgent 上线 → COC 执行安装脚本 → 解析部署信息。

3. 部署成功后输出：
   > ✅ dsh 部署完成！
   >
   > 🌐 **访问 dsh Web UI（需要 SSH 隧道）**：
   > 在你的本地电脑（Windows PowerShell / macOS Terminal）运行以下命令（将 `<公网IP>` 替换为上表中实际的公网 IP）：
   > ```
   > ssh -L 3080:127.0.0.1:3080 root@<公网IP>
   > ```
   > 输入 SSH 密码，保持终端窗口开启，然后浏览器访问 `http://127.0.0.1:3080`
   >
   > - **dsh 版本**：0.1.0-rc.7 | **Node.js**：v22.x
   > - **安全提示**：安全组 `sg-dsh` 当前**无入站规则**，请在控制台手动添加规则：TCP **22** 端口，来源 `your_ip/32`（仅此一条即可，无需放行 80/3080）。

---

### 用例 2：指定区域部署

**触发语句：** "帮我部署到华南-广州，其他用默认"

**识别意图：** `deploy`（区域覆盖）

**Agent 响应流程：**

1. 确认配置（突出变更项）：
   > 好的，配置如下：区域 **华南-广州（cn-south-1）**，规格 x1.2u.4g，按需付费。其他项同默认。
   > 确认请回复 `CONFIRM`，需要修改请直接说明。

2. 用户回复 `CONFIRM` 后执行：
   ```bash
   python3 scripts/deploy_dsh.py --ak <AK> --sk <SK> --region cn-south-1
   ```

3. 输出结果（同用例 1），区域显示为 cn-south-1。

---

### 用例 3：自定义规格与带宽

**触发语句：** "机器配置高一点，用 4 核 8G，带宽 50M"

**识别意图：** `deploy`（规格/带宽覆盖）

**Agent 响应流程：**

1. 确认配置：
   > 好的，配置如下：区域 cn-north-4，规格 **x1.4u.8g（4核8GB）**，带宽 **50Mbps**，按需付费。确认请回复 `CONFIRM`。

2. 用户回复 `CONFIRM` 后执行：
   ```bash
   python3 scripts/deploy_dsh.py --ak <AK> --sk <SK> --flavor x1.4u.8g --bandwidth 50
   ```

> 提示：若指定规格在当前区域不可用，脚本会报 `FlavorNotFound`，Agent 应提示更换区域或规格（可用 `--list-regions` 查看区域支持情况）。

---

### 用例 4：预置 API Key 部署

**触发语句：** "部署 dsh，顺便把 API key 配好，key 是 sk-abc123"

**识别意图：** `deploy`（预置密钥）

**Agent 响应流程：**

1. 确认配置（同用例 1，并说明）：
   > 将使用你提供的 API Key **sk-abc…123**（仅写入服务器 drop-in 文件，权限 600，不回显明文）。确认请回复 `CONFIRM`。

2. 用户回复 `CONFIRM` 后执行：
   ```bash
   python3 scripts/deploy_dsh.py --ak <AK> --sk <SK> --api-key sk-abc123
   ```

3. 部署成功后额外提示：
   > 🔑 API Key 已通过 `/etc/systemd/system/dsh.service.d/10-credentials.conf`（mode 600）注入，仅 dsh 服务可读。

---

### 用例 5：查询可用区域

**触发语句：** "你们支持哪些区域部署？"

**识别意图：** `list-regions`

**Agent 响应流程：**

1. 直接执行（无需费用确认）：
   ```bash
   python3 scripts/deploy_dsh.py --list-regions
   ```
2. 输出格式化区域列表（区域名 + 中文名 + 默认规格），并推荐：
   > 华北-北京四（cn-north-4）为默认区域；若面向华南客户建议 cn-south-1。需要我部署到其中某个区域吗？

---

### 用例 6：测试 AK/SK 凭证

**触发语句：** "我的 AK/SK 能用吗？AK 是 xxx，SK 是 xxx"

**识别意图：** `test`

**Agent 响应流程：**

1. 执行：
   ```bash
   python3 scripts/deploy_dsh.py --test --ak <AK> --sk <SK>
   ```
2. 结果处理：
   - 成功：> ✅ 凭证有效，可正常调用华为云 API（Project ID 已自动获取）。
   - 失败 `401 Unauthorized`：> ❌ AK/SK 无效，请检查是否复制完整、是否正确（注意 SK 仅在创建时显示一次）。同时提醒检查 IAM 权限策略（见 references/iam-policies.md）。

---

### 用例 7：查看已部署服务器列表

**触发语句：** "我现在有哪些 dsh 服务器？"

**识别意图：** `list-servers`

**Agent 响应流程：**

1. 执行：
   ```bash
   python3 scripts/deploy_dsh.py --list-servers --region <REGION>
   ```
   （若用户未指定区域，默认 cn-north-4，并提示可加 `--region`）
2. 输出表格：实例名（如 `x-dsh-202608181025`）、ID、状态（ACTIVE/ERROR）、公网 IP、创建时间。若列表为空提示可执行部署。

---

### 用例 8：检查 dsh 运行状态

**触发语句：** "上次部署的 dsh 还在运行吗？"

**识别意图：** `status`

**Agent 响应流程：**

1. 执行（若用户未提供实例 ID/名称，先 `--list-servers --region <REGION>` 查得实例后再执行）：
   ```bash
   python3 scripts/deploy_dsh.py --status <server_id_or_name> --region <REGION>
   ```
2. 输出：
   > - 实例：x-dsh-xxxx（ACTIVE）
   > - dsh 服务：**active (running)**，监听 127.0.0.1:3080
   > - Nginx：正常（仅本地回环代理，公网不可访问）
   > - Web UI：dsh **不公开暴露**（设计如此，仅监听回环地址），请通过 SSH 隧道验证：
   >
   > **Windows（PowerShell）**：`ssh -L 3080:127.0.0.1:3080 root@<公网IP>`，保持窗口开启，再打开浏览器访问 `http://127.0.0.1:3080`
   >
   > **macOS（Terminal）**：同上命令；或 `ssh -f -N -L 3080:127.0.0.1:3080 root@<公网IP>` 后台运行
   >
   > 若状态输出为 `healthy: False / checked: False`，属正常——公网健康检查已移除，安全组仅放行 22 端口，不会对 80/3080 做公网探测。

---

### 用例 9：删除服务器（含二次确认）

**触发语句：** "把 x-dsh-202608181025 那台删了吧"

**识别意图：** `delete`

**Agent 响应流程：**

1. **首次确认**（列出影响）：
   > ⚠️ 即将删除实例 **x-dsh-202608181025**（cn-north-4），将释放 ECS 实例及公网 IP，**数据不可恢复**（dsh 工作区数据随之删除）。确认删除请回复 `CONFIRM`。

2. 用户回复 `CONFIRM` 后，执行：
   ```bash
   python3 scripts/deploy_dsh.py --delete <ID> --region cn-north-4
   ```
3. 删除完成后提示：> ✅ 实例已释放，安全组 `sg-dsh` 保留（如不再使用可手动删除）。

---

### 用例 10：部署失败处理 —— AK/SK 无效

**触发语句：** （用户已回复 CONFIRM，但部署报 `401 Unauthorized`）

**Agent 响应流程：**

1. 向用户说明失败原因，不重复扣费操作：
   > ❌ 部署中止：AK/SK 认证失败（401）。实例未创建，无费用产生。
2. 引导排查：
   - 重新生成 AK/SK 后再试；
   - 确认账号已实名认证、已开通 ECS/VPC/EIP/COC 服务；
   - 检查 IAM 权限策略（references/iam-policies.md）。

---

### 用例 11：部署失败处理 —— 配额不足 / 实例数量超限

**触发语句：** （部署报 `QuotaExceeded` 或 `ServerLimitExceeded`）

**Agent 响应流程：**

1. > ❌ 部署中止：资源配额不足 / 实例数量已达上限。
2. 处理建议：
   - 前往华为云控制台释放闲置实例；
   - 或申请提高 ECS/EIP 配额；
   - 可使用 `--list-servers` 查看现有实例，配合 `--delete` 释放后再部署。

---

### 用例 12：用户询问价格

**触发语句：** "部署这个要花多少钱？"

**Agent 响应流程：**

1. **禁止自行报价**，引导官方渠道：
   > 具体费用取决于区域、规格、带宽与计费模式，且会随时间调整，我无法给出准确报价。请使用华为云官方[价格计算器](https://www.huaweicloud.com/pricing/calculator.html#/hecs)查询，或查看[Flexus X 定价文档](https://support.huaweicloud.com/price-flexusx/index.html)。
   > 需要我按默认配置继续部署吗？

---

### 用例 13：模糊请求澄清

**触发语句：** "帮我搞个 AI 服务器"

**识别意图：** 意图模糊（可能为 deploy，但对象不明确）

**Agent 响应流程：**

1. 澄清而非默认执行：
   > 我可以帮你在华为云 Flexus X 上部署 DeepSeek Harness（dsh）——一个 AI 智能体开发环境（网页界面 + 插件化工作流）。这是你想要的吗？还是指其他类型的服务器？确认后我会先展示部署配置并请你确认。

2. 用户确认后，进入用例 1 的标准确认流程。

---

### 用例 14：用户放弃确认 / 语气随意

**触发语句：** "随便，你看着办就行"

**识别意图：** `deploy` 但未明确确认

**Agent 响应流程：**

1. **拒绝在未确认时执行**：
   > 抱歉，部署会创建云资源并产生费用，我不能在未确认的情况下替你决定。请至少确认以下三项：区域（默认 cn-north-4）、规格（默认 x1.2u.4g）、计费模式（默认按需付费）。确认后回复 `CONFIRM` 即可开始。

---

### 用例 15：复用上一次配置快速部署

**触发语句：** "上次那种配置再开一台"

**识别意图：** `deploy`（复用配置）

**Agent 响应流程：**

1. 根据历史部署记录（或提示用户提供）复述上次数值：
   > 上次配置为：cn-north-4 / x1.2u.4g / 40GB / 100M / 按需付费。本次按相同配置创建？确认请回复 `CONFIRM`。（提示：实例名会自动生成新时间戳，互不冲突。）
2. 确认后执行标准部署命令。

---

## 三、通用应答规范

| 场景 | 规范 |
|------|------|
| **费用话题** | 一律引导官方价格计算器，禁止给出任何具体金额 |
| **CONFIRM 确认** | 部署/删除前必须得到用户明确的大写 `CONFIRM`，否则不执行 |
| **AK/SK 处理** | 涉及凭证的命令只传参、不回显完整 SK；提示用户 SK 仅创建时可见一次 |
| **安全提示** | 每次部署成功都必须提醒：安全组仅放行 TCP 22（来源 your_ip/32），Web UI 需通过 SSH 隧道访问，禁止开放 80/443/3080 |
| **失败回滚** | 部署失败时明确说明"是否已产生费用/资源"，并给出下一步处理建议 |
| **多区域语境** | 用户提到"华南/广州/深圳"→ cn-south-1；"华东/上海"→ cn-east-3；"新加坡/海外"→ ap-southeast-3，仍需用户确认 |
