---
name: huawei-cloud-modelarts-vllm-ascend-model-deploy
description: "指导在华为云 ModelArts 推理平台通过 vLLM-Ascend 推理框架部署开源大语言模型(GLM/Qwen/DeepSeek/Llama 等)为昇腾 NPU 在线推理服务的完整流程。覆盖:确认模型后按 vllm-ascend 社区文档与用户确认部署形式(单节点/多节点/PD分离/PD共置 4 种形式,统一单部署单元承载),从 HuggingFace/ModelScope 下载模型权重并上传 OBS、从 Quay.io 拉取 vllm-ascend 镜像并推送 SWR、按确认的部署形式选用专用脚本模板(单节点/多节点/PD/PD共置 四套,脚本内不做部署形式运行时分支)生成启动/探针/角色识别脚本并上传 OBS、按 ModelArts 平台适配要点(端口 8080、OBS 挂载、bash 数组、探针命令检查、超节点亲和组)通过新版在线服务部署(二选一: 方式A 调用 CreateInferService API(POST /v2/{project_id}/services)自动部署 / 方式B 在 ModelArts 控制台按一步步点击指导手动部署;不再创建 AI 应用——该模块已废弃)、通过 OpenAI 兼容 API 调用验证。Triggers include: \"ModelArts 部署大模型/开源模型\", \"vllm-ascend\", \"昇腾 NPU 推理\", \"HuggingFace/ModelScope 模型上云\", \"OBS/SWR 镜像迁移\", \"大模型在线服务\", \"多机部署\", \"多副本部署\", \"PD 分离部署\", \"PD 共置部署\", \"超节点亲和组\", \"新版在线服务\", \"CreateInferService\", \"控制台手动部署在线服务\"。当用户提到以上任一场景时都应使用本技能,即使没有明确说出'部署'二字。"
tags: [huawei-cloud, modelarts, vllm-ascend, npu-inference, llm-deploy]
version: 1.0.0
---

# ModelArts vLLM-Ascend 开源大模型部署

## 概述

通过 vLLM-Ascend 推理框架结合 ModelArts 推理平台的在线服务部署能力,将 HuggingFace、ModelScope 等开源社区的大语言模型(GLM、Qwen、DeepSeek、Llama 等)快速部署到昇腾 NPU 环境,提供 OpenAI 兼容的 RESTful API。本 skill 覆盖全流程: 模型确认与部署形式决策(4 种形式: 单节点/多节点/PD 分离/PD 共置,统一单部署单元)→ 权重/镜像准备 → 启动与探针脚本生成 → 新版在线服务部署(API 自动 / 控制台手动)→ OpenAI 兼容调用验证,并内置 ModelArts 平台适配要点(端口 8080、OBS 挂载、超节点亲和组、PD 分离、节点角色经 get_master_ip.py 自动判定)与安全编码规范(URL 白名单 + 用户输入校验)。

> **重要声明**: 本部署方案基于 vLLM-Ascend 开源社区提供的模型与镜像,仅适用于功能验证、原型测试等场景。生产环境的高可用、安全合规、可观测性及运维管控要求,请勿直接将本方案用于业务生产。模型能力与性能取决于开源社区。

## 核心流程总览

**步骤 1 模型权重准备** — 确认部署模型 → 查模型文档 → 与用户确认部署形式(4 种形式 + 节点数 + 副本取舍)→ 确认权重就绪 → OBS
**步骤 2 部署镜像准备** — 按模型文档+部署形式定版本/tag → 确认 SWR 就绪状态(已就绪: 记录地址 / 未就绪: 自行或代下载)→ 记录地址
**步骤 3 脚本准备** — 按确认的部署形式选用专用模板,填充模型文档参数 → 生成 `start_vllm.sh` / `health_check.sh` → **产物自检关卡(可用性硬性 + 性能软性,对照华为云最佳实践 + vllm-ascend 文档)** → OBS SDK 上传
**步骤 4 新版在线部署** — 二选一: 方式A API 自动(`create_infer_service.py` 调 CreateInferService)/ 方式B 控制台手动(9 步点击指导)—— 直接以 SWR 镜像 + OBS 挂载部署,不再创建 AI 应用(该模块已在平台废弃)
**步骤 5 验证服务就绪与获取调用端点** — 查询服务状态/调用端点 → 确认 RUNNING
**步骤 6 调用验证** — OpenAI 兼容 API 调用 `/v1/chat/completions`

> **安全编码规范(强制,所有工具调用必须遵守)**: 本 skill 涉及 curl/脚本/API 等多处工具调用,**任何传给工具的参数在拼接进命令前必须校验**,防止恶意输入被利用(对应安全扫描 TM1 工具参数滥用):
> 1. **URL 白名单校验(强制)**: 任何 curl/HTTP 请求的目标 URL,**主机名必须在白名单内**才允许执行——白名单: `docs.vllm.ai`、`quay.io`、`huggingface.co`、`modelscope.cn`、`*.myhuaweicloud.com`(iam/obs/modelarts/swr 等华为云域名)、`127.0.0.1`/`localhost`(本地探活)。**不在白名单的 URL 一律拒绝执行**,改用 AskUserQuestion 请用户确认目标地址。模型文档/镜像地址等用户提供的 URL 必须校验 host 后使用,禁止直接拼进 curl/命令。
> 2. **用户输入校验(强制)**: 模型名、OBS 路径、SWR 地址、服务名、workspace-id 等用户提供的输入,拼接进命令/请求体前必须先做**格式校验**(正则/白名单枚举,如服务名仅小写字母/数字/连字符、OBS 路径以 `obs://` 开头、SWR 地址形如 `swr.<region>.myhuaweicloud.com/<org>/<name>:<tag>`),**类型与格式不符的非法输入直接拒绝**,用 AskUserQuestion 让用户重新提供,禁止带病执行。**禁止静默修改用户输入**(如服务名含大写时擅自转小写提交、OBS 路径多/少末尾斜杠时擅自增删)——检测到非法输入时必须 AskUserQuestion 披露"输入含非法字符 X,建议改为 Y"让用户确认修正或重新提供,不得在未告知用户的情况下自行修改后提交。
> 3. **禁止未校验拼接**: 禁止将用户输入直接拼进 shell 命令/JSON 请求体(如把 URL 拼进 `curl <url>`、把模型名拼进脚本参数)。脚本侧的参数校验参考 `scripts/create_infer_service.py`/`scripts/upload_code_to_obs.py` 的现有实现(非法参数 `sys.exit` 拒绝)。
> 4. **临时文件一律写入 `/tmp`(强制,不得污染 skill 本体)**: 运行本 skill 过程中产生的**任何临时文件**(含 token 的内联 Python 脚本、临时 JSON 请求体、临时日志/报告、调试脚本等)**必须写入 `/tmp/` 目录**(如 `/tmp/get_token_<随机后缀>.py`),**禁止写入 skill 本体目录**(`scripts/`/`templates/`/`references/` 及 skill 根目录)或部署产物目录以外的位置——临时文件不得影响 skill 原有的目录结构与功能,运行结束后可保留于 /tmp 由系统清理,无需回写 skill 目录。
> **关键原则(镜像与脚本的共同前提)**: 步骤 2(镜像)与步骤 3(脚本)都必须**先根据用户确认的模型,在 vllm-ascend 模型适配文档(`https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/`)中定位该模型页面**,从页面提取镜像版本/tag 要求、启动命令示例与**支持的部署形式**(单节点 / 多节点 / PD 分离),再据此拉镜像、写脚本。禁止脱离模型文档凭经验猜 tag、猜部署形式或套用通用命令。
> **产物生成前置校验(强制,违反=产物作废)**: 生成任何部署产物(`start_vllm.sh` / `health_check.sh` / `probe.sh` / `DEPLOY_GUIDE.md` / 部署指导文本 / API 请求体)前,**必须重新 Read/grep 本 SKILL.md 对应章节 + `templates/` 下实际模板文件,以磁盘当前内容为准**。所有确定性取值(健康检查失败次数、启动延迟、端口、探针脚本文件名、挂载路径、`TP_SIZE` 推导规则、镜像 tag、环境变量清单)**必须来自本 skill 文件或模型适配文档**——**禁止凭经验/记忆/常识填写**(例如健康检查失败次数是 skill 规定的 300 而非 K8s 默认 3;探针脚本是 `health_check.sh` 而非旧的 `probe.sh`)。若产物中的任何数值/文件名/取值与 skill 当前文件不一致,该产物无效,必须按 skill 实际内容重写。**本 skill 文件可能被外部更新**(SKILL.md/模板/references 的时间戳会变),每次生成前必须核对当前文件,不得假设内容与上次会话一致。
> **API 部署前置校验(强制)**: 调用 CreateInferService 创建服务前,必须逐项核对以下规则,违反=请求必然失败:
> 0. **必须经 `create_infer_service.py` 提交(强制)**: 创建请求必须用 `scripts/create_infer_service.py create`(骨架或 `--raw-json`)提交——该脚本的 `validate_request_body()` 在本地拦截必填字段缺失(含 `flavor`/`cmd`/`image.swr_path`/探针/`service_invoke` 三项/`deploy_timeout_minutes=300` 等)。**禁止手写临时脚本绕开脚本直接 POST `/v2/{project_id}/services`**(会跳过 `validate_request_body()`,必填字段缺失只能靠平台 400 报错回填,如 `8003 Cannot find a specific flavor`)。确需自定义请求体时,用 `--raw-json` 传入仍走校验;`--raw-json` 缺失必填字段同样被 `validate_request_body()` 拦截。
> 1. **请求体是顶层平铺结构**(`name`/`type`/`group_configs[]`/`runtime_config` 直接放顶层)——**禁止用 `service.deployment.roles[]` 包裹**(旧骨架报 400 `name/type/group_configs/runtime_config` 缺失)
> 1.5. **`unit_configs[].flavor` 必填(强制)**: 每个推理单元必须显式携带 `flavor`(值从 ShowInferServiceCluster `flavors[]` 按 `ascend.npu` 取 id,见步骤 0 第 ⑦ 条);字段缺失或值为空报 `400 ModelArts.8003 Cannot find a specific flavor`(非格式错误);误填不存在的 id 报 `6404 Flavor not found`
> 2. **`group_configs[].secret_type: "agency"`**(OBS 挂载委托认证)——`dew`/`obspool`/`obs` 报 `ModelArts.8162/8163`;此字段易在修改请求体时被覆盖丢失(修正端口/其他字段后必须复查)
> 3. **`runtime_config.service_invoke.port` 必须与启动脚本 `PORT` 一致(8080)**——否则探针探测端口错位
> 4. **PD 双角色 `unit_configs[].envs` 必须显式设不同 `PORT`**(如 Decode `PORT: "7101"`)+ `VLLM_ROLE`
> 5. **健康检查参数**: `failure_threshold=300`/`initial_delay_seconds=300`/`period_seconds=60`(`failure_threshold=30` 窗口不足,vLLM V1 首启 10~20 分钟触发 Unhealthy)
> 6. **`runtime_config.service_limit` 必填三项**: `request_timeout=300`(秒,平台默认 30s 会掐断慢速推理请求,报 `ModelArts.8909 request timeout: 30s`——PD 分离首请求需 prefill+decode 协作、大模型首请求含权重加载/CUDAGraph 编译,>30s 必触发)、`request_size_limit=20`、`rate_limit`(如 `{"num": 200, "unit": "SECONDS"}`);**`group_configs[].weight`(100)必填**
> 7. **token 获取**: 用户提供的 token 可能复制截断(含 `-`/不以 `==` 结尾 → `401 decrypt token fail`);推荐 IAM API 获取 + **Python 正则完整提取**(`re.search(r'(?i)^X-Subject-Token:\s*(\S+)', content, re.M)`,禁 shell 管道 `grep|sed|tr`,长 token 会丢字符)
> 8. **workspace 传参方式按请求类型区分(强制,POST 与 GET 不同,违反=创建报 8179)**: **GET 查询接口**(list/show/资源池/节点等)必须带 `X-Workspace-Id` 头(不带则查不到对应工作空间的服务(list 返回其他工作空间或空),导致误判"无同名服务"而创建失败(8006/8118))+ URL 双查询参数。**⚠️ ModelArts 各 GET 接口的 `X-Workspace-Id` 头不起过滤作用**,且各微服务对 workspace 参数命名未统一(驼峰 `workspaceId` / 下划线 `workspace_id`)——**除工作空间列表接口 `GET /v1/{project_id}/workspaces`(全局查询,用于获取 WORKSPACE_ID 本身,不携带 workspace 查询参数、不带 `X-Workspace-Id` 头,仅带 `Authorization: Bearer <token>`)外,所有 GET 接口(list/show/资源池等)统一在 URL 上携带 `?workspaceId={WORKSPACE_ID}&workspace_id={WORKSPACE_ID}` 双查询参数**,同时保留 `X-Workspace-Id` 头;`create_infer_service.py` 的 `cmd_list`/`cmd_show` 已用 `append_workspace_query()` 函数拼接双查询参数,其他脚本/手动调用 GET 接口时须加 `?workspaceId={}&workspace_id={}` 双查询参数。**POST 创建请求(CreateInferService)的 `workspace_id` 放在请求 body 顶层字段**(与 `name`/`type` 同级)——**不是请求头、也不是 URL 查询参数**: 实测仅带 `X-Workspace-Id` 头而不在 body 放 `workspace_id`,报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`(资源池实际存在且 X-Infer 已启用);body 顶层补 `workspace_id` 后创建成功。`create_infer_service.py create` 已自动注入该字段(骨架与 `--raw-json` 路径均补齐,`validate_request_body()` 校验缺失)
> 9. **不确定请求体结构时**: 查询已部署成功的现有服务(`show` 返回 `version.instance_groups[].unit_configs[]` 即完整参考),对照构造,不凭空猜
> 10. **部署超时时间统一 300 分钟(强制)**: CreateInferService 请求体顶层必须显式设置 **`deploy_timeout_minutes: 300`**(单位分钟),控制台部署时"部署超时时间"填 **300 分钟**。**禁止使用平台默认(20~60 分钟)**——多节点/大模型(如 GLM-5.2 MoE)首次启动含模型加载 + CUDAGraph 编译,60 分钟仍不足以 RUNNING,会触发部署超时失败(`status: FAILED`,详情 `deploy_timeout_minutes: 60`)。字段在请求体顶层(与 `name`/`type` 同级);构造请求体后复查该字段未被覆盖丢失。
> **部署形式须与用户确认(本技能新增决策点)**: 确认模型后,必须先从模型文档/社区明确该模型采用**单节点部署、多节点部署还是 PD 分离部署**(步骤 1.1),**整理推荐形式与依据,与用户确认后再进入**镜像与脚本准备。不同部署形式下,启动脚本结构(单机 TP / 多机 Ray 分布式 / PD 分离双角色)、健康检查策略(PD 区分 prefill/decode)、ModelArts 部署配置(节点数/实例数/网络)差异显著,先定形式才能针对性适配。
> **部署形式是计划期决策,不是运行时决策(强制)**: 部署形式经用户确认后即**固定为方案输入**,生成的启动/健康检查脚本是**该形式的专用产物**——脚本内**不再通过 `DEPLOY_FORM` 环境变量做运行时分支**。步骤 3 按确认的形式直接从 `templates/` 选用对应模板(单节点/多节点/PD/PD+多节点四套),填充模型文档参数后在本地产物目录保存为 `start_vllm.sh`/`health_check.sh` 上传。ModelArts 部署时**无需也不应**再传 `DEPLOY_FORM` 环境变量(PD 的 `VLLM_ROLE`、多节点的 `NODE_RANK`/`MASTER_ADDR` 等是形式内部的实例属性,由部署单元注入,不受此限制)。
> **⚠️ 官方文档不可达时的强制降级与纠错机制**: 若 `docs.vllm.ai` 网络不可达,严禁改用论坛帖/博客/搜索摘要作为 tag 依据(这些是二手信息,版本常与模型文档不一致)。**先排查是否为 TLS 证书问题,再走降级**。正确做法按优先级:
> 0. **使用 curl 访问第三方服务时的安全约定**: 企业/云上环境常经安全代理(如 netentsec)转发公网请求,代理对目标站点做 TLS 中间人(MITM)证书替换,返回自签名/未知 CA 证书,默认校验失败报 `SSL certificate problem`。**执行前必须先校验目标 URL 主机名在白名单内**(docs.vllm.ai / quay.io / huggingface.co / modelscope.cn / *.myhuaweicloud.com / 127.0.0.1),**不在白名单的 URL 直接拒绝执行并请用户确认**;白名单校验通过后方可执行,必须携带 `-k`(或 `--insecure`)跳过代理 MITM 证书。校验逻辑: 定义 ALLOWED 白名单 → 提取目标 host → `grep -qw` 匹配白名单 → 不匹配则 `exit 1` 拒绝 → 匹配则放行执行。注意: `-k` 仅跳过证书校验,`-k` 后仍返回 000/超时才是真拦截;`-k` 后能拿到 200/302 即说明只是证书问题。内部/本地探活(如 `127.0.0.1` 健康检查)不使用 `-k`;
> 1. **先验证是否证书问题**: 按上述白名单校验通过后,执行 `curl -sk -o /dev/null -w "%{http_code}" --max-time 15` 探测目标(如 docs.vllm.ai 在白名单内),返回 200/302 → 加 `-k` 继续查文档,不降级;
> 2. **加 `-k` 仍不可达(代理真拦截/网络不通)**: 请求用户提供官方文档链接或页面内容(用户通常可访问,或给出如 `https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/<Model>.html` 的直达 URL);
> 3. **向用户明确披露**: "官方文档不可达,当前 tag 依据为 XX,存在不确定性,请协助确认"——不得在未披露的情况下按猜测推进;
> 4. 收到官方文档确认后,**无条件改用官方 tag**,并同步修正启动脚本与已上传 OBS 的产物(覆盖上传)。
> 任何情况下,模型页面明确标注的 `docker pull quay.io/ascend/vllm-ascend:<tag>` 就是最终依据;带芯片变体的 tag(如 `-a3`/`-310p`)按目标芯片选择,不带后缀的通用 tag 默认对应 A2(910B)。

## 何时使用本技能

- 用户要把 HuggingFace / ModelScope 上的开源 LLM 部署到华为云 ModelArts(昇腾 910B NPU 推理);要制作大模型推理镜像、推送 SWR、调用新版推理 API 部署在线服务;要配置 OBS 权重挂载与启动脚本;要用 OpenAI 兼容接口验证已部署服务;要判断部署形式(单节点/多节点/PD 分离)或做多机分布式 / Prefill-Decode 分离部署

## KooCLI 命令格式标准

本 skill 的核心部署操作(镜像推送、OBS 上传、调用 CreateInferService)默认使用 Python 脚本(`scripts/`)与 curl,以支持完整 JSON 请求体与安全 token 传递。若用户环境已配置 KooCLI(hcloud)并希望用 CLI 方式执行同等操作,命令格式遵循华为云 CLI 标准(安装参考 `references/cli-installation-guide.md`)。

```
hcloud <Service> <Operation> --cli-region={region} [--key=value]
```

- **服务名**: 大写 PascalCase,如 `ModelArts`
- **操作名**: 大写 PascalCase,如 `CreateInferService`
- **`--cli-region` 必带**: 指定区域,如 `--cli-region=cn-north-4`,必须与资源池所在区域一致

示例(创建在线服务,需先 `hcloud configure` 配置 AK/SK 或用 `--cli-auth-token`):
```bash
hcloud ModelArts CreateInferService --cli-region=cn-north-4 \
    --project_id=<PROJECT_ID> --body='{"name":"...","type":"REAL_TIME",...}'
```
> **注意**: KooCLI 为可选替代方式;`--cli-region` 是 CLI 命令的必带参数。请求体字段与 Python 脚本 `scripts/create_infer_service.py --raw-json` 完全一致(顶层平铺结构),token 敏感凭据仍按"安全编码规范"处理。若 hcloud 命令执行报参数错误,回退到本 skill 的 Python 脚本方式(见步骤 4.3)。
## 约束限制(先向用户确认)
1. **模型支持列表**: 目标模型必须在 vllm-ascend 官方支持列表(模型列表)中,否则需要用户自行验证适配。不要承诺未验证模型一定能跑通。
2. **模糊模型名必须列全候选(强制)**: 用户输入的模型名若是系列名/模糊描述(如 `GLM5.3`、`Qwen`、`DeepSeek`)而非精确模型 ID,必须先抓取 vllm-ascend 模型索引页检索**全部**相关模型页面,整理完整候选清单(权重版本/硬件要求/镜像 tag/部署形式/下载来源)展示给用户,**由用户确认选择**,**禁止 skill 自行替用户决策使用哪个模型**(见步骤 1.0)。精确模型 ID 或用户明确授权"按你推荐的选"时方可省略候选清单。
3. **部署形式(新增关键决策)**: 确认模型后必须先按 vllm-ascend 模型适配文档明确部署形式——**单节点部署 / 多节点部署 / PD 分离部署**,**并与用户确认**(见步骤 1.1)。判断依据是模型适配文档(部署章节是否给出多机/PD 示例、示例 TP 卡数是否超过单节点卡数)与模型规模对硬件的要求。**部署形式一旦确认即固定为方案输入,脚本按形式生成专用版本,不再通过 `DEPLOY_FORM` 环境变量在脚本内做运行时分支**。不要默认所有模型都单节点部署,也不要在文档未支持时强行套用多机/PD 参数。
4. **网络互通**: **多节点部署与 PD 分离部署必须确保节点间网络互通**,HCCL 通信(多机 TP/DP)与 PD 场景的 KV Cache 传输均依赖节点间网络;ModelArts 需确认资源池支持多机/分布式(如 RDMA/安全组放通)。
5. **区域/资源池**: 需确认用户账号所在区域是否有昇腾 NPU 专属资源池,且资源池能否提供多节点(多机)资源——部分资源池只有单机规格,会直接限制部署形式只能单节点。
6. **芯片型号与资源规格(关键)**: 必须确认目标资源池的**芯片型号**(910B 系列 / 910C(A3) / 310P / 950 系列等)与**卡数**——同一模型在不同芯片/卡数下启动参数可能不同(适配文档常按芯片给不同示例);芯片变体显存不同(910B3 64GB / 910B4 32GB 推理版),直接影响模型选型、TP_SIZE 与"单节点能否放下";310P 为推理卡,只能跑 7B 以下小模型,大模型直接报错。确认方法: 先向用户问清芯片型号/卡数,再查阅 vllm-ascend 对应芯片的适配文档。
   
   > **⚠️ 950 系列必须细分到 950DT/950PR(强制,违反=启动参数错配)**: 用户答"A5"或"950 系列"时,**禁止合并为单一选项,必须进一步细分确认是 950DT 还是 950PR**——两者虽共用 `qwen3.8-a5` 镜像 tag,但**单卡显存不同(950DT 96GB / 950PR 128GB)、模型文档启动示例参数可能不同**(如 Qwen3.8-27B: 950DT 示例 `--max-model-len 131072`+`--gpu-memory-utilization 0.85`,950PR 示例 `--max-model-len 256000`+`--gpu-memory-utilization 0.9`;950DT 文档示例用 w8a8-mxfp8 权重、950PR 推荐 w8a8),**同一模型在 950DT/950PR 的适配文档示例参数值不同,脚本必须按用户确认的具体型号提取参数**。具体差异与确认口径见 `references/ascend-hardware-matrix.md` 第一节 950 系列表。
7. **版本配套**: 镜像中 CANN / torch_npu / vllm-ascend 版本必须按官方配套表整行匹配,与资源池昇腾驱动版本兼容。
8. **生产免责**: 方案仅适用于功能验证、原型测试,不适用于生产商用。
## 前置条件核对清单
开始前逐项与用户确认,缺失则提示补齐:
| 项 | 说明 | 确认方式 |
|----|------|----------|
| 华为云账号 | 已开通 ModelArts、OBS、SWR 服务并完成实名认证;提供 **OBS AK/SK 与 Endpoint**(或临时委托凭据)供 OBS SDK 上传 | 用户确认 |
| OBS 桶 | 存储模型权重、启动脚本、健康检查脚本;建议同区域 | 用户提供桶名与区域 |
| SWR 镜像仓库 | 存放 vllm-ascend 推理镜像 | 用户提供组织名 |
| 昇腾 NPU 资源池 | ModelArts 专属资源池;需确认**芯片型号**(910B 系列/910C(A3)/310P/**950 系列需细分 950DT/950PR**)、**节点卡数**与**推理实例卡数**(flavor 字段,见步骤 0 第 ④ 条),以及资源池是否支持**多节点(多机)规格**(决定部署形式上限) | 用户提供资源池 ID(UUID 格式)/芯片型号(**950 系列须细分 950DT 或 950PR**)/卡数/多机能力 |
| **ModelArts 域名/环境** | **调用 ModelArts API 前必须确认环境域名**: 统一为 `modelarts.<region>.myhuaweicloud.com`(不存在 dev 域名,支持用户自行输入其他生产域名,域名须与资源池同区域);后续步骤 4 所有 API 调用(查工作空间/查资源池/创建服务)必须用确认后的域名 | 用户确认(区域与资源池一致) |
| **工作空间名** | 资源池/服务所属的 ModelArts 工作空间(如 `default` / `test`);**必须先确认工作空间名,再通过 API 查其 workspace-id**(`GET /v1/{project_id}/workspaces`),后续 API 调用带 `X-Workspace-Id` 头 | 用户确认工作空间名 + API 查询 workspace-id |
| 部署形式 + 节点数 | 4 种部署形式(single 单节点 / multinode 多节点 / pd PD 分离 / pd_colocate PD 共置)+ 用户可用节点数 ≥ 最小节点数(见步骤 1.1b;pd 分离资源翻倍),确认后固定为方案输入,脚本按形式专用生成,不做运行时分支 | 模型文档核对 + 用户确认 |
| 模型权重来源 | HuggingFace 或 ModelScope 上的模型 ID;需结合 vllm-ascend 适配文档确认**权重格式**(如 BF16/W8A8)与下载来源 | 用户提供模型名 + 适配文档核对 |
| 网络 | 本地可访问 Quay.io / HuggingFace / ModelScope(必要时配代理或镜像站);**curl 访问第三方服务前先按"安全编码规范"校验目标 URL 主机在白名单内,再加 `-k` 跳过证书校验**(企业代理 MITM 常见,见"关键原则") | 实际执行验证 |
| 工具 | **OBS Python SDK(`esdk-obs-python`,上传部署产物必需)**、obsutil(可选,上传权重)、SWR 登录凭据、docker | 本机环境 |

## 交互式确认规范(强制,所有用户确认点必须遵守)

> **核心原则**: 流程中**所有**需要用户确认、选择、提供信息的决策点,一律通过 **AskUserQuestion 交互式组件**完成(文本输入 / 枚举选择 / 流程走向)。**禁止**用纯文本输出"请提供 X"/"请确认 X"后静默结束回合等待用户回复。
> **用法要求**:
> 1. **枚举/选择类**: 候选直接作为 `options` 展示(如模型候选清单逐条列为 option),每个 option 带简短 description。
> 2. **文本输入类**: 每个 question 至少 2 个 options——提供常见默认值/推荐值作为 option,或在 **question 文本中写明所需信息格式**(如"OBS 权重路径,格式 obs://bucket/prefix/model/<模型名>"),用户通过 Other/notes 补充。文本类信息一次最多 4 个 question(工具上限),超过则分批。
> 3. **合并提问**: 相互独立的确认项合并到同一次 AskUserQuestion(最多 4 个 question);前一步输出(如候选清单表格)后必须紧跟一次交互式询问,不得"输出清单后静默等待"。
> 4. **敏感凭据禁止明文进 notes(强制)**: 涉及 OBS AK/SK、IAM 用户名/密码、token 等敏感凭据的 question,**问题文本必须写明**:"⚠️ 凭据敏感,请通过环境变量/本地文件方式提供,或选 Other 后告知已设置,不要直接粘贴明文到 notes";若用户仍粘贴明文,提示"已检测到明文凭据,建议本次操作完成后在控制台轮换"。**定时轮询/后台任务的 prompt 字段禁止包含凭据明文**(凭据从环境变量或 600 权限文件读取,每次执行现取)。
> **各步骤交互式确认点速查**(均须用 AskUserQuestion): 1.0 模型确认(**硬性 gate,无论精确 ID 还是系列名都必须 AskUserQuestion 确认;模糊名列全候选;实验性模型二次确认**)/ 1.1a 部署形式(4 选 1: single/multinode/pd/pd_colocate)/ 1.1b **可用节点数** / 1.1c 副本取舍(单副本多实例 vs 多副本单实例,PD 分离资源翻倍)/ 1.2 权重是否已下载 + OBS 权重路径 / 2.1 SWR 镜像就绪状态 + 地址 / 2.4 SWR 组织名 + docker login 命令 / 3.0 芯片型号(**950 系列须细分 950DT/950PR**)+ **TP 大小(TP 候选只列合法值)** / 3.4 OBS AK/SK/Endpoint + **code 目录(默认路径展示 + 自定义路径,强制确认后才可上传)** / 4.0 ModelArts 域名·工作空间·区域 / 4.1 部署方式 A/B / 4.3 IAM 域名·凭据或 token 获取方式(**账号密码方式额外确认 project_name**)/ 4.2 末 是否 API 代为部署 / 6 调用 URL·token。

## 步骤 1: 模型权重准备

### 1.0 确认要部署的模型(先查文档,再与用户确认;模糊模型名必须列全候选,禁止自行决策)

> **为什么下载前必须先确认模型?** 用户提示词中的模型名可能是系列名(如"GLM"、"Qwen")而非精确模型 ID;同一系列在 vllm-ascend 适配文档中可能有**多个模型页面与变体**(参数量/量化版本/权重格式不同),直接按猜测下载极易下错。
> **⚠️ 模型确认是硬性 gate(核心约束,违反=流程作废)**: **无论用户提示词中的模型名看起来多精确,进入 1.1 部署形式确认前,必须至少完成一次 AskUserQuestion 模型确认**——本 skill 所有模型决策(权重版本/镜像 tag/部署形式/启动参数)都以"用户确认的那个模型"为唯一输入,确认缺失会导致后续全部步骤建立在未经用户同意的假设上。**禁止出现以下错误**: ① 因索引页存在与提示词同名的页面(精确匹配)就认为"模型已确认",跳过 AskUserQuestion 直接抓文档/问硬件;② 用"该模型只有唯一候选"等主观理由替用户决策;③ 先问硬件/资源/部署形式等下游信息,再回头补模型确认(顺序颠倒)。**正确做法**: 用户输入模型名后,**第一件事**就是抓取 vllm-ascend 文档模型索引页(按上方"安全编码规范"白名单校验后执行(curl 访问前先校验 URL 主机名在白名单内,见关键原则第 0 条)),**凡是输入名命中索引页(精确匹配)或属于某系列(系列名),都按第 1~2 步检索出全部相关候选页面**,整理完整候选清单(表格: 候选模型 | 权重版本 | 硬件要求 | 镜像 tag | 部署形式)并用 AskUserQuestion 请用户确认。**任何情况下不得跳过候选清单**: ① 用户提示词已给出精确模型 ID 且**经 AskUserQuestion 复述确认**——此时候选清单可只含该一个模型,但仍须确认;② 用户明确授权"就按你推荐的选"——此时可省略候选选择,但仍须用 AskUserQuestion 披露所选模型并取得同意。**确认前不进入任何后续步骤(包括但不限于: 查硬件、问节点数、查镜像、写脚本)**。

1. **解析用户提示词,判定精确度**: **精确模型 ID**(如 `Qwen2.5-7B-Instruct`)→ 记录为唯一候选,仍须进入第 4 步复述确认; **模糊模型名/系列名** → 记录为候选集,**必须进入第 2 步检索全部相关模型页面**(禁止只取第一个匹配)。
2. **检索文档中的全部相关模型页面(模糊名必做)**: 按系列名/关键词(如 `glm`/`qwen`/`deepseek`)大小写不敏感过滤索引页,找出**所有**匹配页面;对每个页面提取: 权重版本、硬件要求(节点数/芯片/卡数)、镜像 tag、部署形式、下载来源(HF/ModelScope);整理成**完整候选清单**(表格: 候选模型 | 权重版本 | 硬件要求 | 镜像 tag | 部署形式),**必须包含全部匹配项**。索引页不可达时按"关键原则"降级机制处理,不得凭记忆列候选。
   
   > **⚠️ 索引页与单模型页解析方式不同(强制,违反=索引页返回空候选,误判"模型不在支持列表")**:
   > - **索引页(`tutorials/models/index.html`)的模型清单在侧栏导航 `<nav class="md-nav">` 的 `md-nav__link` 中,不在 `<article>` 正文**(实测正文仅 657 字符、0 个模型链接)。**提取候选必须解析导航栏**,链接为**相对路径**(如 `Qwen-VL-Dense.html`,无 `tutorials/models/` 前缀),禁止用 `tutorials/models/<name>.html` 前缀正则匹配(命中 0);正确正则: `<a[^>]+href="([^"]+\.html)"[^>]*class="md-nav__link"[^>]*>\s*<span class="md-ellipsis">(.*?)</span>`,再按系列名大小写不敏感过滤。**导航提取不到时回退全文 grep 索引页,不得静默返回空候选**。
>   - **单模型页(`tutorials/models/<Model>.html`)才按剥离导航栏/只取正文规则处理**: 该页面的**侧边导航栏含全部模型标题**,混有**其他模型**的标注(如 `Qwen3.8-Flash-Next（实验性支持）`、`Hy4-preview (Experimental)`);用 `grep`/正则全文扫描页面时,**导航栏中的其他模型标注会污染本页候选模型的属性提取**。**正确做法**: 抓取页面后用 Python `html.parser`/正则**剥离 `<nav>` 与 `<article>` 之外的导航结构**(或提取 `<article>` 正文区域),**只在正文中检索**关键词/标注;正文中每个 `Experimental`/`实验性` 命中,必须**核对标注归属的模型名与芯片平台**(如"950DT Products 当前为实验性支持"仅限 950DT,A3/A2 为正式支持),**禁止把相邻/导航栏命中的标注归到目标模型**。
>   - **页名与正文模型 ID 可能不一致**: 一个页面常覆盖同系列多个模型(如 `Qwen-VL-Dense.html` 标题为 `Qwen-VL-Dense(Qwen3-VL-8B/32B)`,正文启动命令直接用 `vllm serve Qwen/Qwen3-VL-8B-Instruct`)。**候选清单按导航标题列出,但核对"模型是否在官方支持列表"时,还需检索该页面正文启动命令中实际用到的模型 ID**(`vllm serve <repo-id>`),页名不含某模型不代表该页面不覆盖它,禁止仅凭导航标题断言"模型不在支持列表"。
3. **查模型适配文档的权重说明**: 打开目标模型页面,重点阅读: 权重**格式要求**(BF16 原生 / FP8 需转 BF16 / W8A8 量化)、**下载地址**(HF/ModelScope repo ID)、**推荐量化版本**(W4A16/W8A8)、是否区分芯片型号给出不同权重说明、**⚠️ 镜像版本要求(实验性模型高频坑)**: 页面标注"文档基于 vX.Y.Z"往往**高于**镜像仓最高稳定 tag(如 GLM-5.3-Flash 文档基于 v0.30.0RC,quay.io 稳定版最高 v0.23.0)——**镜像 tag 必须以模型页面 Docker 安装章节为准,并核对镜像内 transformers 是否认识该模型架构**(不识别报 `Transformers does not recognize this architecture`);必要时换团队/内部新版镜像或换稳定版本模型,`docker run` 验证 transformers 版本(见 2.1 镜像类型识别)。**⚠️ 实验性/Experimental 标注的归属判定(强制,正文内核对)**: 只在剥离导航栏后的正文中检索 `Experimental`/`实验性`;命中时核对**该标注紧跟的模型名/芯片平台**——仅当标注**明确指向目标模型**且覆盖目标部署的**芯片平台**时,才按实验性处理;标注属于其他模型、或仅限其他芯片平台(如 950DT 实验性而 A3/A2 正式)时,**不得**触发实验性二次确认。
4. **用 AskUserQuestion 交互式确认最终模型(强制)**:
   - **模糊模型名场景(强制)**: 将**全部候选清单**在对话中完整展示(表格),**随后必须立即用 AskUserQuestion 将每个候选模型列为 option** 让用户点击选择;确认前不进入后续步骤。若同时需确认资源规格,可合并到同一次 AskUserQuestion(≤4 question)。
   - 精确模型 ID → 候选清单可只含该模型,但**必须用 AskUserQuestion 向用户复述确认**后进入 1.1(禁止跳过: "索引页精确匹配"="已确认" 是错误等价,精确 ID 也须过 AskUserQuestion);多个变体 → 各变体逐一列为 option;模型不在支持列表 → 询问是否继续(自行验证 / 换模型)。
   - **⚠️ 实验性(Experimental)模型二次确认(强制,违反=不得进入后续步骤)**: 模型页面正文标注 **Experimental/实验性**(**仅限已按上述归属判定确认该模型 + 目标芯片平台为实验性时**,如 GLM-5.3-Flash 的 950DT 平台),在用户选定后、进入 1.1 前,**必须再用一次 AskUserQuestion 披露并二次确认**——**披露内容**: ① vLLM 社区实验版本,性能优化与可靠性验证仍在进行中;② **不能保证部署成功**(镜像版本不配套/Transformers 不支持新架构/启动参数未验证/运行期异常等);③ 社区通常不建议用于生产。**二次确认 options**: `继续部署(接受实验版本风险)` / `放弃,换稳定版本模型`;选择"继续部署"后方可进入 1.1,并将该确认记入方案(后续失败复盘时引用)。**不得因导航栏其他模型或非目标芯片平台的实验性标注触发二次确认**(见第 2 步剥离导航栏规则)。
   - **禁止**: 输出候选清单表格后不加 AskUserQuestion 直接静默等待用户回复。
5. **记录确认结果**: 将最终模型 ID(**用户确认的那个**)、权重格式、下载来源、适配文档链接记入方案,供后续启动脚本编写使用。

### 1.1 确定部署形式与节点/副本方案(4 形式 × 单部署单元)(关键前置决策)

> **为什么必须先确定部署形式?** 同一模型可由 vllm-ascend 社区以不同形式部署,不同部署形式直接影响后续每一步:镜像 tag、启动脚本结构(单机 TP / 多机 DP / PD 分离双实例 / PD 共置单引擎)、健康检查策略、ModelArts 部署配置(节点数/副本数/超节点亲和组/推理单元)。**先定部署形式,脚本适配才有的放矢**,避免"先写通用脚本、部署时发现形式不匹配返工"。
> **⚠️ 部署形式收敛为 4 种(本 skill 统一约定)**: `single`(单节点)/ `multinode`(多节点)/ `pd`(PD 分离)/ `pd_colocate`(PD 共置)。**统一单部署单元承载**: 单节点/多节点/PD 共置 = 1 个推理单元(`unit_configs` 1 元素);**PD 分离 = 2 个推理单元**(`unit_configs` 2 元素: prefill + decode,同一部署单元内)。**不再考虑多部署单元场景,不再使用 9 场景编号 S1~S9**。副本数(单副本/多副本)由 1.1c 依据用户可用节点数 + 可靠性需求决策,不独立枚举。

**四阶段交互式确认(1.1a~1.1d,每阶段均用 AskUserQuestion)**:

- **1.1a 确认部署形式(4 选 1,强制)**: 先查模型适配文档(`references/deployment-form-decision.md` 第四节线索表),将推荐的部署形式 + 依据(模型页面链接/内容摘要)整理给用户,用 AskUserQuestion 将 4 种形式列为 options(single / multinode / pd(PD 分离)/ pd_colocate(PD 共置)),由用户点击确认。**确认前不进入镜像/脚本准备**。
  - **single(单节点)**: 权重+KV Cache 可放入单机,文档只给单机示例 → `start_vllm.single.sh`
  - **multinode(多节点)**: 模型过大或文档给出多机/DP+TP 示例,示例 TP 卡数 > 单节点卡数 → `start_vllm.multinode.sh`
  - **pd(PD 分离)**: 文档/社区出现 PD、Prefill-Decode、双实例方案 → `start_vllm.pd.sh`(同一部署单元内 prefill + decode 两个推理单元,资源翻倍)
  - **pd_colocate(PD 共置)**: 官方单引擎 DP 形态(ModelArts 最佳实践 glm_5_2.sh 形态),vLLM 引擎内部完成 PD 分工 → `start_vllm.pd_colocate.sh`
- **1.1b 确认可用节点数 M(强制)**: 用 AskUserQuestion 收集**可部署节点总数 M**(文本输入),并在问题中披露**当前模型形态所需最小节点数**(single=1;multinode/pd_colocate=N=ceil(TP_SIZE/单节点卡数);**pd 分离=2×N,资源翻倍**)。若 M < 最小节点数,明确提示"节点不足,该形式不可行",请用户改形式或增加资源。**TP_SIZE 的确认迁移至步骤 3.0**(确认芯片型号后一并确认,见步骤 3.0)。
- **1.1c 副本/实例取舍(强制)**: 依据 M 决策——
  1. **默认优先「单副本多实例」**: `unit_configs[].count` = 该单元所需节点数 N,`group_configs[].count = 1`;
  2. 用户提出**可靠性需求** → 改「多副本单实例」: `group_configs[].count = floor(M / (N × 单元数))`(PD 分离单元数=2,资源翻倍);
  3. 决策后**必须用 AskUserQuestion 复述给用户确认**是否需要调整。
- **1.1d 记录方案**: 记为方案输入 **`DEPLOY_FORM`**(取值 `single` / `multinode` / `pd` / `pd_colocate`)+ `NNODES`(单副本内节点数)+ `REPLICAS`(副本数)+ PD 角色分配(若 pd)。**`DEPLOY_FORM` 仅是方案记录项,不会作为环境变量注入 ModelArts 或写入脚本**——脚本按确认的形式直接生成专用版本(见步骤 3.2)。PD 的 `VLLM_ROLE`、多节点的 master/slave 判定由 ModelArts 部署单元/rank table 注入,不受此限制。

> **完整决策依据与计算规则**: 4 形式对比表、ModelArts 层级概念(部署单元/推理单元/副本数/亲和组)、vllm-ascend 线索判断表、最小节点数计算、副本/实例取舍算法详见 `references/deployment-form-decision.md`——确认前必须按该文件核对。

### 1.2 确认模型权重是否已就绪(不代下载)

> **为什么不直接下载?** 模型权重文件由用户(或其环境)负责获取与放置到 OBS。本 Skill 不代为下载权重,只负责确认权重已就绪并获取其 OBS 路径,避免越权操作与数十 GB 的下载开销。

1. **用 AskUserQuestion 交互式询问是否已下载**目标模型的权重文件(options: 已下载 / 未下载):
   - **已下载** → 进入第 2 步,用 AskUserQuestion 收集权重在 OBS 上的路径
   - **未下载** → 结合 1.0 中查到的适配文档权重说明,向用户提供该模型的**下载地址**(HuggingFace / ModelScope 上的具体 repo ID 链接),并说明权重格式要求(如 BF16 原生 / W8A8 量化)。可参考 `scripts/download_model.py` 的下载命令示例,但**下载动作由用户执行**;告知放置格式后再次用 AskUserQuestion 确认下载进度/路径。
2. **提示用户将权重文件放置到 OBS 指定目录**:
   ```
   obs://{bucket_name}/{path}/model/
   ```
   其中 `{bucket_name}` 为 OBS 桶名,`{path}` 为用户自定义目录前缀(如 `llm/weights`)。权重文件需直接位于该目录或其子目录下(目录结构即模型目录结构,含 config.json 等)。
3. **用 AskUserQuestion 收集 OBS 路径(文本输入)**: 在 question 文本中写明格式要求(如"OBS 权重路径,格式 obs://bucket/prefix/model/<模型名>"),提供引导 option(如"已在 Other 中填写路径" / "选此项后请补充路径"),用户通过 Other/notes 输入实际放置权重的 OBS 路径(如 `obs://my-bucket/llm/weights/model/Qwen2.5-7B-Instruct`),**确认路径存在后再继续**。**禁止**纯文本"请提供 OBS 路径"等待。
4. **记录权重路径到方案**: 后续步骤 4 调用新版推理 API 部署时,模型来源填该 OBS 路径(只读挂载到 `/home/ma-user/model`)。
5. **确定 code 目录位置(部署产物上传目标)**: 部署产物(启动/健康检查/角色识别脚本等)将上传到该模型目录**同级**的 `code` 目录,即 `obs://{bucket}/{path}/code`(除非用户另行提供 code 目录)。记录该目录为方案输入 **`CODE_OBS_PATH`**,供步骤 3.4 上传与步骤 4/5 部署时引用。

> **为什么权重必须放 OBS 而不是本地/镜像?** ModelArts 在线服务部署时从 OBS 只读挂载权重,服务实例销毁重建后权重仍在,且支持多实例共享;镜像只含推理框架,权重与镜像分离是标准做法。

## 步骤 2: 部署镜像准备

### 2.0 先按确认的模型查文档确定镜像版本与 tag(强制前置)

> **为什么拉镜像前必须先查模型文档?** 不同模型适配的 vllm-ascend 版本不同(如 `v0.23.0`、`v0.18.0rc1`),部分模型还有**专用镜像或芯片变体 tag**(如 `-a3-openeuler`、`-310p-openeuler`,甚至 `DeepSeekV4-flash-0731` 模型专用 tag)。盲目拉 `latest` 会导致版本/芯片不匹配而启动失败。**镜像版本/tag 必须以用户确认的模型页面要求为准**。

1. **定位模型页面**: 在 `https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/` 找到步骤 1.0 确认模型的对应页面(URL 形如 `.../tutorials/models/<ModelName>.html`)。**用 curl 访问前先按"安全编码规范"校验 URL 主机名(docs.vllm.ai 在白名单内),再必须加 `-k` 跳过证书校验**(企业代理 MITM,见"关键原则"第 0 条),如 `curl -sk <url>`;用户提供的其他文档链接同样先校验 host 再访问。
   - **若加 `-k` 后仍不可达(代理真拦截,000/超时)**: 不要退化为搜索摘要/论坛帖,按"关键原则"降级机制——**用 AskUserQuestion 请用户提供官方文档链接或页面内容**,并向用户披露不确定性。
2. **从模型页面提取镜像信息**: 记录该模型适配的 **vllm-ascend 版本**(页面顶部标注)、推荐的**镜像 tag** 及芯片变体(910B/910C(A3)/310P 对应 `v0.23.0`(A2)/`v0.23.0-a3`/`v0.23.0-310p`)、是否有**专用镜像**;页面未直接给出 tag 时按"版本 + 芯片型号"在 [vllm-ascend 官方镜像仓库](https://quay.io/repository/ascend/vllm-ascend) tag 列表选取(版本配套原则见约束限制第 5 条);**记录 tag 来源**(模型页面 URL)便于事后核对。
3. **记录确认**: 将选定的镜像地址(源仓库 + tag)记入方案,**再进入 2.1 确认 SWR 镜像就绪状态**。
4. **若用户后续提供了官方文档/正确 tag,无条件修正**: 更新镜像地址、重写启动脚本、覆盖上传 OBS 产物,并回填记录。

> 详细查阅方法见 `references/vllm-ascend-model-doc-guide.md`。

### 2.1 确认 SWR 镜像就绪状态(部署镜像入口决策点)

> **为什么先确认再拉推?** 镜像从 Quay.io 拉取后推送 SWR 是一次性且体积大(数 GB)的操作。用户环境可能已通过其他项目/团队镜像仓完成过该镜像的下载与上传(同一 SWR 镜像可复用,无需重复拉推);反之,若本地网络无法访问 Quay.io,则只能复用已有 SWR 镜像或改用代理。先确认镜像是否已就绪,可避免重复拉推、节省带宽与时间,也避免在用户本地环境做无意义的操作。

1. **用 AskUserQuestion 交互式询问**: 是否已经下载并将 2.0 确认的镜像(`quay.io/ascend/vllm-ascend:<tag>`)上传到租户的 SWR 镜像仓?(options: 已就绪,提供地址 / 未就绪,自行拉推 / 未就绪,由 skill 代拉推)
2. **分支 A — 已就绪(用户已下载并上传)**: 用 AskUserQuestion 收集**完整的 SWR 镜像地址**(文本输入,question 中写明格式 `swr.<region>.myhuaweicloud.com/<组织>/<镜像名>:<tag>`,用户经 Other/notes 填写):
   ```
   swr.<region>.myhuaweicloud.com/<组织>/<镜像名>:<tag>
   ```
   - **校验**: tag 与 2.0 从模型文档确认的 tag 一致;region 与 ModelArts 资源池同区域
   - **⚠️ 镜像类型识别(强制,实验性模型尤其必要)**: 用户提供的镜像可能是**非标准 vllm-ascend 镜像**(团队基于 MindIE/ATB 链路构建,如环境变量含 `ATB_*`/`LCCL_*`、`SOC_VERSION=ascend910b1`、WorkingDir 非 `/vllm-workspace`、自定义 Entrypoint),其**启动方式可能与标准 `vllm serve` 不同**,直接套用本 skill 的 `start_vllm.sh` 可能启动失败。处理: 让用户确认是否标准官方镜像(或仅升级 transformers 的定制)——是则正常推进;否则**披露"该镜像可能不是标准 vllm-ascend 镜像,本 skill 标准脚本可能不兼容"**并询问镜像预期启动方式,必要时改用镜像自带入口。无法确认时请用户在 ARM 节点 `docker run --rm <镜像> bash -c "uname -m && which python && python -c 'import transformers; print(transformers.__version__)'"` 快速验证(排查 exec format error 与 transformers 版本)。
   - **记录**: 将完整地址记入方案输入 **`SWR_IMAGE_ADDRESS`**,向用户复述确认。后续步骤 4 部署新版在线服务时直接作为模型镜像来源,本步骤不再执行任何拉取/推送
3. **分支 B — 未就绪**: 用 AskUserQuestion 让用户选择处理方式:
   - **B-1 用户自行下载上传**: 用户在自己的环境按 2.2(拉取)与 2.3(推送)的命令完成操作;完成后用 AskUserQuestion 收集完整的 SWR 镜像地址,**校验并记录为 `SWR_IMAGE_ADDRESS`**(同分支 A)
   - **B-2 由本 skill 代下载上传**: 按 2.4 执行——用 AskUserQuestion 收集 **SWR 镜像仓名称**与 **docker login 命令**,拉取/推送过程向用户展示进度,完成后返回并记录完整镜像地址
   - **禁止**: 纯文本"请提供 SWR 镜像地址"等待。

### 2.2/2.3 拉取 Quay.io 镜像并推送 SWR(参考命令,分支 B-1)

> 本节省命令供分支 B-1(用户自行下载上传)参考;分支 B-2(由 skill 代下载上传)的自动化执行见 2.4。**tag 一律以步骤 2.0 从模型文档确认的版本为准**(可能是 `v0.23.0`、`v0.18.0rc1-a3-openeuler`、`DeepSeekV4-flash-0731` 等),不要默认用 `latest`。

```bash
# 1. 拉取(以模型文档确认的 tag 为准,示例为 0.23.0;模型专用镜像拉专用 tag)
docker pull quay.io/ascend/vllm-ascend:v0.23.0

# 2. 登录 SWR(使用 SWR 控制台"操作指南"的登录指令,形如)
# 密码经 stdin 注入(不进命令行 argv,不暴露于 ps/proc/history)
export SWR_PASSWORD="<登录密钥>"
docker login -u cn-north-4@<AK> --password-stdin swr.cn-north-4.myhuaweicloud.com

# 3. 打 tag: <region 域名>/<组织>/<镜像名>:<tag>
docker tag quay.io/ascend/vllm-ascend:v0.23.0 \
  swr.cn-north-4.myhuaweicloud.com/<org>/vllm-ascend:v0.23.0

# 4. 推送
docker push swr.cn-north-4.myhuaweicloud.com/<org>/vllm-ascend:v0.23.0
```

- 镜像体积大、Quay.io 拉取慢时可配置代理或国内镜像加速(见常见问题排查"拉取镜像失败");可用 `docker image inspect <image> | grep -i vllm` 核对镜像内 vllm-ascend 版本与文档一致
- 完成后按 2.1 分支 B-1 要求将完整地址(`swr.cn-north-4.myhuaweicloud.com/my-org/vllm-ascend:<tag>`)提供给 skill 记录

### 2.4 由本 skill 代下载上传镜像(分支 B-2 执行)

> 适用前提: 本地环境可访问 Quay.io 且已安装 docker;用户已开通 SWR 并在控制台获取过登录指令。

**1. 用 AskUserQuestion 收集用户输入(两个文本项合并为同一次 ≤4 question,禁止纯文本等待)**: ① **SWR 镜像仓名称**(文本输入): 用户提供 SWR **组织名**(如 `my-org`)与**镜像名**(可省略,缺省取源镜像名 `vllm-ascend`);② **docker login 命令**(文本输入): 用户在 SWR 控制台(**组织管理 → 操作指南**)复制的登录指令,形如 `docker login -u cn-north-4@<AK> --password-stdin swr.cn-north-4.myhuaweicloud.com`(密码经 `SWR_PASSWORD` 环境变量 + stdin 注入,**禁止 `-p <密码>` 明文传 argv**)——skill 从该命令解析 SWR **登录域名/region** 与**登录凭据**(用户不便提供命令原文时改为提供 region + AK + 登录密钥)。

**2. 执行拉取与推送(全程展示进度,强制)**: 运行 `scripts/pull_push_image.sh`,入参: 源镜像 `quay.io/ascend/vllm-ascend:<tag>`(2.0 确认)、`--org <SWR组织名>`、`--name <SWR镜像名>`(缺省 vllm-ascend)、`--login "<docker login命令>"`。脚本打印 `[1/4]`~`[4/4]` 步骤标记并透传 docker layer 进度行;执行时设置足够长超时(镜像数 GB,建议 ≥ 30 分钟),**禁止中途打断**,同步转述执行输出。大镜像拉取慢时可配置代理或国内镜像加速,但 **tag 仍以模型文档为准**。

**3. 返回并记录结果**: 脚本完成时打印完整镜像地址(形如 `swr.cn-north-4.myhuaweicloud.com/my-org/vllm-ascend:v0.23.0`),skill 记录为方案输入 **`SWR_IMAGE_ADDRESS`** 并向用户复述确认,供步骤 4 部署使用;**安全提醒**: 提醒用户执行 `docker logout swr.<region>.myhuaweicloud.com` 清理本地登录凭据。

## 步骤 3: 启动脚本与健康检查脚本准备

> **⚠️ 阶段门控(强制,违反=流程顺序错乱)**: 步骤 3 完成前**禁止收集/使用步骤 4 的 API 信息**(ModelArts 域名/工作空间/区域、资源池 ID、IAM 凭据/IAM 域名/project_name、token、服务名、调用认证方式)。步骤 3 的产物生成与自检上传**只需**: 模型(步骤 1)、SWR 镜像(步骤 2)、芯片型号/TP 大小(步骤 3.0)、模型文档参数(步骤 3.1)、OBS AK/SK/Endpoint(步骤 3.4 上传 OBS 用,**不含 IAM 凭据**)。步骤 4 的 API 信息**仅在步骤 3 全部完成(`check_artifacts.py` 全 PASS + OBS 上传成功 + `CODE_OBS_PATH` 用户确认)后**才允许在步骤 4.0/4.1/4.3 收集。**注意**: `ShowInferServiceCluster` 查询属步骤 4 方式 A(API 自动部署)构造请求体 `flavor` 字段时才需要,步骤 3 全程不需要(步骤 3.0 的 TP 档位按芯片型号直接推导)。

> **为什么脚本必须与模型、部署形式和资源规格对应?** 不同模型(架构、参数量、上下文长度、是否 MoE)的 vllm 启动参数不同;同一模型在不同**部署形式**(单节点 / 多节点 / PD 分离,步骤 1.1 已确定)、不同**芯片型号**(如 910B 与 310P)与不同**卡数**下,启动脚本的结构差异很大(单机 TP 一条命令 / 多机需 Ray 分布式与节点角色 / PD 分离需 Prefill+Decode 双角色实例)。必须查阅该模型在 vllm-ascend 的**模型适配文档**(`https://docs.vllm.ai/projects/ascend/.../tutorials/models/<ModelName>.html`),按"模型 + 部署形式 + 芯片型号 + 卡数"四维匹配,不能套用通用模板。这是本步骤的核心:先查适配文档,再写脚本。

### 3.0 确认资源规格(芯片型号 + TP 大小)

动手查文档前,先用 AskUserQuestion 交互式确认目标资源池的**芯片型号**(options 列出常见芯片型号 910B(A2)/910C(A3)/310P/**950 系列**),并记录到方案中。**⚠️ 用户选择 950 系列后必须立即用 AskUserQuestion 细分确认 950DT / 950PR(强制,禁止合并为单一选项)**——两者单卡显存不同(950DT 96GB / 950PR 128GB),且**同一模型在 vllm-ascend 适配文档中常给 950DT/950PR 不同的启动示例参数**(如 Qwen3.8-27B: 950DT 示例 `--max-model-len 131072`+`--gpu-memory-utilization 0.85`,950PR 示例 `--max-model-len 256000`+`--gpu-memory-utilization 0.9`),脚本参数必须按用户确认的具体型号从文档提取。**芯片型号 → 产品形态 → 单卡显存速查表(910B3 64GB / 910B4 32GB / 910C(A3) 以官方为准 / 310P 24GB 量级 / 950DT 96GB / 950PR 128GB)与不同芯片 × 模型规模的卡数配置详见 `references/ascend-hardware-matrix.md`**——数值以 vllm-ascend 官方适配文档与昇腾官网规格为准;芯片型号信息缺失时先向用户询问,不要猜测。要点: 310P 是**推理卡**,只适合 7B 以下小模型;大模型直接报错。

**确认 TP 大小(迁移自原步骤 1.1b,芯片型号确认后立即执行,TP 候选只给合法值)**:

1. **先取模型注意力头数(前置,禁止自检时才补)**: 从 vllm-ascend 模型适配文档(参数说明若标注"TP 必须取头数约数")或模型权重 `config.json`(`num_attention_heads` 字段,经 ModelScope/HuggingFace raw 文件或用户 OBS 权重路径)获取头数 H,记录为方案输入 **`ATTENTION_HEADS`**。获取途径按优先级: ① 模型文档页面直接标注(如 Qwen3.8-27B 头数 24);② ModelScope `resolve/master/config.json`;③ 用户权重 OBS 路径经 obsutil 读取;④ 均不可得时在 AskUserQuestion 中让用户提供头数(文本输入)。
2. **计算合法 TP 候选 = 头数约数 ∩ 资源池卡数档位 ∩ 模型文档启动脚本 TP 值**:
   - **头数约数**: H 的所有正约数(如 H=24 → 1/2/3/4/6/8/12/24)
   - **资源池卡数档位(按芯片型号直接推导,与 ShowInferServiceCluster 查询无关)**: **非 A3 芯片(910B(A2)/310P/950 系列等)档位 1/2/4/8;A3 芯片(910C)档位 2/4/6/8/16**——按 3.0 已确认的芯片型号取对应档位作为 TP 候选范围。**禁止提供档位外的值(如 12、24 在无 12/24 卡规格时不存在)**。**注意**: `ShowInferServiceCluster` 查询与本步档位推导无关——它只在步骤 4 方式 A(API 自动部署)构造创建请求体的 `unit_configs[].flavor` 字段时才会调用,本步直接按芯片型号取档位即可。
   - **模型文档启动脚本 TP 值(第三个条件交集,强制)**: 合法 TP 候选还必须**大于等于 vllm-ascend 模型适配文档中启动脚本示例的 `--tensor-parallel-size` 值**(如文档示例 `--tensor-parallel-size 4`,则候选仅保留 ≥4 的档位值)——低于文档示例 TP 的档位不符合模型文档适配要求,直接剔除。**来源(避免顺序歧义)**: 模型适配文档在步骤 1.0/1.1 已查询并记录链接(1.0 第 5 步),此处直接引用其中启动命令示例的 `--tensor-parallel-size`;若 1.0/1.1 未提取到该值,可临时回查文档页面正文提取,或先按"头数约数 ∩ 卡数档位"两条件给候选并在 3.1 查文档后复核修正。
   - 交集为空时: 若模型文档明确给出 TP 示例值(如 `TP=2`),该值即使不在档位也可作候选;否则提示"该模型在此芯片/卡数下无合法 TP,需换权重格式(量化版)或改资源池",请用户决策
3. **用 AskUserQuestion 让用户选择 TP(只列合法候选)**: options 为**交集后的合法 TP 值**(带每档卡数描述,如 `TP=8(8 卡/实例,权重 54GB/8≈6.75GB 每卡)`)。
4. **记录方案**: `TP_SIZE`(用户选定)+ `ATTENTION_HEADS`(头数,供自检 H12 传入 `--num-attention-heads` 二次校验整除性,此时必为合法值,自检仅兜底)。

### 3.1 查询模型适配文档(定位用户确认的模型页面)

- vllm-ascend 官方模型文档(中文): `https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/`(模型页面 URL 形如 `.../tutorials/models/<ModelName>.html`;**curl 访问前先按"安全编码规范"校验 URL 白名单**)
- 打开**用户确认的模型**对应页面,按"模型 + 部署形式 + 芯片型号 + 卡数"四维匹配,提取(**这些是编写启动脚本的直接依据**):
  1. **该模型适配的 vllm-ascend 版本**(与步骤 2.0 一致,保证镜像与脚本配套)
  2. **推荐的启动命令示例**: 首选与目标芯片型号/卡数一致的示例(新版 `vllm serve` / 旧版 `python -m vllm.entrypoints.openai.api_server`,两者等价)。**⚠️ 与步骤 3.0 已确认 TP 的衔接**: 3.0 已按"头数约数 ∩ 卡数档位 ∩ 文档 TP 值"确认 `TP_SIZE`;此处提取的 `--tensor-parallel-size` 必须与 3.0 确认的 `TP_SIZE` 一致——若文档示例与已确认 TP 不符,按"产物生成前置校验"以文档实际值为准重新核对 3.0 候选(文档 TP 值是第三个交集条件,二者不应矛盾;矛盾时向用户披露并重新确认 TP)
  3. **部署形式相关的命令变体**: 多节点找多机/DP+TP 示例与 HCCL/Gloo 通信环境变量(`HCCL_IF_IP`/`GLOO_SOCKET_IFNAME`/`TP_SOCKET_IFNAME`/`HCCL_SOCKET_IFNAME`、`--data-parallel-size`/`--data-parallel-size-local`/`--data-parallel-start-rank`/`--data-parallel-address`/`--data-parallel-rpc-port`、slave 追加 `--headless`(vLLM 0.23.0 默认加;`DP_LB_MODE=external|hybrid` 时不加);PD 分离找 Prefill-Decode 启动参数、`VLLM_ROLE` 与负载均衡要求——**以模型页面/社区文档为准**;多节点与 PD 分离的节点主从角色在 ModelArts 适配阶段由 `get_master_ip.py` 读取 rank table 自动判定,不依赖外部协调组件
  4. **启动前必须设置的环境变量**: 常见 `ASCEND_RT_VISIBLE_DEVICES`、`PYTORCH_NPU_ALLOC_CONF=expandable_segments:True`、`HCCL_BUFFSIZE`、`OMP_PROC_BIND=false`、`OMP_NUM_THREADS`、`VLLM_USE_V1`、`TASK_QUEUE_ENABLE`、`LD_PRELOAD=libjemalloc` 等,**以模型页面为准**
  5. **vllm 启动参数**: `--tensor-parallel-size`(对应卡数)、`--max-model-len`、`--dtype`、量化方式(W8A8 等)、`--kv-cache-dtype`、模型特有参数(`--trust-remote-code`、MoE 的 `--enable-expert-parallel` 等)
  6. 若文档按芯片型号区分(910B 单卡/多卡、310P 单卡、910C(A3)、**950 系列细分 950DT/950PR——同一模型两者示例参数可能不同,如 Qwen3.8-27B 的 `--max-model-len`/`--gpu-memory-utilization` 值不同**),选取与**用户确认的具体型号**一致的示例
- 若模型不在支持列表,告知用户需自行验证适配,不保证可用;详细查阅方法与**部署形式判断线索**见 `references/vllm-ascend-model-doc-guide.md` 与 `references/deployment-form-decision.md`

### 3.2 编写启动脚本(按确认的部署形式选用专用模板)

> **原则**: 部署形式已在步骤 1.1 与用户确认并固定为方案输入(`DEPLOY_FORM`)。**脚本按形式直接生成专用版本,不在脚本内通过 `DEPLOY_FORM` 环境变量做运行时分支**——部署形式是计划期决策,不是运行时决策。

1. **选用对应模板**(`templates/` 下四套启动模板,按步骤 1.1a 确认的 4 种部署形式选择):
   - **单节点(`DEPLOY_FORM=single`)** → `templates/start_vllm.single.sh`: 单机单卡或单机多卡(TP)直启,无跨节点逻辑;多副本由 ModelArts 部署副本数承载,模板无需修改
   - **多节点(`DEPLOY_FORM=multinode`)** → `templates/start_vllm.multinode.sh`: 已内置跨节点分布式结构——各节点运行同一脚本,ModelArts 注入 `GLOBAL_RANK_TABLE_FILE_PATH`(rank table JSON 路径)与 `POD_IP`(当前节点 IP);脚本调用同目录 `get_master_ip.py` 读取 rank table 取 master IP,与 `POD_IP` 比较判定 master/slave 角色(**slave 追加 `--headless`**: vLLM 0.23.0 默认加,需占位 http server 承接探针;`DP_LB_MODE=external|hybrid` 时不加,slave 为完整 API server);根据 `POD_IP` 反查网卡名绑定 `HCCL_IF_IP`/`GLOO_SOCKET_IFNAME`/`TP_SOCKET_IFNAME`/`HCCL_SOCKET_IFNAME`(多网卡必需);**`--data-parallel-size` 由 rank table 全部 server 数(节点数)动态推导**(脚本调用 `get_master_ip.py --dp-size`,不再硬编码默认值);ModelArts 需配置**超节点亲和组实例数=N**(副本内节点数);**自检 H14 强制校验 `--headless` 与 `DP_LB_MODE` 匹配**(FAIL 阻断上传)
   - **PD 分离(`DEPLOY_FORM=pd`)** → `templates/start_vllm.pd.sh`: 已内置实例角色分支(Prefill / Decode 两个独立推理单元,同一部署单元内)——通过 `VLLM_ROLE=prefill|decode`(由 ModelArts 同一部署单元内 2 个推理单元分别注入)区分角色,各自设置端口、NPU 卡;权重目录两个角色实例挂载到相同路径;PD 具体参数(如 `--deployment-config`)以模型页面/社区 PD 方案为准,通过 `PD_EXTRA_ARGS` 追加;**PD 分离资源翻倍(prefill/decode 各需一份节点)**
   - **PD 共置(`DEPLOY_FORM=pd_colocate`)** → `templates/start_vllm.pd_colocate.sh`: **对齐 ModelArts 官方 glm_5_2.sh 单引擎 DP 形态**——所有节点运行同一个 vLLM 进程组(data-parallel),prefill/decode 分工由 vLLM 引擎内部完成,外部只有 master 一个 API 入口;**无需 `VLLM_ROLE`**;master/slave 角色经 `get_master_ip.py` 读 rank table 取 master IP 与 `POD_IP` 比较判定(**slave 追加 `--headless`**,同多节点规则);按 `POD_IP` 反查网卡绑定 `HCCL_IF_IP`/`GLOO_SOCKET_IFNAME` 等;**`--data-parallel-size` 由 rank table 动态推导**;用户按模型文档将额外参数(如 `--enable-expert-parallel`、量化参数)直接加入 `MODEL_ARGS` 数组;需随启动/健康检查脚本一并复制 `get_master_ip.py` 到产物目录;ModelArts 需配置**超节点亲和组实例数=N**;自检 H14 校验同多节点
2. **按 3.1 从模型页面提取的内容填充模板**: 环境变量按模型文档设置,启动命令采用模型文档的示例(含模型特有参数),模板头部"使用说明"逐项核对。
3. **保存为产物**: 在本地产物目录 `./<模型名>-<部署方式>/` 下保存为 **`start_vllm.sh`**(模板文件名仅标识形式,产物统一命名为 `start_vllm.sh` 供 ModelArts 引用)。
4. **共同要点(与部署形式无关,所有模板已内置)**:
   - 从环境变量读取 `MODEL_NAME`、`TP_SIZE`、`MAX_MODEL_LEN` 等,便于 ModelArts 部署时通过环境变量覆盖
   - **TP_SIZE 必须填固定值(强制)**: `TP_SIZE` 默认值必须是从模型适配文档提取的**固定数字**(如 2/4/8),**禁止从 `ASCEND_RT_VISIBLE_DEVICES` 动态推导**——ModelArts 注入 `ASCEND_RT_VISIBLE_DEVICES` 可能只给单卡(如 `"0"`),推导为 TP=1,大模型权重装不进单卡显存,KV cache 为负 → 启动崩溃 `ValueError: No available memory for the cache blocks`;模板已改为固定默认值,生成产物时按模型文档 `--tensor-parallel-size` 替换;**自检 H12 强制校验** TP_SIZE 为固定数字且与 `--tp-size` 一致(FAIL 阻断上传)
   - 显式设置 `ASCEND_RT_VISIBLE_DEVICES`
   - 按模型文档设置必要的昇腾环境变量(如 `PYTORCH_NPU_ALLOC_CONF`、`HCCL_BUFFSIZE`、`OMP_PROC_BIND` 等)
   - 模型特有参数(量化、`--enable-expert-parallel`、`--trust-remote-code` 等)通过模板内置的 **`MODEL_ARGS` bash 数组**追加(每项一个元素,JSON 用单引号包裹)——**禁止用字符串变量(如 `EXTRA_ARGS`)存 JSON 参数**: `${EXTRA_ARGS}` 展开时引号丢失,argparse 报 `error: argument --speculative-config: Value '{"method": cannot be converted ...`。EXTRA_ARGS 环境变量仍可用于追加**无 JSON 的普通参数**(模板内自动并入数组)
   - **脚本必须用 `bash` 执行(关键)**: 因脚本使用 bash 数组,ModelArts 启动命令必须用 `bash` 执行——部署时(code 目录已文件存储挂载到 `/home/ma-user/code/`)启动命令为 `bash /home/ma-user/code/start_vllm.sh`;**禁止用 `sh` 执行**(`sh`/dash 不识别 `(...)` 数组,报 `Syntax error: "(" unexpected`)
   - **健康检查失败次数自动设 300(规避重启循环)**: vLLM V1 引擎首次启动需编译 IR + 捕获 CUDAGraph,耗时 5~10 分钟;部署时健康检查**失败次数(failureThreshold)自动设置为 300**(周期 60s ≈ 18000s/300 分钟容忍窗口),配合启动延迟 600s,彻底规避探针误杀导致实例反复重启(见步骤 4.2 第 5 步单元配置与常见问题排查"服务反复重启")
   - **模型权重挂载自检(必做)**: 启动命令执行前必须检查 `${MODEL_PATH}/config.json` 是否存在,缺失时打印挂载目录内容并退出(见下方代码块)。**为什么?** 权重未正确挂载时,vllm/transformers 会把本地路径当作 HuggingFace repo id 处理,报晦涩错误 `OSError: Repo id must be in the form 'repo_name' or 'namespace/repo_name': '<MODEL_PATH>'`,极难定位;提前检查可将根因(OBS 存储地址填错层级、挂载路径与 MODEL_PATH 不一致、OBS 认证凭据缺失导致挂载为空)直接打印出来
   - **脚本内文件引用必须相对定位**: 脚本引用同目录文件(如多节点场景调用 `get_master_ip.py`)时,一律用 `SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)` 定位,**禁止硬编码 `/code/` 等绝对路径**。**为什么?** 用户挂载脚本的路径可能不是 `/code/`(取决于其 OBS 文件存储挂载配置),硬编码会导致探针报 `can't open file '/code/xxx.py': No such file or directory`
   - 监听 8080 端口(或与后续健康检查一致),提供 OpenAI 兼容接口

> **模板即权威,生成产物前必须 Read 实际模板文件**: 完整可运行的启动脚本模板见 `templates/start_vllm.single.sh`(单节点)/ `start_vllm.multinode.sh`(多节点)/ `start_vllm.pd.sh`(PD 分离)/ `start_vllm.pd_colocate.sh`(PD 共置),本 skill 不在 SKILL.md 内复制示例代码——**生成产物前按"产物生成前置校验"重新 Read/grep 模板文件,以磁盘当前内容为准填充**(bash 数组 `MODEL_ARGS`、权重挂载自检、相对路径定位、`DATA_PARALLEL_SIZE` 动态推导等均已内置在模板中)。

### 3.2.5 ModelArts 平台适配(从 vllm-ascend 官方脚本到 ModelArts 适配)

> **为什么需要平台适配?** vllm-ascend 官方模型适配文档给出的启动命令是为裸机/容器直跑设计的(本地路径、8000 端口、直接 CLI 参数),不能直接用于 ModelArts 在线服务部署。
> **适配检查清单(模板填充完成后逐项核对,详见 `references/modelarts-console-guide.md` 第十节)**: 启动命令包成 bash 脚本(`exec python -m vllm.entrypoints.openai.api_server`);监听端口 **8080**(与探针一致);模型路径 `${MODEL_PATH:-/home/ma-user/model}`(OBS 只读挂载);参数用 bash 数组 `MODEL_ARGS`(JSON 单引号);**`DATA_PARALLEL_SIZE` 由 rank table 动态推导**(脚本调用 `get_master_ip.py --dp-size`,禁硬编码);健康检查所有节点探 master /health(单引擎形态三层探针);探针配置 启动延迟 600s/超时 60s/周期 60s/失败次数 300;启动命令 **`bash /home/ma-user/code/start_vllm.sh`**(禁 sh);脚本内文件引用 `$(dirname "$0")` 相对定位(禁硬编码 `/code/`);权重自检 config.json;多副本由部署副本数承载;超节点亲和组=N;**PD 分离在单部署单元内 2 个推理单元注入 `VLLM_ROLE` + 不同 `PORT`**;多节点/PD 分离的节点主从角色经 `get_master_ip.py` 读取 rank table 自动判定(无需外部协调组件)。

### 3.3 编写探针脚本(命令检查方式,新版在线服务推荐)

新版在线服务健康检查推荐**执行命令检查**方式(官网约定: 启动探针 `bash /code/health_check.sh startup`、就绪探针 `bash /code/health_check.sh readiness`、存活探针 `bash /code/health_check.sh liveness`)。与启动脚本一致,探针脚本**不通过 `DEPLOY_FORM` 环境变量做运行时分支**——以"产物目录是否存在 `get_master_ip.py`"自然区分单/多节点(多节点/PD 共置场景生成时复制该脚本,单节点/PD 分离不复制)。

**各部署形式探针行为**: 单节点(single)`startup`/`liveness` 查 vllm 进程、`readiness` 探本地 `/health`;多节点(multinode)与 PD 共置(pd_colocate,同单引擎 DP 形态)`startup`/`liveness` 查 vllm 进程,`readiness` 调用 `get_master_ip.py` 取 master IP,所有节点都探 master 的 `/health`(对外统一入口);PD 分离(pd)各角色按注入的 `PORT` 探 `/health`。

**通用要点**: 端口与启动脚本一致(默认 8080,PD 按角色 PORT);脚本内引用同目录文件必须用 `$(dirname "$0")` 相对定位,禁硬编码 `/code/`(否则报 `can't open file '/code/xxx.py'`);多节点时 `get_master_ip.py` 需随脚本一并复制上传(见 3.4);三层探针语义(K8s 标准): `startup` 防启动误杀、`liveness` 失败重启容器、`readiness` 失败移出流量端点。**模板即权威**: 完整可运行脚本见 `templates/health_check.sh`,生成产物前按"产物生成前置校验"重新 Read/grep 模板文件。

### 3.4 上传部署产物到 OBS(使用 OBS SDK)

将适配生成的**全部部署产物**上传到 OBS code 目录,包括: 启动脚本(`start_vllm.sh`)、探针脚本(`health_check.sh`)、角色识别脚本(多节点场景的 `get_master_ip.py` 等)以及 code 目录内被引用的其他文件。多节点与 PD 分离的多个角色实例共享同一 code 目录(多节点各节点运行同一脚本;PD 的 Prefill/Decode 实例通过 `VLLM_ROLE` 区分角色)。

> **本地产物目录命名规范(强制)**: 适配产物在**当前工作目录**下以 **`<模型名>-<部署方式>`** 命名一个目录(如 `Qwen3-8B-pd`),不再使用通用的 `code`。`<模型名>` 取用户确认的模型 ID;`<部署方式>` 用小写后缀标识,与 `DEPLOY_FORM` 对应: 单节点=`single`(`Qwen3-8B-single`,单机多卡可写作 `tp{N}`)、多节点=`mn`(`Qwen3-397B-mn`)、PD 分离=`pd`(`Qwen3-8B-pd`)、PD 共置=`pd_co`(`DeepSeek-V3-pd_co`)。其他部署方式可自定义描述性小写后缀;同一模型多种部署方式并存时各自独立目录,互不覆盖。

1. **本地归集产物(按命名规范)**: 将按 3.2/3.3 选用的专用模板填充后保存的 `start_vllm.sh`、`health_check.sh` 放入当前工作目录下的 `./<模型名>-<部署方式>` 目录(如 `./Qwen3-8B-pd`、`./DeepSeek-V3-pd_co`);**多节点(`multinode`)与 PD 共置(`pd_colocate`)部署还需从 `scripts/` 复制 `get_master_ip.py` 到该目录**;执行 `chmod +x` 赋予执行权限。**⚠️ LF 行尾强制(必做,违反=bash 无法执行)**: 产物与模板必须以 **LF 行尾**保存/上传——Windows 编辑/复制会带 CRLF,bash 报 `$'\r': command not found` / `syntax error near unexpected token '$'{\r''`(startup 探针失败转 FAILED)。上传前必须校验: `python -c "d=open('<file>','rb').read(); assert b'\r\n' not in d, 'CRLF found'"`,检测到 CRLF 先转 LF(`d.replace(b'\r\n', b'\n')`)再上传。
   1.5. **⚠️ 产物自检关卡(强制,FAIL 不得上传)**: 产物生成后、上传前,必须按 **`references/artifact-check.md`** 自检清单,运行 `scripts/check_artifacts.py` 静态校验产物的**可用性(硬性)**与**性能最优(软性)**——依据已确认的模型/资源规格/部署形式,对照**华为云官方最佳实践(modelarts_10_3121)**与 **vllm-ascend 模型适配文档**:
   ```bash
   python scripts/check_artifacts.py --artifact-dir ./<模型名>-<部署方式> \
       --deploy-form <single|multinode|pd|pd_colocate> \
       --doc-params '<从模型文档提取的推荐参数 JSON>' \
       --model-doc-url <模型文档 URL> \
       --tp-size <卡数> --dp-size <节点数> \
       --num-attention-heads <ATTENTION_HEADS>
   ```
   - **可用性硬性检查(H01~H12)**: 文件齐全/LF 行尾/bash 语法/bash 数组/权重自检/端口一致/探针命令/多节点与 PD 适配/相对路径/模型文档必备参数/TP_SIZE 固定值与文档一致——**任一 FAIL 禁止上传**,修复后重跑直至全部通过;
   - **性能软性检查(S01~S04)**: 文档性能参数齐全度/昇腾环境变量/TP-DP 匹配/部署配置建议——WARN 不阻断上传,但必须向用户**披露提示项**(如未启用 `FULL_DECODE_ONLY` 图模式、缺 `enable_cpu_binding`、缺 MTP 等),由用户决定是否优化后重新生成;
   - `--doc-params` 来源: 步骤 3.1 从 vllm-ascend 模型页面提取的启动命令参数(如 `--speculative-config`/`--compilation-config`/`--additional-config`/`--quantization` 等),未提供时脚本提示但不 FAIL;**skill 流程要求必须提供**(自检对照依赖它)。
   - **`--num-attention-heads` 来源(必传)**: 步骤 3.0 已获取的模型注意力头数 **`ATTENTION_HEADS`**。H12 用它硬性校验 TP 能整除头数(此时 TP 已按 3.0 合法候选选定,必能整除,自检仅兜底防手改脚本);**禁止在自检阶段才临时去取头数**(应已前置)。
2. **用 AskUserQuestion 交互式确认上传目标目录(强制,禁止跳过/默认,违反=不得上传)**: 脚本生成并自检通过后,**上传到 OBS 前必须先用 AskUserQuestion 向用户确认目标目录位置**——禁止静默采用默认路径直接上传,也禁止把"步骤 1.2 已推导 code 目录"当作已确认。确认时**必须提供两个选项**:
   - **方式 A — 使用默认 code 目录(推荐)**: 即模型目录同级推导的 `obs://<bucket>/<prefix>/code`(与 ModelArts 官方最佳实践目录结构一致:`model/` 与 `code/` 同级)。**question 中必须把默认路径的实际值直接展示**(如"上传到默认目录 `obs://<bucket>/<prefix>/code`?"),用户选此项即视为确认;
   - **方式 B — 用户自定义路径(Other/notes)**: 用户提供自定义 OBS code 目录,如 `obs://<bucket>/<custom>/code`(文本输入,question 中写明格式 `obs://<bucket>/<prefix>/code`,经 Other/notes 填写)。
   - **确认后记录**: 将用户确认(默认或自定义)的目录记录为方案输入 **`CODE_OBS_PATH`**,并在上传命令执行前向用户复述该地址,上传完成后再次确认。
3. **用 AskUserQuestion 收集 OBS AK/SK/Endpoint(文本输入,question 中写明格式;凭据敏感,提醒用户可经环境变量提供;三个值合并为一次 AskUserQuestion)**: 运行 `scripts/upload_code_to_obs.py`,命令如下:
   ```bash
   export OBS_AK="<AK>"
   export OBS_SK="<SK>"
   export OBS_ENDPOINT="https://obs.<region>.myhuaweicloud.com"
   # 方式 A: 用户提供 code 目录(--code-dir 为本地 ./Qwen3-8B-pd)
   python scripts/upload_code_to_obs.py --code-dir ./Qwen3-8B-pd \
       --code-obs-path obs://<bucket>/<prefix>/code
   # 方式 B: 由模型目录推导同级 code 目录
   python scripts/upload_code_to_obs.py --code-dir ./Qwen3-8B-pd \
       --model-obs-path obs://<bucket>/<prefix>/model/Qwen3-8B
   ```
   - 脚本基于 OBS Python SDK(`esdk-obs-python`)递归上传整个本地产物目录(启动/健康检查/角色识别脚本等全部产物),打印每个上传对象与最终 code 目录地址
   - 若用户环境无法安装 OBS SDK 且坚持用 obsutil,可等价执行 `./obsutil cp ./Qwen3-8B-pd/ obs://<bucket>/<prefix>/code/ -f -r`,但**默认使用 OBS SDK**
4. **记录 code 目录(必做)**: 将**用户确认后**的上传目标记录为方案输入 **`CODE_OBS_PATH`**(如 `obs://<bucket>/<prefix>/code`),向用户复述确认(注明"已确认"/"自定义")。步骤 4 部署新版在线服务时,启动脚本路径、探针命令、角色识别脚本引用均基于该目录。

## 步骤 4: 部署新版在线服务(API 自动 / 控制台手动)

> **为什么用新版部署?** ModelArts 平台的"创建 AI 应用 + 部署在线服务"两步式流程(旧版)已废弃下线。新版在线服务**不再创建 AI 应用**,直接在部署配置中指定 SWR 镜像 + OBS 权重挂载 + 探针命令 + 副本/角色结构(请求体结构 `service.deployment.roles[]`,对应部署副本与推理单元)。

### 4.0 前置: 确认方案输入

> **⚠️ 方式选择先于 API 信息收集(强制,违反=收集用户不需要的信息)**: 本节(4.0)的 ModelArts 域名/工作空间/区域确认与 4.3 的 IAM 凭据/服务名/认证方式收集,**仅在用户经 4.1 选定方式 A(API 自动)后才执行**;用户选方式 B(控制台手动)时,4.0 API 环境信息与 4.3 凭据**全部跳过**(4.2 明确"方式 B 不索要 API 环境信息")。**执行顺序**: 先 4.1 AskUserQuestion 选方式 A/B → 选 A 才进入 4.0 确认环境 + 4.3 收集凭据 → 选 B 直接打印 4.2 控制台指导。**禁止**在 4.1 方式选择前索要 IAM 密码、确认 IAM 域名/project_name、确认服务名/认证方式等步骤 4 专属信息。

进入部署前,确认以下方案输入已齐备(均由前序步骤产出): **`SWR_IMAGE_ADDRESS`**(推理镜像地址,步骤 2)/ **`CODE_OBS_PATH`**(code 目录,含 `start_vllm.sh`/`health_check.sh`/`get_master_ip.py`,步骤 3.4)/ **`MODEL_PATH`**(权重 OBS 目录,只读挂载到容器 `/home/ma-user/model`,步骤 1.2)/ **`DEPLOY_FORM` + `NNODES` + `REPLICAS`**(single/multinode/pd/pd_colocate + 副本内节点数 + 副本数,步骤 1.1)/ **资源池信息**(名称、芯片型号、TP 大小,步骤 3.0)/ **`MA_ENDPOINT`**(ModelArts 域名,统一 `modelarts.<region>.myhuaweicloud.com`,不存在 dev 域名,支持用户自行输入其他生产域名,须与资源池同区域)/ **`WORKSPACE_NAME` + `WORKSPACE_ID`**(API 调用带 `X-Workspace-Id` 头,4.3 步骤 0 查 ID)。

> **⚠️ 调用 ModelArts API 前必须先确认环境信息(强制)**: **必须先通过 AskUserQuestion 交互式确认 ModelArts 域名、工作空间名与区域(3 项合并为同一次 AskUserQuestion),再调用任何 ModelArts API**。域名须与资源池同区域(统一 `modelarts.<region>.myhuaweicloud.com`,不存在 dev 域名)→ 必须用正确域名 + 正确 `X-Workspace-Id`。**禁止**不确认环境就凭默认域名直接调 API,**也禁止**纯文本"请确认环境"等待。

### 4.1 选择部署方式(API 自动 / 控制台手动)

**用 AskUserQuestion 交互式确认部署方式**(options: 方式 A — API 自动部署 / 方式 B — 控制台手动部署,附适用场景说明),两种方式等价,按用户偏好选择:

| 方式 | 适用场景 | 特点 |
|------|---------|------|
| **方式 A — API 自动部署** | 用户愿意提供 IAM Token,希望 skill 代调 API 完成部署 | 一条命令完成,需 `--endpoint`/`--project-id`/token(环境变量 `IAM_TOKEN` 或 `--token-file`) |
| **方式 B — 控制台手动部署** | 用户不便提供 Token,或希望保留人工确认每个配置项 | **skill 将完整操作步骤直接打印在对话中**(含该模型的具体取值),用户照此在控制台点击操作 |

> **方式 B 输出要求(强制)**: 用户选择方式 B 后,skill **必须将 4.2 的完整操作步骤逐条打印输出到对话中**,并用 4.0 的方案输入替换所有占位符,生成**自包含、可直接照做**的分步指导。**禁止**只给文件路径或"详见 references/xxx"让用户自行查阅。部署完成后回到步骤 5 验证服务就绪与步骤 6 调用验证。

### 4.2 方式 B: 控制台手动部署(一步步点击指导)

> **方式 B 不索要 API 环境信息(强制)**: 用户选择方式 B 后,**不得向用户索要 ModelArts 域名、工作空间名、资源池名称、project-id、IAM Token 等 API 部署(方式 A)才需要的参数**——控制台部署时这些都在控制台页面上由用户直接选择。打印指导前只需确认**方式 B 自身需要的输入**: 服务名(可自动生成或让用户填)、部署形式/资源规格(步骤 1.1/3.0 已确认)。**唯一例外**: 打印完整指导后,按本小节末尾的强制要求主动询问一次"是否需要 API 代为部署(方式 A)"——那是给出选项,不是索要参数。
> **本小节是打印输出模板,不是让用户查阅的文档。** 用户选择方式 B 后,skill 按 **`references/modelarts-console-guide.md` 第一节的 9 步结构**完整打印到对话中,并把所有占位符(`{CODE_OBS_PATH}`/`{MODEL_PATH}`/`SWR_IMAGE_ADDRESS`/服务名/场景取值等)替换为 4.0 方案输入的实际值,输出一份该模型专属的分步指导。控制台路径以实际版本为准(公有云新版入口: 左侧菜单 **模型推理 > 在线推理**;部分版本为 **模型部署 > 在线服务**)。
> **打印格式(强制)**: 每步用 `**第 N 步 — <标题>**` 开头(1 进入部署页面 / 2 基础信息 / 3 资源配置 / 4 模型配置 / 5 单元配置(含启动命令/健康检查/文件存储挂载) / 6 部署管理配置 / 7 部署超时时间 / 8 亲和调度 / 9 确认部署),下方列出该步要做的具体动作与**已填好的具体值**(不是占位符、不是"按场景选择"式描述);4 种部署形式差异(见 4.4 与 reference 速查表)在打印时直接展开为该形式对应的确定值。整个输出必须自包含——用户无需打开任何其他文件。关键取值速查(**每个值必须填到其标注的归属步骤表格中,禁止跨步骤放置**): 服务名小写字母/数字/下划线(**第 2 步**);权重挂载 `/home/ma-user/model`(**第 4 步模型配置**);code 挂载 `CODE_OBS_PATH → /home/ma-user/code/`(**第 5 步单元配置-文件存储挂载子项**);镜像 `SWR_IMAGE_ADDRESS`(tag 以模型文档为准,勿用 latest)(**第 5 步单元配置-镜像地址**);**容器端口 8080 仅属第 6 步部署管理配置,单元配置(第 5 步)没有"容器端口"项——不得写入第 5 步**(见下方"端口层级强制规则");探针命令 `bash /home/ma-user/code/health_check.sh startup|readiness|liveness`(**第 5 步单元配置-健康检查**);启动延迟 **600s**、失败次数 **300**、超时 60s、周期 60s(**第 5 步单元配置-健康检查探针参数**);启动命令 **`bash /home/ma-user/code/start_vllm.sh`**(禁 sh)(**第 5 步单元配置-启动命令**);PD 单元名小写 `prefill`/`decode`(**第 5 步单元配置-单元名称**);pd(PD 分离)单部署单元内 2 个推理单元注入 `VLLM_ROLE=prefill|decode` + **双角色差异 `PORT`(如 8080/7101)填在各自单元的"环境变量"子项**,与第 6 步"容器端口"(服务对外单一值 8080)是**两个不同层级**;multinode/pd_colocate 亲和调度强亲和指向同一超节点(亲和组实例数=N)(**第 8 步**)。
> **端口层级强制规则(强制,违反=指导作废)**: 端口在控制台指导中出现于**两个不同层级**,必须严格区分归属:
> ① **第 5 步单元配置-环境变量 `PORT`**: PD 分离时 prefill/decode 两单元各自注入 `PORT`(如 prefill=8080 / decode=7101),是**单元内角色端口**——**仅 PD 分离需注入差异端口(4.4 pd 行"需处理"列明确要求),非 PD 分离场景 `PORT` 不填(脚本默认 8080,与下方"环境变量唯一来源"规则一致)**;
> ② **第 6 步部署管理配置-容器端口**: **单一值 8080**,是**服务级对外端口**(与启动脚本 `PORT` 默认值一致,console-guide.md 第 6 步)。**禁止**将 PD 双角色差异端口填入第 6 步"容器端口"(该处只接受单一 8080);**禁止**在第 5 步单元配置中写入"容器端口"配置项(该表格无此字段,console-guide.md 第 5 步)。
> **字段归属强制校验(强制,打印前逐项核对)**: 打印 9 步指导前,必须按 `references/modelarts-console-guide.md` 第一节该步骤表格的**实际字段清单**逐项核对待填值——速查表仅提示"有哪些关键值",**字段归属以 console-guide.md 分步骤表格为准**;凡速查表中的值,必须确认其归属步骤与该步骤表格确有对应字段后才填入,表格中不存在的字段(如第 5 步的"容器端口")一律禁止写入,无论速查表是否出现。打印完成后对每个已填值做反向自检(依据=console-guide.md 哪一行),发现越级/错位立即修正后再输出。
> **第 5 步单元配置中环境变量唯一来源(强制)**: 只列 4.4 表格该场景行第 4 列"需处理"单元格要求的项——该列写"无需注入"则直接写"无需填写任何环境变量";**禁止自行展开脚本默认值参数**(`TP_SIZE`/`MODEL_PATH`/`PORT`/昇腾环境变量/`MODEL_NAME` 等一律不列,脚本已有默认或自动推导)。**部署形式已固定在脚本中,无需也不应再传 `DEPLOY_FORM` 环境变量**。
> **文件存储挂载必须完整打印(强制)**: 第 5 步打印时**必须包含"文件存储挂载"子项**——code 目录(`CODE_OBS_PATH` 实际值)挂载到 `/home/ma-user/code/`,与权重挂载(`/home/ma-user/model`)并列展示,不得遗漏。缺失会导致启动/探针脚本无法访问(报 `can't open file`)。
> **输出自包含(强制)**: 各步打印时把占位符全部替换为该模型的确定值;`references/modelarts-console-guide.md` 与 `references/deployment-form-decision.md` 仅供 skill 填充取值时参考,**不推给用户**。
> **控制台指导展示后主动询问 API 部署(强制)**: 输出完整 9 步控制台指导后,**必须立即用 AskUserQuestion 交互式询问**: 是否由 skill 直接通过 API 代为部署(方式 A)?(options: 代为部署,提供 IAM Token / 自己在控制台操作)。若用户同意,按 4.3 方式 A 执行;若用户选择控制台操作,则结束交付。**不得默认用户自己操作控制台,也不得默认替用户部署——必须询问**;**禁止**输出指导后不加询问静默等待。

### 4.3 方式 A: 调用 create_infer_service.py 部署(API 自动)

> **方式 A 前置**: 需 `--endpoint`(ModelArts 服务端点,与资源池同区域,统一 `modelarts.<region>.myhuaweicloud.com`)、`--project-id`、token(请求头 `Authorization: Bearer <token>`,有效期 24h)、`--workspace-id`(**所有环境都需要,POST 创建请求的 workspace_id 放在请求 body 顶层字段,GET 查询接口须带 `X-Workspace-Id` 头 + URL 双查询参数**,缺失或传错位置则查不到对应工作空间的服务/创建报 8179)——环境信息(域名/区域/工作空间)已在"交互式确认规范"或 4.0 用 AskUserQuestion 确认;IAM 凭据用 AskUserQuestion 收集(见下方 token 获取与提取)。**`project-id` 无需单独向用户索要**——获取 token 后用 `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token` 头)自动查询,按 `name` 匹配 **`PROJECT_NAME`**(步骤 4.3 已与用户确认,见 token 获取第 ③ 条;不再假设 = region)取 `id` 即可(见步骤 0 第 ⑥ 步)。**⚠️ IAM 域名独立确认(强制)**: IAM API 域名(`iam.<region>.myhuaweicloud.com`)与 ModelArts 域名是**两个不同域名**,必须分别用 AskUserQuestion 确认——ModelArts 域名在 4.0 确认;IAM 域名在 4.3 选 token 获取方式后、调 IAM API 前确认(默认 `iam.<region>.myhuaweicloud.com`,支持自输入,须与 ModelArts 同环境)。
> **⚠️ token 安全传递(强制,安全编码规范)**: IAM Token 是敏感凭据,**禁止作为命令行参数传递**(`ps`/`/proc/<pid>/cmdline`/Shell 历史均会明文暴露)。脚本已移除 `--token` 参数,按优先级提供: ① **环境变量 `IAM_TOKEN`**(推荐,不进进程 argv;Windows 上一律用此方式——NTFS 权限映射 0o666,`chmod 600` 不可靠,`--token-file` 会被拒绝) ② **`--token-file <文件>`**(仅 Linux 可靠,权限须 600,脚本拒绝 0o644 等) ③ **交互式输入**(不回显,不可管道/脚本化)。
> **⚠️ Agent Bash 工具独立 shell**: Agent Bash 工具每次调用是独立 shell,`export IAM_TOKEN=...` **不跨调用持久化**——必须 `IAM_TOKEN=<token> python scripts/create_infer_service.py ...` 在同一条命令内完成(token 可由 `python -c "...读 token 文件..."` 内联读取后赋给环境变量再执行)。**⚠️ 超长 token(含 base64 编码的 PKI token 可达 8KB+)**: bash heredoc/内联传递会因引号/特殊字符冲突报 `unexpected EOF`——**禁止用 bash heredoc/`cat <<EOF` 传 token**;改用 Write 工具将含 token 的完整 Python 脚本写入 **`/tmp/` 下的临时文件**(如 `/tmp/get_token_<随机后缀>.py`,token 作为 Python 字符串常量;**禁止写入 skill 本体目录或工作目录,防止污染 skill 目录结构**),再用 `python /tmp/<脚本>.py` 执行(脚本内 `requests` 直接引用 token 变量,不经 shell argv)。**所有运行 skill 产生的临时文件一律写入 `/tmp/`,禁止在 skill 本体(`scripts/`/`templates/`/`references/` 及 skill 根目录)或部署产物目录外创建任何文件**。
> **⚠️ 步骤 0: 调用任何 ModelArts API 前必须先确认环境信息(强制)**: 禁止凭默认域名直接调用。① 用 AskUserQuestion 交互式确认域名(统一 `modelarts.<region>.myhuaweicloud.com`,不存在 dev 域名;支持用户自行输入其他生产域名,须与资源池同区域);② 用 AskUserQuestion 确认工作空间名(options + Other);③ 用确认后的域名查 workspace-id(`GET /v1/{project_id}/workspaces`,**工作空间列表接口不带 `X-Workspace-Id` 头、不带 workspace 查询参数、仅带 `Authorization: Bearer <token>`**——全局查询用于获取 WORKSPACE_ID 本身),按工作空间名匹配出 `id` 记为 `WORKSPACE_ID`;④ **查资源池列表用 `GET /v2/{project_id}/pools`(v1 路径 `/v1/{project_id}/pools` 报 404 `APIGW.0101`)**——URL 须带 `?workspaceId={}&workspace_id={}` 双查询参数 + 头 `X-Workspace-Id`,响应 `items[]` 中取 `metadata.name` 为资源池 ID(pool_id),`spec.resources[].count` 为节点数;查节点卡数用 `GET /v2/{project_id}/pools/{pool_id}/nodes`(带双 workspace 查询参数 + `X-Workspace-Id` 头),响应 `items[].status.resources["huawei.com/ascend-1980"]`=总卡数、`availableResources`=可用卡数;**⚠️ 资源池名称 vs 资源池 ID(强制,违反=查 pool_id 失败)**: 资源池有**用户自定义名称**(如 `pool-infer2-a3-r60070762`,控制台显示,非 API 字段)与**系统生成的资源池 ID**(UUID 格式 `pool-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`,即 `metadata.name`,API 必须用此值)。交互式确认时,问题文本写明:**"资源池 ID(UUID 格式,控制台资源池详情页可查;若只知资源池名称也可提供,skill 查 pools 列表按名称匹配)"**;用户提供的是名称时,调 `GET /v2/{project_id}/pools` 在 `metadata` 的 label/annotation 字段按名称匹配,取其 `metadata.name` 为 pool_id;不匹配则列出全部资源池由用户选择;⑤ 后续所有 API 调用使用: 确认后的域名 + `Authorization: Bearer <token>`。**⚠️ workspace 传参方式按请求类型区分(强制,POST 创建请求与 GET 查询接口不同,违反=创建报 8179)**: **GET 查询接口**(list/show/资源池/节点等)带头 `X-Workspace-Id: {WORKSPACE_ID}` + URL 双查询参数 `?workspaceId={}&workspace_id={}`(除工作空间列表接口外);**POST 创建请求(CreateInferService)的 workspace_id 放在请求 body 顶层字段**(`"workspace_id": "{WORKSPACE_ID}"`,与 `name`/`type` 同级)——**不是请求头、也不是 URL 查询参数**。实测: POST 创建请求仅带 `X-Workspace-Id` 头而不在 body 放 `workspace_id`,报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`(资源池实际存在且 X-Infer 已启用);body 顶层补 `workspace_id` 后创建成功。`create_infer_service.py create` 已自动注入该字段(骨架与 `--raw-json` 路径均补齐,`validate_request_body()` 校验缺失);⑥ **project-id 自动查询(无需向用户索要,按已确认的 PROJECT_NAME 匹配)**: 获取 token 后调 `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token` 头),响应 `projects[]` 中按 `name` 匹配 **`PROJECT_NAME`**(步骤 4.3 token 获取第 ③ 条已与用户确认;默认 region 去掉 `.beta` 等环境后缀)取 `id`。**⚠️ project name ≠ region name(强制)**: project name 可能去掉 `.beta` 等环境后缀(如 region=`cn-southwest-301.beta` → project name=`cn-southwest-301`);禁止假设 project name = region name,先列出全部 projects 再匹配。⑦ **flavor 获取(强制,ShowInferServiceCluster)**: 创建请求体 `unit_configs[].flavor` 通过**查询纳管资源池详情**接口 `GET /v2/{project_id}/services/clusters/{pool_id}`(路径中 id 为资源池 ID;带双 workspace 查询参数 + `X-Workspace-Id` 头)获取——响应 `flavors[]` 数组,每个元素含 `id`(如 `modelarts.vm.arm.16u.64g.npu.16snt9c`)与 `ascend` 对象(`card`=物理卡数、`npu`=实际使用卡数;**以 `npu` 值为准**: 一般资源池 `card=npu`,A3 资源池 `card×2=npu`)。按部署所需卡数选对应条目,取其 `id` 作为请求体 `flavor`;多节点取每节点卡数对应条目(如 16 卡/节点 → `npu=16` 条目)。**禁止从节点规格推导 flavor**(前缀 `vm`/`bm` 与内存取整档无法从节点规格得出)。
> **⚠️ 请求体结构**: 新版 CreateInferService 请求体是**顶层平铺结构**——**不是** `{"service": {"deployment": {"roles": []}}}` 包裹结构(旧骨架报 400 `name/type/group_configs/runtime_config` 缺失)。**⚠️ 顶层 `workspace_id` 必填(强制,违反=报 8179)**: 请求 body 顶层必须含 `"workspace_id": "{WORKSPACE_ID}"`(与 `name`/`type`/`deploy_timeout_minutes` 同级)——POST 创建请求的 workspace 经 body 传递,不是请求头 `X-Workspace-Id`、也不是 URL 查询参数;缺失报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`。`create_infer_service.py create` 自动注入该字段。**完整请求体 JSON 示例与字段说明见 `references/modelarts-console-guide.md` 第三节**(顶层平铺、`secret_type: "agency"`、**`runtime_config.service_invoke` 三项必填: `port`=8080(与启动脚本一致)、`auth_type`=NONE/TOKEN/API_KEY、`protocol`=HTTP**——三项缺失任一项报 400 `ModelArts.6400`、**`deploy_timeout_minutes=300`(部署超时统一 300 分钟,见 API 部署前置校验第 10 条)**、PD 双角色不同 `PORT`、`unit_configs[].name` 仅小写字母/数字/连字符(大写 `Prefill`/`Decode` 报 400)、`flavor` 为推理实例规格,从**查询纳管资源池详情(ShowInferServiceCluster)**获取(见步骤 0 第 ⑦ 条;**禁止从节点 `status.resources` 推导**——`modelarts.vm` vs `modelarts.bm` 前缀与内存取整档无法从节点规格推导;**非资源池节点规格 `modelarts.bm.npu.arm.ssd`** 是 ECS 物理机 flavor,误填报 `400 ModelArts.6404 Flavor not found`)、`failure_threshold=300`/`initial_delay_seconds=300`/`period_seconds=60`、`group_configs[].weight`(100)与 **`service_limit` 三项必填(`request_timeout=300`/`request_size_limit=20`/`rate_limit`,见 API 部署前置校验第 6 条;`request_timeout` 缺失时平台默认 30s,慢速/PD 首请求报 `ModelArts.8909 request timeout`)**、**multinode 多节点用 `unit_configs[].count`=N 承载跨节点数(单副本资源实例数为多,`group_configs[].count`=1)**、获取正确结构的最可靠方法=查询已部署成功的现有服务 `show` 反推)。**构造请求体前对照 reference,字段名以 API Explorer 为准**。
> **⚠️ A5(snt9e/950 系列)芯片特殊字段(强制)**: 上述请求体骨架与 `references/modelarts-console-guide.md` 第三节示例是在 **A2(910B)/A3(910C)资源池**上验证的。**部署到 A5(950 系列 `ascend-snt9e`)资源池时,请求体必须补充 A5 特殊字段**(详见 reference 第三节"A5 特殊字段"小节): `group_configs[].workload_type="LWS"`、`async_scheduling=true`、`priority=1`、`framework="COMMON"`、`system_log_dump_enable=false`、`deploy_type="MULTI"`、`advanced_config`(含 `deploy_timeout_minutes=300`/`port=8080`/`upgrade_config`/`service_secret`)、`secret_type="dew"`(group 与 unit 级)、`unit_configs[].group_count/termination_grace/npu_reset_enable/cpu_affinity/codes/models/dumps`、探针 `name`(survival_probe/ready_probe/start_probe)、`runtime_config.service_invoke.direct_channel_enable/intranet_approval_enable`、`runtime_config.service_limit.ip_white_list/ip_black_list`、顶层 `tags/schedule/log_configs`。**推荐直接走 `create_infer_service.py create --chip-model a5`**,脚本自动注入 A5 特殊字段;**非 A5 场景(a2/a3,默认)不注入这些字段,保持原骨架**。A5 创建报 `8118 Insufficient NPU resources` 时,优先核对 `async_scheduling=true` 是否已注入(缺省同步调度会立即拒绝,而非异步排队)。

**基础命令(推荐骨架 + `--pool-id`/`--model-obs-path`/`--code-obs-path` 自动构建,host_cache 自动注入;复杂结构用 `--raw-json` 整体传入)**:

```bash
# 创建在线服务(单部署单元;PD 分离传两个 --role: prefill + decode,其余形式一个 --role)
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

> **⚠️ 部署前必查资源池可用卡数(强制)**: 发起 CreateInferService **前**,先调 `GET /v2/{project_id}/pools/{pool_id}/nodes`(带双 workspace 查询参数 + `X-Workspace-Id` 头),汇总 `items[].status.availableResources["huawei.com/ascend-1980"]` 为总可用卡数;计算本部署需要卡数 = 副本数 × 单元数 × 每节点卡数(如 multinode 2 节点 × 16 卡 = 32)。**可用卡数 < 需要卡数时,不发起创建**,将可用卡数 + 占用卡数的服务清单(id/name/status,list 的 `resource_details[]` 按 `pool_id` 过滤)告知用户,由用户决定释放哪个服务(见下方 8118 处理)。

> **⚠️ 服务名占用(8006)处理(强制,所有环境一致,禁止 DELETE 与自动 stop)**: 创建服务返回 `400 ModelArts.8006 "The service name xxx already exists"` → 服务名已被占用(同地域唯一)。**处理顺序(强制)**: ① **不自动停止任何服务**——无论占用服务是否为本 skill 部署,一律不主动 `stop`(停止其他用户服务属越权);② **查占用服务归属并告知用户**: `list`/`show` 查该服务状态(DEPLOYING/FAILED/STOPPING 等非运行态仍占服务名与资源池卡数),将服务名/id/状态告知用户;③ **换新服务名创建**: 小写字母/数字/连字符,原名加 `-2`/`-3` 递增(如 `glm53-flash-mn-2`);④ **若用户明确指示释放某个服务**(提供 service_id),skill 仅对该 service_id 执行 `POST /v2/{project_id}/services/{sid}/stop`,等待 STOPPED 后再创建。⑤ **禁止触发 DELETE 动作**(DELETE API 可能 404 且删除他人服务属越权)。⑥ **关键: list 查不到同名服务 ≠ 服务不存在**——list(GetServices)可能不返回 FAILED/DELETING/STOPPING 等非运行态服务,但该服务仍占用服务名与资源池卡数;判断服务是否存在以 **create 返回的 8006/8118** 与**资源池可用卡数**为准。
> **⚠️ 资源不足(8118)处理(强制,所有环境一致,禁止自动 stop)**: 创建新服务返回 `400 ModelArts.8118 Insufficient NPU resources`(Requested 卡数 > Available 0 卡)说明**失败/停止的旧服务仍占用资源池卡数**。处理(所有环境一致,禁止 DELETE 与自动 stop): ① **先查资源池可用卡数** `GET /v2/{project_id}/pools/{pool_id}/nodes`(响应 `items[].status.availableResources["huawei.com/ascend-1980"]`);② **列出占用资源的服务并告知用户**: `list` 查各服务 `resource_details[]`(含 `pool_id`/`resources`/`status`),汇总到目标资源池上仍占用卡数的服务清单(id/name/status);③ **将可用卡数 + 占用清单告知用户,由用户决定**——用户可在控制台自行停止,或明确指示 skill 停止某 service_id;skill 仅执行用户指定的 service_id 的 `POST /v2/{project_id}/services/{sid}/stop`,等待 STOPPED 后再创建。④ **禁止 DELETE**(`method DELETE not found` 或越权)。**禁止 skill 自行批量 stop 非本会话部署的服务**。
> **code 目录文件存储挂载(关键)**: `unit_configs[].files[]` 内配置 code 目录挂载(`files[].address=CODE_OBS_PATH` → `files[].mount_path=/home/ma-user/code`),启动命令与探针命令一律用容器内路径 `bash /home/ma-user/code/...`。
> **⚠️ `host_cache: true` 本地加速(强制,所有芯片 A2/A3/A5 统一开启)**: `group_configs[].model`(权重挂载)与 `unit_configs[].files[]`(code 挂载)都必须带 `host_cache: true`——将 OBS 挂载内容缓存到主机本地,显著加速大模型权重加载(如 54GB BF16)与 code 脚本读取。**缺失会被 create_infer_service.py 的 `validate_request_body()` 拦截(FAIL 拒绝提交)**;骨架路径(`--pool-id`/`--model-obs-path`/`--code-obs-path`)自动注入,`--raw-json` 路径自动补齐缺失项。
> **envs 只需注入少数项**: `TP_SIZE` **无需写入 envs**(脚本按资源池实例规格自动推导);`MODEL_PATH`/昇腾环境变量等模板已有默认值;**pd(PD 分离)必须在同一部署单元内 2 个推理单元分别加 `VLLM_ROLE=prefill|decode`** 与 **`PORT`(双角色不同)**;`MODEL_NAME` 非必填(脚本默认值 `model`,仅在需自定义 served-model-name 时注入)。
> **⚠️ token 获取与提取(强制)**: ① **获取 token 必须用 Python requests 调用 IAM API**: `resp = requests.post('<IAM_DOMAIN>/v3/auth/tokens', json=<IAM请求体>, verify=False, timeout=30)`(requests 直接传 dict/JSON,凭据正确即返回 201),响应头 `resp.headers['X-Subject-Token']` 取 token;**禁止用 curl `-d` 字符串拼接 JSON body 获取 token**(Windows bash 下 `'"$VAR"'` 引号拼接致密码传递错误,凭据正确也返回 401);② **token 必须用 project scope 获取**(`"scope": {"project": {"name": "<PROJECT_NAME>"}}`,与资源池同区域);**禁止 domain scope**(报 `400 ModelArts.6400 ... getProject() is null`);③ **IAM 域名与 project_name 必须先与用户确认(强制)**: ①' **IAM 域名确认(强制)**: 获取 token 前,必须用 AskUserQuestion 交互式确认 **IAM 域名**——options 给默认推导值 `iam.<region>.myhuaweicloud.com`(region 含 `.beta` 时同带),支持用户经 Other 自输入(如 `iam.cn-southwest-301.beta.myhuaweicloud.com`);**禁止不确认就默认 `iam.<region>` 直接调 IAM API**(不同环境 IAM 域名可能与 region 推导不一致);②' **project_name 确认(强制,账号密码方式必做)**: 用户选择 IAM 用户名/密码方式时,除账号名/用户名/密码三要素外,**必须额外用 AskUserQuestion 确认 `project_name`**(token 的 `scope.project.name`)——options 给默认推导值(**region 去掉 `.beta` 等环境后缀后的值**,如 region=`cn-southwest-301.beta` → 默认 `cn-southwest-301`,实测 project name 为 `cn-southwest-301` 时凭据正确才返回 201;用 region 含 `.beta` 的原值会 401),支持用户经 Other 自输入实际 project name;确认后记入方案 **`PROJECT_NAME`**,获取 token 后调 `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token` 头)按 `name` 匹配 `PROJECT_NAME` 取 project-id;④ **IAM 凭据三要素索要顺序必须为「账号名 → IAM 用户名 → 密码」(强制)**: 用 AskUserQuestion 收集时,**按"账号名(domain.name)、IAM 用户名(user.name)、密码(password)"的顺序展示与收集**——账号名(主账号)是用户最易识别的第一要素,放第一位;用户名(IAM 子用户)次之;密码最后。字段对应关系: 账号名=主账号(`domain.name`)、用户名=IAM 子用户(`user.name`)、密码=登录密码;顺序错配会 401 且有账号锁定风险——先询问"以哪种方式提供 token"(IAM 用户名/密码 / 直接提供 Token),收集后按"账号名(domain.name)、IAM 用户名(user.name)、密码(password)"顺序向用户复述字段对应关系再取 token;⑤ **提取 token 必须用 Python 正则完整提取**: `re.search(r'(?i)^X-Subject-Token:\s*(\S+)', content, re.M)`——**禁止用 `grep | sed | tr` 管道**(长 token 丢字符导致 401);⑥ 校验 token 可见项目(可选): `GET https://iam.<region>.myhuaweicloud.com/v3/auth/projects`(带 `X-Auth-Token`);⑦ 用户直接提供 token 时,若含 `-`/`_` 或非 `==` 结尾,先怀疑复制截断,用 AskUserQuestion 请用户选择重新提供 / 改用 IAM 用户名密码。**⑧ 超长 PKI Token 禁止通过 AskUserQuestion 传递(强制)**: IAM Token 为 PKI 格式(含 base64 编码的证书链+签名,可达 8KB+),**AskUserQuestion 的 answer/notes 字段有长度限制,超长 token 会被截断,末尾缺失签名块导致 API 报 `401 decrypt token fail`**——反复重试无效,且用户复制时可能再截断。正确方式: ① 优先请用户提供 IAM 用户名/密码,skill 用 Python requests 调 IAM API 获取 token;② 或请用户将 token 保存为本地文件并提供文件路径,skill 读取后设置 `os.environ['IAM_TOKEN']`(环境变量方式,不进进程 argv,Windows 推荐)调用脚本;③ **禁止把超长 token 作为 Python 字符串常量内嵌脚本**(引号/转义易错,且偏离 skill 的 token 安全传递规范)。**⑨ IAM 凭据三要素错配排查(强制)**: 凭据正确但 401 `The username or password is wrong` 时,**禁止反复猜测用户名/密码组合**(多次错误有账号锁定风险)——让用户提供 postman/已调通的完整请求体,逐字段核对 `user.name`/`domain.name`/`password`,特别是 **domain.name(账号名)易因手工抄录/解析漏字符**而错配(如 `ei_pangu_x60079363_01` 误写 `ei_pangu_x6007963_01`);确认 **project_name 是否正确**(用 region 原值含 `.beta` 会 401,须去掉后缀)。

### 4.4 4 种部署形式 → 部署配置映射(API group_configs/unit_configs 与控制台单元共用)

下表同时适用于方式 A(API `group_configs[]`/`unit_configs[]` 字段)与方式 B(控制台单元配置/环境变量);**完整映射表、环境变量分类速查(①脚本自动推导 `TP_SIZE`/`DATA_PARALLEL_SIZE` ②容器内固定 `MODEL_PATH`/`PORT` ③平台注入 `VLLM_ROLE`(仅 pd 分离)④模型文档要求 `MAX_MODEL_LEN`/`DTYPE`/`MODEL_NAME`)与控制台速查表见 `references/modelarts-console-guide.md` 第一节(4 形式控制台配置速查)与第六节(4 形式 → 请求体映射)**。要点速览:

| 部署形式 | 推理单元 | 副本数 | 需在部署单元/模型配置中处理的项 | 探针 |
|---------|---------|--------|------------------------------|------|
| **single 单节点** | 1 个 `role-1` | 1(默认)/ M(可靠性) | 无需注入(`TP_SIZE` 脚本按卡数推导;`MODEL_NAME` 非必填,脚本默认值 `model`) | health_check.sh 探本地 /health |
| **multinode 多节点** | 1 个 `role-1` | 1(默认)/ M | 请求体 **`unit_configs[].count`=副本内节点数 N**(单副本资源实例数为多,`group_configs[].count`=1);ModelArts 注入 `GLOBAL_RANK_TABLE_FILE_PATH`(rank table JSON 路径)与 `POD_IP`(当前节点 IP)——脚本经 `get_master_ip.py` 读取 rank table 取 master IP 与 `--dp-size` 推导 `DATA_PARALLEL_SIZE`,与 `POD_IP` 比较判定 master/slave 角色(slave 追加 `--headless`: vLLM 0.23.0 默认加;`DP_LB_MODE=external|hybrid` 时不加)+ **超节点亲和组=N** | 所有节点探 master /health |
| **pd PD 分离** | **2 个: prefill + decode**(同一部署单元内) | 1(默认)/ M(可靠性,资源翻倍) | **同一部署单元内 2 个推理单元分别注入 `VLLM_ROLE=prefill` 与 `VLLM_ROLE=decode`** + 双角色不同 `PORT`(如 8080/8081)+ 各 `unit_configs[].count`=该角色节点数 | 各角色按注入 PORT 探 /health |
| **pd_colocate PD 共置** | 1 个 `role-1` | 1(默认)/ M | **无需注入任何角色/端口环境变量**——对齐官方 glm_5_2.sh 单引擎 DP 形态,PD 分工由 vLLM 引擎内部完成;仅需 `unit_configs[].count`=N + **超节点亲和组=N** | 所有节点探 master /health |

> **结论**: 需要**用户/部署配置**处理的只有 —— pd(PD 分离)在单部署单元内 2 个推理单元注入 `VLLM_ROLE` 与双角色不同 `PORT`;模型文档要求不同于默认值时覆盖 `MAX_MODEL_LEN`/`DTYPE`/`TENSOR_PARALLEL_SIZE`。**multinode 与 pd_colocate 对齐官方单引擎 DP 形态,无需注入任何角色变量**(master/slave 由 `get_master_ip.py` 自动判定;`DATA_PARALLEL_SIZE` 由 `get_master_ip.py --dp-size` 动态推导);`TP_SIZE` 已由脚本按资源规格自动推导;健康检查失败次数已自动设 300(见步骤 4.2 第 5 步单元配置);其余全部有默认值或容器内固定,无需用户输入**。
> **A5(snt9e/950 系列)差异(与上表通用行为无关)**: 上表是 A2/A3 验证的部署配置。**A5 资源池部署时,请求体须补充 A5 特殊字段**(`group_configs[].workload_type="LWS"`/`async_scheduling=true`/`advanced_config`/`secret_type="dew"` 等,完整清单见 4.3 请求体结构与 reference 第三节"A5 特殊字段")——方式 A 用 `create_infer_service.py create --chip-model a5` 自动注入;方式 B 控制台部署时控制台会自动生成这些字段,无需人工填。
> 详细字段映射与 PD 多角色配置见 `references/modelarts-console-guide.md`(新版 API 字段详解)。

### 4.5 配套生命周期管理(方式 A API 自动)

| 操作 | 命令 | 说明 |
|------|------|------|
| 扩缩容 | `IAM_TOKEN=<IAM_TOKEN> python scripts/create_infer_service.py scale --service-id <ID> --deployment-id <DID> --replicas 2` | 调整部署副本数(token 用环境变量或 `--token-file`,禁止命令行明文) |
| 更新配置 | 新版 API(UpdateService/重新部署) | 按需参考官方 API |
| 资源释放 | **不自动操作** | 资源不足(8118)/服务名占用(8006)时,**禁止 skill 自动 stop 或 DELETE 任何服务**——查可用卡数 + 占用清单告知用户,由用户自行在控制台停止,或明确指示 skill 停止指定 service_id(见 4.3) |

## 步骤 5: 验证服务就绪与获取调用端点(两种方式通用)

**方式 A(API 自动)**: `IAM_TOKEN=<IAM_TOKEN> python scripts/create_infer_service.py list --endpoint ... --project-id ... --workspace-id <WORKSPACE_ID>`(拿 service_id,**所有环境必须带 workspace-id,GET 接口 `cmd_list`/`cmd_show` 已用 `append_workspace_query()` 拼接 `?workspaceId={}&workspace_id={}` 双查询参数 + `X-Workspace-Id` 头,不带则查到其他工作空间服务或空,误判无同名服务**);`... show --endpoint ... --project-id ... --workspace-id <WORKSPACE_ID> --service-id <SERVICE_ID>`(拿部署状态与调用端点)。**⚠️ list API 响应字段是 `data[]`(非 `services[]`/`items[]`)**: create_infer_service.py 已按 `data` 字段解析;若用其他脚本调 list API,必须取 `resp.json()["data"]`,取错字段会显示空列表误判无服务。**⚠️ list 查不到 ≠ 服务不存在**: GetServices(list) 可能不返回 FAILED/DELETING/STOPPING 等非运行态服务,但该服务仍占用资源池卡数(见 4.3"失败/旧服务资源清理");判断是否有同名/旧服务,以**资源池可用卡数**与 create 返回的 `8006`/`8118` 为准,不要因 list 为空就认定可安全创建。

**方式 B(控制台手动)**: 在线服务列表页查看状态,单击服务名进入详情页获取 **"公网调用 URL"**(`access_address`)。

> **⚠️ 调用端点(predict_url)**: 服务 `RUNNING` 后 `show` 详情若 `access_address: null`,调用端点位于 **`predict_url[]`** 字段(如 `"predict_url": [{"type": "PUBLIC", "urls": ["100.93.1.22"]}, ...]`)。**调用 URL 格式**: `http://{PUBLIC_IP}/v2/infer/{service_id}/v1/chat/completions`(OpenAI 兼容)。注意: ① 协议必须是 **http**(用 https 报 `400 ModelArts.8910 Request protocol: HTTPS does not match...`);② 路径必须带 `/v2/infer/{service_id}` 前缀(裸 IP + `/v1/chat/completions` 报 `404 ModelArts.2836 Path not found`)。

**通用要点**: 等待状态变为 **`RUNNING`**(部署中 `DEPLOYING`,失败 `FAILED`);若 `access_address` 为 None,改用 `predict_url[].urls[]` 中 `type=PUBLIC` 的地址按上述格式拼接;若反复重启,优先检查探针 startup 延迟与失败次数配置(见常见问题排查"服务反复重启");code 目录(`CODE_OBS_PATH`)通过**文件存储挂载**到容器内 **`/home/ma-user/code/`**,启动/探针命令一律用容器内路径(`bash /home/ma-user/code/start_vllm.sh`、`bash /home/ma-user/code/health_check.sh startup`),脚本内引用同目录文件用 `$(dirname "$0")` 相对定位。

## 步骤 6: 调用服务验证

服务就绪后,通过 OpenAI 兼容 API 验证(脚本: `scripts/test_inference.py`)。**调用端点自动从步骤 5 获取(`access_address` 为 null 时为 `http://{PUBLIC_IP}/v2/infer/{service_id}/v1/chat/completions`);若服务配置了推理请求认证,用 AskUserQuestion 交互式收集推理 token(文本输入,question 中写明格式)**:

```bash
python scripts/test_inference.py --url https://<modelarts-inference-endpoint>/v1/chat/completions \
    --token <token> --model <MODEL_NAME> --prompt "你好,请介绍一下你自己"
# 可选参数: --max-tokens 256 --temperature 0.7
```

> **验证要点**: 返回 `choices[0].message.content` 有正常文本 → 部署成功;本地联调可用 `http://127.0.0.1:8080/v1/chat/completions` 先验证脚本与参数,再上云。**完整调用逻辑见 `references/verification-method.md`**(OpenAI 兼容调用示例、认证处理、验证失败定位)。

## 输出格式

各步骤输出: ① 交互式确认 — AskUserQuestion options(模型候选/部署形式/部署方式等);② 部署产物 — `./<模型名>-<部署方式>/` 下 `start_vllm.sh`/`health_check.sh`(多节点含 `get_master_ip.py`),上传至 `CODE_OBS_PATH`;③ 控制台指导 — 9 步分步打印(占位符替换为该模型确定值);④ API 部署 — 服务 `id`/`status` 与调用端点 URL;⑤ 调用验证 — `choices[0].message.content` 返回文本。

## 最佳实践

- 模型/部署形式/部署方式等**一切决策点先用 AskUserQuestion 与用户确认**,禁止替用户决策
- 镜像 tag 与启动参数**一律以 vllm-ascend 模型文档为准**;官方文档不可达时按降级机制披露
- 生成产物前**重新 Read/grep 模板与 SKILL.md**(以磁盘当前内容为准),确定性取值(端口 8080/失败次数 300/启动延迟 600s)不凭记忆填
- token/AK-SK **经环境变量或 600 权限 token-file 传递**;提取 token 用 Python 正则,禁 shell 管道
- 部署失败重试前先查资源池可用卡数与占用清单告知用户,**由用户决定是否释放资源**(禁止 skill 自动 stop/DELETE);本方案仅适用于功能验证/原型测试

## 常见问题排查

> **完整排查表见 `references/troubleshooting.md`**(按现象定位根因与排查动作)。高频问题速览:
>
> | 现象 | 根因 | 快速处理 |
> |------|------|---------|
> | 服务反复重启(最常见) | 健康检查启动延迟过短,vLLM V1 首启 5~10 分钟被杀重启 | 启动延迟 600s + 失败次数 300(部署配置已自动设 300);探针路径/端口与脚本一致 |
> | `ValueError: No available memory for the cache blocks` | `TP_SIZE` 从 `ASCEND_RT_VISIBLE_DEVICES` 动态推导,ModelArts 注入单卡 → TP=1,大模型权重装不进单卡显存,KV cache 为负 | 脚本 `TP_SIZE` 改为模型文档推荐的固定值(如 2/4/8);自检 H12 强制校验 |
> | 启动即退出 `exec format error` | 镜像架构非 arm64 / 非标准镜像(MindIE/ATB) | `docker inspect` 查 Architecture;镜像类型识别见 2.1 |
> | `Transformers does not recognize this architecture` | 镜像内 transformers 过旧,不识别实验性模型新架构 | 核对模型文档版本 vs 镜像 tag;换新版镜像或稳定模型 |
> | `Syntax error: "(" unexpected` | 脚本被 `sh` 执行 | 启动命令用 `bash /home/ma-user/code/start_vllm.sh` |
> | `Repo id must be in the form...` | 模型权重未挂载(MODEL_PATH 下无 config.json) | 核对 OBS 存储地址层级/挂载路径/认证凭据;脚本内置 config.json 自检 |
> | `400 ModelArts.8118 Insufficient NPU resources` | 失败/停止的旧服务仍占用资源池全部卡数 | ① 查资源池节点可用卡数(`GET /v2/{project_id}/pools/{pool_id}/nodes` 的 `availableResources`);② list 查占用卡数的服务清单告知用户,由用户决定停止哪个(禁止 skill 自动 stop/DELETE);**若 list 查不到旧服务(非运行态不返回)仍按 8118 处理** |
> | `400 ModelArts.8006 service name exists` | 服务名已被占用(同地域唯一,含本 skill 本次会话创建的旧服务) | 不自动 stop;查占用服务状态告知用户,换新服务名(原名加 `-2`/`-3`)创建;用户明确指示停止某 service_id 时才执行 stop(见 4.3);**禁止 DELETE** |
> | `400 ModelArts.8006 + 8118 同现` | 旧服务占同名+占资源,list 查不到(非运行态) | 资源池可用卡数为 0 → 查占用清单告知用户,由用户决定停止哪个(禁止 skill 自动 stop/DELETE);判断服务存在以资源池卡数+8006/8118 为准 |
> | `400 name/type/group_configs/runtime_config 缺失` | 请求体用了旧骨架 `service.deployment.roles[]` | 用 4.3 顶层平铺结构;`show` 反推正确结构 |
> | `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled` | **请求 body 顶层缺 `workspace_id`**(资源池实际存在且 X-Infer 已启用;不是资源池不存在,也不是请求头/URL 查询参数问题) | 请求 body 顶层补 `"workspace_id": "<WORKSPACE_ID>"`(与 `name`/`type` 同级)后重新创建;`create_infer_service.py create` 已自动注入(骨架与 `--raw-json` 路径),`validate_request_body()` 校验缺失;若仍报错再查资源池 X-Infer 开关 |
> | 401/403 `decrypt token fail` | IAM Token 失效(24h)或复制截断 | 重新获取 token;IAM API + Python 正则完整提取(禁 shell 管道) |
> | `400 ModelArts.6404 Flavor not found` | `unit_configs[].flavor` 误填资源池节点规格(如 `modelarts.bm.npu.arm.ssd`) | 改填从查询纳管资源池详情(ShowInferServiceCluster)获取的推理实例规格(见步骤 0 第 ⑦ 条) |
> | `400 ModelArts.8003 Cannot find a specific flavor` | `unit_configs[].flavor` **字段缺失或无值**(非格式错误;与 6404 区分: 8003=字段缺失,6404=值不是合法 flavor id) | 在 `unit_configs[]` 补 `flavor` 字段,值从 ShowInferServiceCluster `flavors[]` 按 `ascend.npu` 取 id;提交前确保走 `create_infer_service.py` 的 `validate_request_body()`(已含 flavor 必填校验),禁止绕过脚本手写请求体直接 POST |
> | `RuntimeError: Remote engine N must use --headless unless in external or hybrid dp lb mode` | vLLM 0.23.0 **默认** DP LB 模式 slave 未加 `--headless`(脚本错误按 `DATA_PARALLEL_SIZE_LOCAL=1` 反向判断)。**模板的 `DP_LB_MODE` 判断逻辑本是对的**(默认→加 `--headless`,external/hybrid→不加),**禁止按 `dp_local` 改判**(校验脚本 H14 旧版误判已修复) | slave 分支按模板 `DP_LB_MODE` 判断:默认/未设置→`--headless` + 占位 http server(承接探针);显式 `DP_LB_MODE=external|hybrid`→不加。重跑 `check_artifacts.py` H14 校验通过后再上传 |
> | 查工作空间/资源池列表为空 | 域名用错 / 权限不足 / workspace 查询参数未带 | 确认域名 `modelarts.<region>.myhuaweicloud.com`;GET 接口带 `?workspaceId={}&workspace_id={}` 双查询参数(除工作空间列表接口外)+ `X-Workspace-Id` 头 |
> | list 返回其他工作空间的服务 | list API 的 `X-Workspace-Id` 头不起过滤作用,需 URL 双查询参数 | list URL 拼接 `?workspaceId={}&workspace_id={}` 双查询参数(`create_infer_service.py` 已用 `append_workspace_query()` 修复) |

## 参考文件

- `references/deployment-form-decision.md` — **部署形式决策矩阵(4 形式全覆盖)**: 4 形式对比、ModelArts 关键概念(部署单元/推理单元/副本数/超节点亲和组)、四阶段决策流程(1.1a~1.1d)、模型规模×硬件速查、副本/实例取舍算法、形式×步骤影响矩阵
- `references/modelarts-console-guide.md` — **新版在线服务部署详解**: 控制台 9 步分步操作 + 4 形式控制台速查表;CreateInferService 顶层平铺请求体 JSON 示例 + 字段说明、4 形式 → group_configs/unit_configs 映射矩阵、探针配置、生命周期 API
- `references/vllm-ascend-model-doc-guide.md` — vllm-ascend 模型适配文档查阅指南:URL 结构、模型页面章节、镜像 tag 提取、部署形式线索、常见环境变量速查
- `references/ascend-hardware-matrix.md` — 昇腾芯片型号(A2/A3/310P)速查:产品形态、显存、不同芯片 × 模型规模的卡数配置
- `references/iam-policies.md` — **IAM 最小权限策略**(OBS/SWR/ModelArts/IAM 各操作所需 Action 与 IAM API token 获取请求体示例)
- `references/verification-method.md` — **部署验证方法**(方式 A/B 验证步骤、OpenAI 兼容调用检查、常见验证失败定位)
- `references/acceptance-criteria.md` — **验收标准**(部署成功判定、产物核对清单)
- `references/artifact-check.md` — **部署产物自检清单**(上传 OBS 前强制关卡): 可用性硬性(H01~H12)+ 性能软性(S01~S04),对照华为云最佳实践 + vllm-ascend 模型文档
- `references/troubleshooting.md` — **常见问题排查全表**(现象 → 根因 → 排查动作)
- `references/cli-installation-guide.md` — **KooCLI(hcloud)安装指南**: 下载地址、跨平台安装步骤、AK/SK 配置、常见安装问题
- `scripts/create_infer_service.py` — 新版推理 API 部署脚本(create/list/show/scale;**不提供 delete/stop 命令**——资源释放由用户决定;`--raw-json` 整体传平铺请求体;**token 禁命令行传参,经 `IAM_TOKEN`/`--token-file`(600)/交互式提供**)
- `scripts/check_artifacts.py` — **部署产物自检脚本**(步骤 3.4 强制关卡): 可用性硬性 H01~H12 + 性能软性 S01~S04 静态校验,FAIL 禁止上传(清单见 `references/artifact-check.md`)
- `scripts/upload_code_to_obs.py` — 用 OBS Python SDK(`esdk-obs-python`)上传部署产物到 OBS code 目录(支持 `--code-obs-path` 或 `--model-obs-path` 推导)
- `scripts/pull_push_image.sh` — Quay.io 拉取 + SWR 推送辅助脚本(`--login` 传登录命令(仅支持 `--password-stdin`,密码经 `SWR_PASSWORD` 环境变量注入)
- `scripts/get_master_ip.py` — 多节点/PD 共置场景**角色识别脚本**(从 ModelArts 注入的 `GLOBAL_RANK_TABLE_FILE_PATH` 全局 rank table 取 master IP、dp_rank 与 `--dp-size` 数据并行总数;多节点/pd_colocate 需随脚本一并复制上传)
- `scripts/test_inference.py` — OpenAI 兼容 API 调用验证脚本;`scripts/download_model.py` — 权重下载命令示例(供用户参考);`scripts/obs_upload.sh` — obsutil 上传权重辅助脚本
- `templates/start_vllm.single.sh` — 单节点启动模板(单机单卡/多卡 TP;内置权重挂载自检;不含 `DEPLOY_FORM` 运行时分支)；`templates/start_vllm.multinode.sh` — 多节点启动模板(master/slave 角色判定经 `get_master_ip.py` 读 rank table、`POD_IP` 比较;`HCCL_IF_IP`/`GLOO_SOCKET_IFNAME` 多网卡绑定;`--data-parallel-*` 参数;**`DATA_PARALLEL_SIZE` 经 `get_master_ip.py --dp-size` 动态推导**;slave 追加 `--headless`)；`templates/start_vllm.pd.sh` — PD 分离启动模板(Prefill/Decode 双角色,VLLM_ROLE 注入、各自端口)；`templates/start_vllm.pd_colocate.sh` — PD 共置启动模板(**对齐官方 glm_5_2.sh 单引擎 DP 形态**,无需 `VLLM_ROLE`;master/slave 经 `get_master_ip.py` 读 rank table 判定;`--data-parallel-*` 参数 + slave `--headless`;单一 PORT)；`templates/health_check.sh` — 统一健康检查模板(startup/liveness/readiness 三类探针,按是否存在 `get_master_ip.py` 区分单/多节点)

## 文档来源

- 华为云官方最佳实践《从vLLM-Ascend开源社区获取模型部署在ModelArts推理平台》: https://support.huaweicloud.com/intl/zh-cn/bestpractice-modelarts/modelarts_10_3121.html
- 创建推理服务(CreateInferService)API / 旧版在线服务迁移 / 模型推理(新版)使用指南: https://support.huaweicloud.com/api-modelarts/CreateInferService.html · https://support.huaweicloud.com/intl/zh-cn/inference-modelarts/inference2.0-modelarts-0080.html · https://support.huaweicloud.com/intl/zh-cn/inference-modelarts/inference2.0-modelarts-0002.html
- GLM5.1-w8a8 Atlas800I A2 PD 分离部署(昇腾论坛)/ ModelArts 跨超节点调度故障排除: https://www.hiascend.com/dev/forum/thread-02192217146677654095-1-1.html · https://support.huaweicloud.com/intl/zh-cn/trouble-modelarts/inference2.0-modelarts-0042.html
