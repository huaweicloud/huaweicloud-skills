# 部署形式决策矩阵(3 形式 × 单部署单元)

本文件支撑 SKILL.md 步骤 1.2"确定部署形式"。核心原则:**以 vllm-ascend 模型适配文档/社区方案为准,结合模型规模与可用硬件判断,最终由用户确认**。禁止脱离文档凭经验猜部署形式。

**收敛为 3 种**(单机部署 / 多机部署 / PD 分离部署),统一**单部署单元**承载(多机部署为同一部署单元内 2 个推理单元 master+worker;PD 分离为同一部署单元内 3 个推理单元 proxy+prefill+decode;单机为 1 个推理单元 master)。副本数(单副本/多副本)由"用户可靠性需求"在步骤 1.2c 决策,不再独立枚举场景。

> **核心规范(强制,官网+ModelArts 平台约束)**: 部署的第一推理单元(group 0 / `unit_configs[0]`)**不能**出现 worker 或 decode 启动的实例——ModelArts 在线服务所有请求都发送到 group 0,worker/decode 不具备接受请求功能。`unit_configs[0]` 必须是: 单机=master / 多机=master(实例数=1,不加 --headless) / PD 分离=proxy(0 卡自定义规格,运行 `load_balance_proxy_server_example.py`)。

## 一、3 种部署形式对比(基础概念)

| 维度 | 单机部署(single) | 多机部署(multi_node) | PD 分离部署(pd) |
|------|---------------|-------------------|-------------|
| 推理单元数 | 1(master) | 2(master + worker) | **3**(proxy + prefill + decode) |
| data-parallel-size N | N=1 | N>1 | prefill/decode 各自 dp_size(官网 dp_size = 总卡数/tp_size;**实例规格 npu=每实例单节点内所有并行度乘积 TP×PCP 或 TP×DCP,非仅 TP**) |
| 节点数 | ceil(TP_SIZE / 单节点卡数) | ceil(TP_SIZE × N / 单节点卡数) | prefill 节点数 + decode 节点数(各角色节点数 = ceil(各角色总卡数 / 单节点卡数);PP/DP 多节点时 = 跨节点数;**proxy `card=0` 不额外占节点**,平台自动调度到 P/D 已有节点共享 CPU/内存,不影响其他任务使用卡) |
| 并行方式 | TP ≤ 单节点卡数 | master+worker 主从结构,master 实例数=1,worker 实例数=N-1,经 rank table group 0 判定 | prefill/decode 各自独立 vLLM 实例,各组内 TP;proxy 独立 HTTP 代理 |
| KV Cache | 实例内 | 实例内 | prefill↔decode 经 Mooncake KV 传输;proxy 不参与 KV |
| 部署单元 | 1 | 1 | 1 |
| 角色注入 | 无 | master/worker 经 `get_master_ip.py 0` 读 group 0 判定(worker 加 --headless) | **`VLLM_ROLE=proxy\|prefill\|decode`**(3 个推理单元分别注入;PORT 脚本内置默认值);prefill 经 `get_master_ip.py 1` 读 group 1 判定主从;decode 经 `get_master_ip.py 2` 读 group 2 获取 D 组 DP 主节点 IP |
| 模板 | `start_vllm.single.sh` | `start_vllm.multi_node.sh` | `start_vllm.pd.sh` + `load_balance_proxy_server_example.py` |
| 通信依赖 | 无 | 跨实例 HCCL/DP(跨节点经网卡/RoCE) | P↔D KV 经 Mooncake/UB 传输;proxy HTTP 负载均衡 |
| 复杂度/成本 | 最低 | 中 | 最高 |
| 启动顺序 | 单实例直启 | master 先启,worker 后启 | **先 prefill 后 decode 最后 proxy**(官网 V9) |

> **官网证据**: PD 分离三类角色(proxy + prefiller + decoder)源自 vllm-ascend 官网 `pd_disaggregation_mooncake_multi_node.html` / `pd_disaggregation_mooncake_single_node.html`;proxy 是独立 HTTP 代理进程(`load_balance_proxy_server_example.py`)，不运行 vllm serve,不消耗 NPU 卡;**ModelArts 证据**: server_group_list group 0 = 流量入口,凡是对外提供 API 的角色(master、proxy)必须落在 group 0(内网《ModelArts 上多机多角色部署》)。

## 二、3 形式 × 副本数 R × 实例数 N 配置速查

> **ModelArts 层级(正交两维)**: 副本数 R = `group_configs[].count`(可靠性维度,默认 R=1,不主动让用户选);实例数 N = `unit_configs[].count`(单副本资源实例数维度,按部署形态自适应推导)。**部署副本数(`group_configs[].count`)默认为 1,除非用户主动提出修改,固定为 1,不主动让用户选**;**单元副本数 R(`unit_configs[].group_count`)让用户选**;**实例数 N 按部署形态自适应**(用户只能选副本数 R)。

| 形式 | 推理单元数 | 实例数 N(`unit_configs[].count`,按形态自适应) | 副本数 R(`unit_configs[].group_count`,用户选) | 模板 |
|------|-----------|--------------------------------|----------------------------------|------|
| **single** | 1(master) | N=1(固定,单实例不可调) | R(默认 1,用户选) | `single` |
| **multi_node** | 2(master + worker) | master 单元 count=1;worker 单元 count=N-1(N=data-parallel-size,用户选) | R(默认 1,用户选) | `multi_node` |
| **pd** | 3(proxy + prefill + decode) | proxy 单元 count=1;prefill 单元 count=跨节点数(PP 节点数或 DP 节点数,以文档为准);decode 单元 count=跨节点数(DP 节点数);实例规格 npu=每实例单节点内所有并行度乘积(TP×PCP 或 TP×DCP) | R(默认 1,用户选) | `pd` |

## 三、ModelArts 部署关键概念(决策必备)

| ModelArts 概念 | 对应部署维度 | 触发形式 | 说明 |
|---------------|--------------|---------|------|
| **部署单元 group_configs[].count(副本数)** | 多副本(可靠性) | 用户要求可靠性时 | 副本数>1 即多副本,平台内置流量分发;一个副本即一个独立 TP 域。**默认 1(单副本)** |
| **推理单元 unit_configs[].count(实例数)** | 单副本实例数 | multi_node / | 单副本内多实例承载实例数 N(单副本资源实例数为多,N≥1;跨节点场景 N≥2 对应跨节点数,单节点多实例场景 N>1 同节点多实例);PD 分离两单元各 count 为每角色实例数 N(节点数按 2×TP×N 动态推导) |
| **超节点亲和组实例数** | 多实例 TP 亲和 | multi_node / | 多实例必须配置 = N(副本内实例数),确保多实例调度到同一超节点(否则报业务错误);单节点多实例 N=1 也需配置 |
| **VLLM_ROLE 注入** | PD 角色区分 | **仅 pd(PD 分离)** | 同一部署单元内 3 个推理单元分别注入 `VLLM_ROLE=proxy\|prefill\|decode`(PORT 已在脚本内按角色内置默认值 proxy=8080/prefill=8080/decode=7100,无需注入) |
| **单元实例规格(N 卡)** | 副本内 TP | 全部 | 单副本内的卡数规格,决定副本内 TP 上限 |

> **重要**: ModelArts 在线服务单服务最大昇腾卡规模 384 卡,单个在线服务最多 5 个部署单元。详见 ModelArts 官方约束与限制。

## 四、vllm-ascend 文档/社区线索(判断依据)

在模型适配文档页面(`https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/<Model>.html`)与社区(昇腾论坛、CSDN、hiascend 等)查找以下线索:

| 线索 | 指向部署形式 |
|------|--------------|
| 部署章节只给单机命令、示例 TP ≤ 单节点卡数 | 单节点(single) |
| 部署章节出现多机/multi-node/DP+TP 示例;示例 TP 卡数 > 单节点卡数(如双机 16) | 多实例(multi_node,跨节点子场景) |
| 用户希望单节点内多实例提升并发吞吐(count>1),平台 LB 分发 | 多实例(multi_node,单节点多实例子场景) |
| 页面或社区出现 PD / Prefill-Decode / disaggregated / PD 专用镜像(如 `DeepSeekV4-flash-0731`)/ PD 代理脚本 | PD(pd /) |
| 页面或社区出现 `--kv-transfer-config` / `--deployment-config` / "跨节点 KV 传输" / 双实例方案 | **PD 分离(pd,双引擎形态)** |
| 页面出现"vLLM 引擎内部 PD 分工/单引擎 DP 形态"或 ModelArts 官方 glm_5_2.sh 最佳实践 | **PD 分离(pd)** |
| 页面标注"仅支持 XX 节点""需跨节点" | 多实例(multi_node,跨节点子场景) |
| 模型权重规模估算:权重(按 dtype 折算)+ KV Cache > 单节点总显存 | 多实例(multi_node,跨节点子场景) |
| 社区明确给出 PD 性能收益(高并发/长上下文吞吐) | 可考虑 PD(pd /) |

> **重要**: 文档未给出多节点或 PD 示例时,默认按单节点部署;不要自行发明多机/PD 参数。文档给出多机/PD 示例但用户资源不足(如资源池只有单机规格)时,只能降级单节点或告知用户无法按社区方案部署。

### 4.5 文档拓扑 vs skill 标准模板能力判定(强制,违反=硬套模板必崩)

skill 标准 PD 模板(`templates/start_vllm.pd.sh`)预置能力: **单实例 prefill + MooncakeConnectorV1** + decode DP 多实例 + proxy。部分实验性模型(如 Kimi K3.1 Pro)文档 PD 拓扑超出此能力,需定制适配。

**判定标准(任一命中即"超出模板能力")**:
- 文档 PD 启动命令含 `--pipeline-parallel-size >1`(PP 多节点,Prefill 跨多节点)
- 文档 PD 启动命令含 `--prefill-context-parallel-size >1` / `--decode-context-parallel-size >1`(PCP/DCP 多节点并行)
- 文档 kv-transfer-config 用 `MooncakeConnectorV2`(非 V1),且含 `pp_size/pcp_size/dcp_size` 完整拓扑字段
- 文档 Prefill 跨多节点(如 4 节点 PP=4,每节点 1 个 PP stage)

**超出能力时的处理流程**:
1. **1.2a 前 AskUserQuestion 披露**: "该模型文档拓扑(PP/PCP/DCP 多节点并行 + MooncakeConnectorV2)超出 skill 标准 PD 模板能力(单实例 prefill + V1),需基于文档脚本定制适配"
2. **3.2 基于文档脚本定制** `start_vllm.sh`(**不套用 skill PD 模板**): PD 三角色分支 + 完整 kv-transfer-config(含 `pp_size/pcp_size/dcp_size`)+ 文档参数(MooncakeConnectorV2/`VLLM_USE_V2_MODEL_RUNNER=1` 等)
3. **实例规格推导**: flavor npu = **每实例单节点内所有并行度乘积**(TP×PCP 或 TP×DCP,以文档为准;如 Prefill TP=4×PCP=4=16 卡占满 A3 单节点);**跨节点 PP/DP 经 count(实例数=PP 节点数 或 DP 节点数)表达**(ModelArts 平台无 PP/PCP/DCP 概念,节点内 PCP/DCP 经每实例卡数表达);违反=npu<TP×PCP 时 vLLM `local_world_size=TP×PCP` 启动 worker,local_rank 越界 `out of bounds` 崩溃
4. **1.2e 节点数推导**: prefill 节点数(= PP 节点数) + decode 节点数(= DP 节点数),proxy `card=0` 不额外占节点

**实例(Kimi K3.1 Pro A3 4P4D)**:
| 角色 | 文档拓扑 | flavor npu | count(实例数) | 节点数 |
|------|---------|-----------|--------------|-------|
| proxy | 1 节点 0 卡 | custom_spec card=0 | 1 | 0(共享 P/D) |
| prefill | 4 节点 PP=4,每节点 TP=4×PCP=4=16 卡占满 | 16(TP×PCP) | 4(PP 节点数) | 4 |
| decode | 4 节点 DP=4,每节点 TP=16 占满 | 16(TP) | 4(DP 节点数) | 4 |
| **合计** | 8 节点 | — | — | **8** |

## 五、模型规模 × 硬件 → 部署形式速查(经验值,以文档为准)

| 模型规模(BF16) | 910B3 64GB | 910B4 32GB | 910C(A3) | 310P 24GB |
|----------------|------------|------------|----------|-----------|
| 7B 以下 | single 1 卡 | single 1~2 卡 | single(以文档为准) | single 1 卡 |
| 7B | single 1 卡 | single 2 卡 | single | 不推荐 |
| 14B~32B | single 2~4 卡 | single 4~8 卡 | single/multi_node | 不推荐 |
| 72B | single 8 卡 | 不推荐/multi_node | multi_node | 不支持 |
| 100B+(如 397B MoE) | multi_node(16 卡+) | multi_node | multi_node | 不支持 |
| 高并发/长上下文 | single 或 pd | single 或 pd |(以文档为准) | 不适合 |

> 表格为速查参考,最终以 vllm-ascend 适配文档该模型页面的示例为准。

## 六、决策流程(步骤 1.2 四阶段)

> 步骤 1.2 交互式确认分四阶段: 1.2a 部署形式 → 1.2b(已删除,见 SKILL.md 1.2e 节点汇总确认) 可用节点数 → 1.2c 副本数 R 与实例数 N(两维独立) → 1.2d 记录方案。全程用 AskUserQuestion 与用户确认。

### 1.2a 确认部署形式(3 选 1)

1. **是否 PD?**
   - 否 → single / multi_node(按"单节点还是多节点"判断,见下)
   - 是 → pd(按"双实例分离还是单引擎共置"判断:模型文档出现 `--kv-transfer-config`/双实例 → **pd(PD 分离)**;官方单引擎 DP 形态(glm_5_2.sh)→ **pd(共置)**)
2. **单节点还是多节点?**
   - 单节点(TP ≤ 单节点卡数)→ **single**
   - 多节点(TP > 单节点卡数)→ **multi_node** / **pd**

用 AskUserQuestion 将 3 形式列为 options(single/multi_node/pd),每个 option 带资源需求与文档依据,由用户点击确认。

### 1.2b(已删除,见 SKILL.md 1.2e 节点汇总确认) 确认可用节点数 M(强制)

**TP 大小确认已迁移至 SKILL.md 步骤 3.0**(确认芯片型号后立即执行,见 SKILL.md 步骤 3.0 的 TP 候选计算: 头数约数 ∩ 资源池卡数档位 ∩ 模型文档启动脚本 TP 值 ∩ 显存可容纳(KV cache 非负))。本节仅确认可用节点数:

1. **节点数无形式强制的固定值,按总卡数需求动态推导**: 单副本总卡数需求 = 部署单元数(默认 1)× 推理单元数 × TP_SIZE × 实例数 N;单副本所需节点数 = ceil(单副本总卡数需求 / 单节点卡数)(单节点卡数按 1.1 确认的芯片型号取,如 A2=8 卡/节点、A3=16 卡/节点)。总卡数 ≤ 单节点卡数则 1 节点即可,超过则按 ceil 推导。各形式单副本总卡数需求:

| 部署形式 | 推理单元数 | 单副本总卡数需求 | 单副本最小节点数 |
|---------|-----------|----------------|----------------|
| single | 1 | 1 × 1 × TP_SIZE × 1 = TP_SIZE | ceil(TP_SIZE / 单节点卡数) |
| multi_node | 1 | 1 × 1 × TP_SIZE × N | ceil(TP_SIZE × N / 单节点卡数) |
| pd(PD 分离) | 3(proxy+prefill+decode) | prefill 总卡数 + decode 总卡数(各角色 = TP × 跨节点数;proxy `card=0` 不占卡) | prefill 节点数 + decode 节点数(各角色节点数 = ceil(各角色总卡数 / 单节点卡数);PP/DP 多节点时 = 跨节点数;**proxy `card=0` 不额外占节点**,平台调度到 P/D 已有节点共享) |

2. **AskUserQuestion 让用户提供可部署节点总数 M**(文本输入),并在问题中披露按上表推导的当前形态最小节点数。若 `M < 最小节点数`,在问题中明确提示"节点不足,该形式不可行",请用户改形式或增加资源。

### 1.2c 副本数 R 与实例数 N 两维独立选择(强制确认)

ModelArts 副本数 R(`group_configs[].count`,可靠性维度)与实例数 N(`unit_configs[].count`,单副本资源实例数维度)是**正交两维**,须独立询问,禁止建模为二元互斥;默认取最小(R=1, N=1),用户按需升级任一维度。依据 M 与 1.2b(已删除,见 SKILL.md 1.2e 节点汇总确认) 推导的单副本最小节点数决策:

1. **实例数 N(`unit_configs[].count`,单副本资源实例数,非节点数)**: 按 1.2b(已删除,见 SKILL.md 1.2e 节点汇总确认) 推导单副本最小节点数,N 的合法候选按部署形式与"单副本总卡数 = 部署单元 × 推理单元 × TP_SIZE × N ≤ M × 单节点卡数"约束推导;**必须用 AskUserQuestion 让用户从合法候选中选 N**(候选下限含 N=1,禁止钉死计算结果;每个候选注明占卡数 = 单副本总卡数、DP 并发数 = N、节点数 = ceil(单副本总卡数 / 单节点卡数)):
   - **single**: N=1(单实例,不可调),节点数 = ceil(TP_SIZE / 单节点卡数)
   - **multi_node 单节点子场景**(单副本总卡数 ≤ 单节点卡数): N ∈ {1, 2, ..., floor(单节点总卡数 / TP_SIZE)}(N=1 即单副本单实例),节点数 = 1
   - **multi_node 跨节点子场景**(单副本总卡数 > 单节点卡数): N ∈ {2, 3, ...}(N=1 时单副本总卡数 ≤ 单节点卡数,归单节点子场景;候选下限由"节点数 = ceil(TP_SIZE × N / 单节点卡数) ≥ 2"约束),节点数 = ceil(TP_SIZE × N / 单节点卡数)
   - **pd 分离**: prefill 与 decode 两个推理单元各自 N = 实例数(候选受"2 × TP_SIZE × N ≤ M × 单节点卡数"约束,N=1 即每角色单实例),节点数 = ceil(2 × TP_SIZE × N / 单节点卡数)(双角色共节点承载,1 节点能放下则不翻倍)
   - **pd**: 同 multi_node,N ∈ {1, 2, ...}(N=1 即单副本单实例),节点数 = ceil(TP_SIZE × N / 单节点卡数)
2. **副本数 R(`group_configs[].count`,可靠性维度)**: 用 AskUserQuestion 让用户选 R(默认 R=1 单副本;可靠性需求选 R>1,R 上限 = floor(M × 单节点卡数 / 单副本总卡数),单副本总卡数按第 1 条确认的 N 推导;R 上限 < 1 时提示"节点不足,无法多副本,改单副本或增资源")
3. **复述确认**: 用 AskUserQuestion 复述给用户确认(复述项含: 副本数 R / 实例数 N / 单副本节点数 / 总占用节点数 = R × 单副本节点数 / 可靠性)

### 1.2d 记录方案(方案输入)

记录为方案输入,供步骤 3 脚本填充与步骤 4 部署配置使用:
- **`DEPLOY_FORM`**: `single` / `multi_node` / `pd` / `pd`(仅方案记录项,不作为运行时分支注入,脚本按形式直接生成专用版本)
- **`NNODES`**: 单副本内节点数
- **`REPLICAS`**: 副本数 R(group_configs[].count,可靠性维度)
- **`INSTANCE_COUNT`**: 实例数 N(unit_configs[].count,单副本资源实例数维度)
- **PD 角色分配**: pd 分离场景 prefill/decode 各自的节点数与 PORT
- 数据并行总数(multi_node 形态): `DATA_PARALLEL_SIZE=N`(N=master 单元实例数+worker 单元实例数,与单元副本数 R 无关)由模板按 1.2 确认的 N 固定填入并 export(同 `TP_SIZE`,不依赖 envs 注入)
- PD 分离 DP/TP 推导: `PREFILL_DP_SIZE=1`、`DECODE_DP_SIZE=部署所需节点数×芯片卡数/TP_SIZE`(TP_SIZE 取单节点脚本 TP 值,缺失时按芯片卡数 A2/950DT=8、A3=16),`DATA_PARALLEL_SIZE` 按 `VLLM_ROLE` 切换(prefill 用 PREFILL_DP_SIZE,decode 用 DECODE_DP_SIZE)

## 七、部署形式对后续步骤的影响

| 后续步骤 | single | multi_node | pd(PD 分离) |
|----------|--------|-----------|----------|
| 步骤 2 镜像 | 通用 tag | 通用 tag;核对多机示例对应的版本 | 可能模型专用镜像/tag(如 `DeepSeekV4-flash-0731`) | 通用 tag;核对多机示例对应的版本 |
| 步骤 3 启动脚本 | `start_vllm.single.sh`,TP 单机卡数 | `start_vllm.multi_node.sh`,master/worker 分支 + `--data-parallel-*` + worker `--headless` | `start_vllm.pd.sh`,VLLM_ROLE 角色分支、端口按角色内置默认值 |
| 步骤 3 探针 | `health_check.sh`,探本地 `/health` | `health_check.sh`,所有实例探 master /health | `health_check.sh`,所有实例探 master /health |
| 步骤 4 部署 | `unit_configs=[role-1]`,count=1 或副本 M | `unit_configs=[master,worker]`,count 分别 1 与 N-1(N=data-parallel-size,用户选;N=2 时 master=1 + worker=1)+ 亲和组=N | `unit_configs=[proxy,prefill,decode]`,各注入 VLLM_ROLE(PORT 脚本内置默认值) |
| 产物目录后缀 | `single` / `tp{N}` | `mi` | `pd` |
