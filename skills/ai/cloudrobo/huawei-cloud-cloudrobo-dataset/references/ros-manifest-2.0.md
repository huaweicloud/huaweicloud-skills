# ROS Manifest 2.0 生成与校验准则

本文件根据用户提供的《LeRobot Toolkit — Manifest 2.0 规范》整理，仅适用于 ROS 转换。配置入口仍属于 dataset skill；不包含 H5、UMI 的策略或参数。

## 必需结构

必须有 `schema_version: "2.0"`、`source_type: ros2`、非空 `state`、`action`、`cameras`、`source`，以及 `task`。可选 `repo_id`（默认 converted）、`robot_type`（unknown）、`fps`（30）、`output`、`extra_features`、`curation`。

```yaml
schema_version: "2.0"
source_type: ros2
repo_id: demo/pick-place
fps: 30
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
      names_from: explicit
      names: [joint_1_exp, joint_2_exp]
    - strategy: next_state
      state_index: 2
      name: gripper_exp
      role: gripper
cameras:
  wrist: {locator: /camera/image_raw, depth: false}
task: {mode: const, text: pick up the red cube}
source:
  bag_glob: "*.db3"
  time: {stamp_source: auto, tolerance_ms: 17, on_stale: hold}
  segment: {mode: per_bag, min_frames: 30}
output:
  chunk_size: 1000
  data_file_size_mb: 100
  video_file_size_mb: 200
  video_codec: auto
```

## 字段项：顺序、维度、单位

- 导出的 state/action/extra_features 使用对象，普通字段写 `locator`，计算字段写 `expr` + 有序 `inputs`，两者互斥。旧字符串、`path` 不是新版配置。
- **JointState 数组必须使用 `names_from: embedded` + 有序 `names`**。从每条消息的 `msg.name` 反查下标；names 决定选哪些关节和输出顺序，不能假设发布顺序稳定。
- 普通数值数组使用 `names_from: explicit`（可省略）+ `names`，按 data[i] 取值；重命名 names 不会改变读取下标。选非连续维度时使用带下标的 scalar locator。
- state 是所有字段项展开后依次拼接的向量。统计维度应按 names 数量展开，不能数 YAML 项数。恒定关节默认保留并告警，删除需有机器人语义依据。
- 夹爪项标 `role: gripper`。名称识别只是建议，要确认实际物理含义。保留原始单位和数值尺度；不能仅因名字像夹爪就自动归一化。
- normalize **只可出现在 expr**，格式为递增、有限的 `[min, max]`。Web 的按样例范围归一化需用户主动勾选；样例极值不一定代表机械限位。普通字段需要归一化时改为 identity expr `f0`，明确输入和区间。
- expr 允许 `+ - * / ** % //`、一元正负、括号、单个比较 `> < >= <= == !=` 和 `abs/min/max/sqrt/exp/log/clip/where`；输入依次绑定 f0、f1……。禁止任意 Python、属性访问、下标表达式和链式比较。

## 动作确认：只支持 stored / next_state

1. `stored`：显式读取 fields；普通动作默认 linear，role=gripper 默认 nearest。
2. 整段 `next_state`：action[t] = state[t+1]，末帧复制；不配置 fields。没有指令话题时可以建议，但必须确认它符合训练目标。
3. 混合动作：stored.fields 中允许单维 `{strategy: next_state, state_index, name, role}`。手臂读取指令，夹爪引用下一帧状态；也可以显式添加夹爪 expr，例如 `where(f0 > 0.1, 0, 100)` 或 `f0 * 1000`。**不自动追加夹爪动作话题**。

`state_index` 按最终拼接向量从 0 起计；上例 state 有 3 维，夹爪为 index=2。原始规范一句话写“state 列表下标”，但其 6/7 维手臂示例使用 6/7，因此实现按展开维度校验。Web 按字段身份跟随重排更新 index；删掉引用维度会标记失效，需重新选择或撤销。手动编辑 YAML 后仍需核对 index，实际转换应验证这个约定。

动作候选名字含 command/cmd/target/setpoint/goal/teleop/joint_plan；夹爪类话题不进入主动作自动选择。维度匹配仅供排序，不能证明话题就是实际控制指令。多候选 E021 必须核对再确认；动作与状态维度不同可作为 warning，但必须解释控制语义。

## 插值与缺失话题

| 字段段落 | 缺省 interpolation |
| --- | --- |
| state | nearest |
| stored 普通 action | linear |
| stored gripper action | nearest |
| extra_features | nearest |

可在单项覆盖 nearest / linear / front；front 取当前帧之前最新的值。`default` 为有限标量（所有维度同值）或与展开维度等长的数值数组。缺少话题时，只在用户明确声明 fallback 的情况下放行并告警，不能自动创造真实控制信号。

## 相机、任务、时间与输出

- 相机用 `{locator: /topic, depth: false, resize: [H,W]}`。核对画面、编码、频率和尺寸；本工具为视频输出要求 resize 正偶数。至少启用一路相机。
- task 仅 const/text 或 topic/topic。const 任务优先级：env task → 数据集目录 task.txt → prompt.json → manifest task.text → lerobot_teleoperation。prompt.json 的 list 按 episode 循环，dict 按文件名匹配；未命中回退 manifest。没有 `task.mode: sidecar`。
- 时间、分段配置放在 **source 内**。时间源 auto/log_time/header_time/rosbag_time；仅支持 on_stale=hold、segment.mode=per_bag。规范默认容差50ms；推断模式生成 round(500/fps)，30fps 即17ms。min_frames 默认30。
- source.bag_glob 必须确认它匹配**将要转换的整批文件**，不能把样例路径当 glob。规范明确举例 *.db3/*.bag；工具可以扫描 MCAP 并建议 *.mcap，但目标转换器是否读取 MCAP需单独确认。可用 CLI `--bag-glob '*.db3'` 覆盖。
- output 字段为 chunk_size=1000、data_file_size_mb=100、video_file_size_mb=200、video_codec=auto/libx264/libsvtav1。
- curation 是可选 dict，原样携带给下游 sidecar，不在本工具执行清洗。转换算子根据 role 推导夹爪在 state/action 中的维度索引；配置 gripper_dims 不应代替正确的 role。
- 不导出旧版顶层 time/segment/quality、旧文件大小键，以及 delta_state、drop、time_gap 等未支持选项。ROS 中不使用 UMI 的 delta/binary_gripper。

## 交付检查

读取 summary/profile/issues，确认消息定义、关节顺序、动作语义与单位、夹爪策略、图像、任务和时钟。退出码2表示有阻塞错误；0表示本工具的契约及样例校验通过。Web 遇配置错误不给下载。所有通过结论仅覆盖样例和本地验证，正式全量转换前需在实际 Toolkit 上试跑少量 episode。

## 尚未定义的转换行为

时间戳来源不是输出主时间轴。本文未定义主话题/网格时间轴的选择、起止边界、auto的逐bag/话题/消息选择粒度及回退优先级、log_time与rosbag_time的区别、容差如何作用于nearest/linear/front、首帧hold与default优先级、DB3分片如何归组为episode，以及topic任务是否被外部文本覆盖。Web展示已知配置和推断依据，不增加这些尚无契约的字段；依赖这些行为时需补充转换器实现或规范。
