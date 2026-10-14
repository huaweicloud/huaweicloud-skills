# 部署产物自检清单(artifact-check)

本文件定义 ModelArts 部署产物(`start_vllm.sh` / `health_check.sh` / `get_master_ip.py`)在**上传 OBS 前的强制自检关卡**(SKILL.md 步骤 3.4)。自检依据: **华为云官方最佳实践《从 vLLM-Ascend 开源社区获取模型部署在 ModelArts 推理平台》(modelarts_10_3121)+ vllm-ascend 模型适配文档(该模型页面)**。

> **执行方式(强制)**: 产物生成后、上传 OBS 前,运行 `scripts/check_artifacts.py` 自动静态校验:
> ```bash
> python scripts/check_artifacts.py --artifact-dir ./<模型名>-<部署方式> \
>     --deploy-form single|multinode|pd|pd_colocate \
>     --doc-params '<模型文档推荐参数 JSON>' \
>     --model-doc-url <模型文档 URL> \
>     --tp-size <卡数> --dp-size <节点数>
> ```
> 退出码 0 = 全部硬性通过可上传;1 = 存在 FAIL(禁止上传);2 = 参数错误。

## 一、可用性检查(硬性,FAIL 不得上传)

| 编号 | 检查项 | 判定标准 | 违反后果 |
|------|--------|---------|---------|
| H01 | 产物文件齐全 | 必含 `start_vllm.sh`、`health_check.sh`;多节点(`multinode`)/PD 共置(`pd_colocate`)必含 `get_master_ip.py` | 部署时脚本缺失,实例启动失败 |
| H02 | LF 行尾 | 全部 `.sh`/`.py` 无 CRLF(`\r\n`);Windows 编辑/复制会带 CRLF,bash 报 `$'\r': command not found` | bash 无法执行,startup 探针失败转 FAILED |
| H03 | bash 语法 | `bash -n` 对 `start_vllm.sh`/`health_check.sh` 通过 | 语法错误直接启动失败 |
| H04 | bash 数组 | `start_vllm.sh` 含 `MODEL_ARGS=(...)` bash 数组定义 | 脚本被 `sh` 执行时报 `Syntax error: "(" unexpected` |
| H05 | 权重挂载自检 | 脚本检查 `${MODEL_PATH}/config.json` 存在,缺失时打印挂载目录并退出 | 权重未挂载时 vllm 报晦涩错误 `OSError: Repo id must be in the form...` |
| H06 | 端口一致性 | 启动脚本默认 `PORT` 与探针脚本/部署配置一致(默认 8080;PD 按角色 PORT) | 探针探测端口错位,健康检查失效 |
| H07 | 探针命令 | `health_check.sh` 含 `startup`/`liveness`/`readiness` 三类探针分支 | 探针命令缺失,部署无法就绪 |
| H08 | 多节点/PD共置适配 | 脚本引用 `get_master_ip.py`(取 master IP/`--dp-size` 推导 `DATA_PARALLEL_SIZE`)且文件存在 | 跨节点无法判定 master/slave,分布式启动失败 |
| H09 | PD 分离适配 | `start_vllm.sh` 含 `VLLM_ROLE` 角色分支(prefill/decode) | 双角色实例无法区分角色,启动失败 |
| H10 | 相对路径定位 | 脚本内文件引用用 `$(dirname "$0")` 相对定位,禁硬编码 `/code/` | 挂载路径非 `/code/` 时探针报 `can't open file '/code/xxx.py'` |
| H11 | 模型文档必备参数 | `--doc-params` 传入的模型文档推荐参数均包含在脚本中(如 `--quantization`、`--speculative-config`、`--compilation-config` 等) | 缺模型必要参数,模型无法加载/精度异常 |
| H12 | TP_SIZE 固定值与文档一致 | `TP_SIZE`/`TENSOR_PARALLEL_SIZE` 默认值为**固定数字**(非动态推导),且与 `--tp-size` 一致 | 动态推导 → ModelArts 注入单卡 TP=1 → 大模型权重装不进单卡显存 → KV cache 为负 → 崩溃 `ValueError: No available memory for the cache blocks` |

> **说明**: H01~H10 由脚本静态检查;H11 依赖 agent 从模型文档提取的参数清单(经 `--doc-params` 传入),未提供时脚本提示"建议提供"而非 FAIL——但 skill 流程要求**必须从模型文档提取参数清单并传入**(见 SKILL.md 步骤 3.1)。**H12 为硬性检查**: TP_SIZE 默认值从 `ASCEND_RT_VISIBLE_DEVICES` 动态推导时直接 FAIL(根因: ModelArts 注入单卡 → TP=1 → OOM 崩溃),必须改为模型文档推荐的固定数字。

## 二、性能最优检查(软性,WARN 提示不阻断上传)

| 编号 | 检查项 | 提示内容 | 处理建议 |
|------|--------|---------|---------|
| S01 | 模型文档性能参数齐全度 | 文档推荐参数未在脚本中发现(可能经 `EXTRA_ARGS` 注入,或确实缺失) | 对照模型文档核对;确认是否通过环境变量/`MODEL_ARGS` 注入 |
| S02 | 昇腾环境变量 | `PYTORCH_NPU_ALLOC_CONF`/`HCCL_BUFFSIZE`/`OMP_PROC_BIND` 等未发现(以模型文档为准,文档未要求可不加) | 按模型文档补充;`PYTORCH_NPU_ALLOC_CONF=expandable_segments:True` 减少显存碎片 |
| S03 | DP 匹配 | 脚本默认 `DATA_PARALLEL_SIZE` 与资源规格不符(TP 已由 H12 硬性检查) | 部署时用环境变量覆盖或按资源规格修正模板默认值 |
| S04 | 部署配置建议 | 多节点/PD共置需超节点亲和组=N;PD 分离需注入 `VLLM_ROLE` + 不同 `PORT` | 按 SKILL.md 4.5 部署配置核对 |

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
