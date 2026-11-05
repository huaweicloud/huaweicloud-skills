# Data Flow Diagram（数据流图）

> 本 skill 的数据流：**Agent → 环境与授权准备（`setup.*` / `permission.*`）→ wrapper（`codearts_run.*`）→ `codearts` CLI → CodeArts Agent / 模型服务 → JSONL 事件 → Agent 解析并落盘**。
> 图中每个节点的输出都遵循同一套退出码与 stdout 契约（见文末表格）。

---

## 1. 端到端数据流

```mermaid
flowchart TD
  U([用户请求：生成代码 / 写函数 / 开发项目]) --> AG["Agent<br/>（强制先走本 Skill）"]

  AG -->|"bash scripts/setup.sh<br/>或 setup.ps1"| SETUP["环境与凭据准备"]
  SETUP --> CLI_CHECK{"~/.codeartsdoer/installers<br/>下有 codearts 吗？"}
  CLI_CHECK -->|"否"| OBS["从华为云 OBS 下载安装脚本<br/>install.sh / install.ps1<br/>重试 3 次"]
  OBS --> CLI_OK{"安装后存在？"}
  CLI_OK -->|"否"| E30["exit 30<br/>install_failed / install_verify_failed"]
  CLI_OK -->|"是"| AKSK
  CLI_CHECK -->|"是"| AKSK{"凭据已配置？<br/>CODEARTS_CLI_AK / CODEARTS_CLI_SK"}

  AKSK -->|"否"| E10["exit 10 need_input<br/>Agent 向用户索取 AK/SK"]
  E10 --> SAVE["bash scripts/setup.sh --save-aksk AK SK<br/>写入 ~/.bashrc / 用户级环境变量"]
  SAVE --> AKSK
  AKSK -->|"是"| PERM

  PERM{"权限已配置？<br/>permission/global.json<br/>edit+write = allow"}
  PERM -->|"否"| E20["exit 20 need_consent<br/>Agent 取得用户显式同意"]
  E20 --> PCFG["bash scripts/permission.sh --agree /workspace<br/>原子写入 global.json"]
  PCFG --> PERM
  PERM -->|"是"| VERIFY

  VERIFY["连通性验证<br/>wrapper: codearts_run.sh models"] -->|"缺凭据"| E10
  VERIFY -->|"认证失败"| E50["exit 50 auth_failed"]
  VERIFY -->|"网络失败"| E40["exit 40 network_failed"]
  VERIFY -->|"成功"| READY["exit 0 ready"]

  READY --> RUN["bash scripts/codearts_run.sh run --format json -m provider/model [-f file]... task"]
  RUN --> WRAP["wrapper codearts_run.sh / .ps1"]

  subgraph WRAPBOX["wrapper 职责（稳定契约层）"]
    W1["定位 CLI：CODEARTS_CLI_BIN 或 ~/.codeartsdoer/installers/codearts"]
    W2["加载凭据：环境变量 → ~/.bashrc；缺失即 exit 10，不调用 CLI"]
    W3["附件：吃掉 -f/--file，把文件内容以 fenced block 追加到任务描述"]
    W4["执行 CLI，捕获 stdout/stderr，日志走 stderr"]
    W5["校验：退出码 = 0 且 stdout 非空 且 每行均为合法 JSONL 且无顶层 error"]
    W1 --> W2 --> W3 --> W4 --> W5
  end
  WRAP --> WRAPBOX
  WRAPBOX -->|"校验失败"| EMAP["exit 1 / 40 / 50 / 60<br/>stdout 仅一个错误 JSON"]
  WRAPBOX -->|"校验通过"| CLI["codearts CLI"]

  CLI -->|"调用 CodeArts 代码生成 / 模型服务"| CA["CodeArts Agent / MaaS"]
  CA -->|"JSONL 事件流"| EV["step_start / text / tool_use / step_finish / error"]
  EV --> PARSE["Agent 逐行解析 JSONL"]
  PARSE -->|"text 事件 .content 的 markdown 代码块"| CODE["提取生成代码"]
  CODE --> WRITE["Agent 自行创建目录并写盘<br/>（CLI 不会创建或写入任何文件）"]
  WRITE --> REPORT["报告真实写入的文件路径<br/>+ 项目说明 + 启动命令"]
  REPORT --> CLEAN["提醒并询问是否删除 AK/SK<br/>setup.sh --clear-aksk / setup.ps1 -ClearAksk"]

  EMAP --> FIX["按 fix_hint 修复后重试<br/>或经用户同意后放弃 CodeArts"]
  FIX --> AG
```

---

## 2. 说明（3 句）

1. **准备阶段是三道前置门**：`setup.sh` / `setup.ps1` 依次完成 CLI 安装、凭据、权限三项检查，任一项不满足就以对应的结构化 JSON + 专属退出码（`30` / `10` / `20`）中断，由 Agent 向用户索取输入或同意，而不是把失败当成成功继续往下走。
2. **wrapper 是唯一的契约层**：`codearts_run.sh` / `codearts_run.ps1` 负责定位 CLI、加载凭据、把 `-f` 附件以 fenced block 追加到任务描述，并强制「退出码 0 + stdout 非空 + 逐行合法 JSONL」的成功判据；任何失败都映射为唯一的错误 JSON 与非零退出码（`1 / 10 / 30 / 40 / 50 / 60`），**绝不 `exit 0`**。
3. **落盘由 Agent 负责**：`codearts run --format json` 只返回 JSONL 事件流，生成的代码位于 `text` 事件的 markdown 代码块中，CLI **不会创建或写入任何文件**；Agent 必须自己创建父目录、写入代码，并只报告确实写入过的路径（任务描述里的 `Output:` 只是提示）。

---

## 3. 契约速查

| 阶段 | 产出 | 退出码 |
|------|------|--------|
| `setup.sh` / `setup.ps1`（参数校验） | `{"status":"error","code":2,"type":"invalid_arguments"\|"empty_credentials"\|"lock_timeout"}` | `2` |
| CLI 安装 | `download_failed` / `install_failed` / `install_verify_failed` / `dependency_missing` / `unsupported_os` | `30` |
| 凭据检查 | `{"status":"need_input","code":10,"type":"aksk_required",...}` | `10` |
| 权限检查 | `{"status":"need_consent","code":20,"type":"permission_required",...}` | `20` |
| 连通性检查 | `ready` / `auth_failed` / `network_failed` | `0` / `50` / `40` |
| `permission.sh --agree` | `PERMISSION_CONFIGURED` + `global.json` 绝对路径 | `0`（拒绝或参数错误 `1`） |
| 凭据清理 | `{"status":"cleared","code":0,"message":"AK/SK removed from ~/.bashrc"}` | `0` |
| wrapper 成功 | CLI 的 stdout 原样透传（JSONL） | `0` |
| wrapper 失败 | stdout 有且仅有一个 `{"status":"error","code":N,"type":"...","message":"...","fix_hint":"..."}`；日志在 stderr（前缀 `[codearts_run]`） | `1` / `10` / `30` / `40` / `50` / `60` |

---

## 4. 关键数据落点

| 数据 | 位置 | 写入方 |
|------|------|--------|
| `codearts` 可执行文件 | `~/.codeartsdoer/installers/codearts`（Windows：`codearts.cmd`） | 官方安装脚本（由 `setup.*` 触发） |
| AK/SK | `~/.bashrc` 的 `export CODEARTS_CLI_AK/SK=`（Windows：用户级环境变量） | `setup.sh` / `setup.ps1`（含清理命令） |
| 权限配置 | `~/.codeartsdoer/cli-data/storage/permission/global.json` | `permission.sh` / `permission.ps1`（原子替换） |
| 代码生成结果 | 由 **Agent** 写入工作区内的目标路径 | Agent（CLI 不写文件） |
| 临时文件 | wrapper 的私有工作目录（stdout / stderr 捕获） | `codearts_run.*` |
