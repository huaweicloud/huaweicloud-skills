# 步骤 4.3 方式 A — API 自动部署详细流程

> 本文件承载 SKILL.md 步骤 4.3 的详细流程约束,SKILL.md 仅保留核心命令骨架与必填字段,运行时按需加载本文件。

## 1. 前置环境信息确认(强制)

### 1.1 ModelArts 域名/工作空间/区域(3 项合并 AskUserQuestion)
- 域名统一 `modelarts.<region>.myhuaweicloud.com`(不存在 dev 域名,支持用户自输入其他生产域名,须与资源池同区域)
- 工作空间名经 AskUserQuestion 确认,通过 `GET /v1/{project_id}/workspaces`(路径中 `{project_id}` 必须用 UUID Project ID,非 Project Name;工作空间列表接口不带 `X-Workspace-Id` 头、不带 workspace 查询参数、仅带 `Authorization: Bearer <token>`)按工作空间名匹配 `id` 记为 `WORKSPACE_ID`
- **workspace-id 格式(不假设 UUID)**: 多数工作空间 `id` 是 UUID,但 `default` 工作空间 `id` 实测为简写 `"0"`,以 API 返回值为准

### 1.2 project-id 自动查询(无需向用户索要)
- 获取 token 后调 `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token` 头),响应 `projects[]` 中按 `name` 匹配 `PROJECT_NAME`(步骤 4.3 token 获取第 ③ 条已确认;默认 region 去掉 `.beta` 等环境后缀)取 `id`
- **⚠️ project name ≠ region name(强制)**: project name 可能去掉 `.beta` 等环境后缀(如 region=`cn-southwest-301.beta` → project name=`cn-southwest-301`);禁止假设 project name = region name,先列出全部 projects 再匹配
- **⚠️ Project ID 必须用 UUID(强制,违反=API 报 `token should contains projectId` 等 400/401)**: `GET iam/v3/auth/projects` 返回的 `id` 是 32 位 UUID(如 `<PROJECT_ID_UUID>`),所有 ModelArts API 路径段 `{project_id}` 必须用此 UUID;`Project Name`(region name 格式如 `cn-north-7`)仅用于获取 token 的 `scope.project.name`,禁止用 Project Name 占据 API 路径段
- `create_infer_service.py` 的 `--project-id` 参数已增加 UUID 格式校验(32 位十六进制),非 UUID 直接拒绝

### 1.3 flavor 获取(强制,ShowInferServiceCluster)
- 创建请求体 `unit_configs[].flavor` 通过查询纳管资源池详情接口 `GET /v2/{project_id}/services/clusters/{pool_id}`(路径中 id 为资源池 ID;带双 workspace 查询参数 + `X-Workspace-Id` 头)获取
- 响应 `flavors[]` 数组,每个元素含 `id`(如 `modelarts.vm.arm.16u.64g.npu.16snt9c`)与 `ascend` 对象(`card`=物理卡数、`npu`=实际使用卡数;以 `npu` 值为准: 一般资源池 `card=npu`,A3 资源池 `card×2=npu`)
- 按部署所需卡数选对应条目,取其 `id` 作为请求体 `flavor`;多节点取每节点卡数对应条目(如 16 卡/节点 → `npu=16` 条目)
- **禁止从节点规格推导 flavor**(前缀 `vm`/`bm` 与内存取整档无法从节点规格得出)
- **PD 分离 proxy 单元例外(强制)**: proxy 不消耗 NPU 卡,资源池无 0 卡预置 flavor,必须用 `custom_spec`(JSON,`card=0.0` + `cpu`/`memory`/`type_alias`/`arch`/`ratio`)替代 `flavor`(`recovery=Instance`+`termination_grace={"termination_grace_period_seconds":1}` 与其他单元一致,骨架统一注入所有推理单元,proxy 不特殊化;参考已部署 routeserver 实测配置: `{"arch":"arm64","card":0.0,"cpu":10,"memory":102400.0,"ratio":2,"type_alias":"Snt9b23"}`)。`create_infer_service.py` 用 `--proxy-custom-spec '<JSON>'` 自动注入到名为 proxy 的 unit(仅替代 flavor,不覆盖 recovery/termination_grace);骨架默认为所有推理单元注入 `recovery=Instance`+`termination_grace=1s`;`validate_request_body` 允许 proxy 单元用 custom_spec 替代 flavor

## 2. token 获取与提取(强制)

### 2.1 token 安全传递
- IAM Token 是敏感凭据,**禁止作为命令行参数传递**(`ps`/`/proc/<pid>/cmdline`/Shell 历史均会明文暴露)
- 脚本已移除 `--token` 参数,按优先级提供:
  - ① **环境变量 `IAM_TOKEN`**(推荐,不进进程 argv;Windows 上一律用此方式——NTFS 权限映射 0o666,`chmod 600` 不可靠,`--token-file` 会被拒绝)
  - ② **`--token-file <文件>`**(仅 Linux 可靠,权限须 600,脚本拒绝 0o644 等)
  - ③ **交互式输入**(不回显,不可管道/脚本化)

### 2.2 Agent Bash 工具独立 shell
- Agent Bash 工具每次调用是独立 shell,`export IAM_TOKEN=...` **不跨调用持久化**——必须 `IAM_TOKEN=<token> python scripts/create_infer_service.py ...` 在同一条命令内完成(token 可由 `python -c "...读 token 文件..."` 内联读取后赋给环境变量再执行)

### 2.3 超长 token(含 base64 编码的 PKI token 可达 8KB+)
- bash heredoc/内联传递会因引号/特殊字符冲突报 `unexpected EOF`——**禁止用 bash heredoc/`cat <<EOF` 传 token**
- 改用 Write 工具将含 token 的完整 Python 脚本写入 **`/tmp/` 下的临时文件**(如 `/tmp/get_token_<随机后缀>.py`,token 作为 Python 字符串常量;**禁止写入 skill 本体目录或工作目录,防止污染 skill 目录结构**),再用 `python /tmp/<脚本>.py` 执行(脚本内 `requests` 直接引用 token 变量,不经 shell argv)
- **所有运行 skill 产生的临时文件一律写入 `/tmp/`,禁止在 skill 本体(`scripts/`/`templates/`/`references/` 及 skill 根目录)或部署产物目录外创建任何文件**

### 2.4 获取 token 必须用 Python requests 调 IAM API
- `resp = requests.post('<IAM_DOMAIN>/v3/auth/tokens', json=<IAM请求体>, verify=True, timeout=30)`(requests 直接传 dict/JSON,凭据正确即返回 201),响应头 `resp.headers['X-Subject-Token']` 取 token
- **HTTPS 证书校验默认保持开启**: 仅自签证书/企业代理 MITM 调试场景可临时关闭,须使用与 `scripts/create_infer_service.py` 一致的开关 `--insecure` 或 `MODELARTS_INSECURE_TLS=1`(不得引入第二套开关名)并在 stderr 打印告警;禁止在脚本中把关闭校验写成默认值
- **禁止用 curl `-d` 字符串拼接 JSON body 获取 token**(Windows bash 下 `'"$VAR"'` 引号拼接致密码传递错误,凭据正确也返回 401)

### 2.5 token 必须用 project scope 获取
- `"scope": {"project": {"name": "<PROJECT_NAME>"}}`(与资源池同区域)
- **禁止 domain scope**(报 `400 ModelArts.6400 ... getProject() is null`)

### 2.6 IAM 域名与 project_name 必须先与用户确认
- ①' **IAM 域名确认(强制)**: 获取 token 前,必须用 AskUserQuestion 交互式确认 IAM 域名——options 给默认推导值 `iam.<region>.myhuaweicloud.com`(region 含 `.beta` 时同带),支持用户经 Other 自输入(如 `iam.cn-southwest-301.beta.myhuaweicloud.com`);禁止不确认就默认 `iam.<region>` 直接调 IAM API
- ②' **project_name 确认(强制,账号密码方式必做)**: 用户选择 IAM 用户名/密码方式时,除账号名/用户名/密码三要素外,必须额外用 AskUserQuestion 确认 `project_name`(token 的 `scope.project.name`)——options 给默认推导值(region 去掉 `.beta` 等环境后缀后的值,如 region=`cn-southwest-301.beta` → 默认 `cn-southwest-301`,实测 project name 为 `cn-southwest-301` 时凭据正确才返回 201;用 region 含 `.beta` 的原值会 401),支持用户经 Other 自输入实际 project name

### 2.7 IAM 凭据三要素索要顺序必须为「账号名 → IAM 用户名 → 密码」(强制)
- 用 AskUserQuestion 收集时,按"账号名(domain.name)、IAM 用户名(user.name)、密码(password)"的顺序展示与收集——账号名(主账号)是用户最易识别的第一要素,放第一位;用户名(IAM 子用户)次之;密码最后
- 字段对应关系: 账号名=主账号(`domain.name`)、用户名=IAM 子用户(`user.name`)、密码=登录密码
- 顺序错配会 401 且有账号锁定风险——先询问"以哪种方式提供 token"(IAM 用户名/密码 / 直接提供 Token),收集后按"账号名(domain.name)、IAM 用户名(user.name)、密码(password)"顺序向用户复述字段对应关系再取 token

### 2.8 提取 token 必须用 Python 正则完整提取
- `re.search(r'(?i)^X-Subject-Token:\s*(\S+)', content, re.M)`——禁止用 `grep | sed | tr` 管道(长 token 丢字符导致 401)

### 2.9 校验 token 可见项目(可选)
- `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token`)

### 2.10 用户直接提供 token 时
- 若含 `-`/`_` 或非 `==` 结尾,先怀疑复制截断,用 AskUserQuestion 请用户选择重新提供 / 改用 IAM 用户名密码

### 2.11 超长 PKI Token 禁止通过 AskUserQuestion 传递(强制)
- IAM Token 为 PKI 格式(含 base64 编码的证书链+签名,可达 8KB+),AskUserQuestion 的 answer/notes 字段有长度限制,超长 token 会被截断,末尾缺失签名块导致 API 报 `401 decrypt token fail`——反复重试无效,且用户复制时可能再截断
- 正确方式:
  - ① 优先请用户提供 IAM 用户名/密码,skill 用 Python requests 调 IAM API 获取 token
  - ② 或请用户将 token 保存为本地文件并提供文件路径,skill 读取后设置 `os.environ['IAM_TOKEN']`(环境变量方式,不进进程 argv,Windows 推荐)调用脚本
  - ③ **禁止把超长 token 作为 Python 字符串常量内嵌脚本**(引号/转义易错,且偏离 skill 的 token 安全传递规范)

### 2.12 IAM 凭据三要素错配排查(强制)
- 凭据正确但 401 `The username or password is wrong` 时,禁止反复猜测用户名/密码组合(多次错误有账号锁定风险)——让用户提供 postman/已调通的完整请求体,逐字段核对 `user.name`/`domain.name`/`password`,特别是 **domain.name(账号名)易因手工抄录/解析漏字符**而错配(如 `ei_pangu_x60079363_01` 误写 `ei_pangu_x6007963_01`)
- 确认 **project_name 是否正确**(用 region 原值含 `.beta` 会 401,须去掉后缀)

## 3. workspace 传参方式按请求类型区分(强制,POST 创建请求与 GET 查询接口不同,违反=创建报 8179)

- **GET 查询接口**(list/show/资源池/节点等)必须带 `X-Workspace-Id` 头(不带则查不到对应工作空间的服务,误判"无同名服务"而创建失败(8006/8118))+ URL 双查询参数
- **⚠️ ModelArts 各 GET 接口的 `X-Workspace-Id` 头不起过滤作用**,且各微服务对 workspace 参数命名未统一(驼峰 `workspaceId` / 下划线 `workspace_id`)
- **除工作空间列表接口 `GET /v1/{project_id}/workspaces`(全局查询,用于获取 WORKSPACE_ID 本身,不携带 workspace 查询参数、不带 `X-Workspace-Id` 头,仅带 `Authorization: Bearer <token>`)外,所有 GET 接口(list/show/资源池等)统一在 URL 上携带 `?workspaceId={WORKSPACE_ID}&workspace_id={WORKSPACE_ID}` 双查询参数**,同时保留 `X-Workspace-Id` 头
- `create_infer_service.py` 的 `cmd_list`/`cmd_show` 已用 `append_workspace_query()` 函数拼接双查询参数,其他脚本/手动调用 GET 接口时须加 `?workspaceId={}&workspace_id={}` 双查询参数
- **POST 创建请求(CreateInferService)的 `workspace_id` 放在请求 body 顶层字段**(与 `name`/`type` 同级)——不是请求头、也不是 URL 查询参数
- 实测仅带 `X-Workspace-Id` 头而不在 body 放 `workspace_id`,报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`(资源池实际存在且 X-Infer 已启用);body 顶层补 `workspace_id` 后创建成功
- `create_infer_service.py create` 已自动注入该字段(骨架与 `--raw-json` 路径均补齐,`validate_request_body()` 校验缺失)

## 4. 资源池与节点查询

### 4.1 查资源池列表
- `GET /v2/{project_id}/pools`(v1 路径 `/v1/{project_id}/pools` 报 404 `APIGW.0101`)——URL 须带 `?workspaceId={}&workspace_id={}` 双查询参数 + 头 `X-Workspace-Id`
- 响应 `items[]` 中取 `metadata.name` 为资源池 ID(pool_id),`spec.resources[].count` 为节点数

### 4.2 查节点卡数
- `GET /v2/{project_id}/pools/{pool_id}/nodes`(带双 workspace 查询参数 + `X-Workspace-Id` 头)
- 响应 `items[].status.resources["huawei.com/ascend-1980"]`=总卡数、`availableResources`=可用卡数

### 4.3 资源池名称 vs 资源池 ID(强制,违反=查 pool_id 失败)
- 资源池有用户自定义名称(如 `pool-infer2-a3-r60070762`,控制台显示,非 API 字段)与系统生成的资源池 ID(UUID 格式 `pool-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`,即 `metadata.name`,API 必须用此值)
- 交互式确认时,问题文本写明:"资源池 ID(UUID 格式,控制台资源池详情页可查;若只知资源池名称也可提供,skill 查 pools 列表按名称匹配)"
- 用户提供的是名称时,调 `GET /v2/{project_id}/pools` 在 `metadata` 的 label/annotation 字段按名称匹配,取其 `metadata.name` 为 pool_id;不匹配则列出全部资源池由用户选择

## 5. 部署前必查资源池可用卡数(强制)
- 发起 CreateInferService **前**,先调 `GET /v2/{project_id}/pools/{pool_id}/nodes`(带双 workspace 查询参数 + `X-Workspace-Id` 头),汇总 `items[].status.availableResources["huawei.com/ascend-1980"]` 为总可用卡数
- 计算本部署需要卡数 = 副本数 × 单元数 × 每节点卡数(如 multi_node 2 节点 × 16 卡 = 32)
- **可用卡数 < 需要卡数时,告知用户"资源不足,任务将排队等待(async_scheduling=true 已默认注入,平台收到请求后异步排队,资源释放后自动调度)"**,然后继续发起 CreateInferService 创建请求(不阻断);创建请求返回 200/201 即排队成功,服务状态进入 `DEPLOYING`(等待资源);若返回 8118(同步调度拒绝,极少发生,因 async_scheduling=true 已注入),按 §7 处理

## 6. 服务名占用(8006)处理(强制,所有环境一致,禁止 DELETE 与自动 stop)
- 创建服务返回 `400 ModelArts.8006 "The service name xxx already exists"` → 服务名已被占用(同地域唯一)
- 处理顺序(强制):
  - ① **不自动停止任何服务**——无论占用服务是否为本 skill 部署,一律不主动 `stop`(停止其他用户服务属越权)
  - ② **查占用服务归属并告知用户**: `list`/`show` 查该服务状态(DEPLOYING/FAILED/STOPPING 等非运行态仍占服务名与资源池卡数),将服务名/id/状态告知用户
  - ③ **换新服务名创建**: 小写字母/数字/连字符,原名加 `-2`/`-3` 递增(如 `glm53-flash-mn-2`)
  - ④ **若用户明确指示释放某个服务**(提供 service_id),skill 仅对该 service_id 执行 `POST /v2/{project_id}/services/{sid}/stop`,等待 STOPPED 后再创建
  - ⑤ **禁止触发 DELETE 动作**(DELETE API 可能 404 且删除他人服务属越权)
  - ⑥ **关键: list 查不到同名服务 ≠ 服务不存在**——list(GetServices)可能不返回 FAILED/DELETING/STOPPING 等非运行态服务,但该服务仍占用服务名与资源池卡数;判断服务是否存在以 create 返回的 8006/8118 与资源池可用卡数为准

## 7. 资源不足(8118)处理(强制,所有环境一致,禁止自动 stop)
- 创建新服务返回 `400 ModelArts.8118 Insufficient NPU resources`(Requested 卡数 > Available 0 卡)说明失败/停止的旧服务仍占用资源池卡数,**且 async_scheduling=true 未生效**(async_scheduling=true 已默认注入所有芯片,正常情况资源不足应排队而非 8118 拒绝)
- 处理(所有环境一致,禁止 DELETE 与自动 stop):
  - ① **先查资源池可用卡数** `GET /v2/{project_id}/pools/{pool_id}/nodes`(响应 `items[].status.availableResources["huawei.com/ascend-1980"]`)
  - ② **列出占用资源的服务并告知用户**: `list` 查各服务 `resource_details[]`(含 `pool_id`/`resources`/`status`),汇总到目标资源池上仍占用卡数的服务清单(id/name/status)
  - ③ **将可用卡数 + 占用清单告知用户,由用户决定**——用户可在控制台自行停止,或明确指示 skill 停止某 service_id;skill 仅执行用户指定的 service_id 的 `POST /v2/{project_id}/services/{sid}/stop`,等待 STOPPED 后再创建
  - ④ **禁止 DELETE**(`method DELETE not found` 或越权);**禁止 skill 自行批量 stop 非本会话部署的服务**

## 8. code 目录文件存储挂载(关键)
- `unit_configs[].files[]` 内配置 code 目录挂载(`files[].address=CODE_OBS_PATH` → `files[].mount_path=/home/ma-user/code`)
- 启动命令与探针命令一律用容器内路径 `bash /home/ma-user/code/...`

## 9. host_cache 本地加速(强制,所有芯片 A2/A3/A5 统一开启)
- `group_configs[].model`(权重挂载)与 `unit_configs[].files[]`(code 挂载)都必须带 `host_cache: true`——将 OBS 挂载内容缓存到主机本地,显著加速大模型权重加载(如 54GB BF16)与 code 脚本读取
- 缺失会被 `create_infer_service.py` 的 `validate_request_body()` 拦截(FAIL 拒绝提交);骨架路径(`--pool-id`/`--model-obs-path`/`--code-obs-path`)自动注入,`--raw-json` 路径自动补齐缺失项

## 10. envs 只需注入少数项
- `TP_SIZE` **无需写入 envs**(脚本按资源池实例规格自动推导)
- `MODEL_PATH`/昇腾环境变量等模板已有默认值
- **pd(PD 分离)必须在同一部署单元内 3 个推理单元分别加 `VLLM_ROLE=proxy|prefill|decode`**(脚本无法自行区分共享 code 目录的单元角色,平台按单元注入;**PORT 已在脚本内按角色内置默认值 proxy=8080/prefill=8080/decode=7100,无需 envs 注入**)
- `MODEL_NAME` 在模型文档明确给出 `--served-model-name` 值时(如 Qwen3.8-27B 文档示例 = `qwen3.8`),脚本默认值应填文档值(生成脚本时按 3.1 查文档提取的值填充固定默认值,禁止保留模板兜底值 `model`);文档无明确值时才退兜底默认 `model`,仅用于无 served-model-name 约定的模型

## 11. 请求体结构(顶层平铺,强制)
- 新版 CreateInferService 请求体是**顶层平铺结构**——不是 `{"service": {"deployment": {"roles": []}}}` 包裹结构(旧骨架报 400 `name/type/group_configs/runtime_config` 缺失)
- **顶层 `workspace_id` 必填(强制,违反=报 8179)**: 请求 body 顶层必须含 `"workspace_id": "{WORKSPACE_ID}"`(与 `name`/`type`/`deploy_timeout_minutes` 同级)
- 完整请求体 JSON 示例与字段说明见 `references/modelarts-console-guide.md` 第三节(顶层平铺、`secret_type: "agency"`、`runtime_config.service_invoke` 三项必填: `port`=8080(与启动脚本一致)、`auth_type`=NONE/TOKEN/API_KEY、`protocol`=HTTP——三项缺失任一项报 400 `ModelArts.6400`、`deploy_timeout_minutes=300`(部署超时统一 300 分钟)、PD 三角色 envs 仅 `VLLM_ROLE`(PORT 脚本内置默认值)、`unit_configs[].name` 仅小写字母/数字/连字符(大写 `Prefill`/`Decode` 报 400)、`flavor` 为推理实例规格从 ShowInferServiceCluster 获取、`failure_threshold=300`/`initial_delay_seconds=300`/`period_seconds=60`、`group_configs[].weight`(100)与 `service_limit` 三项必填(`request_timeout=300`/`request_size_limit=20`/`rate_limit`)、multi_node 多机部署用 2 个 unit_configs(master count=1 + worker count=N-1)承载、获取正确结构的最可靠方法=查询已部署成功的现有服务 `show` 反推)
- 构造请求体前对照 reference,字段名以 API Explorer 为准

## 12. A5(snt9e/950 系列)芯片特殊字段(强制)
- 上述请求体骨架与 `references/modelarts-console-guide.md` 第三节示例是在 A2(910B)/A3(910C)资源池上验证的
- **部署到 A5(950 系列 `ascend-snt9e`)资源池时,请求体必须补充 A5 特殊字段**(详见 reference 第三节"A5 特殊字段"小节): `group_configs[].workload_type="LWS"`、`async_scheduling=true`、`priority=1`、`framework="COMMON"`、`system_log_dump_enable=false`、`deploy_type="MULTI"`、`advanced_config`(含 `deploy_timeout_minutes=300`/`port=8080`/`upgrade_config`/`service_secret`)、`secret_type="dew"`(group 与 unit 级)、`unit_configs[].termination_grace/npu_reset_enable/cpu_affinity/codes/models/dumps`、探针 `name`(survival_probe/ready_probe/start_probe)、`runtime_config.service_invoke.direct_channel_enable/intranet_approval_enable`、`runtime_config.service_limit.ip_white_list/ip_black_list`、顶层 `tags/schedule/log_configs`
- **`group_count`/`count` 为通用必填字段(不区分芯片型号),不属 A5 特殊字段**
- **推荐直接走 `create_infer_service.py create --chip-model a5`**,脚本自动注入 A5 特殊字段;**非 A5 场景(a2/a3,默认)不注入这些字段,保持原骨架**
- A5 创建报 `8118 Insufficient NPU resources` 时,优先核对 `async_scheduling=true` 是否已注入(缺省同步调度会立即拒绝,而非异步排队)

## 13. 基础命令(推荐骨架 + 自动构建)

```bash
# 创建在线服务(单部署单元;--role 按部署形式传: single=1 个 master;multi_node=2 个 master+worker;pd=3 个 proxy+prefill+decode)
# token 安全提供: 环境变量 IAM_TOKEN(推荐,不进进程 argv),或 --token-file <文件>(权限 600)
# --chip-model: 目标资源池芯片型号。默认 a2(910B)/a3(910C)走原骨架;
#               部署到 A5(950 系列 snt9e)时必须显式传 a5,脚本自动补充 A5 特殊字段
# --pool-id/--model-obs-path/--code-obs-path: 骨架路径自动填 pool_id/model(权重挂载)/
#                files[](code 挂载),均默认 host_cache=true(本地加速,所有芯片必开)
# --role-extra-json: 按单元名补 flavor/image 等字段(如 {"role-1":{"flavor":"...","image":{"source":"SWR","swr_path":"..."}}})
IAM_TOKEN=<IAM_TOKEN> python scripts/create_infer_service.py create \
    --endpoint https://modelarts.cn-north-4.myhuaweicloud.com \
    --project-id <PROJECT_ID> \
    --workspace-id <WORKSPACE_ID> \
    --service-name qwen3-8b \
    --chip-model a5 \
    --pool-id <POOL_ID> \
    --model-obs-path obs://<bucket>/<prefix>/model/<模型名> \
    --code-obs-path obs://<bucket>/<prefix>/code \
    --role "name=role-1,replicas=1" \
    --role-extra-json '{"role-1": {"flavor": "modelarts.vm.arm.24u.192g.npu.1snt9e", "image": {"source": "SWR", "swr_path": "swr.xxx/vllm-ascend:tag"}}}'
# 或 --raw-json '{"name": "...", "type": "REAL_TIME", ...}'  # 完整平铺请求体见 reference(脚本自动补 host_cache/A5 字段)
```

## 14. 配套生命周期管理

| 操作 | 命令 | 说明 |
|------|------|------|
| 扩缩容 | `IAM_TOKEN=<IAM_TOKEN> python scripts/create_infer_service.py scale --service-id <ID> --deployment-id <DID> --replicas 2` | 调整部署副本数(token 用环境变量或 `--token-file`,禁止命令行明文) |
| 更新配置 | 新版 API(UpdateService/重新部署) | 按需参考官方 API |
| 资源释放 | **不自动操作** | 资源不足(8118)/服务名占用(8006)时,禁止 skill 自动 stop 或 DELETE 任何服务——查可用卡数 + 占用清单告知用户,由用户自行在控制台停止,或明确指示 skill 停止指定 service_id(见 6/7 节) |

## 15. 拉取 Quay.io 镜像并推送 SWR(分支 B-1 完整命令参考)

> SKILL.md 2.2 节只保留要点速览,完整命令示例与本节降级处理在此承载。

```bash
# 1. 拉取 ARM64 架构镜像(以模型文档确认的 tag 为准,示例为 0.23.0;模型专用镜像拉专用 tag)
#    必须带 --platform linux/arm64,昇腾 NPU 节点为 ARM64 架构,拉到 x86 镜像会 exec format error
docker pull --platform linux/arm64 quay.io/ascend/vllm-ascend:v0.23.0

# 2. 校验镜像架构必须为 arm64(强制,失败需重新拉取)
docker inspect quay.io/ascend/vllm-ascend:v0.23.0 | grep -i architecture
#    预期输出: "Architecture": "arm64"
#    若输出 "amd64"/"x86_64" 等非 arm64 架构,删镜像重拉并复查 --platform 参数

# 3. 登录 SWR(使用 SWR 控制台"操作指南"的登录指令,形如)
#    密码经 stdin 注入(不进命令行 argv,不暴露于 ps/proc/history)
export SWR_PASSWORD="<登录密钥>"
docker login -u cn-north-4@<AK> --password-stdin swr.cn-north-4.myhuaweicloud.com

# 4. 打 tag: <region 域名>/<组织>/<镜像名>:<tag>
docker tag quay.io/ascend/vllm-ascend:v0.23.0 \
  swr.cn-north-4.myhuaweicloud.com/<org>/vllm-ascend:v0.23.0

# 5. 推送(同样带 --platform linux/arm64,确保推送的目标镜像架构正确)
docker push --platform linux/arm64 swr.cn-north-4.myhuaweicloud.com/<org>/vllm-ascend:v0.23.0
```

### `--platform` 报错处理(强制,出现报错时按此降级)

若 `docker pull --platform linux/arm64` 报 `unknown flag: --platform` 或 `"--platform" is only supported on a Docker daemon with experimental features enabled`,原因使用的 Docker 版本较旧,或 Docker 守护进程(Daemon)未开启实验特性(Experimental features)。按以下步骤开启后重试:

a. 打开或创建 `/etc/docker/daemon.json` 文件;
b. 添加实验特性配置,在 JSON 文件中加入 `"experimental": true`:
   ```json
   {
     "experimental": true
   }
   ```
c. 执行 `sudo systemctl daemon-reload` 重新加载 systemd 配置;
d. 执行 `sudo systemctl restart docker` 重启 Docker 守护进程;
e. 重启后用 `docker version` 确认 `Server` 段 `Experimental` 字段为 `true`,再重试 `docker pull --platform linux/arm64`。

若重启后仍报错,改用 `docker pull` 不带 `--platform`(默认拉取宿主机同架构镜像,ARM64 宿主机拉到的即为 arm64 镜像),拉取完成后**必须**用 `docker inspect <image> | grep -i architecture` 校验为 `arm64` 后再推送。

- 镜像体积大、Quay.io 拉取慢时可配置代理或国内镜像加速(见 `references/troubleshooting.md` "拉取镜像失败");可用 `docker image inspect <image> | grep -i vllm` 核对镜像内 vllm-ascend 版本与文档一致
- 完成后按 SKILL.md 2.1 分支 B-1 要求将完整地址(`swr.<region>.myhuaweicloud.com/<org>/vllm-ascend:<tag>`)提供给 skill 记录
