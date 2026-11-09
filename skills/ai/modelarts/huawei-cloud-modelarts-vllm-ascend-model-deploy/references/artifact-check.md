# 部署产物自检清单(artifact-check)

本文件定义 ModelArts 部署产物(`start_vllm.sh` / `health_check.sh` / `get_master_ip.py`)在**上传 OBS 前的强制自检关卡**(SKILL.md 步骤 3.4)。自检依据: **华为云官方最佳实践《从 vLLM-Ascend 开源社区获取模型部署在 ModelArts 推理平台》(modelarts_10_3121)+ vllm-ascend 模型适配文档(该模型页面)**。

> **执行方式(强制)**: 产物生成后、上传 OBS 前,运行 `scripts/check_artifacts.py` 自动静态校验:
> ```bash
> python scripts/check_artifacts.py --artifact-dir ./<模型名>-<部署方式> \
>     --deploy-form single|multi_node|pd \
>     --doc-params '<模型文档推荐参数 JSON>' \
>     --model-doc-url <模型文档 URL> \
>     --tp-size <卡数> --dp-size <节点数>
> ```
> 退出码 0 = 全部硬性通过可上传;1 = 存在 FAIL(禁止上传);2 = 参数错误。

## 一、可用性检查(硬性,FAIL 不得上传)

| 编号 | 检查项 | 判定标准 | 违反后果 |
|------|--------|---------|---------|
| H01 | 产物文件齐全 | 必含 `start_vllm.sh`、`health_check.sh`;多实例 DP>1(multi_node/pd 每角色多实例 多实例)必含 `get_master_ip.py`,单实例 DP=1 不含 | 部署时脚本缺失,实例启动失败 |
| H02 | LF 行尾 | 全部 `.sh`/`.py` 无 CRLF(`\r\n`);Windows 编辑/复制会带 CRLF,bash 报 `$'\r': command not found` | bash 无法执行,startup 探针失败转 FAILED |
| H03 | bash 语法 | `bash -n` 对 `start_vllm.sh`/`health_check.sh` 通过 | 语法错误直接启动失败 |
| H04 | bash 数组 | `start_vllm.sh` 含 `MODEL_ARGS=(...)` bash 数组定义 | 脚本被 `sh` 执行时报 `Syntax error: "(" unexpected` |
| H05 | 权重挂载自检 | 脚本检查 `${MODEL_PATH}/config.json` 存在,缺失时打印挂载目录并退出 | 权重未挂载时 vllm 报晦涩错误 `OSError: Repo id must be in the form...` |
| H06 | 端口一致性 | 启动脚本默认 `PORT` 与探针脚本/部署配置一致(默认 8080;PD 按角色 PORT) | 探针探测端口错位,健康检查失效 |
| H07 | 探针命令 | `health_check.sh` 含 `startup`/`liveness`/`readiness` 三类探针分支 | 探针命令缺失,部署无法就绪 |
| H08 | 多实例/PD 适配 | DP>1 时脚本引用 `get_master_ip.py`(取 master IP/`--dp-size` 推导 `DATA_PARALLEL_SIZE`)且文件存在;DP=1 不需要 | 跨节点无法判定 master/worker,分布式启动失败 |
| H09 | PD 分离适配 | `start_vllm.sh` 含 `VLLM_ROLE` 角色分支(prefill/decode) | 双角色实例无法区分角色,启动失败 |
| H10 | 相对路径定位 | 脚本内文件引用用 `$(dirname "$0")` 相对定位,禁硬编码 `/code/` | 挂载路径非 `/code/` 时探针报 `can't open file '/code/xxx.py'` |
| H11 | 模型文档必备参数 | `--doc-params` 传入的模型文档推荐参数均包含在脚本中(如 `--quantization`、`--speculative-config`、`--compilation-config` 等) | 缺模型必要参数,模型无法加载/精度异常 |
| H12 | TP_SIZE 固定值与文档一致 | `TP_SIZE`/`TENSOR_PARALLEL_SIZE` 默认值为**固定数字**(非动态推导),且与 `--tp-size` 一致;**若提供 `--num-attention-heads`(模型注意力头数),TP 必须能被头数整除(`头数 % TP == 0`),否则 FAIL** | 动态推导 → ModelArts 注入单卡 TP=1 → 大模型权重装不进单卡显存 → KV cache 为负 → 崩溃 `ValueError: No available memory for the cache blocks`;**TP 不能被模型注意力头数整除 → vLLM 启动硬校验崩溃 `ValueError: Total number of attention heads (N) must be divisible by tensor parallel size`(实测 Qwen3.8-27B 头数 24 + TP=16 → master/worker 全部崩溃,整服务无法启动)。TP 必须取头数的约数且 ≤ 单节点卡数 |
| H13 | 角色专属参数归属校验 | 非 single 形式(multi_node/pd)产物 `MODEL_ARGS=(...)` 数组**不得包含**角色专属参数(`--api-server-count`/`--nnodes`/`--node-rank`/`--master-addr`/`--master-port`) | 角色专属参数(仅 master 命令有)放入共享 `MODEL_ARGS` → worker 节点同时获得该参数与模板自动追加的 `--headless` → vllm 参数校验拒绝(如 `ValueError: --api-server-count=1 cannot be used with --headless`)→ worker 在参数解析阶段崩溃,部署失败 |
| H14 | `--headless` 与 DP LB 模式匹配 | 非 single 形式(multi_node/pd)产物中 `--headless` 必须按 `DP_LB_MODE` 条件判断: 默认/未设置 → worker 加 `--headless`(**禁止占位 http server**——会占用 PORT 与 vLLM `--master-port` PP/DP 通信冲突,worker 卡在 `distributed_init`,日志卡在 `cpu_binding.py` 之后无法进入 `parallel_state.py`);`DP_LB_MODE=external\|hybrid` → 不加。脚本必须含 `DP_LB_MODE="${DP_LB_MODE:-none}"` 判断分支、默认分支含 `WORKER_OPTS="--headless"` 与 `export DATA_PARALLEL_SIZE=2`(触发 health_check.sh 探 master /health);否则 FAIL | vLLM 0.23.0 **默认**非 external/hybrid DP LB 模式: worker **必须**追加 `--headless`,否则报 `RuntimeError: Remote engine N must use --headless unless in external or hybrid dp lb mode`,worker 启动崩溃、部署反复重启(实测 vLLM 0.23.0 + multi_node 2 节点 BF16 部署触发)。**禁止按 `DATA_PARALLEL_SIZE_LOCAL` 判断**——旧版 H14 误以为 `dp_local=1` ⇒ external LB ⇒ 禁 `--headless`,与 vLLM 0.23.0 实际行为相反,导致模板正确逻辑被误改坏。**禁止占位 http server**(实测 Kimi K3.1 Pro 4P4D Prefill P1-P3 worker 启动 `nohup python -m http.server 8080` 占用 8080,vLLM `--master-port 8080` 连本地占位 server 而非 P0 master,分布式初始化卡住) |
| H15 | 量化参数 × 权重文件交叉校验 | `start_vllm.sh` 必须含量化参数 × 权重文件交叉校验代码段(校验目标文件 `quant_model_description.json`): 启用 `--quantization ascend`(来源: `MODEL_ARGS`/`EXTRA_ARGS`/`PD_EXTRA_ARGS`/`QUANTIZATION` 环境变量驱动 `QUANT_OPTS`)但权重目录无 `quant_model_description.json` → 启动前直接 exit 1 报错;反之权重目录含该文件但未启用 → WARN 提示。**脚本侧该检查是运行时兜底,本 H15 是上传前预检**(校验脚本是否含交叉校验代码段) | BF16 原版权重误带 `--quantization ascend` → 启动崩溃 `ModelSlim Quantization Config Not Found`(实测 Qwen3.8-27B BF16 + 文档示例 #3 含 `--quantization ascend` → 启动失败);w8a8 量化版权重误漏 `--quantization ascend` → 推理精度退化。根因: vllm-ascend 模型适配文档常覆盖多权重版本启动示例,易错把量化版示例参数套用到 BF16 原版权重(见 SKILL.md 步骤 3.1 第 7 条"权重版本 × 启动参数严格对应"对应表) |
| H16 | PD 模板 kv-transfer-config 内 tp_size/dp_size 变量化 | **仅 PD 形式**(`deploy_form=pd`)校验: `start_vllm.sh` 中 `KV_TRANSFER_CONFIG` 拼装行内的 `kv_connector_extra_config.{prefill,decode}.tp_size` 必须为 `${TP_SIZE}` 变量引用、`dp_size` 必须为 `${DATA_PARALLEL_SIZE}`(由 ModelArts envs 注入(步骤 1.2 确认 N))变量引用,**出现裸数字(如 `tp_size: 1`)即 FAIL**;非 PD 形式直接跳过(该 JSON 仅 PD 模板存在) | 模板早期版本硬编码 `tp_size:1`/`dp_size:1`: 硬编码 `tp_size:1` 在 TP>1 时触发 pydantic 校验 `KV transfer 'prefill' config has a conflicting tensor parallel size. Expected 2, but got 1`;硬编码 `dp_size:1` 在 DP>1 时触发 `KV transfer 'prefill' config has a conflicting data parallel size. Expected 2, but got 1`,均在模型权重加载前分钟级内秒级退出(非应用超时),prefill/decode 两角色实例同时崩溃(实测 Qwen3.8-27B BF16 + PD + TP=2 → 两角色同时 ValidationError 崩溃)。根因: `kv_connector_extra_config.{prefill,decode}.{tp_size,dp_size}` 描述各角色 vLLM 引擎内部 KV cache 分片方式,tp_size 必须等于该角色 `--tensor-parallel-size`,dp_size 必须等于该角色 `--data-parallel-size`(总 DP,非每节点 `--data-parallel-size-local`),与角色数正交,不能写死 |
| H17 | enable_flashcomm1 × TP_SIZE 通用交叉校验 | **所有部署形式覆盖**(single/multi_node/pd,与形式无关): `--tp-size` 入参为 1 时,`start_vllm.sh` 中 `enable_flashcomm1` 实际启用(`"enable_flashcomm1": true` JSON 值,含 `\"` 转义变体)即 FAIL;**仅匹配 JSON 启用值,排除注释/说明性字符串**;TP>1 时不限制;未提供 `--tp-size` 时跳过 | vLLM 0.23.0 AscendConfig pydantic 校验 `Assertion failed, Flash Comm v1 is only supported when tp_size > 1.`,TP=1 时 `create_engine_config` 阶段崩溃(模型权重加载前分钟级秒级退出,非应用超时,实测 Qwen3.8-27B BF16 + multi_node + TP=1 + `--additional-config '{"enable_flashcomm1":true}'` → 两实例同时 ValidationError 崩溃)。根因: agent 误把文档量化版示例(含量化版 `enable_flashcomm1`)当 BF16+TP=1 示例套用;该约束与部署形式无关,vLLM 0.23.0 在任何形式下 TP=1 套用 `enable_flashcomm1` 均崩(见 SKILL.md 3.1 "enable_flashcomm1 × TP_SIZE 通用约束")。修复: `--additional-config` 移除 `enable_flashcomm1`,仅留 `enable_cpu_binding` |
| H18 | 第一推理单元不能是 worker/decode | **multi_node/pd 形式**校验: 部署的第一推理单元(group 0 / `unit_configs[0]`)不能出现 worker 或 decode 启动的实例——ModelArts 在线服务所有请求都发送到 group 0,worker/decode 不具备接受请求功能。`unit_configs[0]` 必须是: single=master / multi_node=master(实例数=1,不加 --headless) / pd=proxy(0 卡自定义规格)。实际请求体层校验由 `create_infer_service.py validate_request_body()` 承载,本检查作为产物侧补充(产物脚本不含 unit_configs 顺序信息,仅做角色分支存在性校验) | ModelArts 平台约束: server_group_list group 0 = 流量入口,凡是对外提供 API 的角色(master、proxy)必须落在 group 0。worker/decode 不接受请求,放在 group 0 会导致请求转发到无法处理的实例 |
| H19 | PD 分离 kv_port 范围校验 | **pd 形式**校验: `start_vllm.sh` 中 `KV_PORT` 默认值须避开 Mooncake AscendDirectTransport 随机端口范围 `[20000, 20000 + npu_per_node × 1000)`:8 卡 → kv_port ≥ 28000;16 卡 → kv_port ≥ 36000。`KV_PORT="${KV_PORT:-<值>}"` 中 `<值>` 不满足范围即 FAIL | kv_port 与 AscendDirectTransport 随机端口冲突会导致间歇性 `zmq.error.ZMQError: Address already in use`(官网 F4 约束) |
| H20 | health_check.sh decode 角色探本地 /health | **PD 形式**(`deploy_form=pd`)校验: `health_check.sh` 的 readiness 探针分支中 `VLLM_ROLE=decode` 必须**探本地 /health**(`target_ip=127.0.0.1`),**禁止调用 `get_master_ip.py` 探 group master**;仅 prefill worker(P1-P3)/multi_node worker 探 master。脚本须含 `if [ "${VLLM_ROLE:-}" != "decode" ]` 包裹 `get_master_ip.py` 调用;否则 FAIL | vLLM 文档 Kimi K3.1 Pro 4P4D 明确 Decode 4 节点**各自独立暴露 API**(D0-D3 各自 API endpoint),每节点应独立健康检查。旧版 health_check.sh 无差别对所有 DP>1 角色调 `get_master_ip.py 2` 取 D0 IP,导致 D1-D3 readiness 探 D0 跨节点 /health——D0 加载中未就绪或跨节点网络不通时 D1-D3 readiness 失败,不被标 ready(无健康检查日志,实测 Kimi K3.1 Pro 4P4D D1-D3 `Application startup complete` 后无健康检查日志) |

| H21 | health_check.sh PP/DP worker 进程匹配 | **PD/multi_node 形式**校验: `health_check.sh` 的 `check_process()` 除 `vllm serve`/`vllm.entrypoints.openai.api_server` 外,**必须额外匹配 `vllm.v1.worker`/`base_worker.py`**(PP/DP worker `--headless` 容器内无 `vllm serve` 独立进程,由 EngineCore 经 RPC fork 的 `Worker_PP*`/`Worker_DP*` 子进程,命令行含 `vllm.v1.worker`/`base_worker.py`);脚本须含 `pgrep -f "vllm.v1.worker" \|\| pgrep -f "base_worker.py"` 兜底;否则 FAIL | PP/DP worker(`--headless`)容器内无 `vllm serve` 独立进程(由 P0/D0 EngineCore 经 multiproc_executor RPC fork 的远程 worker 子进程),`pgrep -f "vllm serve"` 找不到进程 → startup/liveness 探针失败 → 实例异常/重启循环(实测 Kimi K3.1 Pro 4P4D P1-P3 状态异常,日志止于 `base_worker.py:161 Initializing Mooncake worker`,proxy/D0 运行中;P1-P3 worker 进程实际正常运行,仅探针进程匹配失败导致误判) |
| H22 | health_check.sh decode PORT 按 DP rank 推导 | **PD 形式**校验: `health_check.sh` 的 decode 角色 `PORT` **禁止硬编码为 7100**;必须与 `start_vllm.sh` 一致按 `PORT=$((DECODE_START_PORT + DP_rank))` 推导(DP rank 从 rank table group 2 按 `POD_IP` 索引取);脚本须含 `DECODE_START_PORT` 变量 + rank table 查找 DP rank 的 python 内联段;否则 FAIL | PD 分离 decode 各节点独立暴露 API 且端口递增(D0=7100, D1=7101, D2=7102, D3=7103,文档 4P4D proxy `--decoder-ports` 需不同端口区分 D0-D3);旧版 health_check.sh `PORT=7100` 硬编码,所有 decode 实例都探 7100(D0 端口)——D0 监听 7100 探成功,D1-D3 监听 7101/7102/7103 但探 7100 连接失败(不产生 vllm 日志),readiness 失败 → D1-D3 异常(实测 Kimi K3.1 Pro 4P4D D0 运行中收到 7 次 `GET /health 200 OK`,D1-D3 `Application startup complete` 后零探针请求,实例异常) |
| H23 | PP master_port 独立于 API port | **PD 形式含 PP 多节点**(`--pipeline-parallel-size >1`)校验: `start_vllm.sh` 中 `--master-port`(PP 分布式通信端口)**禁止与 `--port`(API server 端口)相同**;必须用独立变量(如 `VLLM_MASTER_PORT=29500`),与 `VLLM_START_PORT`/`PORT` 分离;否则 FAIL | PP 分布式通信(`distributed_init tcp://master:master_port`)先占用端口,uvicorn bind API server 端口失败/阻塞——`Application startup complete` 只是 FastAPI app 初始化完成,但 `Uvicorn running on http://0.0.0.0:PORT` 日志缺失,端口未监听,readiness 探针连接拒绝,实例状态异常;P1-P3 PP worker 因 P0 EngineCore 卡住(Mooncake scheduler handshake 等待)而阻塞(实测 Kimi K3.1 Pro 4P4D P0 `non-default args` 中 `port: 8080, master_port: 8080`,P0 `Application startup complete` 后无 `Uvicorn running`,P1-P3 卡在 `cpu_binding.py` 之后) |

> **说明**: H01~H10 由脚本静态检查;H11 依赖 agent 从模型文档提取的参数清单(经 `--doc-params` 传入),未提供时脚本提示"建议提供"而非 FAIL——但 skill 流程要求**必须从模型文档提取参数清单并传入**(见 SKILL.md 步骤 3.1)。**H12 为硬性检查**: ① TP_SIZE 默认值从 `ASCEND_RT_VISIBLE_DEVICES` 动态推导时直接 FAIL(根因: ModelArts 注入单卡 → TP=1 → OOM 崩溃),必须改为模型文档推荐的固定数字;② 提供 `--num-attention-heads` 时,TP 必须能被模型注意力头数整除(硬性,FAIL)——头数从模型 config.json 的 `num_attention_heads` 字段获取(如 Qwen3.8-27B=24),TP 取值必须为头数的约数且 ≤ 单节点卡数(实测头数 24 + TP=16 → vLLM 启动校验崩溃)。**H13 为硬性检查**: 针对非 single 形式(multi_node/pd);`--headless` 本身由模板 `WORKER_OPTS` 自动处理,不在检查范围,不得误报。

## 二、性能最优检查(软性,WARN 提示不阻断上传)

| 编号 | 检查项 | 提示内容 | 处理建议 |
|------|--------|---------|---------|
| S01 | 模型文档性能参数齐全度 | 文档推荐参数未在脚本中发现(可能经 `EXTRA_ARGS` 注入,或确实缺失) | 对照模型文档核对;确认是否通过环境变量/`MODEL_ARGS` 注入 |
| S02 | 昇腾环境变量 | `PYTORCH_NPU_ALLOC_CONF`/`HCCL_BUFFSIZE`/`OMP_PROC_BIND` 等未发现(以模型文档为准,文档未要求可不加) | 按模型文档补充;`PYTORCH_NPU_ALLOC_CONF=expandable_segments:True` 减少显存碎片 |
| S03 | DP 匹配 | 脚本默认 `DATA_PARALLEL_SIZE` 与资源规格不符(TP 已由 H12 硬性检查) | 部署时用环境变量覆盖或按资源规格修正模板默认值 |
| S04 | 部署配置建议 | 非 single 形式需超节点亲和组=N;PD 分离需注入 `VLLM_ROLE`(PORT 已在脚本内按角色内置默认值) | 按 SKILL.md 4.4 部署配置核对 |

> **性能最优判断依据**(对照模型文档,软性项):
> - vLLM V1 引擎参数: `--max-model-len`(上下文长度,按模型支持上限与显存)、`--gpu-memory-utilization`(显存利用率,默认 0.9)、`--max-num-batched-tokens`(每步 token 上限,chunk prefill 生效)、`--max-num-seqs`(并发上限,按吞吐/显存)
> - 图模式优化: `--compilation-config '{"cudagraph_mode":"FULL_DECODE_ONLY"}'`(全解码 ACL 图,降算子调度开销,推荐)
> - CPU 绑定: `--additional-config '{"enable_cpu_binding":true}'`(工作线程绑核,稳定解码延迟,950PR 实测单流 decode 32→63 tok/s)
> - MTP 投机解码: `--speculative-config '{"method":"qwen3_5_mtp","num_speculative_tokens":3,...}'`(解码密集场景,按模型文档确认支持)
> - MoE 专家并行: `--enable-expert-parallel`(MoE 模型按文档)
> - 前缀缓存: `--enable-prefix-caching`
> - 以上参数是否启用、取何值**一律以 vllm-ascend 该模型页面为准**,禁止凭经验猜测;页面未给出的不要擅自补。

## 三、自检结果处置(强制)

1. **FAIL = 0 且通过全部硬性检查** → 可上传 OBS(进入 SKILL.md 步骤 3.4 上传)。
2. **任一 FAIL** → **禁止上传**。按检查项修复产物(转 LF、改 bash 数组、补权重自检、补探针、补模型文档参数等)后**重新运行自检**,直至全部硬性通过。
3. **WARN(软性)** → 不阻断上传,但 agent 必须向用户**披露提示项**(性能优化建议),由用户决定是否调整;若调整则重新生成产物并重跑自检。

## 四、自检与部署验收的关系

- 本自检是**部署前**的产物级检查(静态,本地执行);
- 部署后仍有**运行时验收**(SKILL.md 步骤 5/6: `RUNNING` 状态 + OpenAI 兼容调用验证,见 `references/acceptance-criteria.md`);
- 自检通过 ≠ 部署成功;但自检是部署成功的前置保障,硬性项不通过时部署必然失败或反复重启。
