# 本地 Web 监控 Web Monitor

本目录随 skill 一起复制到内网运行。本地 HTTP 服务、文件状态和离线演示使用 Python 标准库，
前端使用原生 HTML/CSS/JS，无 npm 构建、CDN、遥测或外部字体。Python 3.9+，支持 Windows/macOS/Linux。
**智能体的发现、提交、等待和产物交接保持 CLI；Web 后端的平台查询与确认后重新提交使用 Python SDK。**
浏览器只请求本地 HTTP API，不直接调用 SDK、不接触 AK/SK。两者共享运行状态事务，网页不推进后续 DAG。

<a id="web-sdk-setup"></a>
## Web SDK 环境与认证

真实监控需在**启动 server.py 的同一个 Python 环境**安装兼容的三个 SDK 包。评测任务已不再使用 `robot_config`
（配置文件通过 `inputs` 挂载），须使用不再强制该字段的 SDK 版本；提交评测时若提示缺少 `robot_config`，说明 SDK 过旧：

```bash
python -m pip install -U hw-cloudrobo-core hw-cloudrobo-dataset hw-cloudrobo-asset
python scripts/pipeline-monitor/server.py --diagnose
```

python 替换为环境预检选定的解释器。已有 CLI 环境通常已安装这些包，但另一个 Python 环境不会自动共用；
内网按企业包源或预先准备的兼容 wheel 安装，不把依赖复制进 skill。缺失/不兼容时显示具体提示，不回退 CLI。
空运行列表和显式 --demo 不加载 SDK/认证配置，仍可在纯标准库环境运行。

SDK 的 Config 读取 CLI 管理的 ~/.cloudrobo/config.yaml 及其支持的环境变量，沿用 AK/SK 加密存储、
端点、区域、代理和证书设置，不新增凭据文件或网页凭据输入。区域预检仍由 Agent 按 CLI 安装说明执行。
网页重试使用运行记录的 workspace_id，不切换全局工作空间。评测保留原顶层数据集字段与单项 dataset_configs 中的确切版本、核实原版本，不增加处理任务的输出名或 Head 配置。不要把默认区域当成用户已核实的区域。

| Web 功能 | SDK 方法 |
|---|---|
| 处理/评测任务详情 | DatasetClient.get_task_detail / get_eval_task_detail |
| 作业/系统日志列表 | list_log_files / list_eval_log_files |
| 默认末尾 64 KB / 完整日志 | get_task_log_tail / get_eval_task_log_tail；get_task_log / get_eval_task_log |
| 处理输出目录与数据预览 | get_task_frames / get_task_preview |
| 评测报告预览或下载链接 | get_eval_task_preview（is_download） |
| 重试时更新算子、核实每份数据版本 | AssetClient.list_publication_assets / show_asset_version |
| 用户确认后新建处理/评测任务 | DatasetClient.create_task / create_eval_task |

查询/手动刷新不生成 CLI 子进程。“复制 CLI”仅生成供用户在终端执行的文本；
跳过申请、取消、建议性跳过、终止后续编排及删除本地运行记录均是本地文件操作，不调用云端停止或删除接口。

界面沿用配套 `console-mockup.html` 的颜色、状态图标、分栏抽屉和确认对话框；正文放大到 16 px，流程图按可用宽度布局。
主页面包括运行列表、动态 DAG、分段进度、事件时间线、五类步骤详情、操作确认和完成摘要。

首次使用请先阅读 [模块用户指南](user-guide.md)，了解页面操作、状态含义与常见问题。

## 默认打开规则 Default Opening

用户说“打开监控网站”“查看管线监控”时，直接启动或复用真实运行目录的服务并打开页面。
不要先给出“离线演示（推荐）/真实运行”的模式选择，也不要因 run_id 不明或没有云端接口而推荐演示。

1. 已知当前真实 run_id 和自定义 runs-root 时沿用，直接打开该运行。
2. 未知 run_id 时省略 `--run`，打开运行列表，用户可以在列表里选择；多个记录也无需先问启动模式。
3. 没有任何记录时仍打开空列表，说明尚无本地运行。打开网站不创建示例记录，也不启动管线执行。
4. 打开空列表无需 CLI、凭据或已确认的执行计划。已有任务查询失败时展示真实错误，不切换为模拟数据。
5. 只有用户明确要求“演示”“模拟数据”“离线体验网站”时才加 `--demo`，并使用隔离目录。
   排查真实任务、无法访问云端、未提供运行 ID 都不等于要求演示。

以下命令均在 **skill 根目录**运行。先按[环境预检](cli-installation-guide.md#environment-preflight)确认 Shell 和 Python 3.9+；
示例中的 `python3` 须替换为已验证的解释器，Git Bash/Miniconda 可以统一用 `python`，Windows 路径用带引号的正斜杠。
默认打开命令不依赖 run_id：

```bash
python3 scripts/pipeline-monitor/server.py --background --open

# 当前对话已有真实运行时：
python3 scripts/pipeline-monitor/server.py --run <run_id> --background --open
```

沿用对话中已指定的 `--runs-root`，否则使用默认 `~/.cloudrobo/pipeline-runs/`。
用户的打开请求已授权启动本地服务和浏览器；无需再次询问启动模式。
只有目标目录存在无法消除的歧义时才补问目录，不将“打开监控”转成创建或提交云端任务。

### 执行计划确认后的主动提示

用户确认完整执行计划后，先保存实例化计划并 init 创建本次真实 run_id，随即询问一次是否打开**本次运行**监控。
**询问必须早于上传、本地或 OBS 资产注册、版本发布以及首个处理/评测任务提交**，不能等注册完成或格式转换开始才问。
本地、OBS、已有资产及仅评测流程均用这个顺序；只创建配置而未确认执行时不 init。

推荐提示：“执行计划已确认，运行记录 `<run_id>` 已创建，准备执行。是否打开本次运行监控？终端会继续跟踪。”
选项为“打开本次运行监控”和“仅终端跟踪”，不再选择离线/真实模式。
此时页面可展示已确认计划、待准备输入及未开始的算子；复用已有资产时上传注册为不适用/跳过。
没有任务 ID 也能打开，不把本地 init 说成云端资产或任务已创建。
“已有资产”指本次运行开始时用户选择复用的资产，不包括本次上传/注册刚创建的资产。
不得先导入本地数据，再把它改写成 source_type: asset 初始化；这会丢失本次数据准备的来源信息，
导致 upload 被误判为不适用。监控和后续步骤始终使用上传前创建的同一 run。

- 用户此前已要求打开：init 后立即带本次 `--run` 打开，已有授权有效，不重复询问。
- 用户选择打开：先启动/复用同一个 runs-root 并定位本次 run_id，再继续输入准备和任务提交。
  打开失败时说明实际错误、保留运行记录；默认继续已授权执行，不切到演示或等待首个任务才再提示。
- 用户选择仅终端跟踪，或暂未回复：继续终端执行与状态记录；未回复不代表同意启动浏览器。
  有异步询问能力时在开始输入准备前发出询问，不为该展示偏好设置 await-decision 或暂停编排；后续同意时打开同一 run。
- 每次新运行确认并初始化后提示一次；轮询、重试、阶段切换和断点恢复不重复询问。
- 只创建配置、离线草案或尚未确认执行时不触发该提示。用户随时可主动说“打开监控网站”。

## 1. 显式请求的本地演示 Local Demo

以下命令均在 **skill 根目录**运行，而不是整个仓库根目录：

```bash
python3 scripts/pipeline-monitor/server.py --demo --run demo-running-1001 --open
```

演示使用独立临时目录，内置运行中、等待处理、完成有告警三个运行。页面明确标注模拟数据，
重试、日志、报告和预览均不会调用云端。关闭终端进程即可停止；演示数据不会与真实运行混用。

请访问服务启动时打印的完整 HTTP 地址。直接打开 `static/index.html` 时会显示启动引导，
不会读取运行记录；该页面需要本地服务提供 API。若页面脚本加载失败，也会提示检查服务和文件完整性。

```bash
# 后台演示（显式指定独立目录，便于稍后停止）
python3 scripts/pipeline-monitor/server.py --demo --runs-root /tmp/cloudrobo-demo --background --open
python3 scripts/pipeline-monitor/server.py --runs-root /tmp/cloudrobo-demo --stop
```

<a id="windows-console-diagnostics"></a>
### Windows 黑框与更新后的服务版本

Web 平台访问已使用 SDK，刷新状态、日志、目录和预览不再启动 cloudrobo 控制台进程。
后台服务首次启动仍需一个 Python 进程，Windows 使用 CREATE_NO_WINDOW、STARTF_USESHOWWINDOW/SW_HIDE
及独立进程组；不叠加 DETACHED_PROCESS 或 CREATE_NEW_CONSOLE。智能体自身的 CLI 命令不属于 Web 查询链路。

替换文件不会自动替换已经加载的后台代码。新版 health 返回 source_revision，启动命令核对当前源码：
旧服务/无版本号服务会提示停止再启动，不再静默复用。使用同一个 runs-root（自定义目录则每条都加 --runs-root）：

```powershell
python scripts/pipeline-monitor/server.py --diagnose
python scripts/pipeline-monitor/server.py --stop
python scripts/pipeline-monitor/server.py --background --open
python scripts/pipeline-monitor/server.py --diagnose
```

按环境预检结果替换 python。diagnose 只读本地服务信息和已安装包元数据，不查询云端、不显示会话令牌；
restart_required 应为 false，service_revision 与 source_revision 应一致。
backend 应为 sdk，真实监控要求 available=true，versions 列出三个 SDK 包版本。
停止监控保留运行记录与云端任务，并等待服务锁释放后才报告已停止，避免立即重启时仍被旧进程占用。
若接口收尾超过 15 秒，命令明确提示仍在关闭，稍后再次 --stop 后再启动。重新打开网页后继续查看。Windows 桌面表现仍需在目标机器复测，不能据本机模拟测试宣称已经通过。

<a id="windows-powershell"></a>
### Windows / PowerShell

在 skill 根目录运行；`py -3` 选择已安装的 Python 3，版本需为 3.9+。若未安装 `py` 启动器，使用 `python`。

```powershell
py -3 --version
# 默认打开真实运行列表，允许空列表，无需提供 run_id
py -3 scripts/pipeline-monitor/server.py --background --open

# 仅用户明确要求演示时，无需云端接口或额外依赖
py -3 scripts/pipeline-monitor/server.py --demo --open

# 后台演示与停止：两次命令使用同一个运行目录
$demoRoot = Join-Path $env:TEMP 'cloudrobo-web-demo'
py -3 scripts/pipeline-monitor/server.py --demo --runs-root $demoRoot --background --open
py -3 scripts/pipeline-monitor/server.py --runs-root $demoRoot --stop

# 离线回归，无需 CLI 凭据
py -3 -m unittest discover -s scripts/pipeline-monitor/tests -p 'test_*.py' -v
```

Windows 文件锁使用标准库 `msvcrt`，显式锁定/释放偏移 0 的 1 字节；锁由进程关闭句柄时释放。
状态事务与服务单实例使用同一跨平台实现。后台进程使用 Windows 创建标志，与 POSIX 的新会话参数分开。
`--stop` 使用已有会话认证的本地 HTTP 停止接口，不依赖 Unix 进程信号。
状态临时文件在关闭句柄后原子替换，Windows 短暂共享冲突会有限重试，原状态保留到替换成功。

Web 查询和确认后重试通过进程内 SDK 执行；后台服务启动保留 Windows 无窗口参数。
SDK 查询不会创建子进程，测试同时禁止 subprocess.run/Popen，避免将“隐藏 CLI 窗口”当成 SDK 迁移。

更新代码后必须停止旧服务再启动，仅刷新网页或再次执行启动命令会继续使用已有进程中的旧代码。
整体更新 skill 后，在根目录运行：

```powershell
py -3 scripts/pipeline-monitor/server.py --stop
py -3 scripts/pipeline-monitor/server.py --background --open
```

使用自定义 runs-root 时，两条命令均带同一个 `--runs-root`；停止服务不会删除运行记录或取消云端任务。

JSON 输入接受 UTF-8 和 PowerShell 5.1 常见的 UTF-8 BOM。控制台与状态文件使用 UTF-8。SDK 直接接收 Python 参数，保留中文与嵌套 JSON，不经 shell 拼接。

页面在 Windows 上“复制 CLI”时生成 PowerShell/Python 参数桥接片段，避免 PowerShell 5.1 破坏嵌套 JSON 引号。
该片段需要 `python` 在 PATH；如只安装了启动器，可将其中 `python -c` 改为 `py -3 -c`。
本地 Web 操作通过 SDK 对象传参，不依赖 Bash、WSL 或 PowerShell 的 JSON 参数规则。

可选浏览器测试需要 Node 22+ 和 Chrome；Windows 会尝试查找常见 Chrome 安装目录：

```powershell
$env:PYTHON = py -3 -c 'import sys; print(sys.executable)'
node scripts/pipeline-monitor/tests/test_browser.mjs --out "$env:TEMP/cloudrobo-browser-check"
```

`test-cli-commands.sh` 是可选的 Bash 只读联调工具；Windows 运行它需 Git Bash/WSL，正常创建、状态和 Web 不需要它。
当前本机是 macOS，Windows API 分支已做替身验证；真实 Windows 服务/CLI 和浏览器联调仍需在目标机器执行上述检查。

## 2. 真实运行 Real Runs

查看已有运行只需启动服务，无需重新 init。省略 `--run` 即打开列表。
以下 init 是执行计划确认后创建新运行记录的步骤，不是打开网站的前提。

Agent 在 Stage 0 确认执行计划后，将实例化计划保存成 **JSON**。无需给服务安装 YAML 解析器；
pipeline.yaml 的解析与字段确认仍由 Agent 完成。结构见
[`monitor-plan.example.json`](../templates/monitor-plan.example.json)。替换示例中的占位符，不能直接提交示例数据。
init 后立即按上文询问；选择打开或此前已授权时先启动页面，再准备输入。尚未注册的输入保留真实
source_type/路径，资产和版本 ID 待注册核实后记录，不为了提前监控编造 ID 或先注册。

```bash
python3 scripts/pipeline_state.py --run <run_id> init --plan /path/to/resolved-plan.json
python3 scripts/pipeline-monitor/server.py --run <run_id> --background --open
python3 scripts/pipeline-monitor/server.py --stop
```

默认运行目录 `~/.cloudrobo/pipeline-runs/`，可在两条命令中同时指定 `--runs-root /path/to/runs`。
默认端口 8765，被占用时自动选择空闲端口。每个 runs-root 只有一个服务，健康的已有服务会复用。
不需要自动打开浏览器时省略 `--open`，手动访问打印的完整地址。没有图形浏览器的服务器可使用
SSH 本地端口转发到本机同一个端口，再访问该地址；服务始终只绑定 `127.0.0.1`。

所有运行都处于终态且 30 分钟无请求后自动退出。`--idle-exit 0` 关闭自动退出。
服务停止不会修改管线状态，也不会取消云端任务。

```text
<runs-root>/<run_id>/
  plan.json                已确认的实例化计划
  state.json               schema v2，version 用于比较并交换（CAS）
  events.jsonl             追加事件；状态变更按 task_id/status 去重
  tasks/<task_id>.json     每次提交的 task_config、task_name、by、at
  pending-config.json     创建结果不确定时用于终端核对的原始配置
  logs/<random>.log       用户主动下载的完整日志
<runs-root>/.monitor.json  pid、port、随机访问令牌；POSIX 权限 0600，Windows 沿用目录 ACL
```

运行目录和配置文件含内部路径及任务配置，应按内部运行数据保管，不提交到 Git。
Web 展示会递归打码 AK/SK、TOKEN、SECRET、PASSWORD 等敏感 env 值；任务配置不应承载云账号凭据。

## 3. Agent 协同 Agent Coordination

**Web 不自动推进下一阶段。** 用户在网页处理失败后，需要在终端回复“继续”。每次新对话回合、
每段等待结束和每次提交前，Agent 都先重新读取 state，以 Web/终端先完成的事务为准。
状态更新必须走脚本，不直接编辑 state.json，也不覆盖 Web 已记录的任务 ID。

```bash
# 读取完整状态；输出中的敏感值已打码
python3 scripts/pipeline_state.py --run <run_id> show

# 每次云端创建前先保留操作事务；配置文件是已确认的 task_config 对象本身
python3 scripts/pipeline_state.py --run <run_id> reserve-task \
  --stage cleaning --expect-task none \
  --config /path/to/task-config.json --name <confirmed-task-name>

# 仅保留事务成功后，调用原 skill 的 create-task；再确认 ID 并完成事务
python3 scripts/pipeline_state.py --run <run_id> resolve-action \
  --action-id <returned-pending_action.id> --task-id <verified-new-task-id>

# 记录 show-task 和 show-version 核实的结果；并行成员加 --member quality-eval
python3 scripts/pipeline_state.py --run <run_id> set-result \
  --stage cleaning --expect-task <task_id> --result /path/to/result.json

python3 scripts/pipeline_state.py --run <run_id> heartbeat
python3 scripts/pipeline_state.py --run <run_id> await-decision \
  --stage cleaning --expect-task <task_id>
```

<a id="result-fields"></a>
`result.json` 必须是 JSON 对象，只允许以下 10 个字段；按需要提供，不要求全部填写：

| 字段 | 用途 |
|---|---|
| `status` | 步骤/任务状态，例如 `SUCCEEDED`、`FAILED`；不是资产版本状态 |
| `output_name` | 本步骤输出名称 |
| `target_path` | 核实后的数据产物 OBS 路径 |
| `target_asset_id` | 数据产物资产 ID |
| `target_version_id` | 对应的确切版本 ID |
| `target_report_path` | 评测报告 OBS 路径 |
| `error` | 任务错误信息 |
| `start_at` | 任务开始时间 |
| `finish_at` | 任务结束时间 |
| `pod_names` | Pod 名称列表 |

`target_asset_name`、`times`、`pod` 不是合法字段，也不会自动映射。报错会列出本次不支持的字段及完整合法清单。
资产版本状态（例如 DRAFT）在智能体最终摘要中记录，不写成任务 `status`。例如：

```json
{
  "status": "SUCCEEDED",
  "target_path": "obs://<bucket>/cleaned/",
  "target_asset_id": "<asset_id>",
  "target_version_id": "<version_id>"
}
```

`--expect-task none` 表示无任务；其他值必须与当前 task_id 一致。冲突退出码为 **3**，此时重新读状态，
按实际原因处理：已有提交事务时先核实并 resolve；任务 ID/版本变化时跟进新状态；管线终止时停止。
不能把所有 exit 3 都解释成“该步骤已在 Web 上处理”，也不能直接清除未核实的事务。
Agent 在每次新的云端创建操作前必须 reserve-task，网页和终端共用该操作锁；若已有 pending_action，
先完成下述核对流程，禁止并发创建。`set-task` 仅用于登记已经存在的任务，不应代替提交前的事务保留。

<a id="record-inputs"></a>
### 保存上传注册结果

`resolve-inputs --inputs-file` 只读生成下游配置，不会保存上传注册结果。Asset Center CLI 上传/注册成功并
用 show-version 核实后，先将每份输入的真实资产、确切版本、名称和版本 URL 写入 JSON 文件：

```json
{
  "default": {
    "asset_id": "verified-asset-id",
    "version_id": "verified-version-id",
    "asset_name": "verified-asset-name",
    "obs_path": "obs://example-bucket/verified-version/"
  }
}
```

单输入未命名时用 default；多输入按 plan.inputs 中的真实 ID（如 left/right）逐项记录，可分批保存。
上述内容必须来自实际 CLI 返回，不执行示例值，也不从生成名推断路径。读取当前 state.version 后执行：

```bash
python scripts/pipeline_state.py --run RUN_ID show
python scripts/pipeline_state.py --run RUN_ID record-inputs --inputs-file resolved-inputs.json --expect-version CURRENT_VERSION
```

命令只写本地状态，受共享锁和状态版本检查保护，不上传/注册或发布云端资产。原始 source_type/local_path 保留；
已登记资产、确切版本和固定路径不能被替换；冲突时重新读取状态并核实，不覆盖。
state.inputs 按输入 ID 保存元数据，单输入兼容写入 upload.target_*，多个输入不压成同一组 target_*。
全部输入都有资产 ID、版本 ID 和 OBS 路径后，upload 才标记成功（已登记）；本次开始前已选择复用的
已有资产无需上传，状态仍为 SKIPPED。本次上传/注册后不把 source_type 改成 asset，不用 set-result
将 local/obs 的 upload 标为 SKIPPED；脚本会拒绝这种写入。
对原始 local/obs 来源仍保留、却误写了跳过标记的未结束运行，核实后 record-inputs 会恢复为已登记；
若原始来源已丢失或记录已结束，先核实本次上传与运行的对应关系，不根据资产 ID 猜测或批量改写历史。
Web 注册信息逐输入展示，当前页签和其他缓存页签随后补信息更新。旧记录只有成功状态却缺少登记信息时，
显示“登记信息待补全”，回智能体核实并用此命令补齐即可，无需重复上传。旧版单输入完整的 set-result 登记仍兼容；
只有 status 的新成功登记会被拒绝。Git Bash 同样使用 JSON 文件，避免把 OBS URL 放进容易转换的内联参数。

<a id="resolve-inputs"></a>
### 按数据来源生成任务输入（支持多输入）

计划中的 `input_from` 是有序数据来源，`depends_on` 是等待条件。C 可以等待 A、B 和评测 check，
同时只消费 A、B；snapshot/概览分别展示两者。旧计划省略 input_from 时仍兼容单个上游/初始数据集，
多路等待或多个初始输入则必须明确选择。配置与分支示例见 [自定义创建](custom-pipeline-authoring.md#multi-input)。

在 A、B 都已用 show-task 核实并通过 set-result 记录 SUCCEEDED、output_name、target_path、
target_asset_id、target_version_id 后，运行：

```bash
python scripts/pipeline_state.py --run RUN_ID resolve-inputs --stage C
# 初始数据尚未在 plan.inputs 记录完整资产/版本/名称/路径时，可另提供已核实的映射：
python scripts/pipeline_state.py --run RUN_ID resolve-inputs --stage A --inputs-file resolved-inputs.json
```

`resolved-inputs.json` 只映射初始输入 ID，例如（单个未命名输入用 default）：

```json
{"left": {"asset_id": "<已核实资产 ID>", "version_id": "<确切版本 ID>", "asset_name": "<数据集名称>", "obs_path": "obs://<bucket>/left/"}}
```

多个本地/OBS 初始来源要分别完成上传/注册并保留映射；不能把 upload 的单组产物复制给所有初始来源。
全部准备就绪后再将 upload 标成成功；只有一个初始来源时仍兼容 upload 上登记的原有产物字段。
inputs-file 不允许覆盖处理步骤产物；已有 asset 初始源也不能通过该文件换资产/版本。
plan 已包含的确切资产路径同样不能被 inputs-file 替换；不一致时先回智能体核实计划。

输出包含 input_from、datasets 和 task_config 片段。proc 的 dataset_configs 是按绑定顺序编码的 JSON 数组字符串；
eval/eval-group 保持一个数据集，同时返回顶层 dataset 字段和带确切 version_id 的单项 dataset_configs。将片段合入原有完整配置，不能把片段直接当成完整创建参数。
工具只读本地快照，不调用云端、不提交任务、不修改状态；缺失来源、未完成依赖、不成功或跳过的生产步骤、
不完整资产/版本/名称/路径都会拒绝。输出不替代提交前的实时版本/路径与算子能力复核；DRAFT 规则同前文。
保留真实 create-task 的完整配置，Web 重试会逐项重新核实所有 dataset_configs，保持原顺序。
旧评测配置缺少整个 dataset_configs 时，只有顶层资产/名称/路径一致、运行交接记录仍保留确切版本、
并通过 show-version 核实该版本路径，才在待确认重试草稿中补齐；不会改写原任务或历史配置。
数组已存在却缺版本、版本不匹配或交接缺失时拒绝重试，回智能体核实，不查询最新版本代替。

<a id="parallel-submission"></a>
### 统一任务图与不阻塞的提交

执行统一使用任务节点、依赖边和就绪集合。旧 parallel_group 只是输入适配形式：加载时展开成员任务，
继承组级默认值并用成员配置覆盖；对该组的等待边展开为对所有成员的等待。普通步骤直接映射成任务节点。
不要求用户区分两套运行场景，不改写旧 YAML/运行历史；Web 保留分组展示，使用同一个依赖完成判定。

智能体在初始化/输入登记后、每次提交登记后、每轮结果更新后查询：

```bash
python scripts/pipeline_state.py --run RUN_ID ready-tasks
```

命令只读本地状态，不发云端请求、不预留任务，也不授权自动重试。返回 `ready`、`active`、`state_version` 和 `action`：

| action | 智能体下一步 |
|---|---|
| submit | 仍有未提交的就绪任务，先核实配置并逐个提交；每次 resolve 后重查，不进入 wait-task |
| reconcile | 有尚未核实的提交事务；核实创建结果并 resolve，不重复 create |
| poll | 没有可提交任务且有活跃任务；对全部活跃 ID 做短周期 CLI 查询，更新结果后重查 |
| decide / blocked | 处理相应决策、输入或手动检查；不猜测缺失信息或自动重试失败任务 |
| readonly / stopped | 不提交新任务；终态后的显式补跑仍走原有确认流程 |

例如初始 ready=[A,B]；提交并登记 A 后即使 A=PENDING/RUNNING，仍返回 action=submit、ready=[B]；
两者都已提交后才返回 action=poll。合并 C 继续等待所有必要输入，不能为了并行提前放行。
本地就绪判定不替代 CLI 对算子能力、确切版本、数据契约及用户授权的核实。

采用**不阻塞的顺序提交**：每个 run 仍只有一个 `pending_action` 和一份 `pending-config.json`；
`.lock` 保护短暂状态读写，未 resolve 的创建事务占位。占位只持续到拿到并核实任务 ID，
不会持有到任务结束；不同 run 独立。以下旧分组配置也走上述同一队列，使用已预检的 `python`：

```bash
# A：预留成功后才提交，并用 show-task 核实返回的 ID
python scripts/pipeline_state.py --run RUN_ID reserve-task --stage evaluation --member quality-eval --expect-task none --config quality.json --name CONFIRMED_QUALITY_NAME
cloudrobo dataset eval create-task --name CONFIRMED_QUALITY_NAME --task-config "$(cat quality.json)"
cloudrobo dataset eval show-task --task-id QUALITY_TASK_ID
python scripts/pipeline_state.py --run RUN_ID resolve-action --action-id QUALITY_ACTION_ID --task-id QUALITY_TASK_ID

# 不必等 A 执行结束；resolve A 后即可提交 B
python scripts/pipeline_state.py --run RUN_ID reserve-task --stage evaluation --member diversity-eval --expect-task none --config diversity.json --name CONFIRMED_DIVERSITY_NAME
cloudrobo dataset eval create-task --name CONFIRMED_DIVERSITY_NAME --task-config "$(cat diversity.json)"
cloudrobo dataset eval show-task --task-id DIVERSITY_TASK_ID
python scripts/pipeline_state.py --run RUN_ID resolve-action --action-id DIVERSITY_ACTION_ID --task-id DIVERSITY_TASK_ID
```

配置文件、create-task 参数与任务名必须一致。以上为 Bash/Git Bash 示例；PowerShell 的 JSON 参数使用前文说明的
argv 桥接方式。步骤失败、提交超时或返回 ID 不确定时先核实平台是否已创建任务，不能直接 reserve B 或重复 create A。
冲突错误会指出占位步骤、成员和操作 ID；只有明确已终止的运行才提示对应终止状态。
这里的 resolve 只确认任务已创建并登记 ID，不表示任务执行完成。A 仍 PENDING/RUNNING 时就应提交 B。
该规则也适用于上传后的独立处理分支：A/B 各自绑定原始输入并等待 upload，不能为方便遍历而给 B 添加 A 依赖。
每次状态变化后先遍历所有已满足依赖的未提交任务，逐个完成提交事务，再等待云端结果。

单链且没有其他可就绪分支时，可使用 `wait-task --timeout 300 --interval 15` 分段等待，而非一次阻塞数十分钟。
存在独立运行分支时，约每 15 秒对全部活跃 ID 做一轮 CLI show-task、记录变化并扫描新就绪步骤，
避免一次等待 A 耽误 B 提交。云端资源不足导致已提交 B 排队时，展示其真实任务 ID 和排队状态。
失败时 CLI 会询问查看日志，
非交互调用需用 `printf 'n\n' | cloudrobo ... wait-task ...`。每段返回后写心跳、重新读 state、
用 show-task 确认当前任务；ID 变化则跟进新 ID，管线终止则停止，建议性步骤跳过则继续。
Web 服务只轮询 show-task，永不调用 wait-task。

上传注册完成后先按 [record-inputs](#record-inputs) 保存全部输入的资产/版本/路径；结束时对 `output`
执行 `set-result --expect-task none` 记录已经核实的最终数据产物三元组（来源为 output.from_stage，仅评测时为输入数据集），再执行：

```bash
python3 scripts/pipeline_state.py --run <run_id> finish
```

finish 只在阻断步骤成功或已校验保留原输入跳过、所有成员结束且产物完整时完成运行。建议性失败/跳过对应
`SUCCEEDED_WITH_WARNINGS`（原文档的 PARTIAL）；等待处理为 AWAITING_DECISION，显式终止为 TERMINATED。
Monitor 中的实时平台状态属于缓存；Agent 仍需用 set-result 记录最终状态与产物后才能 finish。

所有输入都已提供 `source_type: asset`、asset_id 和 version_id 时，初始化会将手动 `upload` 节点
记为 `status: SKIPPED`、`skipped: true`、`not_applicable: true`，并保存 skip_reason。
这是无需上传注册的正常分支，不阻断下游，也不使 finish 变成“完成有告警”。
已有资产的版本和真实路径仍须核实；DRAFT 不自动要求发布，仅明确的下游 RELEASE 要求需要确认发布。OBS 输入只需注册，本地输入才需上传并注册。
未提供完整输入交接信息时不会自动跳过。显式不使用 monitor_bookends 的计划不会补入这些节点。

<a id="processing-skip"></a>
### 未提交的处理步骤：保留原输入跳过

转换/清洗等单输入处理步骤现在显示“跳过…”。这与评测的直接跳过不同：网页先登记申请，
节点显示“等待处理”，原输入和所有直接下游步骤显示在确认框中。此时没有新任务/新版本，也没有
放行下游。用户可在网页取消申请；已有其他决策、提交事务、只读或已结束运行不接受新申请。

智能体每次读取 state 时检查 awaiting_decision.kind 是否为 skip：

1. 读取该步骤 input_from；只支持保留一个原输入。多输入合并步骤不能被当成一个输出原样跳过。
2. 等待来源与控制依赖完成，使用 CLI 核实原输入确切资产、版本、OBS 路径和实际格式。
   来源尚未提交/完成时先按原计划推进该来源；跳过请求不禁止上游和独立分支的运行，不能等一个尚未提交的来源而停住编排。
3. 查询每个直接下游算子的真实输入契约；并行评测逐成员核实，多输入消费者还须核实这一项的顺序/语义。
   已知原始 H5/ROS2/UMI 与预置 LeRobot 清洗/评测不兼容时明确阻止跳过必要转换。
   空间/OBS 算子契约未知时不能仅凭名称、用户点击或一句说明认为已经兼容。
4. 兼容后读取最新 state.version，记录实际核实结果并应用；不兼容或用户不再跳过则保留原步骤。

```bash
# 下游兼容性须由智能体实时核实；本命令不查询云端，也不会执行/提交任务
python scripts/pipeline_state.py --run RUN_ID resolve-skip --stage cleaning --expect-version VERSION --decision skip --compatibility-note "已通过 CLI 核实原输入资产/版本/路径和各下游算子的实际格式契约"
# 初始元数据不完整时，同 resolve-inputs 一样加 --inputs-file resolved-inputs.json
# 拒绝/取消申请，保留原处理步骤
python scripts/pipeline_state.py --run RUN_ID resolve-skip --stage cleaning --expect-version VERSION --decision keep
```

脚本在共享锁内再次检查状态版本、依赖完成、单输入、未提交/未处理、下游尚未提交以及已知格式约束。
检查失败不改变状态；不要用 set-result 手工标记成功或清空请求绕过检查。
校验通过后记录 bypassed=true、status=SKIPPED、bypass_from 和原输入的产物字段，不改写数据绑定或制造新资产。
下游 resolve-inputs 沿用这份确切数据；摘要标明未执行该处理，最终为完成有告警，不能声称已清洗/转换或 TrainingReady。
已开始/失败的处理任务不能使用这个入口。它也不提供“任意指定外部产物跳过”或自动执行后续管线的能力。

## 4. 页面与操作 Pages and Actions

| 页面 | 行为 |
|---|---|
| 运行列表 | 名称/run_id 搜索，状态筛选，分段进度，开始时间与耗时；列表在固定工作台内滚动 |
| 运行主页面 | 根据 depends_on 拓扑分层；parallel_group 分叉汇合，自定义步骤复用布局；窗口固定高度，DAG 在独立区域内滚动，浏览器整页不随内容增长 |
| 事件时间线 | 默认收起并显示计数，展开后固定面板；保留三种筛选，每页最多 20 条；历史页固定事件范围，新事件提示数量，回到最新后恢复跟随；不裁剪/删除本地事件文件 |
| 部分管线 | 在计划中将已有产物表示为 `external: true` 的步骤，并带 artifacts；节点标记“外部输入” |
| 详情概览 | 任务、算子、输入输出、状态原值、错误、查询命令；支持切换历史尝试，历史只读 |
| 计划确认 | 检查项，不展示镜像/任务 ID/资源等任务字段或重试入口；“检查项”页展示输入、依赖、算子、资源和执行范围核对内容；日志/预览说明不产生作业或数据输出 |
| 上传注册 | 数据准备节点，不创建 proc/eval 任务；本地上传并注册，OBS 只注册，已有资产版本显示“已跳过”及复用原因；展示登记资产/版本/路径，不显示“任务尚未提交” |
| 产物核对 | 展示已核实的最终路径、资产与版本；日志说明到对应处理/评测步骤查看，不显示任务提交提示 |
| 任务配置 | JSON-array 字符串展开表格、原始 JSON、与上次差异、复制配置/CLI 命令；掩码值需在终端补全 |
| 日志 | 作业/系统日志，文件选择，最新 64 KB，搜索/错误过滤与跳转，完整日志、下载；默认手动刷新，可选开启运行中每 60 秒自动刷新 |
| 输出预览 | proc 仅列输出根目录第一层文件夹和文件，不展开子目录，支持手动刷新；当前层文件/评测报告按点击获取预览/下载链接 |
| 详细资源情况 | 在概览复制任务 ID，到 CloudRobo Console 查询；本地 Web 不提供资源监控或资源查询接口 |
| 完成摘要 | 已核实的 TrainingReady 产物、统计、步骤表、评测报告、告警；可导出 Markdown |

任务时间兼容 ISO 字符串及秒/毫秒时间戳。任务配置仍保存资源池和 worker/head 规格，用于任务提交与重试。
运行提示过多时在提示区域内查看；完成摘要、运行列表、时间线和步骤抽屉各自容纳长内容。
刷新保留流程图、事件面板、列表和摘要的滚动位置；切换运行重新回到最新事件并收起面板。
浏览器仍增量读取事件，前端仅渲染当前页，分页与折叠不影响任务状态、事件持久化和 Agent 编排。
长详情默认摘要，原生 details 提供完整内容并保留展开状态；窄屏/矮屏展开时间线时聚焦事件面板，收起后恢复流程图。
CLI 提供 get-resource-usage 命令，但本地 Web 不调用它；该查询已从服务路由、SDK 适配及演示实现移除。

重新提交先查询最新预置算子、复核数据集版本与路径，生成十分钟有效的待确认草稿。
proc 默认生成新的 `管线名-步骤短名-MMDDHHmmss` 输出名，可确认前修改。任务名也保留该管线/步骤前缀，
完整长度 ≤64（含必要重名序号），默认不加随机串；超长报错并要求缩短名称，不静默裁剪。
再次打开新的重试草稿会建议新名，同进程同秒碰撞才加 -2/-3；这不是跨机器的全局唯一保证。
已确认任务恢复沿用原名；后续交接使用新提交配置及核实的实际产物名，不累加旧名后缀。
eval 输入名不变，处理旁路也沿用原输入。历史配置保留原名，新提交先清除旧产物名，待 Agent 核实后登记新实际产物名。
路径匹配且状态为 DRAFT 或 RELEASE 时可继续；CREATING、未知或其他尚未确认可用的状态请回智能体核实，网页不自动发布。
若实际平台/算子另有 RELEASE 要求，由智能体确认发布后再处理；不能把所有下游失败归因于版本未发布。
镜像、algo_id、入口和算子声明不可编辑。可修改任务/输出名、规格、资源池和已声明 env 值、输入 url_path。
勾选明确确认后才调用 create-task，新 ID 会替换当前 ID，旧 ID 保留在 attempts。
原始配置缺失、算子缺失/匹配不唯一、状态过期、接口失败或 CAS 冲突都会阻止操作。
OBS/工作空间自定义算子可监控，但重新查询与重提需回终端执行，以免网页复用旧算子信息。

直接跳过允许 `fail_fast: false` 的未提交/失败/删除成员。单输入且未提交的处理步骤可以申请保留原输入跳过，
需智能体核实兼容性后生效；已知不兼容时禁用按钮并显示原因，已提交的阻断任务不能直接跳过。
完成后的失败或跳过评测可补跑；结果需要 Agent 重新记录并 finish 以更新最终摘要状态。
终止需要输入 run_id 后四位，页面会列出现有运行任务并说明它们仍继续运行。

首版保留方案中的可选增强边界：**不提供删除云端任务、提供外部产物后跳过阻断步骤、无人值守 runner**。
这些操作在终端按原 skill 流程执行；没有用占位按钮模拟成功。

### 删除本地运行记录

运行列表和详情页均提供“删除本地记录”，操作前明确展示名称、run_id、删除范围和不可恢复提示。
仅 schema v2 且 status 为 SUCCEEDED / SUCCEEDED_WITH_WARNINGS / FAILED / TERMINATED、无 pending_action 时允许。
等待处理或运行中须先终止后续编排；终止不停止云端任务。删除本身也不查询、停止或删除平台任务/资产/OBS 对象。

POST 使用同一 Host/会话/Origin/自定义请求头校验；body 为 confirmed=true 和整数 expected_version，
版本值来自当前快照的 state_version。在与智能体共用的运行锁内复核版本、状态、提交事务和路径。
先将 state.json 标记为待删除，阻止迟到状态写入或同名 init；关闭 Windows 文件锁后，将目录移动到
同一 runs-root 下的随机 .deleted-* 临时目录，再移除全部文件。常规删除完成不保留备份。
移走失败则恢复状态文件并返回错误；移走后文件清理失败会返回 cleanup_pending=true 和明确的剩余目录提示，
不能将这种结果描述为全部文件已清理。删除/服务中断后的残余临时目录需按实际文件占用和权限清理，不能恢复为成功运行。

后端清除该 run 的任务/日志/预览列表与重试草稿缓存，并隔离迟到任务查询；下载写盘也复用运行锁。
成功后页面回到列表、清理详情和日志缓存；其他页面收到记录不存在响应时也返回列表，不重新 init。
云端任务、资产、版本和 OBS 数据保持原状，后续查询使用平台 Console。

## 5. 异常恢复 Recovery

创建超时、网络中断或未能解析新 ID 时，可能已经创建了云端任务，服务会保留 pending_action。
服务在创建后崩溃也可能留下相同状态；此时不自动清锁、不再重复提交。

1. 用 `pipeline_state.py show` 读取 pending_action.id / name。
2. 在终端按任务名 list-tasks，再 show-task，确认新任务是否存在。
3. 确认存在，登记已核实的新任务；确认不存在，才释放操作锁：

```bash
python3 scripts/pipeline_state.py --run <run_id> resolve-action \
  --action-id <pending_action.id> --task-id <verified-new-task-id>

# 仅在平台确认没有新任务后：
python3 scripts/pipeline_state.py --run <run_id> resolve-action \
  --action-id <pending_action.id> --not-created
```

非超时的明确提交失败会清理 pending_action、记录 action_failed，保留对话框和 SDK 错误。
恢复网络/认证后，任务状态按 15→30→60→120 秒退避重试。日志/预览接口失败时保留错误原文供核对。
两个轮询周期内没有取得有效状态则标记“可能过期”并禁用对应修改操作。

旧版 checkpoint 可导入为只读运行，**不自动迁移为可修改状态**：

```bash
python3 scripts/pipeline_state.py --run <legacy_run_id> import-legacy \
  --checkpoint /path/to/old.checkpoint.json
```

## 6. 本地 API 与安全 API and Security

服务只接受正确的 127.0.0.1/localhost Host 和实际监听端口。首次 URL 的 32 字节随机 token 换成
HttpOnly + SameSite=Strict Cookie 后立即重定向清理 URL。所有 API/静态文件均需认证，不返回 CORS 头；
POST 必须含 `X-Pipeline-Monitor: 1`，Origin 若存在必须同源，正文须为不超过 1 MB 的 JSON。
浏览器展示的云端字符串经过转义；预览链接只允许 http/https，新窗口使用 noopener/noreferrer。
本地文件、日志、task_id 均做运行归属或列表校验。服务仅调用上述 SDK 方法，最多四个并行操作，每次操作独享 HTTP 会话并在结束时关闭。
连接超时 10 秒，单次读取等待上限为查询 50 秒、创建 110 秒（不是整个复合 SDK 操作的总时限）。
传输 max_retries=0，禁用连接/超时等瞬时故障的自动重试；SDK 自身的鉴权签名修正和标准重定向行为保留。
状态轮询失败仍按退避周期再查，预览失败保留手动重试，创建结果不明不自动再提交。
创建已发出后遇到超时、网络中断、5xx 或缺失有效任务 ID，保留 pending_action，由智能体通过 CLI 核实。
明确的 4xx 拒绝（408 除外）或发出前的配置/字段校验失败可清理提交锁。关闭 SDK 流量日志，不记录签名头或凭据。

| API | 用途 |
|---|---|
| `GET /api/runs` | 所有运行 |
| `GET /api/runs/{run}?since=<snapshot-version>` | 计算快照；不变时 204 |
| `GET /api/runs/{run}/events?after=<seq>` | 增量事件 |
| `GET /api/runs/{run}/summary` | 下载 Markdown 摘要 |
| `GET /api/runs/{run}/tasks/{tid}?refresh=1` | 原始配置与 SDK 任务详情，refresh 强制查询 |
| `GET …/tasks/{tid}/logs?system=true|false` | 日志文件列表 |
| `GET …/tasks/{tid}/logs/content?file=&path=&all=0|1` | 末尾/完整日志；超过 5 MB 提示下载 |
| `POST …/tasks/{tid}/logs/download` | 保存 SDK get_task_log/get_eval_task_log 内容，返回受保护的本地下载 URL |
| `GET …/tasks/{tid}/frames?prefix=` | 输出根目录第一层文件和文件夹；prefix 只接受本任务根目录，不能请求子目录 |
| `GET …/tasks/{tid}/preview?file=&download=0|1` | 输出预览/评测报告 |
| `GET …/actions/retry/draft?stage=&member=` | 最新重试草稿 |
| `POST …/actions` | retry/skip/terminate；confirmed、expected_task_id 必填，支持 expected_version |
| `POST …/delete` | 仅删除终态 v2 本地记录；confirmed=true 与当前整数 expected_version 必填，无 SDK 调用；返回 deleted/run_id/cleanup_pending，部分文件未清理时含 warning |

snapshot.version 是状态和实时缓存的摘要；POST expected_version 使用 snapshot.state_version 数值，
二者用途不同。网页每三秒请求快照，隐藏标签页暂停。状态文件每轮重新读取，云端未结束任务按
12–18 秒抖动轮询，终态取一次缓存；刷新详情可强制重新读取。

## 7. 测试 Testing

```bash
# 离线测试：不需要 CLI、凭据或云端；无 SDK 时跳过 4 项已安装 SDK 契约测试
python3 -m unittest discover -s scripts/pipeline-monitor/tests -p 'test_*.py' -v

# 可选浏览器检查：Node 22+、本机 Chrome/Chromium，无 npm 依赖
node scripts/pipeline-monitor/tests/test_browser.mjs --out /tmp/cloudrobo-monitor-qa
```

浏览器脚本自行启动独立 demo 服务，验证页面、抽屉、日志、重试、跳过、终止、报告、摘要与
1512/1280/768/390 视口，输出截图和 report.json；可通过 CHROME_PATH/PYTHON 指定运行程序。
智能体 CLI 的真实云端只读检查仍使用原 `scripts/test-cli-commands.sh`，它与离线 Web 检查分开运行。

进入内网后的最低联调清单：

1. 真实 SDK 任务详情的时间、错误，日志列表/内容与 frames/preview 字段；资源详情到 CloudRobo Console 查询。
2. 一条可运行的预置算子失败任务：重试草稿是否使用当前镜像、入口、输入声明和已核实上游版本。
3. 用户确认后新建任务，终端在等待间隙读取到新 ID，继续记录最终产物并 finish。
4. 建议性跳过与终止：摘要告警正确，终止后已有云端任务仍保持原样。
5. 日志下载和评测临时链接在内网可用，数据打码、只读模式和冲突提示符合预期。
6. 使用已安装 SDK 的 Python 运行相同 unittest 命令，4 项实际 SDK 契约检查不应被跳过；这些检查只拦截 HTTP，不调用云端。

当前环境的验证结果与待内网确认项见 [Web 测试记录](web-monitor-test-report.md)。

## 8. 前端模块 Frontend Modules

前端使用浏览器原生 ES Modules，由 `index.html` 加载普通脚本 `bootstrap.js`，
确认通过 HTTP 访问后动态加载 `app.js`，再通过相对路径导入模块。
运行时无需构建、npm 包或外部静态资源。模块职责如下：

| 文件（`scripts/pipeline-monitor/static/`） | 职责 |
|---|---|
| `bootstrap.js` | 本地文件启动引导、模块加载失败提示与 HTTP 入口加载 |
| `app.js` | 入口、事件绑定、定时器与首次刷新 |
| `common.js` | DOM、文本转义、格式化、请求、通知和复制 |
| `state.js` | 共享页面状态、当前步骤与 API 路径 |
| `manual.js` | 计划检查、上传注册和最终产物核对 |
| `pipeline.js` | 运行列表、进度、DAG、时间线和完成摘要 |
| `details.js` | 步骤抽屉、历史尝试、任务概览和配置 |
| `logs.js` | 日志读取、筛选、搜索与自动刷新条件 |
| `preview.js` | 输出文件、目录和评测报告预览 |
| `actions.js` | 重试、跳过、终止的确认与提交 |
| `navigation.js` | 运行切换、快照刷新与过期响应保护 |

模块依赖无循环，公共状态由 `state.js` 维护；入口统一绑定事件，避免重复注册。
服务仅开放明确列出的静态文件，模块请求仍需会话认证，并返回 JavaScript MIME 类型。
本地服务连接队列支持浏览器并发加载模块。日志继续默认手动刷新，可选自动刷新间隔为 60 秒。

生产 JS 单文件最多 400 行，含注释和空行；本地 ESLint 配置还检查未定义与未使用的绑定，
命令见 [代码检视规则](verification-method.md#code-review-rules-代码检视规则)。

### 详情页签与目录缓存

浏览器只保留当前任务上下文的四个详情页签 DOM，切换页签不重建抽屉、不重复请求已加载的任务详情、日志或目录。
保留搜索、完整日志模式、第一层目录列表及滚动位置；首次未完成的请求仍由 drawerEpoch 隔离，晚返回的数据不会覆盖其他页签。
切换运行、步骤、尝试或任务状态变化时清理；“查询最新状态”强制重新查询详情。
日志默认手动刷新，可选 60 秒自动刷新；手动刷新同时重查文件列表，以发现新日志文件。目录使用“刷新目录”重查。
这属于浏览器当前页面内存缓存，不写入数据库或运行目录；页面刷新后重新读取。预览和报告临时链接始终按点击重新请求。
输出列表合并平台 files/items 和独立 directories/folders/dirs、common-prefix 类目录数组，兼容 payload/item/data 包装。
深层文件 key 仅投影为根目录第一层文件夹，按名称去重并优先展示文件夹；不递归请求或渲染子目录。
只有本次根目录列表中的直接文件进入预览白名单，目录和深层对象不能绕过列表发起预览；刷新会替换旧白名单。
目录根路径统一补齐末尾 /，保留当前任务及路径归属校验。真实内网返回结构仍需按接口响应核对，不把本地模拟当作联调通过。

### 待提交时的智能体提示

保持现有阻断和终端确认流程。运行未结束、没有操作正在提交且存在 READY 的处理/评测步骤时，网页显示
“请到智能体确认进度”，列出待提交步骤；步骤概览与页脚也引导回智能体检查产物版本、参数等待确认事项。
提示不推断具体暂停原因，不捕获终端问答，不增加网页审批或自动推进能力；只读、完成和终止运行不显示此提示。
