# /etc/hixlep 生成与调用指南

昇腾 A5 (950DT/950) 超平面通信（UB 链路）专用配置目录。当 `/etc/hixlep` 不存在或为空、且 `ASCEND_LOCAL_COMM_RES` 自动生成机制不可用时，按本指南手动生成并通过 vllm-ascend 启动参数调用。

## 1. 角色与适用场景

`/etc/hixlep/` 由 hixl（HCCN Inter-X Logical EP）工具生成，存放昇腾 UB（Unified Bus，超平面）链路的端点（endpoint）拓扑、路由发现结果与 net_instance_id。

适用范围：A5 节点间需走超平面 UB 通信的部署形态。

| 部署形态 | 是否需要 hixlep | 说明 |
|---------|---------------|------|
| 单机单卡（TP=1） | 否 | 无跨卡通信，HCCL 不建链 |
| 单机多卡（TP>1） | 通常否 | 同节点 8 卡走 HCCS，HCCL 通过 `hccl_rootinfo.json` 自发现；仅当走 UB 走超平面路由时需要 |
| 多节点（TP>1/PP>1/EP>1） | 是 | 跨节点 UB 通信，需配置 hixlep |
| PD 分离（MooncakeConnectorV1） | 是 | P↔D 间 KV cache 经 UB 传输，必须配置 hixlep |
| PD 分离（同机两角色） | 是 | 与 PD 分离同，跨容器/跨卡 UB 传输 |

判定准则：**只要 vllm-ascend 进程间存在 UB 通信，就需 /etc/hixlep**；纯单机单卡无任何分布式通信则不需要。

## 2. 必备前置文件

```
/etc/hccl_rootinfo.json   # HCCL 建链根信息（多机 rootInfo），优先于 hixlep
/lib/route.conf           # UB 路由表
/etc/hixlep/             # UB endpoint 拓扑（本指南生成对象）
```

`/etc/hccl_rootinfo.json` 缺失时先单独生成（见附录 B），hixlep 生成前 rootinfo 必须正确。

## 3. 生成工具链

### 3.1 生成依赖（脚本随 skill 内置;unofficial-ascend-tools 运行时获取）

| 文件 | 位置 | 作用 |
|------|------|------|
| `generate_ep.py` | `${SCRIPT_DIR}/a5_hixlep/generate_ep.py` | skill 权威源,hixl 研发提供,读 hccl_rootinfo.json + route.conf + 拓扑 JSON,输出 `/etc/hixlep/ub_endpoint_npu_*.json` |
| `fix_ub_endpoint.py` | `${SCRIPT_DIR}/a5_hixlep/fix_ub_endpoint.py` | hixlep 生成后修正 NPU ID ↔ Chip Phy-ID 文件名映射(用 `npu-smi info -m` 建立映射重命名) |
| `gen_route.sh` | `${OFFLINE_PKG_DIR}/gen_route.sh` | 纯 bash 脚本,读 `/proc/ascend_ub` 驱动接口,生成 `/lib/route.conf` |
| `get_route_eid.py` | `${OFFLINE_PKG_DIR}/get_route_eid.py` | 独立脚本,多机场景由 gen_route.sh 调用读 `/home/source_dest_ips.txt` |
| `unofficial-ascend-tools==0.0.7rc4` | 运行时安装(PyPI) | 纯 Python 包无外部依赖,由包内 console script `mindcluster-tools` 提供 `rootinfo` 子命令生成 `/etc/hccl_rootinfo.json`(包内**没有**可供 `python3 -m` 调用的同名模块,入口以 `entry_points.txt` 的 `mindcluster-tools = unofficial_ascend_tools.rankinfo.main:main` 为准)。该 wheel 不随 skill 内置(二进制文件不在产物文件类型白名单);启动脚本运行时执行 `python3 -m pip install unofficial-ascend-tools==0.0.7rc4`,离线环境可下载同版本 wheel 后用 `HCCL_TOOLS_WHEEL` 指定本地路径;显式指定但文件不存在时脚本直接报错退出,不会静默回落联网 |

`generate_ep.py` 仅依赖 Python 标准库(argparse/json/pathlib/typing),无需 pip 安装任何依赖。`gen_route.sh` 是纯 bash 脚本,仅需 `/proc/ascend_ub`(或 `/proc/asdrv_ub`)+ `/proc/uda/namespace_node` 驱动接口,无额外 Python 依赖。

### 3.2 输入文件前置条件(三类文件均容器内现生成)

`generate_ep.py` 需要三个输入,均可容器内现生成(无需主机预生成或 ModelArts 挂载主机路径):

| 输入 | 路径 | 来源 |
|------|------|------|
| route.conf | `/lib/route.conf` | 容器内调用内置 `gen_route.sh` 生成(纯 bash,读 `/proc/ascend_ub` 驱动接口);需主机 HDK 驱动已装且容器可访问 `/proc` |
| hccl_rootinfo.json | `/etc/hccl_rootinfo.json` | 主机已存在则直接用;缺失则运行时安装 `unofficial-ascend-tools==0.0.7rc4` 生成 |
| 拓扑 JSON | hccl_rootinfo.json 中 `topo_file_path` 字段指向 | 随 hccl_rootinfo.json 一并由 mindcluster-tools 生成 |

### 3.3 生成流程(skill 启动脚本内置自动执行)

> `HCCL_TOOLS_WHEEL` 显式设置但文件不存在 → 脚本直接 `[ERROR]` 非零退出(不会静默改走 PyPI);未设置且产物目录无内置 wheel 时才从 PyPI 安装并打印提示。`rootinfo` 入口优先用 console script `mindcluster-tools`,不在 PATH 时回退 `python3 -c 'from unofficial_ascend_tools.rankinfo.main import main; ...'`;禁止用 `python3 -m unofficial_ascend_tools.rankinfo.*`(无 `__main__` 守卫,会静默 exit 0 不产出文件)。

```bash
# 1) hccl_rootinfo.json 缺失则运行时获取 unofficial-ascend-tools 生成
if [ ! -s /etc/hccl_rootinfo.json ]; then
    # 有网: 直接从 PyPI 安装同版本;离线: 用 HCCL_TOOLS_WHEEL 指定已下载的本地 wheel 路径
    if [ -n "${HCCL_TOOLS_WHEEL:-}" ]; then
        # 显式指定就必须命中,文件不存在直接报错退出(不会静默回落到 PyPI 联网安装)
        [ -f "${HCCL_TOOLS_WHEEL}" ] || { echo "[ERROR] HCCL_TOOLS_WHEEL=${HCCL_TOOLS_WHEEL} 不存在,离线安装失败(不会回落到 PyPI)" >&2; exit 1; }
        python3 -m pip install --no-index --no-deps "${HCCL_TOOLS_WHEEL}" || { echo "[ERROR] 安装 unofficial-ascend-tools 失败: ${HCCL_TOOLS_WHEEL}" >&2; exit 1; }
    else
        echo "[hixlep] 未指定 HCCL_TOOLS_WHEEL,从 PyPI 安装 unofficial-ascend-tools==0.0.7rc4"
        python3 -m pip install "unofficial-ascend-tools==0.0.7rc4" || { echo "[ERROR] 安装 unofficial-ascend-tools==0.0.7rc4 失败;离线环境可下载同版本 wheel 后用 HCCL_TOOLS_WHEEL 指定本地路径" >&2; exit 1; }
    fi
    # 入口是 unofficial-ascend-tools 提供的 console script `mindcluster-tools`(见 entry_points.txt),
    # 包内没有可供 python3 -m 调用的同名模块;rankinfo/main.py 也无 __main__ 守卫,`python3 -m ...` 会
    # exit 0 但不产出文件(静默失败),禁止使用。
    # &&/|| 形式避免 set -e 下直接退出,保证能捕获真实退出码
    if command -v mindcluster-tools >/dev/null 2>&1; then
        mindcluster-tools rootinfo --product_type server --output /etc/hccl_rootinfo.json && rc=0 || rc=$?
    else
        # console script 不在 PATH(pip install --user 常落到 ~/.local/bin)时直接调用包入口
        python3 -c 'from unofficial_ascend_tools.rankinfo.main import main; import sys; sys.exit(main())' \
            rootinfo --product_type server --output /etc/hccl_rootinfo.json && rc=0 || rc=$?
    fi
    [ "${rc}" -eq 0 ] || { echo "[ERROR] mindcluster-tools rootinfo 执行失败(rc=${rc}): 入口解析或工具执行异常(检查安装与 Ascend HDK 驱动)" >&2; exit 1; }
    # 不只信退出码: 断言产物存在且非空
    [ -s /etc/hccl_rootinfo.json ] || { echo "[ERROR] mindcluster-tools rootinfo 退出码 0 但未生成 /etc/hccl_rootinfo.json" >&2; exit 1; }
fi

# 1.5) hccl_rootinfo.json rank_list[].local_id 范围调整:
#      mindcluster-tools 生成或主机自带的 hccl_rootinfo.json 的 local_id 可能不是 0-7
#      (实测 950DT 主机 rootinfo 的 local_id 为 48-55,多节点 rank table 全局 ID 可能为 8-15),
#      而 route.conf 的 dev_id 为 0-7(本地 davinci ID),
#      generate_ep.py 用 local_id_to_device_id.get(route_conf_dev_id) 查 0-7 在 48-55/8-15 映射表里找不到,
#      导致 8 个 endpoint 全部 Warning: device_id not found、hixlep 文件数为 0。
#      修复: 按 rank_list 索引重新分配 local_id = 0,1,...,N-1(与 route.conf dev_id 0-7 对齐),
#      与原 local_id 取值范围无关,兼容 8-15 / 48-55 等任意取值(容器内临时文件,不影响主机原文件)。
cp /etc/hccl_rootinfo.json /tmp/hccl_rootinfo_adj.json
HCCL_ROOTINFO_PATH_ADJ=/tmp/hccl_rootinfo_adj.json python3 -c '
import json, os
path = os.environ["HCCL_ROOTINFO_PATH_ADJ"]
with open(path) as f:
    data = json.load(f)
rank_list = data.get("rank_list", [])
adjusted = 0
for idx, rank in enumerate(rank_list):
    lid = rank.get("local_id")
    if isinstance(lid, int) and lid != idx:
        rank["local_id"] = idx
        adjusted += 1
if adjusted > 0:
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[hixlep] hccl_rootinfo.json local_id 按 rank_list 索引重排 {adjusted} 个 rank -> 0..{len(rank_list)-1}")
'

# 2) route.conf 缺失则调用内置 gen_route.sh 生成(纯 bash,读 /proc/ascend_ub 驱动接口)
#    gen_route.sh 来自 a5_hixlep 目录,直接调 bash 脚本即可
if [ ! -s /lib/route.conf ]; then
    bash a5_hixlep/gen_route.sh
fi

# 3) 生成 /etc/hixlep/ub_endpoint_npu_*.json
#    -s: server 模式(0+8 server 拓扑),匹配 A5 单机 8 卡;多机/PD 分离沿用同模板
#    generate_ep.py 内置 plane_uboe/plane_roce 跳过逻辑:
#      - plane_uboe: 不参与 PD KV 传输,跳过该 endpoint
#      - plane_roce: addr 为 IP 格式,放入 comm_id 会触发 Mooncake ParseEidAddress 失败;
#        PD 分离 P↔D 跨卡 KV 传输走 UB 链路不依赖 RoCE plane,跳过该 endpoint 规避畸形条目
python3 generate_ep.py -s

# 4) 多机 net_instance_id 一致性核验(单机可忽略)
grep -h net_instance_id /etc/hixlep/*.json | sort -u   # 多机应只有 1 行

# 5) NPU ID ↔ Chip Phy-ID 文件名映射修正(A5 PD 分离 RoCE 场景必需)
#    generate_ep.py 按 hccl_rootinfo.json 的 device_id(可能为 Chip Phy-ID 如 32-39)命名
#    ub_endpoint_npu_<device_id>.json,但 vllm-ascend 按 NPU ID(0-7)索引文件 → 文件名错位
#    fix_ub_endpoint.py 用 npu-smi info -m 建立映射,删除不存在的 + 按 NPU ID 重命名
#    参考 wiki《A5 带Roce场景参数面部署》PD 分离 1p1d 单机 8 卡方案
HIXLEP_DIR=/etc/hixlep python3 fix_ub_endpoint.py -y
```

### 3.4 核验规则

生成后**必须核验**四项(generate_ep.py 默认正确,但多机场景必须人工确认):

1. **文件命名**:`ub_endpoint_npu_0.json` ~ `ub_endpoint_npu_7.json`(0-7 连续,不可有缺号或乱序名)
2. **host 字段**:删除所有 `host` 相关键值(含外层花括号);保留 eid/net_instance_id 等字段
3. **net_instance_id**:多机场景下,所有节点生成的 endpoint 文件中 `net_instance_id` 必须一致
4. **endpoint_list 内 comm_id 格式**:全部为 20 字节 hex eid,不应含 IP 格式(RoCE plane 已跳过)

```bash
# 多机核对(每节点执行后比对输出)
grep -h net_instance_id /etc/hixlep/*.json | sort -u   # 多机输出应只有 1 行
grep -l '"host"' /etc/hixlep/*.json                    # 输出应为空
ls /etc/hixlep/ | sed 's/.*npu_\([0-9]\)\.json/\1/' | sort -n | uniq   # 应为 0..7
```

## 4. vllm-ascend 调用方式

vllm-ascend 通过 `--kv-transfer-config` 的 `kv_connector_extra_config.ascend_local_comm_res_path` 字段读取 hixlep 目录,**不是**通过环境变量,也**不是**通过 vllm serve 命令行直接挂载。容器启动时仍需挂载主机 hixlep 目录到容器内(`-v /etc/hixlep:/etc/hixlep`)。

### 4.1 PD 分离 / PD 分离（MooncakeConnectorV1）

prefill 与 decode 启动命令的 `--kv-transfer-config` 都需加入 `ascend_local_comm_res_path`：

```jsonc
--kv-transfer-config '{
  "kv_connector": "MooncakeConnectorV1",
  "kv_role": "kv_producer",     // prefill=kv_producer / decode=kv_consumer
  "kv_port": "23010",
  "kv_buffer_device": "npu",
  "engine_id": "0",
  "kv_connector_extra_config": {
    "prefill": { "dp_size": 1, "tp_size": 2 },
    "decode":  { "dp_size": 1, "tp_size": 2 },
    "ascend_local_comm_res_path": "/etc/hixlep"
  }
}'
```

### 4.2 多节点 TP/PP/EP（不走 PD 分离）

非 PD 场景下，UB 通信通过 `--additional-config` 传递：

```jsonc
--additional-config '{"ascend_local_comm_res_path": "/etc/hixlep", "enable_cpu_binding": true}'
```

### 4.3 单机多卡（TP>1）

同节点 UB 通信，使用 4.2 同样的 `--additional-config` 传入 `ascend_local_comm_res_path`；若 8 卡全走 HCCS（不经过 UB），可省略。

## 5. 容器侧挂载

hixlep 与 route.conf 都位于主机 `/etc/hixlep` 与 `/lib/route.conf`，容器启动必须挂载进容器同路径：

```bash
docker run ... \
  -v /usr/local/Ascend/driver:/usr/local/Ascend/driver \
  -v /etc/hccl_rootinfo.json:/etc/hccl_rootinfo.json \
  -v /etc/hixlep:/etc/hixlep \
  -v /lib/route.conf:/lib/route.conf \
  ...
```

ModelArts 在线服务部署时改用 `volumes` 配置挂载主机目录，等价于 docker `-v`。

## 6. 与 ASCEND_LOCAL_COMM_RES 环境变量的关系

```
export ASCEND_LOCAL_COMM_RES='{"version":"1.3"}'
```

- 作用：让 716 之后的镜像在运行时**自动生成** `loc_comm_res`（与 hixlep 是同义机制）
- 何时替代 hixlep：镜像内置 hixl 自动生成功能时（云上 A5 镜像 716 之后），仅需环境变量
- 何时不可替代：镜像无自动生成功能、或 vllm-ascend 通过 `ascend_local_comm_res_path` 显式读取 `/etc/hixlep` 时，必须手动生成 hixlep 文件并显式传 path

建议：**同时配置**环境变量与显式 path，让 vllm-ascend 优先读 `/etc/hixlep`，环境变量作为兜底。

## 7. 验证

启动后查 vllm 日志应出现 hixl 初始化相关条目，无 `local_comm_res not found` / `endpoint file missing` 类报错。HCCL 通信异常（`HcclCommInitRootInfoConfigV2 errNo[0x0000000005000001]`）通常与 hixlep 缺失或 net_instance_id 不一致相关。

跨节点 UB 链路连通性自检：

```bash
# 节点1 → 节点2 UB ping（eid 来自 hccn_tool -g -dev_info -i 0）
hccn_tool -t -ub_ping -i 0 -src_eid <node1_eid> -dst_eid <node2_eid>
```

## 附录 A：来源文档(均为华为内部第一方,无第三方依赖)

| 来源 | 用途 |
|------|------|
| clouddevops WIKI2026070300170「A5部署qwen&Deepseek」常见问题 2. hixlep | hixlep 角色定义、PD分离 8 文件要求 |
| clouddevops NOTE2026060300025「云上A5开荒」技能2 | generate_ep.py 生成方式、核验规则 |
| 2012labs「Qwen3.5 A5 PD分离实战」2.1 使用部署方式 / 5.2 PD分离启动命令 | vllm-ascend 通过 `kv_connector_extra_config.ascend_local_comm_res_path` 调用 hixlep |

## 附录 B：hccl_rootinfo.json 生成（缺失时）

```bash
python3 -m pip install unofficial-ascend-tools==0.0.7rc4
mindcluster-tools rootinfo --product_type server --output /etc/hccl_rootinfo.json
# 或生成后复制到 /etc 下
mindcluster-tools rootinfo --max_level 2 --output hccl_rootinfo.json && cp hccl_rootinfo.json /etc/
```

`hccn_tool -g -dev_info -i 0` 输出与 `/etc/hccl_rootinfo.json` 内容不一致时必须重新生成。
