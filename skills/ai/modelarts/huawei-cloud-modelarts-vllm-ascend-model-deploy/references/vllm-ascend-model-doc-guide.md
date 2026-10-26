# vllm-ascend 模型适配文档查阅指南

本文件用于在 ModelArts 部署流程中,根据**用户确认的模型**快速定位 vllm-ascend 模型适配文档,并从中提取**镜像版本/tag**与**启动命令**,支撑步骤 2(镜像准备)与步骤 3(脚本准备)。**镜像与脚本均以本文档中该模型页面给出的信息为准,禁止凭经验猜测。**

## 一、文档地址与 URL 结构

| 用途 | URL |
|------|-----|
| 模型列表(中文,最新版) | `https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/` |
| 单个模型页面 | `https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/<ModelName>.html` |
| 历史/固定版本(中文) | `https://docs.vllm.ai/projects/ascend/zh-cn/<v版本>/tutorials/models/`(如 `v0.23.0`) |
| 英文版(内容与中文一致,可对照) | `https://docs.vllm.ai/projects/ascend/en/latest/tutorials/models/` |
| 镜像 tag 列表 | `https://quay.io/repository/ascend/vllm-ascend?tab=tags` |

> 说明:
> - `latest` 对应最新文档;若模型页面标注适配版本(如 `v0.23.0`),建议对照固定版本路径确认内容一致。
> - 一个模型系列可能共用一个页面,如 `Qwen3.5-27B-Qwen3.6-27B.html`;也可能按量化/芯片变体拆分为多个页面(如 `xxx-W8A8-310p`)。
>
> **访问方式(强制)**: 用 curl 抓取上述第三方站点(docs.vllm.ai、quay.io 等)时必须加 **`-k`(跳过证书校验)**——企业/云上代理常对公网站点做 TLS 中间人(MITM)证书替换,不带 `-k` 会报 `SSL certificate problem: self-signed certificate in certificate chain` 而失败,误判为"网络不可达"。`-k` 后仍 000/超时才是代理真拦截(详见 SKILL.md"关键原则")。示例: `curl -sk https://docs.vllm.ai/projects/ascend/zh-cn/latest/tutorials/models/`。

## 二、模型页面常见结构(按需提取)

进入模型页面后,重点阅读以下部分(不同模型章节名略有差异,以页面实际为准):

> **⚠️ 索引页与单模型页解析方式不同(强制,违反=索引页返回空候选,误判"模型不在支持列表")**:
> - **索引页(`tutorials/models/index.html`)的模型清单在侧栏导航 `<nav class="md-nav">` 的 `md-nav__link` 中,不在 `<article>` 正文**(实测正文仅 657 字符、0 个模型链接)。**提取候选必须解析导航栏**,链接为**相对路径**(如 `Qwen-VL-Dense.html`,无 `tutorials/models/` 前缀),禁止用 `tutorials/models/<name>.html` 前缀正则匹配(命中 0);正确正则: `<a[^>]+href="([^"]+\.html)"[^>]*class="md-nav__link"[^>]*>\s*<span class="md-ellipsis">(.*?)</span>`,再按系列名大小写不敏感过滤。**导航提取不到时回退全文 grep 索引页,不得静默返回空候选**。
> - **单模型页(`tutorials/models/<Model>.html`)才按剥离导航栏/只取正文规则处理**: 页面 HTML 的**侧边导航栏包含全部模型标题**,混有**其他模型**的标注(如 `Qwen3.8-Flash-Next（实验性支持）`、`Hy4-preview (Experimental)`)。**全文 grep/正则扫描会命中导航栏**,把这些标注误归到当前页面的目标模型。**正确做法**: 用 Python `html.parser`/正则提取 `<article>` 正文区域(或剥离 `<nav>` 及导航结构)后,**只在正文中检索**;正文每个 `Experimental`/`实验性` 命中,必须**核对标注归属的模型名与芯片平台**(如"950DT Products 当前为实验性支持"仅限 950DT,A3/A2 为正式支持),归属其他模型或仅限其他芯片平台的标注**不得**算作目标模型的实验性。
> - **页名与正文模型 ID 可能不一致**: 一个页面常覆盖同系列多个模型(如 `Qwen-VL-Dense.html` 标题为 `Qwen-VL-Dense(Qwen3-VL-8B/32B)`,正文启动命令直接用 `vllm serve Qwen/Qwen3-VL-8B-Instruct`)。**候选清单按导航标题列出,但核对"模型是否在官方支持列表"时,还需检索该页面正文启动命令中实际用到的模型 ID**(`vllm serve <repo-id>`),页名不含某模型不代表该页面不覆盖它,禁止仅凭导航标题断言"模型不在支持列表"。

| 章节 | 提取内容 | 用途 |
|------|----------|------|
| 页面头部/简介 | 模型简介、适配的 vllm-ascend 版本、支持矩阵 | 步骤 2.0:定镜像版本/tag |
| 环境准备 | 推荐的镜像、CANN/torch_npu 版本配套 | 步骤 2.0:定镜像 tag;约束第 5 条版本配套 |
| 权重准备 | 权重格式(BF16/FP8/W8A8)、下载地址(HF/ModelScope repo ID)、是否需要转换 | 步骤 1.0:权重说明 |
| 部署/Deployment | **启动命令示例**(含环境变量与 vllm 参数) | 步骤 3.1:启动脚本直接依据 |
| 性能调优(performance tuning) | 性能相关环境变量/参数建议 | 步骤 3.2 可选增强 |

### 部署章节通常给出两类内容

1. **环境变量(export 块)**: 启动前必须设置,常见示例:
   ```bash
   export ASCEND_RT_VISIBLE_DEVICES=0,1          # 使用的 NPU 卡
   export OMP_PROC_BIND=false
   export OMP_NUM_THREADS=1                      # 或按核数
   export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
   export HCCL_BUFFSIZE=512
   export TASK_QUEUE_ENABLE=1
   export VLLM_USE_V1=1                           # 启用 V1 引擎(部分版本/模型)
   export VLLM_USE_MODELSCOPE=true                # 从 ModelScope 加载权重时
   export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2   # 多卡性能优化
   ```
   值以页面给出的为准,未给出的不要擅自补。

2. **启动命令**: 新版文档多用 `vllm serve <model> --host 0.0.0.0 --port ...`,旧版用 `python -m vllm.entrypoints.openai.api_server ...`,二者等价,ModelArts 启动脚本任选一种改写为脚本即可。注意保留模型特有参数:
   - 量化: `--quantization`(如 `w8a8`、`awq`)、`--kv-cache-dtype fp8`
   - MoE 模型: `--enable-expert-parallel`
   - 自定义代码: `--trust-remote-code`
   - 并行: `--tensor-parallel-size <卡数>`

## 三、从模型页面确定部署形式(步骤 1.1,先于镜像与脚本)

同一模型可由 vllm-ascend 社区以**单节点 / 多节点 / PD 分离**不同形式部署。从模型页面(结合社区)判断支持哪种形式:

| 页面/社区线索 | 指向部署形式 |
|----------------|--------------|
| 部署章节只给单机命令,示例 `--tensor-parallel-size` ≤ 单节点卡数 | 单节点 |
| 部署章节出现多机/multi-node/DP+TP 示例,或示例 TP 卡数 > 单节点卡数(如双机 16 卡) | 多节点 |
| 出现 PD / Prefill-Decode / disaggregated / PD 专用镜像 / PD 代理脚本 等 | PD 分离 |
| 页面标注"仅支持多节点/需跨节点" | 多节点 |

> 判断结论还需结合模型规模与用户硬件(单节点总显存能否容纳权重+KV Cache)与性能需求(高并发/长上下文可考虑 PD)。详细决策矩阵见 `references/deployment-form-decision.md`。**文档未给出多节点/PD 示例时默认单节点,不要自行发明多机/PD 参数。**

## 四、从模型页面提取镜像 tag 的方法(步骤 2.0)

1. 找到模型页面标注的 **vllm-ascend 版本**(页面头部或环境准备章节)。
2. 在 `https://quay.io/repository/ascend/vllm-ascend?tab=tags` 找对应版本的 tag:
   - 通用 tag 形如 `v0.23.0`、`v0.18.0rc1`
   - 芯片变体 tag 带后缀,如 `-a3-openeuler`(910C/A3)、`-310p` / `-310p-openeuler`(310P),按目标芯片选择
   - 个别模型有**模型专用镜像/tag**(如 `DeepSeekV4-flash-0731`),模型页面或社区文档会直接给出
3. 无法访问 Quay.io 时,可用国内镜像源拉取同一 tag(见 SKILL.md 常见问题排查),但**tag 本身仍以模型文档为准**。
4. 拉取后可用 `docker image inspect <image> | grep -iE "vllm|cann"` 核对镜像内版本与模型文档标注一致。

## 五、按"模型 + 部署形式 + 芯片型号 + 卡数"匹配启动示例

同一模型页面的部署章节常按芯片型号或卡数给出多段示例,选取原则(部署形式见步骤 1.1 确认的 `DEPLOY_FORM`):

| 匹配维度 | 选取规则 |
|----------|----------|
| 部署形式 | 单节点选单机示例;多节点选多机/multi-node/DP+TP 示例(注意 HCCL/Gloo 环境变量与 `--data-parallel-*` 参数);PD 分离选 Prefill-Decode 示例(角色环境变量、VLLM_ROLE) |
| 芯片型号 | 优先选与目标资源池一致的小节(910B / 910C(A3) / 310P);页面未区分时,用通用示例并核对显存是否满足 |
| 卡数 | 按目标卡数选;`--tensor-parallel-size` 一般等于卡数;多节点时等于**全部节点卡数总和**;MoE 大模型多卡时核对是否需 `--enable-expert-parallel` |
| 量化 | 权重格式与启动参数一一对应(W8A8 权重对应 `--quantization w8a8` 等),不得混用 |

> 310P 为推理卡,只能跑 7B 以下小模型;页面若无 310P 示例,不要强行套用 910B 示例。

## 六、常见环境变量速查表

| 环境变量 | 常见取值 | 作用 |
|----------|----------|------|
| `ASCEND_RT_VISIBLE_DEVICES` | `0` / `0,1` / `0,1,2,3` | 指定使用的 NPU 卡 |
| `PYTORCH_NPU_ALLOC_CONF` | `expandable_segments:True` | 显存分配优化,避免碎片 |
| `HCCL_BUFFSIZE` | `512` 等 | HCCL 通信缓冲区大小,多卡调优 |
| `OMP_PROC_BIND` | `false` | 线程绑定,避免性能问题 |
| `OMP_NUM_THREADS` | `1` 或按核数 | 单实例线程数 |
| `TASK_QUEUE_ENABLE` | `1` | 使能任务队列(部分场景) |
| `VLLM_USE_V1` | `1` | 启用 vLLM V1 引擎(视版本/模型) |
| `VLLM_USE_MODELSCOPE` | `true` | 权重从 ModelScope 加载 |
| `LD_PRELOAD` | `.../libjemalloc.so.2` | 多卡/大模型内存性能优化 |

> 注意: 上表仅为常见项,是否设置、取何值**一律以模型页面为准**。不同模型/版本的必选环境变量可能不同。

## 七、常见模型页面命名示例(便于快速定位)

以下为历史/近期文档中出现过的页面命名方式,仅作定位参考,不保证永久有效:

- `Qwen3.5-27B-Qwen3.6-27B.html`(系列合并)
- `Qwen3-VL-30B-A3B-Instruct.html`(多模态)
- `Qwen3.5-397B-A17B.html`(MoE 大模型)
- `DeepSeek-R1-Distill-Qwen-14B.html` 等
- 量化变体: 页面名可能带 `W8A8` / `AWQ` / `FP8` 等后缀

找不到页面时: 回到模型列表页按模型系列查找;仍找不到 → 告知用户该模型不在 vllm-ascend 官方适配列表,需自行验证适配,不保证可用。
