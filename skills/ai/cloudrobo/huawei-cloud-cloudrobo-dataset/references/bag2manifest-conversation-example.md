# bag2manifest：推断规则与逐步对话示例

本示例对应 **ROS Manifest 2.0**，具体字段准则见 [ROS Manifest 2.0](ros-manifest-2.0.md)。使用随包生成器制作的 10 秒 MCAP，下面的数字来自实际扫描。真实项目每次都应读取该 bag 的 `summary.md`、`profile.json` 和 `issues.json`，不能照搬这些话题和数值。所有命令都在 dataset skill 目录执行。

```bash
python scripts/bag2manifest/tools/make_synth_bag.py -o /tmp/synth_demo.mcap --seconds 10
```

## 工具做了什么

终端入口读取一个样例 bag，产出五个文件：`summary.md` 是给人看的数据摘要；`profile.json` 保存话题、统计量、缩略图、曲线与推断；`choices.json` 是可编辑的映射选择；`manifest.yaml` 是转换配置草稿；`issues.json` 保存扫描和配置校验结果。它只准备配置，不执行 LeRobot 数据集转换，也不创建 CloudRobo 任务。

### 当前实现的主要推断规则

| 规则 | 自动选择依据 | 需要人确认的地方 |
| --- | --- | --- |
| `R-CAM-01/02` | 识别原始或压缩图像话题；从话题名派生相机名。深度图默认不启用，低于 1 Hz 的图像不进入自动相机建议。 | 哪些相机用于训练；画面方向、颜色、编码、尺寸是否正确。 |
| `R-FPS-01/02` | 有启用相机时取最低相机频率；否则取数值话题频率。与常用档位相差不超过 0.5 Hz 时取档位，否则向下取整。 | 目标帧率是否符合采集与训练需求。 |
| `R-ST-01/02/03` | 优先选 `JointState.position[关节名]`，追加夹爪状态；无 `JointState` 时寻找名称含 state/status/feedback 等的数值话题。数组主字段组保留完整维度，包括样例中恒定的维度。 | 状态字段的物理意义、顺序、单位；恒定通道是正常静止还是传感器问题。 |
| `R-ACT-01/02/03` | 从 command/cmd/target/joint_plan 等话题找动作；过滤夹爪主候选，不自动追加夹爪动作；多候选时按与手臂状态维度的接近程度给出建议，同时报 `E021`；找不到则建议 `next_state` 并告警。 | **动作必须确认**：记录的是实际控制指令、遥操作目标，还是其他回读/伺服信号。 |
| `R-TASK-01/02` | 从任务描述类文本话题找任务文本；找不到则需要常量文本；const 可被 env task/task.txt/prompt.json 覆盖。 | 文本能否代表每条 episode 的任务。 |
| `R-TIME-01/02` | 正常时 `stamp_source: auto`；若 header 与 bag 记录时间相差超过 1 秒，建议全局 `log_time` 并报 `W043`。无效 stamp 或无 header 会单独提示。 | 是否跨设备采集、是否同一时钟域、对齐误差是否可接受。 |

自动建议来自 `bag2manifest/infer.py`，`summary.md` 展示其结果。`manifest.yaml` 导出 schema_version=2.0、source_type=ros2；time/segment 位于 source 内，不导出旧 quality。UI 每维选择在导出时合并成字段段：7 维 JointState + 1 维夹爪是两个 YAML 项，仍为8维。

## 逐步对话：终端模式

### 第 0 步：确认输入与目标

**用户：** “请分析 `/tmp/synth_demo.mcap`，生成 LeRobot 配置。目标仓库 ID 是 `demo/pick-place`。”

**Agent：** “我会先读取样例 bag，整理话题、频率、候选映射和告警；有歧义的字段会请你确认。”

```bash
python scripts/bag2manifest/generate_manifest.py /tmp/synth_demo.mcap \
  --output /tmp/bag2manifest-demo --repo-id demo/pick-place
```

首次运行退出码为 `2`，提示 `E021`。这是一个**待确认的动作歧义**；五个文件已经生成，`manifest.yaml` 仍是草稿。Agent 先读 `summary.md`，需要细节时再查 JSON。

### 第 1 步：确认录制内容

实际扫描结果：时长 **9.99 秒**，原始话题 **12** 个；`/rosout` 与 `/camera/camera_info` 被忽略，参与分析的 **10** 个。关键数据如下。

| 话题 | 消息数 | 估算频率 | 数据 |
| --- | ---: | ---: | --- |
| `/camera/color/image_raw` | 300 | 30.03 Hz | 240×180，`rgb8` |
| `/wrist_cam/image_raw/compressed` | 300 | 30.03 Hz | 240×180，JPEG |
| `/joint_states` | 1000 | 100.10 Hz | 关节状态 |
| `/my_robot/gripper_state` | 500 | 50.05 Hz | 夹爪状态 |
| `/arm_controller/commands` | 500 | 50.05 Hz | 7 维控制器指令 |
| `/servo_node/delta_twist_cmd` | 200 | 20.02 Hz | 6 维伺服指令 |
| `/gripper_controller/command` | 500 | 50.05 Hz | 夹爪指令 |
| `/task_description` | 10 | 1.00 Hz | 文本任务 |

频率是扫描器根据消息数和时间范围估算的，例如相机约 `300 ÷ 9.99 = 30.03 Hz`。其余话题在 `summary.md` 的 Topics 表中。

**Agent：** “这是约 10 秒的一条样例轨迹，包含两路相机、关节与夹爪状态、两种疑似动作来源。它是否能代表你接下来要转换的整批数据？若其他 bag 的话题或关节布局不同，需要再抽样检查。”

**用户：** “可以代表这批数据。”

### 第 2 步：确认相机

`R-CAM-01` 建议启用 `camera` 和 `wrist`。两路都采到了 **6 张预览缩略图**，分辨率都稳定在 **240×180**；前者是 `rgb8`，后者是 JPEG。最低启用相机频率是 **30.03 Hz**，所以 `R-FPS-01` 给出 **30 fps**。按 9.99 秒粗算约 **300 帧**，实际转换帧数可能受时间对齐与质量规则影响。

**Agent：** “建议两路相机都保留，名称分别为 `camera`、`wrist`，不缩放。你希望两路都进入数据集吗？终端统计只能确认编码与尺寸；若要核对画面是否倒置、偏色或花屏，我可以打开 Web 预览。”

**用户：** “两路都保留，暂不缩放。我稍后看 Web 画面。”

### 第 3 步：确认状态向量

`R-ST-01+R-ST-02` 给出的顺序是 7 个按**关节名**索引的 `position`，末尾追加夹爪宽度，共 **8 维**。每个字段在本次扫描中有 500 个数值样本。`summary.md` 列出每维的最小值、最大值与是否恒定；这里摘出关键几维：

| 序号 | 状态字段 | 样例范围 | 说明 |
| ---: | --- | --- | --- |
| 1 | `/joint_states.position[panda_joint1]` | −0.599983～0.599999 | 有变化 |
| 2 | `/joint_states.position[panda_joint2]` | −0.599994～0.600000 | 有变化 |
| 3～6 | `panda_joint3`～`panda_joint6` 的 `position` | 约 −0.6～0.6 | 完整范围见 `summary.md` |
| 7 | `/joint_states.position[panda_joint7]` | 0～0 | `W105/W106`：样例中恒定，默认保留 |
| 8 | `/my_robot/gripper_state.width` | 0.009938～0.080000 | 标 role=gripper，保留原始尺度 |

恒定的第 7 维没有被自动删除：样例里没动，不等于全量数据里不会动；静默删维可能使不同批次的状态维度不一致。

**Agent：** “状态建议按这 8 维及这个顺序输出。第 7 个关节在样例中一直是 0，你确认这是本次动作没有用到它，还是传感器异常？是否保留？”

**用户：** “关节正常，只是这段轨迹没有动它。保留 8 维。关节是 rad，夹爪宽度是 m，暂时不归一化。”

**Agent：** “导出关节数组时会用 `names_from: embedded` 和这7个有序关节名，避免消息发布顺序改变。夹爪单项标 `role: gripper`，保持米单位；整个状态默认 nearest 插值。”

### 第 4 步：确认动作来源

这是本例唯一未解决的 error。`R-ACT-02` 检测到两个候选：

| 候选 | 频率 | 主向量 | 本次数据范围与现象 |
| --- | ---: | ---: | --- |
| `/arm_controller/commands` | 50.05 Hz | `data[0..6]`，7 维 | 前 6 维约 −0.6～0.6；`data[6]` 恒为 0 |
| `/servo_node/delta_twist_cmd` | 20.02 Hz | `data[0..5]`，6 维 | 多维约 ±0.01，部分维度恒为 0 |

推断器暂选第一条的 **7 维手臂指令**，strategy=stored。夹爪指令不会自动追加，因此初稿为 state=8、action=7，同时记录 `W110`（需显式配置夹爪）和 `W109`（维度差）。维度接近只是排序依据，不证明话题就是训练需要的动作。

**Agent：** “哪条话题是实际训练动作？手臂可以读 `/arm_controller/commands`；夹爪需要你确认是读取指令、计算表达式，还是引用下一帧状态。`/gripper_controller/command.width` 有数据，样例范围0.007925～0.080000；如果目标策略应模仿下一帧实际开度，也可用 state_index=7。”

**用户：** “手臂用 `/arm_controller/commands`。夹爪用下一帧实际宽度，不做单位转换。控制器第7维这次没变化，保留。”

**Agent：** “会输出7维手臂 stored + 1维夹爪 next_state。夹爪是拼接状态的第8维，索引7；role=gripper。若后面调换状态顺序，我会重核这个索引。手臂存储动作默认 linear 插值。”

Agent 在 `choices.json` 的完整 action 数组末尾追加：

```json
{"strategy": "next_state", "state_index": 7, "name": "gripper_exp", "role": "gripper"}
```

此操作在 action 保留 `/arm_controller/commands.data[0]` 到 `[6]` 后添加一项，不能只用这一个对象覆盖全部动作。另一种已确认的方案是显式添加 `{"expr":"f0", "inputs":["/gripper_controller/command.width"], "name":"gripper_exp", "role":"gripper"}`；需要阶跃/单位变换才改为 where/f0*1000，并确认阈值及单位。

### 第 5 步：确认其他特征

默认没有 `extra_features`。只有用户需要例如 `observation.force`、`next.reward` 时才添加；字段可以来自话题，也可以用 `f0`、`f1` 等输入写计算表达式。

**Agent：** “除了相机、状态和动作，还要添加力、奖励或其他特征吗？”

**用户：** “这批数据暂时不加。”

### 第 6 步：确认任务、时间与导出

`R-TASK-01` 找到 `/task_description`，样本文本是 **“pick up the red cube and place it in the box”**，建议 `task.mode: topic`。`R-TIME-01` 建议 `stamp_source: auto`。一个旧状态话题 `/legacy_sensor/status` 有 header 但 stamp 无效（`W041`），五个话题没有 header、只能用记录时间对齐（`I042`）；本例未触发时钟域不一致的 `W043`。目标是 30 fps，推断生成的半帧容差为 **17 ms**（规范省略此字段时默认50ms）。source 的分段为 per_bag、min_frames=30，on_stale=hold。

**Agent：** “任务文字直接从 `/task_description` 读，时间源保持 `auto`，目标 30 fps，仓库 ID 为 `demo/pick-place`。旧状态话题不在当前映射里。本例是 MCAP，工具建议 bag_glob=*.mcap；实际转换器是否接受MCAP、还是整批为DB3，需要确认。”

**用户：** “我们这批正式数据是DB3，样例MCAP只用于看映射，bag_glob 写 *.db3。其他设置按上述导出。”

Agent 保存已确认的混合 action 到 choices.json 后复跑：

```bash
python scripts/bag2manifest/generate_manifest.py /tmp/synth_demo.mcap \
  --output /tmp/bag2manifest-demo --repo-id demo/pick-place \
  --choices /tmp/bag2manifest-demo/choices.json --confirm-action --bag-glob '*.db3'
```

退出码 **0**，`issues.json.unresolved_errors=[]`。source 仍保留初扫 E021/W110，用于记录历史推断；当前动作是否仍缺夹爪应查看最终 fields 和 validation。最终为两路相机、8维状态、8维混合 stored 动作、topic任务，保留 W105/W106/W107/W041/I042 等样例告警。

最终关键配置为：

```yaml
schema_version: "2.0"
source_type: ros2
repo_id: demo/pick-place
fps: 30
state:
  - locator: /joint_states.position
    names_from: embedded
    names: [panda_joint1, panda_joint2, panda_joint3, panda_joint4, panda_joint5, panda_joint6, panda_joint7]
  - locator: /my_robot/gripper_state.width
    role: gripper
action:
  strategy: stored
  fields:
    - locator: /arm_controller/commands.data
      names_from: explicit
      names: [action_0, action_1, action_2, action_3, action_4, action_5, action_6]
    - strategy: next_state
      state_index: 7
      name: gripper_exp
      role: gripper
cameras:
  camera: {locator: /camera/color/image_raw, depth: false}
  wrist: {locator: /wrist_cam/image_raw/compressed, depth: false}
task: {mode: topic, topic: /task_description}
source:
  bag_glob: "*.db3"
  time: {stamp_source: auto, tolerance_ms: 17, on_stale: hold}
  segment: {mode: per_bag, min_frames: 30}
output: {chunk_size: 1000, data_file_size_mb: 100, video_file_size_mb: 200, video_codec: auto}
```

**Agent：** “配置已写入 `/tmp/bag2manifest-demo/manifest.yaml`，本工具校验通过。保留第7个恒定关节；夹爪是下一帧状态，不是独立控制指令。预计每条约300帧只是时长×fps估算。下一步在实际Toolkit上拿一条DB3试转，核对 state/action列顺序、夹爪尺度和画面同步，再处理整批。”

## 如果用户改了自动建议

若用户选择另一个动作话题、关闭某路相机、调换状态顺序或补充额外特征，Agent 应修改输出目录中的 `choices.json`，再用 `--choices /tmp/bag2manifest-demo/choices.json` 重跑。数组字段是**完整有序列表**，修改时不要只写局部字段。`--confirm-action` 只确认当前自动建议，不能代替改选动作字段。重新检查 `summary.md`、`manifest.yaml` 和 `unresolved_errors`。

## 切换到 Web 预览

**用户：** “我想亲眼看相机画面和动作曲线。”

**Agent：** 在 dataset skill 目录启动服务，保持进程运行：

```bash
python scripts/bag2manifest/start_web.py --port 7860
```

**Agent：** “打开 `http://127.0.0.1:7860`，载入 bag 后依次检查相机缩略图、状态曲线、动作与状态叠加图，最后在输出页生成并校验 YAML。Web 导出的也是供后续转换使用的 `manifest.yaml`。”

## Web 对应操作（统一编辑器）

1. ①载入样例，②核对相机。
2. ③状态：左侧选择一维；右侧在“原始字段/计算公式”间选择来源。话题筛选与字段搜索共用一个选择器。点击“保存修改”替换该维；“＋新增”切换到新增模式。行操作在列表上方；曲线始终展开，默认显示当前表单全部字段，随新增、删除和修改自动更新；选中行只用于编辑。可用曲线筛选或图例单独查看。
3. ④动作：选 stored，核对手臂指令；点击“＋新增”，来源选“下一帧状态”，引用索引7、填gripper_exp并勾选夹爪，然后“添加维度”。状态重排时引用自动跟随；删除被引用状态会使配置报错。公式可原位修改。多候选时核对后勾选确认。
4. ⑤其他特征：采用相同编辑器；编辑完成后“保存特征”，再继续。
5. ⑥输出：先选择任务来源。const填固定文本；topic选择文本话题并查看样本。分别确认fps、消息时间戳来源、自动/手动容差，再确认正式bag_glob及最少帧数。字段插值在各字段编辑器中设置；per_bag与hold显示为固定支持规则。
6. 查看最终摘要，生成并校验后下载。表单变更使旧下载失效；手动YAML变更需重新校验，再次生成会覆盖手动内容。

“归一化显示曲线”不会写入normalize；公式编辑器的“写入公式归一化配置”才改变manifest。曲线不是实际转换后的时间同步结果。规范未定义主时间轴或主话题，页面不提供未经定义的主相机选择。
