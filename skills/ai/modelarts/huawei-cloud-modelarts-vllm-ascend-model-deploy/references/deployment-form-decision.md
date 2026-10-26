# 部署形式决策矩阵(4 形式 × 单部署单元)

本文件支撑 SKILL.md 步骤 1.1"确定部署形式"。核心原则:**以 vllm-ascend 模型适配文档/社区方案为准,结合模型规模与可用硬件判断,最终由用户确认**。禁止脱离文档凭经验猜部署形式。

**收敛为 4 种**(单节点 / 多节点 / PD 分离 / PD 共置),统一**单部署单元**承载(PD 分离为同一部署单元内 2 个推理单元,其余形式为 1 个推理单元)。副本数(单副本/多副本)由"用户可用节点数 + 可靠性需求"在步骤 1.1c 决策,不再独立枚举场景。

## 一、4 种部署形式对比(基础概念)

| 维度 | 单节点(single) | 多节点(multinode) | PD 分离(pd) | PD 共置(pd_colocate) |
|------|---------------|-------------------|-------------|---------------------|
| 推理单元数 | 1 | 1 | **2**(prefill + decode) | 1 |
| 节点数 | 1 | ≥2 | ≥2(每角色各需节点,资源翻倍) | ≥2 |
| 并行方式 | TP ≤ 单节点卡数 | TP 跨节点 + DP(单引擎形态) | 每角色独立 vLLM 实例,各组内 TP | TP 跨节点 + DP(单引擎形态) |
| KV Cache | 实例内 | 实例内 | 各角色实例内 | 实例内 |
| 部署单元 | 1 | 1 | 1 | 1 |
| 角色注入 | 无 | 无 | **`VLLM_ROLE=prefill\|decode` + 双角色不同 `PORT`** | 无(master/slave 经 `get_master_ip.py` 判定) |
| 模板 | `start_vllm.single.sh` | `start_vllm.multinode.sh` | `start_vllm.pd.sh` | `start_vllm.pd_colocate.sh` |
| 通信依赖 | 无 | 跨节点 HCCL/DP | 节点间通信 + 负载均衡 | 跨节点 HCCL/DP |
| 复杂度/成本 | 最低 | 中 | 最高 | 中 |

> **PD 分离 vs PD 共置(核心差异)**: PD 分离 = Prefill 与 Decode 由**不同的推理实例**处理,前端负载均衡分发,吞吐最优但架构复杂、资源翻倍;PD 共置 = Prefill 与 Decode 在**同一推理实例**内由 vLLM 引擎内部调度完成,无前端 LB,架构简单,但 prefill 与 decode 共享资源。两者节点主从角色均经 `get_master_ip.py` 读取 rank table 自动判定,不依赖外部协调组件。

## 二、4 形式 × 副本/实例配置速查

> **ModelArts 层级**: 部署单元 `group_configs[].count`(副本数)承载多副本(可靠性);推理单元 `unit_configs[].count`(单元内实例数)承载跨节点数(单副本多实例)。

| 形式 | 推理单元数 | 单副本多实例(默认) | 多副本单实例(可靠性) | 模板 |
|------|-----------|-------------------|---------------------|------|
| **single** | 1 | `unit_configs[0].count=1` | `group_configs[].count=M`(每副本 1 节点) | `single` |
| **multinode** | 1 | `unit_configs[0].count=N` + 亲和组=N | `group_configs[].count=ceil(M/N)` | `multinode` |
| **pd** | 2(prefill/decode) | 两单元各 `count`=该角色节点数 | `group_configs[].count=ceil(M/(2N))`(**资源翻倍**) | `pd` |
| **pd_colocate** | 1 | `unit_configs[0].count=N` + 亲和组=N | `group_configs[].count=ceil(M/N)` | `pd_colocate` |

## 三、ModelArts 部署关键概念(决策必备)

| ModelArts 概念 | 对应部署维度 | 触发形式 | 说明 |
|---------------|--------------|---------|------|
| **部署单元 group_configs[].count(副本数)** | 多副本(可靠性) | 用户要求可靠性时 | 副本数>1 即多副本,平台内置流量分发;一个副本即一个独立 TP 域。**默认 1(单副本)** |
| **推理单元 unit_configs[].count(实例数)** | 跨节点数 | multinode / pd_colocate | 单副本内多实例承载跨节点数 N(单副本资源实例数为多);PD 分离两单元各 count 为该角色节点数 |
| **超节点亲和组实例数** | 跨节点 TP 亲和 | multinode / pd_colocate | 跨节点 TP 必须配置 = N(副本内节点数),确保多机调度到同一超节点(否则报业务错误) |
| **VLLM_ROLE 注入** | PD 角色区分 | **仅 pd(分离)** | 同一部署单元内 2 个推理单元分别注入 `VLLM_ROLE=prefill\|decode` + 不同 `PORT`;pd_colocate 无需注入 |
| **单元实例规格(N 卡)** | 副本内 TP | 全部 | 单副本内的卡数规格,决定副本内 TP 上限 |

> **重要**: ModelArts 在线服务单服务最大昇腾卡规模 384 卡,单个在线服务最多 5 个部署单元。详见 ModelArts 官方约束与限制。

## 四、vllm-ascend 文档/社区线索(判断依据)

在模型适配文档页面(`https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/<Model>.html`)与社区(昇腾论坛、CSDN、hiascend 等)查找以下线索:

| 线索 | 指向部署形式 |
|------|--------------|
| 部署章节只给单机命令、示例 TP ≤ 单节点卡数 | 单节点(single) |
| 部署章节出现多机/multi-node/DP+TP 示例;示例 TP 卡数 > 单节点卡数(如双机 16) | 多节点(multinode) |
| 页面或社区出现 PD / Prefill-Decode / disaggregated / PD 专用镜像(如 `DeepSeekV4-flash-0731`)/ PD 代理脚本 | PD(pd / pd_colocate) |
| 页面或社区出现 `--kv-transfer-config` / `--deployment-config` / "跨节点 KV 传输" / 双实例方案 | **PD 分离(pd,双引擎形态)** |
| 页面出现"vLLM 引擎内部 PD 分工/单引擎 DP 形态"或 ModelArts 官方 glm_5_2.sh 最佳实践 | **PD 共置(pd_colocate)** |
| 页面标注"仅支持 XX 节点""需跨节点" | 多节点(multinode) |
| 模型权重规模估算:权重(按 dtype 折算)+ KV Cache > 单节点总显存 | 多节点(multinode) |
| 社区明确给出 PD 性能收益(高并发/长上下文吞吐) | 可考虑 PD(pd / pd_colocate) |

> **重要**: 文档未给出多节点或 PD 示例时,默认按单节点部署;不要自行发明多机/PD 参数。文档给出多机/PD 示例但用户资源不足(如资源池只有单机规格)时,只能降级单节点或告知用户无法按社区方案部署。

## 五、模型规模 × 硬件 → 部署形式速查(经验值,以文档为准)

| 模型规模(BF16) | 910B3 64GB | 910B4 32GB | 910C(A3) | 310P 24GB |
|----------------|------------|------------|----------|-----------|
| 7B 以下 | single 1 卡 | single 1~2 卡 | single(以文档为准) | single 1 卡 |
| 7B | single 1 卡 | single 2 卡 | single | 不推荐 |
| 14B~32B | single 2~4 卡 | single 4~8 卡 | single/multinode | 不推荐 |
| 72B | single 8 卡 | 不推荐/multinode | multinode | 不支持 |
| 100B+(如 397B MoE) | multinode(16 卡+) | multinode | multinode | 不支持 |
| 高并发/长上下文 | single 或 pd/pd_colocate | single 或 pd | pd_colocate(以文档为准) | 不适合 |

> 表格为速查参考,最终以 vllm-ascend 适配文档该模型页面的示例为准。

## 六、决策流程(步骤 1.1 四阶段)

> 步骤 1.1 交互式确认分四阶段: 1.1a 部署形式 → 1.1b 可用节点数 → 1.1c 副本取舍 → 1.1d 记录方案。全程用 AskUserQuestion 与用户确认。

### 1.1a 确认部署形式(4 选 1)

1. **是否 PD?**
   - 否 → single / multinode(按"单节点还是多节点"判断,见下)
   - 是 → pd / pd_colocate(按"双实例分离还是单引擎共置"判断:模型文档出现 `--kv-transfer-config`/双实例 → **pd(分离)**;官方单引擎 DP 形态(glm_5_2.sh)→ **pd_colocate(共置)**)
2. **单节点还是多节点?**
   - 单节点(TP ≤ 单节点卡数)→ **single**
   - 多节点(TP > 单节点卡数)→ **multinode** / **pd_colocate**

用 AskUserQuestion 将 4 形式列为 options(single/multinode/pd/pd_colocate),每个 option 带资源需求与文档依据,由用户点击确认。

### 1.1b 确认可用节点数 M(强制)

**TP 大小确认已迁移至 SKILL.md 步骤 3.0**(确认芯片型号后立即执行,见 SKILL.md 步骤 3.0 的 TP 候选计算: 头数约数 ∩ 资源池卡数档位 ∩ 模型文档启动脚本 TP 值)。本节仅确认可用节点数:

1. **AskUserQuestion 让用户提供可部署节点总数 M**(文本输入),并披露当前形态最小节点数:

| 部署形式 | 最小节点数 | 计算依据 |
|---------|-----------|---------|
| single | 1 | 单机即可 |
| multinode | N = ceil(TP_SIZE / 单节点卡数) | 模型文档示例 TP / 单节点卡数 |
| pd_colocate | N(同上) | 单引擎形态,节点数 = TP_SIZE / 单节点卡数 |
| pd(分离) | **2 × N**(prefill + decode 各 N 节点) | **两个推理单元各需一份节点,资源翻倍** |

2. 若 `M < 最小节点数`,在问题中明确提示"节点不足,该形式不可行",请用户改形式或增加资源。

### 1.1c 副本/实例取舍(用户第 4 点,强制确认)

依据 M 与最小节点数,按以下顺序决策:

1. **默认优先「单副本多实例」**: 单副本内 `unit_configs[].count` = 该单元所需节点数 N;`group_configs[].count = 1`。资源利用率最高。
2. **用户要求增加可靠性** → 改「多副本单实例」: 每副本 N 个节点,`group_configs[].count = floor(M / (N × 单元数))`(PD 分离单元数=2,资源翻倍)。
3. **决策后必须用 AskUserQuestion 复述给用户确认** 是否需要调整(副本数 / 节点数 / 可靠性)。

### 1.1d 记录方案(方案输入)

记录为方案输入,供步骤 3 脚本填充与步骤 4 部署配置使用:
- **`DEPLOY_FORM`**: `single` / `multinode` / `pd` / `pd_colocate`(仅方案记录项,不作为运行时分支注入,脚本按形式直接生成专用版本)
- **`NNODES`**: 单副本内节点数
- **`REPLICAS`**: 副本数(group_configs[].count)
- **PD 角色分配**: pd 分离场景 prefill/decode 各自的节点数与 PORT
- 数据并行总数(单引擎形态): `DATA_PARALLEL_SIZE = NNODES`(rank table 动态推导,脚本无需手工填)

## 七、部署形式对后续步骤的影响

| 后续步骤 | single | multinode | pd(分离) | pd_colocate |
|----------|--------|-----------|----------|-------------|
| 步骤 2 镜像 | 通用 tag | 通用 tag;核对多机示例对应的版本 | 可能模型专用镜像/tag(如 `DeepSeekV4-flash-0731`) | 通用 tag;核对多机示例对应的版本 |
| 步骤 3 启动脚本 | `start_vllm.single.sh`,TP 单机卡数 | `start_vllm.multinode.sh`,master/slave 分支 + `--data-parallel-*` + slave `--headless` | `start_vllm.pd.sh`,VLLM_ROLE 角色分支、各自端口 | `start_vllm.pd_colocate.sh`(单引擎形态,master/slave 分支 + `--data-parallel-*` + slave `--headless`,无 VLLM_ROLE) |
| 步骤 3 探针 | `health_check.sh`,探本地 `/health` | `health_check.sh`,所有节点探 master /health | `health_check.sh`,各角色探各自 PORT | `health_check.sh`,所有节点探 master /health |
| 步骤 4 部署 | `unit_configs=[role-1]`,count=1 或副本 M | `unit_configs=[role-1]`,count=N + 亲和组=N | `unit_configs=[prefill,decode]`,各注入 VLLM_ROLE + 不同 PORT | `unit_configs=[role-1]`,count=N + 亲和组=N |
| 产物目录后缀 | `single` / `tp{N}` | `mn` | `pd` | `pd_co` |
