# Mooncake PD 分离部署指南(社区双引擎 PD 方案参考)

本文件是 **vllm-ascend 社区双引擎 PD + Mooncake KV 传输方案**的参数填充与部署参考,覆盖 Mooncake KV 传输 / XpYd 代理 / `--kv-transfer-config` / `--deployment-config` 等。

> **⚠️ 与 skill 默认形态的关系**: **pd(PD 分离)默认对齐 ModelArts 官方最佳实践 glm_5_2.sh 单引擎 DP 形态**(`start_vllm.pd_colocate.sh` 已实现: 单 vLLM 进程组 + `--data-parallel-*`,PD 分工由引擎内部完成,**无需 Mooncake / VLLM_ROLE**)。本文件描述的社区双引擎 PD + Mooncake 方案**仅当模型文档明确要求时**作为替代——如 DeepSeek-V4-Flash 等模型在 vllm-ascend 社区文档中明确给出 `--kv-transfer-config`/`--deployment-config` 双引擎示例。此时需按本文件改造模板(加回 `VLLM_ROLE` 强校验与 `MOONCAKE_*` 注入),并按第六节配置单部署单元内两个推理单元(prefill/decode)。

> **重要**: 本文件内容基于 vllm-ascend 社区 PD 方案与华为云昇腾论坛实践整理,**具体参数以 vllm-ascend 模型适配文档/社区 PD 方案为准**。本 skill 不代为拉起 Mooncake Master / XpYd Proxy,仅提供参数填充指南。

> **免责**: PD 分离部署复杂度高,适用于高并发/长上下文场景的功能验证与原型测试,不适用于生产商用。

## 一、Mooncake KV 传输概述

PD 分离场景下,Prefill 实例组负责首 token 生成(prefill),Decode 实例组负责后续 token 生成(decode)。Prefill 完成后需将 KV Cache 传输到 Decode 实例,这一传输由 Mooncake 完成。

| 组件 | 作用 | 部署形态 |
|------|------|---------|
| **Mooncake Master** | KV Cache 传输协调节点,管理 Prefill/Decode 实例的 KV Cache 路由 | 独立容器/进程,通常 1 个 |
| **Prefill 实例组** | 执行 prefill,生成 KV Cache 并发送到 Mooncake | ModelArts 部署单元 1 |
| **Decode 实例组** | 执行 decode,从 Mooncake 接收 KV Cache | ModelArts 部署单元 2 |
| **XpYd 代理(可选)** | 前置代理,统一入口,X 个 Prefill + Y 个 Decode | 独立容器/进程,通常 1 个 |

> PD 分离(pd)双引擎形态在**模型文档/社区 PD 方案要求 Mooncake 跨节点传输**时才需要配置(MA 官方最佳实践 section7 无此参数,Mooncake 是 vllm-ascend 社区方案)。

## 二、XpYd 代理(前置负载均衡)

XpYd 是 vllm-ascend 社区 PD 方案的常用前置代理,形如 "X 个 Prefill + Y 个 Decode"。

| 配置项 | 说明 |
|--------|------|
| 代理监听端口 | 对外统一入口(如 8000) |
| Prefill 后端 | X 个 Prefill 实例地址(各实例 PORT) |
| Decode 后端 | Y 个 Decode 实例地址(各实例 PORT) |
| 路由策略 | prefill 请求 → Prefill 后端;decode 请求 → Decode 后端 |

> XpYd 代理的拉起方式以 vllm-ascend 社区 PD 方案为准,本 skill 不代为拉起。ModelArts 多部署单元的"流量权重"可部分替代 XpYd 代理(平台内置 LB)。

## 三、`--kv-transfer-config` 参数(JSON)

`--kv-transfer-config` 是 vllm-ascend PD 分离的关键参数,JSON 结构由模型文档/社区方案规定。常见字段:

| 字段 | 取值 | 说明 |
|------|------|------|
| `role` | `prefill` / `decode` | 当前实例角色(由 `VLLM_ROLE` 注入) |
| `master_addr` | Mooncake Master IP | KV Cache 协调节点地址 |
| `master_port` | Mooncake Master 端口(如 11337) | 协调节点端口 |
| `backend` | `mooncake` | KV 传输后端 |

`start_vllm.pd_colocate.sh` 模板内置的半结构化注入逻辑(模板内已实现,无需用户手写):

```bash
if [ -n "${MOONCAKE_MASTER_ADDR}" ]; then
    PD_JSON_ARGS+=(
        "--kv-transfer-config" "{\"role\": \"${VLLM_ROLE}\", \"master_addr\": \"${MOONCAKE_MASTER_ADDR}\", \"master_port\": ${MOONCAKE_MASTER_PORT:-11337}, \"backend\": \"${MOONCAKE_TRANSFER_BACKEND:-mooncake}\"}"
    )
fi
```

> 部署配置时只需在对应部署单元的环境变量中注入 `MOONCAKE_MASTER_ADDR`(必填)与可选的 `MOONCAKE_MASTER_PORT` / `MOONCAKE_TRANSFER_BACKEND`(有默认值),模板自动拼装 JSON 并加入 `MODEL_ARGS` 数组(单引号包裹,引号不丢失)。**注意: 这是部署单元配置(平台注入),不是用户手动在控制台逐个填的普通环境变量**。

## 四、`--deployment-config` 参数(JSON)

`--deployment-config` 是 vllm-ascend PD 部署配置,JSON 结构由模型文档规定。常见字段:

| 字段 | 取值 | 说明 |
|------|------|------|
| `pd_role` | `prefill` / `decode` | 部署角色(部分版本用 `VLLM_ROLE` 替代) |
| `kv_role` | `producer` / `consumer` | KV Cache 生产/消费角色 |
| `...` | 以模型文档为准 | 不同模型/版本字段不同 |

**填充方法**: 直接将模型文档要求的 `--deployment-config` JSON 参数加入 `start_vllm.pd_colocate.sh` 模板的 `MODEL_ARGS` 数组(单引号包裹):

```bash
MODEL_ARGS=(
    --distributed-executor-backend ray
    --deployment-config '{"pd_role": "prefill", "kv_role": "producer", ...}'
    # 其他模型文档要求的参数
)
```

> **关键**: JSON 参数必须直接写入 `MODEL_ARGS` 数组(单引号包裹),**禁止用字符串变量**(如 `EXTRA_ARGS`)传递,否则 `${EXTRA_ARGS}` 展开时引号丢失,argparse 报错。

## 五、`pd_colocate` 模板填充指南

> **前提**: 本节针对**社区双引擎 PD + Mooncake 方案**,需在默认 `start_vllm.pd_colocate.sh`(官方单引擎 DP 形态)基础上改造——加回 `VLLM_ROLE` 强校验与 `MOONCAKE_*` 环境变量注入段,并按第六节配置单部署单元内两个推理单元(prefill/decode)。

### 5.1 环境变量注入映射

| ModelArts 部署单元环境变量 | 模板内变量 | 作用 |
|---------------------------|-----------|------|
| `VLLM_ROLE=prefill` / `decode` | `VLLM_ROLE` | PD 角色强校验 |
| `GLOBAL_RANK_TABLE_FILE_PATH`(平台注入) | `get_master_ip.py` 读取 | 全局 rank table JSON 路径,取 master IP |
| `POD_IP`(平台注入) | `POD_IP` | 当前节点 IP,与 master IP 比较判定 master/slave |
| `MOONCAKE_MASTER_ADDR=<IP>` | `MOONCAKE_MASTER_ADDR` | Mooncake Master IP |
| `MOONCAKE_MASTER_PORT=11337` | `MOONCAKE_MASTER_PORT` | Mooncake Master 端口 |
| `MOONCAKE_TRANSFER_BACKEND=mooncake` | `MOONCAKE_TRANSFER_BACKEND` | KV 传输后端 |
| `MOONCAKE_PROXY_ADDR=<IP>`(可选) | `MOONCAKE_PROXY_ADDR` | XpYd 代理地址 |

> **多节点角色无需手动注入**: `NNODES`/`NODE_RANK`/`MASTER_ADDR` 不再由部署单元环境变量注入——`start_vllm.pd_colocate.sh` 调用同目录 `get_master_ip.py` 读取平台注入的 rank table 取 master IP,与 `POD_IP` 比较自动判定 master/slave(slave 追加 `--headless`)。

### 5.2 用户按模型文档填入的额外参数

将模型文档要求的 PD 专用参数(除 `--kv-transfer-config` 外)直接加入 `MODEL_ARGS` 数组。示例(以模型文档为准):

```bash
MODEL_ARGS=(
    # 模型文档要求的 PD 参数(示例,实际以文档为准):
    --deployment-config '{"pd_role": "prefill", "kv_role": "producer"}'
    --enable-chunked-prefill
    # 其他模型特有参数
)
```

### 5.3 模板自动注入的参数

模板内以下参数由环境变量自动拼装,**用户无需手写**:
- `--kv-transfer-config '{"role": ..., "master_addr": ..., ...}'`(由 `MOONCAKE_*` 变量拼装)
- `--data-parallel-size`/`--data-parallel-size-local`/`--data-parallel-start-rank`/`--data-parallel-address`/`--data-parallel-rpc-port`(多节点 DP 参数,`start-rank`/`address` 由 `get_master_ip.py` 从 rank table 取)
- `--headless`(slave 节点由脚本按 master/slave 判定自动追加)
- 健康检查失败次数 60(部署配置自动设置,见 SKILL.md 步骤 4.2 第 8 步)

## 六、ModelArts 单部署单元双推理单元 PD 部署步骤(pd 分离)

> 详细 API 字段说明见 `references/modelarts-console-guide.md`(新版推理 API 详解,group_configs/unit_configs 结构)。

1. **调用新版推理 API 部署服务**: 通过 `scripts/create_infer_service.py` 调用 CreateInferService(`POST /v2/{project_id}/services`),**单部署单元内配置两个推理单元(Prefill/Decode)**,镜像地址填 SWR(可能为 PD 专用 tag 如 `DeepSeekV4-flash-0731`),code 目录文件存储挂载到 `/home/ma-user/code/`,启动命令 `bash /home/ma-user/code/start_vllm.sh`,探针命令检查三层探针(`bash /home/ma-user/code/health_check.sh startup/liveness/readiness`)
2. **配置 Prefill 推理单元(unit_configs[0])**:
   - 单元名: `prefill`(**仅小写字母/数字/连字符,大写 `Prefill` 报 400**,见 SKILL.md 4.3 关键字段要点),单元内实例数: 该角色节点数
   - 节点数/副本: N(跨节点 TP)
   - 超节点亲和组实例数: N
   - 环境变量(envs): `VLLM_ROLE=prefill`, `MOONCAKE_MASTER_ADDR=<IP>`, `MOONCAKE_MASTER_PORT=11337`, `PORT=8080`(master/slave 角色由平台注入 `GLOBAL_RANK_TABLE_FILE_PATH`/`POD_IP` + `get_master_ip.py` 自动判定,无需手动注入 `NNODES`/`NODE_RANK`/`MASTER_ADDR`)
3. **配置 Decode 推理单元(unit_configs[1])**:
   - 单元名: `decode`(仅小写字母/数字/连字符,大写 `Decode` 报 400),单元内实例数: 该角色节点数
   - 节点数/副本: N
   - 超节点亲和组实例数: N
   - 环境变量(envs): `VLLM_ROLE=decode`, `MOONCAKE_MASTER_ADDR=<IP>`, `MOONCAKE_MASTER_PORT=11337`, `PORT=8081`(与 Prefill 区分;master/slave 自动判定同上)
4. **网络放通**: HCCL/DP 通信端口(副本内,如 `--data-parallel-rpc-port` 13389)+ Mooncake 端口(跨副本)+ 前置 LB 端口
5. **部署 Mooncake Master**(独立容器/进程,以社区方案为准)
6. **(可选)部署 XpYd 代理**(以社区方案为准)
7. **验证**: `python scripts/test_inference.py --url https://<endpoint>/v1/chat/completions --token <token> --model <MODEL_NAME>`

## 七、常见问题

| 现象 | 可能原因 | 排查动作 |
|------|----------|----------|
| 实例间 ConnectError | XpYd 代理或 Mooncake Master 未就绪 | 核对 `MOONCAKE_MASTER_ADDR/PORT` 可达、Proxy 进程存活、各角色副本内 master/worker 角色判定正确 |
| KV Cache 传输超时 | Mooncake 网络不通或端口未放通 | 放通 Mooncake 端口(如 11337);核对 `MOONCAKE_MASTER_ADDR` 在各实例可 ping |
| 请求 502/504 | 前置 LB 或流量权重配置错误 | 核对 ModelArts 多部署单元流量权重;核对 XpYd 代理后端地址列表 |
| Prefill/Decode 实例启动成相同角色 | `VLLM_ROLE` 未注入或注入错误 | 核对各部署单元环境变量 `VLLM_ROLE=prefill|decode` |
| `--kv-transfer-config` JSON 解析失败 | JSON 用字符串变量传递(引号丢失) | 改用 `MODEL_ARGS` 数组(单引号包裹);或确认 `MOONCAKE_*` 变量已注入由模板自动拼装 |
| 跨节点 TP 报业务错误 | 超节点亲和组实例数未配置或不等于 N | ModelArts 部署配置"超节点亲和组实例数"=N |
| 多副本(S9)DP 端口冲突 | 多副本实例 `--data-parallel-rpc-port` 相同 | 各副本 `DATA_PARALLEL_RPC_PORT` 环境变量按副本注入不同值 |
