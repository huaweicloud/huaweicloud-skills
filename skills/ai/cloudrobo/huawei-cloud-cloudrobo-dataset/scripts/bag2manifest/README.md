---
domain: multi-modal
tags:
- ros2
- lerobot
- robotics
license: MIT
---

# bag2manifest

**从 ROS2 bag 生成 LeRobot v3 的 ROS Manifest 2.0 配置（`manifest.yaml`）的交互式可视化工具。**

## ModelScope Studio 部署

本仓库可直接作为 ModelScope 的 **Gradio Studio** 使用，入口为 `app.py`。

在 Studio 中上传一条有代表性的样例 bag，完成映射确认后下载 `manifest.yaml` 与
`profile.json`。上传文件会被发送到运行环境；请不要上传敏感或受限数据。
对于多文件 ROS2 bag，推荐先打成 `.zip`，或优先使用单文件 `.mcap`。

选一个样例 bag，自动分析后逐页确认，导出 `manifest.yaml` 交给后续转换流程。
它是一个**带即时预览的配置验证台**——让你在转换之前就看清图像方向、状态曲线、
动作与状态的关系，而不是转完几十分钟才发现配错。

```
┌──────────────┐  manifest.yaml   ┌────────────────┐
│ bag2manifest │ ───────────────> │ 转换流程        │ ──> LeRobotDataset v3
│ 本地 / 交互   │                  │ （不在本仓库）   │
└──────────────┘                  └────────────────┘
```

## 特性

- **不装 ROS、不依赖 `metadata.yaml`**：`.db3` 直接读 sqlite3 的 `topics`/`messages` 表；
  `.mcap` schema 内嵌，自定义消息直接解码
- **输入灵活**：可选 bag 目录、`.db3` 文件（分片多选）、`.mcap`、`.zip`，或直接填本地路径
- **数据不出本机**：只读 bag，不上传、不修改
- **完全自由的字段选择**：任意话题、任意维度、任意顺序，支持跨话题拼接
- **计算字段表达式**：如左右夹爪相加 `abs(f0) + abs(f1)`，结果可自动归一化
- **任意其他特征**：除 state/action 外可自由添加 `next.reward` / `observation.force` 等顶层特征
- **即时预览**：相机缩略图、状态曲线、状态 vs 动作叠加图、计算字段曲线
- **manifest 可编辑**：导出后可直接改 YAML，并用同一套规则复检

### 输入支持矩阵

| 输入 | metadata.yaml | 自定义消息 | 说明 |
|---|---|---|---|
| `.mcap` | 不需要 | ✅ 内嵌 schema 自动可解 | **推荐** |
| `.db3` / bag 目录 | **不需要** | 需在界面提供 `.msg` 目录 | 标准消息开箱即用 |
| 分片 `bag_0.db3 bag_1.db3` | 不需要 | 同上 | 自动按时间归并 |
| ROS1 `.bag` | — | — | 兜底支持 |

## 安装

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

### 1. 没有真实数据？先生成一个合成 bag

内置生成器会造一个"像真的"的 bag，并刻意埋了若干常见坑（自定义消息、多个候选动作话题、
恒定关节、`header.stamp` 全 0、噪声话题），用来验证告警是否生效：

```bash
python tools/make_synth_bag.py -o /tmp/synth_demo.mcap --seconds 12
```

### 2. 启动工作台

```bash
python start_web.py --port 7860  # http://127.0.0.1:7860
```

六步向导。每页直接提供必要的核对与编辑操作，不常用的设置在该页按需展开。状态、动作和其他特征共用同一个字段编辑器，列表、行操作、保存与曲线布局一致。

| 页 | 做什么 | 预览什么 |
|---|---|---|
| ① 载入与体检 | 上传 bag，点击“开始分析”；成功后自动进入相机页 | 可展开目录/本地路径、话题表、完整体检信息 |
| ② 相机 | 直接查看并编辑相机映射表，核对相机名、话题和画面缩略图 | 可调整启用、改名、缩放 |
| ③ 状态 | 统一维度列表和编辑器：原始字段或计算公式，支持原位修改、新增、移动、删除、撤销 | 常驻曲线默认显示表单全部字段，随增删改自动更新，可筛选维度 |
| ④ 动作 | 同一编辑器，额外支持单维下一帧状态引用；多候选需核对 | 状态引用跟随重排，删除引用对象会阻止导出 |
| ⑤ 其他特征 | 使用相同编辑器，完成后保存特征 | 显式保存；曲线常驻 |
| ⑥ 输出 | 信息→任务来源→采样与时间→正式输入与episode→高级输出→检查导出 | 条件显示文本/话题、样本预览、最终摘要；表单改动使旧下载失效 |

**计算字段**：先在同一页字段池选中输入字段（表达式里叫 `f0, f1, …`，页面实时显示映射），
再写表达式。可用 `+ - * / ** % //` 和单个比较运算、括号，以及 `abs / min / max / sqrt / exp / log / clip / where`。
例：左右夹爪指关节绝对值相加 → `abs(f0) + abs(f1)`，勾选归一化后区间由样例数据自动算出。

除载入页外，每页底部有 **下一步 / 上一步** 导航；状态页可用 **恢复自动推断**
（只还原当前页；① 页的「全部恢复」还原所有页）。

### 3. 自测

```bash
python tests/smoke_test.py
python tests/manifest_v2_test.py
```

## 输入要求

| 级别 | 要求 |
|---|---|
| MUST | `.mcap`、`.db3`（可无 `metadata.yaml`）、bag 目录或其 zip 包 |
| MUST | 图像为 `sensor_msgs/Image`（rgb8/bgr8/rgba8/mono8/16UC1/32FC1/bayer\*）或 `CompressedImage` |
| MUST | 同一图像话题内分辨率、encoding 全程不变 |
| SHOULD | 消息填写有效 `header.stamp`（否则回退 bag 记录时间，会告警）|
| SHOULD | 所有节点同一时钟域，偏差 < `1/(2·fps)` |
| SHOULD | 至少 1 个状态源；动作可来自话题或由状态推导 |

不满足时不会静默兜底，而是给出带**可复制修复片段**的错误。

## 产物：manifest.yaml

生成 ROS Manifest 2.0，显式保留必需结构、source 配置与输出参数。
用户不接触 LeRobot 内部命名（`observation.images.*` 由转换流程补全）。

```yaml
schema_version: "2.0"
source_type: ros2
repo_id: myorg/franka_pick_v1
fps: 30
cameras:
  camera: {locator: /camera/color/image_raw, depth: false}
  wrist: {locator: /wrist_cam/image_raw/compressed, depth: false}
state:
  - locator: /joint_states.position
    names_from: embedded
    names: [joint_1, joint_2]
  - locator: /gripper/state.width
    role: gripper
action:
  strategy: stored
  fields:
    - locator: /arm/commands.data
      names: [joint_1_exp, joint_2_exp]
    - strategy: next_state
      state_index: 2
      name: gripper_exp
      role: gripper
task: {mode: const, text: pick up the red cube}
source:
  bag_glob: "*.db3"
  time: {stamp_source: auto, tolerance_ms: 17, on_stale: hold}
  segment: {mode: per_bag, min_frames: 30}
output: {chunk_size: 1000, data_file_size_mb: 100, video_file_size_mb: 200, video_codec: auto}
```

导出后可直接在页面里编辑，点「校验编辑后的 YAML」用同一套规则复检。
同时导出 `profile.json`（Web 与算子间的数据契约，含缩略图与降采样曲线）。

## 推断规则

全部在 `bag2manifest/infer.py`，每条带 ID，产物中的 `_provenance.rules_hit` 可追溯。

| ID | 规则 |
|---|---|
| R-CAM-01/02 | 图像话题 → 相机；深度编码单列且默认不启用 |
| R-FPS-01/02 | fps = 最低启用相机频率（不高于源频率）：离档位 ≤0.5Hz 取档，否则向下取整（9Hz→9）|
| R-ST-01 | `JointState.position[*]` **按关节名**取值（ROS 不保证顺序），**保留恒定关节**并告警 |
| R-ST-02 | 夹爪类话题追加到状态末尾 |
| R-ST-03 | 无 JointState 时取名字含 `state/status/feedback` 的话题主向量组 |
| R-ACT-01/02 | 名字含 `command/cmd/target/setpoint/goal/teleop/joint_plan` 的话题；多候选报 **E021** |
| R-ACT-03 | 找不到 → 回退 `next_state` 并**显式告警**（不静默）|
| R-ACT-04 | 去除 `_action/` 空话题与极稀疏（<0.5Hz）的指令回读 |
| R-TIME-01/02 | 检测 `header.stamp` 与 `log_time` 是否同钟；不一致时强制 `stamp_source: log_time` |
| R-TASK-01/02 | 任务描述话题 / 需手工填写 |

**设计约束**：`vector_fields()` 取"主向量字段组"并**完整保留**，即使某维在样例 bag 中恒定
——样例里没动 ≠ 全量里不动，静默丢维会导致批次间维度不一致。

## 常见告警

| Code | 含义 |
|---|---|
| `E015` | db3 里的自定义消息无定义，需提供 `msg_dir`（或改用 mcap）|
| `E021` | 多个候选动作话题，需人工选定 |
| `E013/E014` | 图像解码失败 / 分辨率不稳定 |
| `W105/W106` | 通道全程恒定（已保留，请确认传感器）|
| `W041` | 有 header 但 `stamp` 未填，回退 log_time |
| `W043` | `header.stamp` 与 bag 记录时间差 >1s（相对时钟驱动），强制统一用 log_time |
| `E112/E113` | 状态 / 动作里的计算字段表达式非法 |
| `E121`–`E125` | 其他特征名非法、为空，或与内建键冲突 |
| `I042` | 消息类型不含 header，只能用 log_time 对齐 |
| `W110` | 自动动作仅选择手臂，夹爪动作需要显式配置 expr 或单维 next_state |
| `W109` | 动作维度 ≠ 状态维度（末端速度控制正常；关节位控则可疑）|

## 模块

```
bag2manifest/
├── app.py              入口：python app.py
├── bag2manifest/
│   ├── reader.py       bag 读取 (mcap / db3，无 ROS 依赖)
│   ├── msgutil.py      类型分类 · 数值字段展平 · 图像解码
│   ├── profiler.py     扫描 -> profile.json（低维合并扫描 + 图像分窗 seek）
│   ├── infer.py        推断规则 ← 唯一真相源
│   ├── derive.py       计算字段表达式（AST 白名单，安全求值）
│   ├── manifest.py     manifest.yaml 构建 / 序列化 / 校验
│   └── webapp.py       Gradio 工作台
├── tools/make_synth_bag.py   合成 bag 生成器（演示/测试用）
└── tests/smoke_test.py       端到端冒烟测试
```

性能参考：53 MB / 90 s / 12 话题的 mcap，完整扫描 **1.7 s**（图像走分窗 seek，不整包解码）。

## 说明

本仓库只负责**配置生成**，不包含实际的 bag → LeRobotDataset 落盘转换。
输出 `manifest.yaml` 作为转换流程的输入契约。

## License

MIT，见 [LICENSE](LICENSE)。

## Manifest 2.0 注意事项

JointState 用 embedded + 有序 names；普通数值数组 names 按位置映射。夹爪 role 影响默认插值和下游清洗索引，但不自动归一化或追加夹爪动作。ROS action 仅 stored/next_state；混合动作的 state_index 按展开后的最终向量从0起计。默认 state/extra 为 nearest，stored普通动作linear，gripper nearest；可在YAML覆盖 interpolation，并用有限数值 default 处理缺失话题。normalize仅用于expr。

source.bag_glob需匹配正式转换的整批文件。工具能扫描MCAP；规范举例DB3/BAG，目标转换器的MCAP支持需另行确认。time/segment放source内，只支持hold/per_bag。task仅const/topic，const优先级为env task→task.txt→prompt.json→manifest text→lerobot_teleoperation。curation按原样传给下游，不在此处执行清洗。

终端模式：`python generate_manifest.py <bag-path> --output <dir>`，阅读summary.md、choices.json和issues.json，确认后用`--choices <choices.json> --confirm-action`复跑；`--bag-glob '*.db3'`可指定正式批次模式。退出码2表示草稿存在未解决错误，0表示样例校验通过。

本仓库是实现源，dataset skill的scripts/bag2manifest保存可独立运行的副本。更新共同模块、入口、依赖和测试时须同步两处；skill的详细规范与对话指南位于references。

## 统一字段编辑

搜索与话题浏览合并为一个选择器。点击左侧一维，右侧编辑后“保存修改”；点击“新增”，填写来源后“添加维度”。插值、夹爪role和缺失默认值可直接设置；公式归一化可以按样例范围或指定区间。曲线归一化仅影响显示，不修改配置。混合动作按状态维度身份跟随排序；删除其来源后引用失效，可撤销恢复。

输出页先选任务来源，再显示对应文本或话题与样本。时间戳来源、容差、字段插值分别设置。ROS规范未定义输出主时间轴、auto回退的完整规则、插值与容差耦合、首帧hold/default关系和分片episode归组，不能把当前曲线视为真实转换后的同步结果。需要这些行为时应补充转换器规范或代码。
