# ModelArts 新版推理部署详解(控制台手动 / API 自动)

本文件补充 SKILL.md 中步骤 4 的**新版在线服务部署**各字段说明,覆盖两种部署方式:
- **方式 B — 控制台手动部署**(第一节,一步步点击操作指导,供用户不提供 Token 时使用)
- **方式 A — API 自动部署**(第二节起,CreateInferService API 字段详解,供 `create_infer_service.py` 使用)

新版在线服务通过 API 或控制台直接部署,已废弃旧版"创建 AI 应用 + 部署在线服务"两步式流程。**字段名以 API 文档/API Explorer 为准**,本文为参考骨架。

## 一、控制台手动部署分步操作(方式 B)

> 适用: 用户不便提供 IAM Token,或希望保留人工确认每个配置项。以下为通用分步指导,**各步骤取值按 SKILL.md 步骤 4.4 的 4 种部署形式映射表选用**。控制台路径以实际版本为准(公有云新版入口: 左侧菜单 **模型推理 > 在线推理**;部分版本为 **模型部署 > 在线服务**)。

### 第 1 步 — 进入部署页面

1. 登录 ModelArts 管理控制台,左侧菜单选择 **模型推理 > 在线推理**(或 **模型部署 > 在线服务**),进入在线服务管理页面。
2. 单击 **"部署服务"**(或服务列表右上角 **"部署"**),进入"部署在线服务"页面。

### 第 2 步 — 基础信息

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 部署名称/服务名称 | 服务标识,1-64 字符,同地域唯一 | `qwen3-8b` 等(小写字母/数字/下划线) |
| 描述 | 可选备注 | 按需 |
| 请求超时时间（秒） | 请求发送后等待响应的超时时间 | 300 |

填写后单击 **"下一步"** 进入部署配置。

### 第 3 步 — 资源配置

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 资源池类型 | 公共资源池(开发测试,可能排队)/ 专属资源池(生产,独占) | **专属资源池**(NPU 推理必须) |
| 选择专属资源池 | 昇腾 NPU 专属资源池,芯片型号与步骤 3.0 确认一致 | 用户资源池 |
| 部署副本数 | 1=单副本多实例(默认);>1=多副本单实例(可靠性,平台内置流量分发) | **1**(默认)或 M(步骤 1.1c 决策;PD 分离资源翻倍) |

### 第 4 步 — 模型配置

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 模型来源 | 选择模型来源 | 自定义模型 |
| 存储类型 | 选择权重位置 | 对象存储 OBS - 对象桶 |
| 存储地址(权重) | 选择权重 OBS 位置 | `obs://<bucket>/<prefix>/model/<模型目录>`(SKILL.md 步骤 1.2 的 `MODEL_PATH`) |
| 权重挂载路径 | 权重在容器内的只读挂载路径 | **`/home/ma-user/model`**(与启动脚本 `MODEL_PATH` 默认值一致) |
| 本地存储加速   | 开启本地存储加速后，文件会下载到节点上，如原始存储地址路径上的文件发生变化，将无法实时更新，若需更新请重启服务。 | 开启                                                         |

### 第 5 步 — 单元配置(角色/推理单元,含启动命令/健康检查/文件存储挂载)

> **单元配置是部署核心**: 推理单元(角色)、镜像、环境变量、启动命令、三层探针、code 目录文件存储挂载全部在本步配置。各推理单元配置项逐一填写后,再按下方"启动命令/健康检查"子项为每个单元配置探针与启动命令。
> **⚠️ 字段边界(强制,填写时逐项对照本表格字段清单)**: 本步**只包含下表列出的配置项**——单元名称/单元内实例数/单元实例规格/多机多卡部署/镜像类型/环境变量/文件存储挂载/启动命令,加上下方"健康检查"子项(启动/就绪/存活探针+探针参数)。**本步没有"容器端口"配置项**——容器端口属**第 6 步部署管理配置**,是**服务级对外端口,单一值 8080**。PD 分离的 prefill/decode 差异端口(如 8080/7101)属于本步**各单元的"环境变量"子项**(`PORT` 环境变量),**禁止**写入第 6 步容器端口。速查表(如 SKILL.md 4.2)中的关键值仅作提示,**字段归属以本表格为准**。

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 单元名称 | 推理单元名(即 API 的 `unit_configs[].name`,只允许 0-16 字符,仅小写字母/数字/连字符,且以字母或数字开头结尾) | **单部署单元结构**: 单节点/多节点/PD 共置 `role-1`;**PD 分离配置 2 个单元: `prefill` 与 `decode`**(同一部署单元内,`大写 `Prefill`/`Decode` 会报 400**) |
| 单元内实例数(资源实例数) | 单元内实例数(即 API 的 `unit_configs[].count`) | 单节点=1;**multinode/pd_colocate=N(副本内节点数)**;PD 分离=各角色节点数(资源翻倍) |
| 单元实例规格 | 预置规格 | 按节点卡数选型(如 8 规格) |
| 多机多卡部署 | multinode/pd_colocate 在部署页面选择"多机多卡部署" | **单副本资源实例数 = N(副本内节点数)**,部署副本数=1(多节点实例数在资源实例层级,不在单元副本层级) |
| 镜像类型 | 自定义镜像 | **容器镜像服务 SWR** 中的 `SWR_IMAGE_ADDRESS`(步骤 2;tag 以模型文档确认的版本为准,不要用 `latest`) |
| 环境变量                 | **仅注入部署单元配置项,其余脚本自动推导/有默认值**(见 SKILL.md 4.4 分类速查表) | **无需填 `TP_SIZE`/`DATA_PARALLEL_SIZE`**(脚本按资源池实例规格/rank table 自动推导);pd(PD 分离)2 个推理单元分别注入 `VLLM_ROLE=prefill` 与 `VLLM_ROLE=decode` + 双角色不同 `PORT`。`MODEL_PATH`/`PORT`/昇腾环境变量等**不用填**(容器内固定/模板默认)。**部署形式已固定在生成的脚本中,无需也不应再传 `DEPLOY_FORM` 环境变量** |
| 文件存储挂载(code 目录)  | 部署脚本目录,关键                                            | **存储地址 `CODE_OBS_PATH`(如 `obs://<bucket>/models/code/`)→ 挂载路径 `/home/ma-user/code/`→ 本地存储加速`开启`**;`start_vllm.sh`/`health_check.sh`/`get_master_ip.py` 均经此挂载访问,命令一律用容器内路径 `bash /home/ma-user/code/...` |
| 启动命令 | 容器启动命令(code 目录已挂载到 `/home/ma-user/code/`) | `bash /home/ma-user/code/start_vllm.sh`(**必须用 bash**,禁用 `sh`,脚本使用 bash 数组) |

**健康检查(每个推理单元均需配置,关键)**

单击 **启动探针** / **就绪探针** / **存活探针**,均选择 **"执行命令检查"**,命令为(code 目录已通过文件存储挂载到 `/home/ma-user/code/`,用容器内路径):

| 探针     | 命令                                                |
| -------- | --------------------------------------------------- |
| 启动探针 | `bash /home/ma-user/code/health_check.sh startup`   |
| 就绪探针 | `bash /home/ma-user/code/health_check.sh readiness` |
| 存活探针 | `bash /home/ma-user/code/health_check.sh liveness`  |

> **启动延迟(initial delay)设置 600 秒及以上**(超时 60s、周期 60s),**失败次数(failureThreshold)设置为 300**(周期 60s ≈ 18000s/300 分钟容忍窗口)——vLLM V1 引擎首次启动需编译 IR + 捕获 CUDAGraph,耗时 5~10 分钟;探针过早探测超时 → 实例被杀 → 重启 → 重新编译 → 死循环。启动延迟 + 大失败阈值双保险,彻底规避重启循环。

### 第 6 步 — 部署管理配置

> **⚠️ 本步是"容器端口"唯一归属处(强制)**: "容器端口"**只在本步配置**,第 5 步单元配置无此字段。值为**服务级对外端口,单一 8080**(与启动脚本 `PORT` 默认值一致)。**禁止**将 PD 分离的 prefill/decode 双角色差异端口(8080/7101)填入此处——那是第 5 步各单元"环境变量"子项的 `PORT` 值,与本步容器端口是两个不同层级。

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 容器协议 | 镜像内服务协议 | HTTP(或 HTTPS,与镜像一致) |
| 容器端口 | 镜像监听端口,与探针一致 | **8080**(服务级对外端口,单一值;与启动脚本 `PORT` 默认值一致) |

### 第 7 步 — 更多配置 > 部署超时时间 (分钟)

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| 部署超时时间 | 单次部署超时 | **300 分钟**(统一设置,多节点/大模型首启含模型加载 + CUDAGraph 编译,60 分钟不足会超时失败) |

### 第 8 步 — 更多配置 > 亲和调度(仅多机 multinode/pd_colocate)

1. 单击 **"亲和调度"**,亲和类型选 **"节点亲和"**,强度选 **"强亲和"**,添加节点选 **目标超节点**。
2. 将所有单元(副本内多节点)的亲和调度指向**同一超节点**(等效"超节点亲和组实例数=N",否则跨超节点调度报业务错误)。

### 第 9 步 — 确认部署

1. 核对全部配置后,单击 **"确定部署"**(或 **"确认部署"**)。
2. 部署一般耗时几分钟到几十分钟,在服务列表等待状态变为 **"运行中"**;若反复重启,优先检查健康检查启动延迟与失败次数配置(见常见排查)。
3. 部署完成后,在服务详情页获取 **"公网调用 URL"**(`access_address`),进入 SKILL.md 步骤 6 验证。

### 4 种部署形式控制台配置速查

> 统一单部署单元;副本数(部署副本数)由步骤 1.1c 依据可用节点数与可靠性需求决策(默认 1 单副本多实例;可靠性时 >1 多副本单实例)。

| 部署形式 | 部署副本数 | 单元数 | 单元名 | 单元内实例数(count) | 多机多卡 | 亲和调度 | **需在部署单元/模型配置中处理的项** |
|---------|-----------|--------|--------|---------------------|---------|---------|-------------|
| **single** 单节点 | 1(默认)或 M | 1 | role-1 | 1 | 否 | 无 | 无需环境变量(`TP_SIZE` 脚本按卡数自动推导;`MODEL_NAME` 建议填,非必填) |
| **multinode** 多节点 | 1(默认)或 M | 1 | role-1 | **N(副本内节点数)** | **是** | **强亲和=同一超节点(亲和组=N)** | ModelArts 注入 `GLOBAL_RANK_TABLE_FILE_PATH`(rank table JSON 路径)与 `POD_IP`(当前节点 IP);脚本经 `get_master_ip.py` 读取 rank table 取 master IP 与 `--dp-size` 推导 `DATA_PARALLEL_SIZE`,与 `POD_IP` 比较判定 master/slave 角色 |
| **pd** PD 分离 | 1(默认)或 M(**资源翻倍**) | **2**(同一部署单元内) | prefill / decode | 各角色节点数 | 否 | 无 | **同一部署单元内 2 个推理单元分别注入 `VLLM_ROLE=prefill` 与 `VLLM_ROLE=decode`** + 双角色不同 `PORT`(如 8080/7101) |
| **pd_colocate** PD 共置 | 1(默认)或 M | 1 | role-1 | **N(副本内节点数)** | **是** | **强亲和=同一超节点(亲和组=N)** | **无需注入任何角色/端口环境变量**(对齐官方 glm_5_2.sh 单引擎 DP 形态,PD 分工由 vLLM 引擎内部完成;master/slave 经 `get_master_ip.py` 读 rank table 判定) |

## 二、API 端点与鉴权(方式 A)

| 项 | 值 |
|----|-----|
| 创建在线服务 | `POST /v2/{project_id}/services` |
| 查询服务列表 | `GET /v2/{project_id}/services` |
| 查询服务详情 | `GET /v2/{project_id}/services/{service_id}` |
| 删除服务 | `DELETE /v2/{project_id}/services/{service_id}`(路径以 API 文档为准) |
| 扩缩容 | UpdateInferDeploymentScale(路径以 API 文档为准) |
| 鉴权 | 请求头 `Authorization: Bearer <IAM Token>`(有效期 24h)或 AK/SK 签名 |
| 权限 | `modelarts:service:create`(Write)/ `modelarts:service:get`(Read) |

> **注意**: 公有云新版 API 使用 `/v2`;旧版/HCS 私有化版本使用 `/v1/{project_id}/services` 的 `config[]` 结构,两者不能混用。本 skill 以 `/v2` 新版为准。

## 三、请求体结构(顶层平铺)

> **⚠️ 注意**: 新版 CreateInferService 请求体是**顶层平铺结构**——**不是**旧文档的 `service.deployment.roles[]` 嵌套结构(旧结构报 400 `name/type/group_configs/runtime_config` 缺失)。正确结构: 顶层直接放 `name`/`type`/`deploy_type`/`task_type`/`workspace_id`/`group_configs[]`/`runtime_config`。**⚠️ 顶层 `workspace_id` 必填(强制,违反=报 8179)**: POST 创建请求的 `workspace_id` 放请求 body 顶层(与 `name`/`type` 同级)——**不是请求头 `X-Workspace-Id`、也不是 URL 查询参数**;实测缺失报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`(资源池实际存在且 X-Infer 已启用),body 顶层补 `workspace_id` 后创建成功。**部署超时统一 300 分钟**: 顶层必须显式设置 **`deploy_timeout_minutes: 300`**(单位分钟),禁止使用平台默认(20~60 分钟,多节点/大模型首启超时会 FAILED)。

```json
{
  "name": "qwen3-8-27b-pd",
  "type": "REAL_TIME",
  "deploy_type": "MULTI",
  "task_type": "TEXT_GENERATION",
  "workspace_id": "<workspace-id>",
  "deploy_timeout_minutes": 300,
  "group_configs": [
    {
      "name": "group-0",
      "weight": 100,
      "pool_id": "<资源池ID>",
      "secret_type": "agency",
      "model": {
        "address": "obs://my-bucket/llm/model/Qwen3-8B",
        "mount_path": "/home/ma-user/model/",
        "source": "OBS",
        "type": "MODEL",
        "read_only": true,
        "host_cache": true
      },
      "count": 1,
      "schedule_strategy": "HIGH_AVAILABILITY",
      "unit_configs": [
        {
          "name": "prefill",
          "count": 2,
          "role": "COMMON",
          "flavor": "modelarts.vm.arm.16u.64g.npu.16snt9c",  # 从 ShowInferServiceCluster flavors[] 按 ascend.npu=16 取 id
          "cmd": "bash /home/ma-user/code/start_vllm.sh",
          "envs": {"VLLM_ROLE": "prefill", "PORT": "8080"},
          "image": {"source": "SWR", "swr_path": "swr.cn-north-4.myhuaweicloud.com/my-org/vllm-ascend:v0.23.0"},
          "files": [
            {"address": "obs://my-bucket/llm/code", "mount_path": "/home/ma-user/code/", "source": "OBS", "type": "FILE", "read_only": true, "host_cache": true}
          ],
          "liveness_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh liveness", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "readiness_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh readiness", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "startup_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh startup", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "recovery": "Instance"
        },
        {
          "name": "decode",
          "count": 2,
          "role": "COMMON",
          "flavor": "modelarts.vm.arm.16u.64g.npu.16snt9c",  # 从 ShowInferServiceCluster flavors[] 按 ascend.npu=16 取 id
          "cmd": "bash /home/ma-user/code/start_vllm.sh",
          "envs": {"VLLM_ROLE": "decode", "PORT": "7101"},
          "image": {"source": "SWR", "swr_path": "swr.cn-north-4.myhuaweicloud.com/my-org/vllm-ascend:v0.23.0"},
          "files": [
            {"address": "obs://my-bucket/llm/code", "mount_path": "/home/ma-user/code/", "source": "OBS", "type": "FILE", "read_only": true, "host_cache": true}
          ],
          "liveness_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh liveness", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "readiness_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh readiness", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "startup_health": {"check_method": "EXEC", "cmd": "bash /home/ma-user/code/health_check.sh startup", "failure_threshold": 300, "initial_delay_seconds": 300, "period_seconds": 60, "protocol": "HTTP", "timeout_seconds": 60},
          "recovery": "Instance"
        }
      ]
    }
  ],
  "runtime_config": {
    "service_invoke": {"auth_type": "NONE", "port": 8080, "protocol": "HTTP", "internet_access_enable": true},
    "service_limit": {"request_timeout": 300, "request_size_limit": 20, "rate_limit": {"num": 200, "unit": "SECONDS"}},
    "service_secret": {"group_enable": false, "secret_enable": false, "secret_volumes": []}
  }
}
```

> **多节点结构要点(与 PD 的差异)**: 多节点(multinode)与 PD 共置(pd_colocate,非 PD 分离)用 **1 个单元 + `unit_configs[].count=N`**(N=副本内节点数,如 2)承载多节点,`group_configs[].count=1`。**平台把 count 解释为单元内资源实例数**(单副本资源实例数为多,而非单元副本数/group 级实例数);平台不会自动注入 `NODE_RANK`/`MASTER_ADDR`/`VC_WORKER_HOSTS` 等组网变量——**start_vllm.sh/get_master_ip.py 需自带确定性主从判定**(get_master_ip.py 优先读 `MASTER_ADDR`,其次 `VC_WORKER_HOSTS` 取第一个 IP 为 master,多网卡按本机 IP 遍历比较,禁止退回 127.0.0.1 导致全部实例判为 worker)。上方 JSON 示例是 **PD 分离双单元结构**(单部署单元内 prefill + decode 两个推理单元);多节点/PD 共置时把 `unit_configs[]` 缩为 1 个 `role-1`,`count` 改为 N,`envs` 删掉 `VLLM_ROLE`。

> **⚠️ A5(snt9e/950 系列)特殊字段(强制,与 A2/A3 差异)**: 上方 JSON 骨架与字段说明是在 **A2(910B)/A3(910C)资源池**上验证过的。本次 A5(950 系列 `ascend-snt9e`)控制台实际创建请求体相比 A2/A3 骨架,**多出以下字段**——部署到 A5 资源池时必须补充(推荐直接用 `create_infer_service.py create --chip-model a5`,脚本自动注入;或 `--raw-json` 手工构造时逐项核对)。**非 A5 场景(a2/a3)保持原骨架,不注入这些字段**。

| 字段位置 | A5 取值 | 说明 |
|---------|--------|------|
| 顶层 `tags` | `[]` | A5 请求体实测必带空数组 |
| 顶层 `schedule` | `[]` | A5 请求体实测必带空数组 |
| 顶层 `log_configs` | `[{"status":"OFF","type":"STDOUT"},{"status":"OFF","type":"EVENT"},{"status":"OFF","type":"FILE","files":[]}]` | A5 请求体实测必带 |
| `group_configs[].workload_type` | `"LWS"` | A5 轻量服务调度策略(LWS);A2/A3 骨架无此字段 |
| `group_configs[].async_scheduling` | `true` | **资源不足时异步排队而非立即 8118 拒绝**;A2/A3 骨架无此字段(缺省同步调度) |
| `group_configs[].priority` | `1` | 调度优先级 |
| `group_configs[].framework` | `"COMMON"` | 框架类型 |
| `group_configs[].system_log_dump_enable` | `false` | 系统日志转储开关 |
| `group_configs[].deploy_type` | `"MULTI"` | group 级部署类型 |
| `group_configs[].advanced_config` | 对象,含 `protocol`/`port`/`ports`/`network_isolation_enable`/`deploy_timeout_minutes`/`dynamic_routing_enable`/`mooncake_enable`/`custom_metrics_path`/`upgrade_config`/`service_secret` | **A5 的 `deploy_timeout_minutes: 300`、`port: 8080`、`protocol`、`upgrade_config`、`service_secret` 全在这个对象里**(非 A2/A3 骨架的顶层 `deploy_timeout_minutes`/`runtime_config.service_invoke.port`) |
| `group_configs[].secret_type` | `"dew"` | A5 控制台实测用 `dew`(A2/A3 骨架用 `agency`;两者平台均接受,但 A5 以 `dew` 为准) |
| `unit_configs[].group_count` | `replicas` | 单元所属 group 内实例数 |
| `unit_configs[].termination_grace` | `{"termination_grace_period_seconds": 30}` | 终止宽限期 |
| `unit_configs[].npu_reset_enable` | `false` | NPU 复位开关 |
| `unit_configs[].cpu_affinity` | `false` | CPU 绑核开关 |
| `unit_configs[].codes` | `[]` | A5 实测必带空数组 |
| `unit_configs[].models` | `[]` | A5 实测必带空数组 |
| `unit_configs[].dumps` | `[]` | A5 实测必带空数组 |
| `unit_configs[].secret_type` | `"dew"` | unit 级也有 secret_type |
| `unit_configs[].{liveness,readiness,startup}_health.name` | `"survival_probe"`/`"ready_probe"`/`"start_probe"` | A5 探针对象带 name;A2/A3 骨架无 |
| `runtime_config.service_invoke.direct_channel_enable` | `false` | 直连通道开关 |
| `runtime_config.service_invoke.intranet_approval_enable` | `true` | 内网审批开关 |
| `runtime_config.service_limit.ip_white_list` | `[]` | IP 白名单 |
| `runtime_config.service_limit.ip_black_list` | `[]` | IP 黑名单 |

### 字段说明(以 API 文档为准)

| 字段 | 必选 | 类型 | 说明 |
|------|------|------|------|
| `name` | 是 | String | 服务名,1-64 字符,同地域唯一(顶层,非 service 包裹) |
| `type` | 是 | String | 服务类型: `REAL_TIME`/`BATCH`/`EDGE`/`ASYNC_REAL_TIME`/`ASYNC_EDGE` |
| `deploy_type` | 否 | String | 部署类型: `MULTI`(多单元/PD)等 |
| `task_type` | 否 | String | 任务类型: `TEXT_GENERATION` |
| `workspace_id` | **是** | String | **所有环境必填,放请求 body 顶层字段(与 `name`/`type` 同级)——POST 创建请求经 body 传递,不是请求头 `X-Workspace-Id`、也不是 URL 查询参数**。**实测缺失报 `400 ModelArts.8179 Resource pool does not exist or the x-infer service is disabled`**(资源池实际存在且 X-Infer 已启用,仅因 body 缺 `workspace_id`)。GET 查询接口则带头 `X-Workspace-Id` + URL 双查询参数 `?workspaceId={}&workspace_id={}`(除工作空间列表接口外) |
| `deploy_timeout_minutes` | 否 | Integer | **部署超时时间(分钟),统一设置 300**。**禁止用平台默认(20~60 分钟)**——多节点/大模型(如 GLM-5.2 MoE)首次启动含模型加载 + CUDAGraph 编译,60 分钟不足会触发部署超时失败(`status: FAILED`)。请求体顶层字段,构造后复查未被覆盖丢失。控制台对应"部署超时时间"填 300 分钟 |
| `group_configs[].name` | 是 | String | 部署组名称(如 group-0) |
| `group_configs[].weight` | **是** | Integer | 流量权重,必填(如 100) |
| `group_configs[].pool_id` | 是 | String | 专属资源池 ID |
| `group_configs[].secret_type` | **是** | String | OBS 挂载认证: **`agency`**(委托,控制台默认);`dew`/`obspool`/`obs` 均报错 |
| `group_configs[].model` | 是 | Object | 权重挂载: `address`=MODEL_PATH、`mount_path`=`/home/ma-user/model/`、`source`=OBS、`type`=MODEL、`read_only`=true、**`host_cache`=true(本地加速,OBS 挂载缓存到主机本地,加速模型权重加载;所有芯片 A2/A3/A5 统一开启)** |
| `group_configs[].count` | 是 | Integer | **副本数(部署单元级)**: 默认 1(单副本多实例);多副本单实例(可靠性)时 >1。多节点场景固定为 1(节点数 N 由 `unit_configs[].count` 承载);单节点 = 1 |
| `group_configs[].schedule_strategy` | 否 | String | 调度策略: `HIGH_AVAILABILITY` |
| `unit_configs[].name` | 是 | String | 单元名称(**单部署单元结构**: 单节点/多节点/PD 共置用 `role-1`;PD 分离用 2 个 `prefill`/`decode`)。**命名规范**: 只允许 0-16 字符,仅小写字母/数字/连字符 `-`,且以字母或数字开头结尾——**大写 `Prefill`/`Decode` 报 400** |
| `unit_configs[].count` | 是 | Integer | **单元内资源实例数(单副本多实例场景承载跨节点数 N)**: 多节点(multinode)/PD 共置(pd_colocate) = N(副本内节点数,单副本资源实例数为多);PD 分离 = 各角色节点数;单节点 = 1 |
| `unit_configs[].role` | 否 | String | 角色: `COMMON` |
| `unit_configs[].flavor` | 是 | String | **推理实例规格**,从**查询纳管资源池详情(ShowInferServiceCluster)** `GET /v2/{project_id}/services/clusters/{pool_id}` 获取(见 SKILL.md 步骤 0 第 ⑦ 条): 响应 `flavors[]` 中按 `ascend.npu`(实际使用卡数,一般 `card=npu`,A3 `card×2=npu`;**以 `npu` 为准**)选所需卡数条目,取其 `id`(如 `modelarts.vm.arm.16u.64g.npu.16snt9c`)。**禁止从节点规格推导**(前缀 `vm`/`bm` 与内存取整档无法从节点规格得出);**禁止填资源池节点规格**(如 `modelarts.bm.npu.arm.ssd`——这是 ECS 物理机 flavor,报 `400 ModelArts.6404 Flavor not found`) |
| `unit_configs[].cmd` | 是 | String | 启动命令 `bash /home/ma-user/code/start_vllm.sh` |
| `unit_configs[].envs` | 否 | Object | 环境变量(**pd PD 分离必填 `VLLM_ROLE=prefill\|decode` + 双角色不同 `PORT`**,2 个推理单元分别注入;multinode/pd_colocate 单引擎形态无需注入任何角色/端口变量,由 `get_master_ip.py` 自动判定) |
| `unit_configs[].image` | **是** | Object | SWR 镜像: `source`=SWR、`swr_path`=SWR_IMAGE_ADDRESS |
| `unit_configs[].files[]` | 是 | Array | code 目录挂载: `address`=CODE_OBS_PATH、`mount_path`=`/home/ma-user/code/`、`type`=FILE、`read_only`=true、**`host_cache`=true(本地加速,OBS 挂载缓存到主机本地;所有芯片 A2/A3/A5 统一开启)** |
| `unit_configs[].{startup,liveness,readiness}_health` | 是 | Object | 探针: `check_method`=EXEC、`cmd`、**`failure_threshold`=300、`initial_delay_seconds`=300、`period_seconds`=60**、`timeout_seconds`=60 |
| `unit_configs[].recovery` | 否 | String | 恢复策略: `Instance` |
| `runtime_config.service_invoke` | 是 | Object | `auth_type`=NONE/TOKEN/API_KEY、**`port`=8080(必须与启动脚本一致)**、`protocol`=HTTP |
| `runtime_config.service_limit` | 是 | Object | `request_timeout`=300、`request_size_limit`=20、**`rate_limit` 必填** |
| `runtime_config.service_secret` | 否 | Object | 服务访问密钥配置 |

> **获取正确结构的最可靠方法**: 查询**已部署成功的现有服务**(`show` 返回 `version.instance_groups[].unit_configs[]` 即完整参考),对照其字段构造创建请求。字段名以 API Explorer 为准。

## 四、模型来源与挂载(新版,无需创建 AI 应用)

新版在线服务**不再需要先创建 AI 应用**,直接在 `roles[]` 中配置:

| 模型来源方式 | 说明 | 大模型场景(vLLM 镜像 + OBS 权重) |
|-------------|------|----------------------------------|
| SWR 容器镜像 | 自有镜像 / 共享镜像 / 企业版镜像 | **采用**: `roles[].image` 填 `SWR_IMAGE_ADDRESS` |
| OBS 权重挂载 | OBS 桶指定文件夹只读挂载到容器路径 | **采用**: `roles[].model.obs_path` 填权重目录,`mount_path` 填 `/home/ma-user/model` |
| 资源池已预热模型 | 提前预热权重到资源池 | 备选(需预热流程) |
| ModelArts 预置镜像 | 平台预置镜像 | 不适用于 vllm-ascend 定制镜像 |

**OBS 挂载机制**: OBS 挂载把 OBS 桶指定文件夹内的文件**只读挂载**到容器指定路径。实际部署以镜像为基础拉起容器,以只读文件系统形式挂载 OBS 文件。优点: OBS 文件变动无需重新创建镜像。

**目录结构(model/ 与 code/ 同级)**: 权重目录 `obs://<bucket>/<prefix>/model/<模型目录>` 与部署脚本目录 `obs://<bucket>/<prefix>/code` 同级。code 目录(CODE_OBS_PATH)存放启动脚本 `start_vllm.sh`、探针脚本 `health_check.sh`、角色识别脚本 `get_master_ip.py` 等全部部署产物,由 `scripts/upload_code_to_obs.py` 上传。

## 五、探针配置(命令检查方式)

新版在线服务推荐**执行命令检查**方式,三类探针:

| 探针 | 命令示例 | 语义(K8s) |
|------|---------|-----------|
| 启动探针 | `bash /code/health_check.sh startup` | 启动初期查 vllm 进程存活,防止启动误杀 |
| 就绪探针 | `bash /code/health_check.sh readiness` | 服务就绪判定,失败移出流量端点 |
| 存活探针 | `bash /code/health_check.sh liveness` | 运行期查进程,失败重启容器 |

> **启动延迟(initial delay)设置 600 秒及以上,失败次数(failureThreshold)自动设置为 300**(超时 60s、周期 60s;失败次数 300 × 周期 60s ≈ 18000s/300 分钟容忍窗口)——vLLM V1 引擎首次启动需编译 IR + 捕获 CUDAGraph,耗时可达 5~10 分钟;探针过早探测超时 → 实例被杀 → 重启 → 重新编译 → 死循环(详见常见问题排查"服务反复重启")。启动延迟 + 大失败阈值双保险,彻底规避重启循环。

## 六、4 种部署形式 → 请求体映射矩阵

> **单部署单元结构**: 所有推理单元放在同一 `group_configs[0].unit_configs[]`;`group_configs[0].count`=副本数(默认 1),`unit_configs[].count`=单元内实例数(跨节点数)。

| 部署形式 | group_configs[0].count(副本数) | unit_configs[](推理单元) | 关键 envs / 字段 |
|---------|-------------------------------|--------------------------|------------------|
| **single** 单节点 | 1(默认)或 M | 1 个 role-1,`count`=1 | `TP_SIZE`=卡数、`ASCEND_RT_VISIBLE_DEVICES`、`MODEL_NAME` |
| **multinode** 多节点 | 1(默认)或 M | 1 个 role-1,`count`=N(副本内节点数) | ModelArts 注入 `GLOBAL_RANK_TABLE_FILE_PATH` + `POD_IP`;脚本经 `get_master_ip.py` 读 rank table 取 master IP 与 `--dp-size` 推导 `DATA_PARALLEL_SIZE`,判定 master/slave + 超节点亲和组=N |
| **pd** PD 分离 | 1(默认)或 M(**资源翻倍**) | **2 个: prefill + decode**,各 `count`=该角色节点数 | `VLLM_ROLE=prefill\|decode`(2 个推理单元分别注入)、各自不同 `PORT` |
| **pd_colocate** PD 共置 | 1(默认)或 M | 1 个 role-1,`count`=N(副本内节点数) | **无需注入任何角色/端口环境变量**(对齐官方 glm_5_2.sh 单引擎 DP 形态,PD 分工由 vLLM 引擎内部完成;master/slave 经 `get_master_ip.py` 读 rank table 判定)+ **亲和组=N** |

> 详细场景决策依据见 `references/deployment-form-decision.md`。**部署形式已固定在生成的脚本中,无需也不应再传 `DEPLOY_FORM` 环境变量**。

## 七、配套 API 与生命周期管理

| 操作 | API | create_infer_service.py 子命令 |
|------|-----|-------------------------------|
| 创建服务 | `POST /v2/{project_id}/services` | `create` |
| 查询服务列表 | `GET /v2/{project_id}/services` | `list` |
| 查询服务详情(状态 + 调用端点) | `GET /v2/{project_id}/services/{service_id}` | `show` |
| 删除服务 | `DELETE /v2/{project_id}/services/{service_id}` | `delete` |
| 扩缩容 | UpdateInferDeploymentScale | `scale` |
| 切换部署版本 | SwitchInferDeploymentVersion | — |

服务状态取值: `DEPLOYING`(部署中)/ `RUNNING`(运行中)/ `STOPPED` / `FAILED`(失败)/ `DELETING` / `UPGRADING` / `CONCERNING`。

调用端点: 服务详情返回 `access_address`(公网调用 URL)或 `internal_path`(内网),大模型服务追加 `/v1/chat/completions` 即 OpenAI 兼容端点。

## 八、关键约束与限制

- 单个在线服务最多 **5 个部署**、最多 **10 个版本**、单个部署副本数有上限(以官方约束页为准)
- 最大昇腾卡规模 **384 卡**;单用户最多 20 个在线服务(新版推理)
- 部署在线服务仅支持专属资源池、逻辑子池;逻辑资源池**不支持**多角色分离部署、亲和调度
- 跨节点 TP(multinode/pd_colocate)必须配置**超节点亲和组实例数=N**(副本内节点数),否则部署后报业务错误(参见故障排除 inference2.0-modelarts-0042)
- 忙态流控: 单用户 120 次请求/分钟、单接口 1000 次请求/分钟

## 九、常见排查

| 现象 | 处理 |
|------|------|
| 创建 API 返回 401/403 | IAM Token 失效(24h)或权限不足(缺 modelarts:service:create);重新获取 Token / 确认权限 |
| 创建 API 返回 4xx(参数错误) | `roles[]` 请求体字段名与当前 API 版本不符;在 API Explorer 生成完整请求体,用 `--raw-json` 传入 |
| 服务一直"部署中" | 查看实例日志,重点看模型加载是否完成、探针是否通过;`show` 轮询状态 |
| 实例反复重启 | 探针 startup 延迟过短;确认启动延迟 600s 与失败次数 300 已配置 |
| 启动报 CANN/驱动错误 | 镜像 tag 与资源池昇腾版本不兼容,换用匹配的镜像版本 |
| OOM | 调小 MAX_MODEL_LEN / GPU_MEM_UTIL,或增加卡数 |
| 跨节点 TP(multinode/pd_colocate)报业务错误 | 超节点亲和组实例数未配置或不等于 N,改为 N(副本内节点数) |
| 多副本实例间端口冲突 | vllm 原生 DP 多副本实例的 `--data-parallel-rpc-port` 需区分(`DATA_PARALLEL_RPC_PORT` 环境变量按副本注入不同值) |
| pd_colocate 实例间通信失败 | DP 通信端口未放通或 master/slave 角色判定失败;核对 `--data-parallel-rpc-port`(13389)放通、`get_master_ip.py` 读 rank table 角色判定正确 |
| pd(分离)请求 502/504 | 前置 LB 或流量权重配置错误;核对双推理单元流量权重与前置 LB 健康检查 |

## 十、ModelArts 平台适配清单(从 vllm-ascend 官方脚本到 ModelArts 适配)

> vllm-ascend 官方模型适配文档给出的启动命令是为裸机/容器直跑设计的(本地路径、8000 端口、直接 CLI 参数),不能直接用于 ModelArts 在线服务部署。下表是模板填充完成后的**自检清单**(参考华为云官方最佳实践 modelarts_10_3121 section7),逐项核对模板是否符合 ModelArts 适配要求;模板已内置大部分适配点,仅需按模型文档填充环境变量与 `MODEL_ARGS` 数组。

| 适配维度 | vllm-ascend 官方 | ModelArts 适配后 | 原因 |
|---------|-----------------|-----------------|------|
| 启动命令 | `vllm serve ...` | `exec python -m vllm.entrypoints.openai.api_server` 包成 bash 脚本 | ModelArts 启动命令引用 OBS 上的 bash 脚本路径 |
| 监听端口 | 8000(默认) | **8080**(与探针一致) | ModelArts 探针端口约定 |
| 模型路径 | 本地绝对路径 | `${MODEL_PATH:-/home/ma-user/model}`(OBS 只读挂载) | 权重与镜像分离,实例重建后权重仍在 |
| 参数传递 | 直接 CLI | bash 数组 `MODEL_ARGS=(...)` + 环境变量覆盖 | JSON 参数引号不丢失;ModelArts 通过环境变量覆盖 |
| TP_SIZE(多节点) | 本机卡数 | **每台推理单元 NPU 卡数**(如 8) | TP 是单节点内并行,多机 DP 由 `--data-parallel-*` 参数承载 |
| 健康检查(多节点) | 所有节点探 /health | **所有节点探 master 的 /health**(调用 `get_master_ip.py` 取 master IP) | slave 不直接对外提供 API,但探 master /health 反映集群就绪状态 |
| 健康检查(PD 共置) | 无 | **三层探针**(startup/liveness 查 vllm 进程,readiness 调用 `get_master_ip.py` 取 master IP 探 `/health`) | 所有节点探 master /health 反映集群就绪,规避 PD 共置启动慢导致的重启循环 |
| 新增文件 | 无 | `start_vllm.sh`、`health_check.sh`、`get_master_ip.py`(multinode/pd_colocate) | ModelArts 平台要求 |
| 文件存储挂载 | 无 | OBS `model/` 与 `code/` 同级,挂载到容器内 | 权重与脚本分离 |
| 探针配置 | 无 | 路径 /health、端口 8080、启动延迟 600s、超时 60s、周期 60s、失败次数 300 | 规避 vLLM V1 首启 5~10 分钟导致的重启循环 |
| 环境变量 | 文档给定 | 同文档;健康检查失败次数自动设 300(首启容忍窗口) | 规避 ModelArts 探针误杀重启循环 |
| 启动命令执行 | 任意 shell | **`bash /home/ma-user/code/start_vllm.sh`**(code 目录挂载到容器后;禁用 `sh`) | bash 数组语法 `sh` 不识别 |
| 脚本内文件引用 | 任意 | `$(dirname "$0")` 相对定位,禁硬编码 `/code/` | 挂载路径由用户配置决定 |
| JSON 参数 | 字符串变量 | bash 数组,单引号包裹 | 避免引号丢失 |
| 权重自检 | 无 | `config.json` 存在性检查,缺失时打印挂载目录并退出 | 规避 `OSError: Repo id must be in the form...` 晦涩报错 |
| 多副本(可靠性) | 无 | ModelArts `group_configs[].count` 承载,平台流量分发,模板无需修改 | 副本即独立 TP 域 |
| 超节点亲和组(multinode/pd_colocate) | 无 | **=N**(副本内节点数),确保跨节点 TP 多机调度到同一超节点 | 跨超节点通信带宽低,直接报业务错误 |
| PD 分离(pd) | 无 | **单部署单元内 2 个推理单元(prefill + decode)**,分别注入 `VLLM_ROLE`,双角色不同 PORT | PD 分离平台承载,单部署单元双 unit |
| PD 共置(pd_colocate) | 无 | **单单元 N 节点**(`unit_configs[].count`=N),vLLM 引擎内部 PD 分工,无需 `VLLM_ROLE` | 对齐官方 glm_5_2.sh 单引擎 DP 形态 |
