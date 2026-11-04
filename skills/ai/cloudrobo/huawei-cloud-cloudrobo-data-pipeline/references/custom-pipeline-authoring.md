# 引导创建自定义管线 Guided Custom Pipeline Authoring

用户说“帮我创建自定义管线”“引导我配置处理步骤”“不想手写 YAML”“给现有管线加一步”时，
先进入本流程。用户无需预先提供 YAML；由 Agent 根据已知需求维护草案、补问缺项、生成配置。
仅当用户明确要求使用内置模板时加载内置模板，不能把所有自然语言请求都路由到内置模板。

面向使用者的完整示例与网页操作说明见 [模块用户指南](user-guide.md)；本文件供 Agent 引导和配置时使用。

## 意图与交付 Intent and Deliverables

| 用户意图 | 行为 |
|---|---|
| 创建/设计/配置管线 | 生成并交付配置与预览；不创建资产、发布版本、提交任务或初始化 Web 运行 |
| 修改已有管线 | 读取并保留已有字段及用户选择，补问本次改动相关缺项；导出新目录，不覆盖原文件 |
| 创建后执行 | 先完成配置，再进入原 Stage 0 的实时查询与执行计划确认；已有明确确认仍然有效 |
| 仅离线草案/接口尚未上线 | 允许保存明确标记的缺项草案，列出内网待查项，不捏造算子 ID、镜像或元数据 |

对话的结果是三个文件：`pipeline.yaml`、可继续修改的 `pipeline.draft.json`、便于审阅的
`pipeline-preview.md`。执行配置只在 YAML 的 `pipeline` 对象里；对话中的资源选择、输入所处阶段、
上游产物和步骤用途存放于 JSON 的 `authoring` 对象，不塞进 `params` 或虚构 `type` 字段。

## 对话引导 Interview

先从当前对话与已有文件提取信息。不要重新询问用户已给出的路径、格式、机器人、目标步骤和资源。
按缺项推进，每轮围绕一个决策主题；简单选项放在同一问中，不把整张字段表一次抛给用户。
用户回答可直接引用普通术语，不要求其知道 CLI 字段名或算子 asset_id。

默认从空白工作流开始。信息不足时补问，不预填模板、数据格式、机器人、转换/清洗/评测或输出名称。
自定义管线也可以完全由内置算子组成；空间资产算法与内置算子是每个步骤可以独立选择的来源。

### 从数据与目标开始

第一次优先确认 **希望处理什么数据、得到什么结果**。例如用户只说“帮我建管线”时：

> 希望处理什么数据、得到什么结果？如果已有想用的算子，请告诉我名称和顺序；还没选好也可以先描述目标。

再按缺项确认位置、格式和处理历史。用户已选定标准 LeRobot 清洗/评测、输入却为原始 H5 时，
说明格式不匹配并建议转换；不因用户提到 H5 就默认加入清洗和评测。
空间算法若声明能直接处理 H5，按其实际能力配置。机器人描述目录（通过评测成员 `params.inputs` 挂载）仅在用户选择提供或所选评测指标需要时补问。

接着补齐输入：

| 选择 | 必需内容 | 规则 |
|---|---|---|
| 本地目录 | local_path、实际数据格式 | 不凭目录名推断 H5/ROS2/UMI；不自动上传 |
| OBS 目录 | obs_path、实际数据格式 | 只接受 obs:// 路径；注册/发布属于后续执行 |
| 已注册资产 | asset_id、version_id；可先由用户给资产名 | 允许通过只读 list-assets/list-versions/show-version 补齐，路径来自版本 url |
| 已转换/已清洗/其他已处理输入 | 实际格式和来源；已有资产则补版本、asset_name、target_path | 按首个算子要求检查；OBS/本地数据在执行时按需注册，不自动添加模板处理步骤 |

数据来源 `local/obs/asset` 与数据阶段 `raw/converted/cleaned/processed` 是两件事，格式也不限于 H5/ROS2/UMI。
后者仅记在 authoring.input_stage；processed 表示其他已处理数据。不能因为用户给的是资产就断定已清洗。

用户要求执行本地数据管线时，不先导入数据再创建管线。确认执行计划后，以原始 local/obs/asset
来源 init，同一 run 先询问/打开监控，再按需调用资产中心 skill 准备输入并 record-inputs。
本次导入得到资产 ID 后仍保留 source_type: local 和 local_path；不能改成 asset 而让上传注册被判为跳过。

### 选择步骤和算子

按用户目标与算子能力确认顺序，再落到 id、operator、等待依赖 depends_on 与有序数据来源 input_from。
可以是“内置筛选 → 内置抽样”、完全由空间算法组成，或“内置转换 → 空间标准化 → 自选评测”。
这些是组合形式，算子名称须由实际查询或用户提供，不能把示例功能名当成已上线算子。

- 支持增加、移除、调整自定义处理步骤；评测可仅选质量、仅选多样性、两者或不评测。
- 为便于理解，建议每条分支围绕单数据集处理；这只是使用建议，不强制限制 proc 的输入数量。
  质量/多样性组成 advisory parallel_group，每个评测仍接收一个数据集。成员 ID 不能重复，后续不把报告作为数据集使用。
- 每条数据边都检查实际输入/输出格式及资产交接。标准 LeRobot 算子不能直接消费原始 H5/ROS2/UMI；
  需要时建议转换并确认。清洗不是所有评测的前置步骤，兼容的已有数据可直接评测。
- 单步独立选择 preset（内置）、workspace（空间算法资产）、obs（OBS 处理代码）。
  空间算法可位于任意符合数据契约的位置，也可构成整条管线，不限于“在清洗后插入一步”。
  评测使用预置或空间算法资产；OBS 代码来源当前仅用于 proc 处理步骤。
- 支持 A、B 各输出单数据集，再由支持多数据集输入的合并/处理算子 C 产出一个数据集。
  明确数据来源与顺序、逐项核实资产/版本/路径，不替算子拼文件；有多个未合并输出分支时让用户选择最终来源。
  多输入数量、顺序、挂载语义和格式必须按当前算子核实，不能因配置数组合法就断定任意内置/空间算子均支持。
- `id` 是稳定的 ASCII 标签；`operator` 是精确算子名；`operator_id` 只从用户或当次真实查询取得。
  单个评测步骤显式设 `kind: eval`，普通处理为 proc；并行组由 parallel_group 表示。

有 CLI 和已配置环境时，围绕本轮目标只读查询候选，用户也可直接提供已有的精确名称/ID：

```bash
cloudrobo workspace current
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "<用户所需功能片段>"
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "<用户所需评测片段>"
```

工作空间算法通过 `cloudrobo workspace current` 获取 catalog_id 后，使用
`cloudrobo asset list-assets --catalog-id <id> --type algorithm --name "<功能片段或精确名称>"` 查询；
按实际处理/评测用途筛选，并从结果读取子类型、镜像、入口、envs、inputs 和数据契约。
不要因为阶段 ID 叫 cleaning 就把空间算法当成内置清洗算子。

候选展示精确名称、ID、来源、用途/输入输出说明及当前元数据。多个匹配时让用户选；没有匹配时保留原需求并标待验证，
不换成另一个功能。工作空间算子按现有 Custom Operator Stages 的 list-assets 路径查询；OBS 代码算子需要用户提供
algo_path、容器 job_local_path、image 和 algo_entrance。读取的镜像/入口不固化成预置算子的长期模板；执行前仍重查。

没有内网连接时，可以先选精确算子名称并导出结构完整的草案，但明确“尚未验证可用性”；名称也未知则保留为缺项。
本地脚本不会调用 CLI，不能据其 STRUCTURE_VALID 结果声称算子已经上线。

<a id="multi-input"></a>
### 分支与多输入

`depends_on` 只描述“等谁完成”，`input_from` 描述“用谁的数据”，数组顺序就是处理任务
`dataset_configs` 的顺序。若 C 等待 A、B 和评测检查 check，但只使用 A、B 的数据，写：
`depends_on: [A, B, check]`、`input_from: [A, B]`；check 可为评测步骤，其报告不能作为数据来源。

兼容规则：不写 input_from 且仅有一个依赖时沿用该上游；首步只有一个初始输入时沿用它。
多个等待依赖或多个初始输入不能猜数据来源，需明确选择。只写 input_from 时，步骤来源会自动成为等待依赖。
已有 depends_on 则须包含所有被引用的生产步骤。初始来源用 `input:<id>`；一个未命名初始输入兼容 `input:default`。
多个初始来源必须有唯一 id，同一个初始来源也可以被两个分支使用。

下面是 **草案示意**：A 与 B 各处理一个初始数据集，C 接收两个结果，再输出一个数据集。
算子 ID 与资产信息须换成用户确认/真实查询的值；这不是新增内置模板：

```yaml
pipeline:
  name: branch-merge
  inputs:
    - id: left
      source_type: asset
      asset_id: "<左侧数据资产 ID>"
      version_id: "<左侧版本 ID>"
    - id: right
      source_type: asset
      asset_id: "<右侧数据资产 ID>"
      version_id: "<右侧版本 ID>"
  output:
    asset_name: merged-data
    from_stage: C
  stages:
    - id: A
      operator_source: workspace
      operator_id: "<A 算子资产 ID>"
      input_from: ["input:left"]
    - id: B
      operator_source: workspace
      operator_id: "<B 算子资产 ID>"
      input_from: ["input:right"]
    - id: C
      operator_source: workspace
      operator_id: "<支持双输入、单输出的合并算子资产 ID>"
      depends_on: [A, B]
      input_from: [A, B]
```

C 的结果可再接单输入评测。A、B 云端可并行运行，但同一 run 的 reserve/create/resolve
提交事务仍须串行；C 在两份数据都成功且交接核实后才提交。等待依赖中的建议性评测可以失败/跳过，
被选为数据来源的处理步骤则必须成功且有完整产物，不能用跳过代替输入。

`authoring.input_stage` 支持旧字符串（全部输入同阶段）或按初始 ID 映射，例如
`{"left": "converted", "right": "cleaned"}`。多个已处理资产的交接信息用
`authoring.upstream: {"left": {...}, "right": {...}}`，每项仍为 target_path、asset_id、version_id、asset_name。
只有一个初始输入时保留原有平铺 upstream 对象；阶段、格式、来源分别核实，不从分支名推断。
原始 H5/ROS2/UMI 是否已转换沿实际数据来源检查，无关分支上的转换或控制依赖不能代替本分支转换。

### 参数、资源和失败策略

- 从当前算子的 environment_variables 与 inputs 展示可选项；仅询问必要参数或用户要求自定义的部分。
  保留默认行为时省略 params，尤其不主动要求所有可选 config 挂载目录。
- `params` 只有 envs 与 inputs。环境变量名称和枚举、输入 name 需按当次算子声明确认。
  YAML inputs 只写 name/url_path；执行时按原 skill 展开为完整算子输入声明。
- CPU/内存、资源池、worker 数量属于 authoring.resources，转换/自定义步骤的输出名属于 authoring.output_names；
  不是算子 params，也不额外扩展 pipeline.yaml schema。Agent 在执行计划中将它们用于 task_config。
- 可建议“公共池、4c8g、1 worker”，但作为待用户确认的建议，不能把它当成用户已选值。
  专属池补齐 resource_id/name；并行评测显示所有成员合计的资源需求。
- 产生后续数据的处理步骤默认 fail_fast=true；评测 fail_fast=false。未提交的单输入处理步骤可在 Web 申请保留原输入跳过，
  智能体实时核实所有下游契约后生效；不是把 fail_fast 改 false，也不能以跳过掩盖缺失/不兼容数据。
- 机器人类型只有在算子需要时询问，robot env 枚举来自当前声明；内置 robot/配置不要求额外提供 YAML。
  评测 `robot_config` 已移除：机器人描述等配置目录只通过算子声明的 inputs 挂载（如 `ROBOT_CONFIG_PATH`），
  写在各评测成员自己的 `params.inputs` 中，没有组级默认值；未挂载时按算子内置/默认配置执行并列明未覆盖指标。
  manifest 类别不使挂载必填。草案中出现 `robot_config` 会校验失败，需迁移到对应成员的 `params.inputs`。
  CLI/SDK 若仍要求 `robot_config`，说明客户端过旧，升级后再提交，不编造路径。
- 不索要或写入 AK/SK；身份认证由 CLI 本地配置或运行环境提供。不要在参数示例中加入真实凭据。

例如，下面是 `pipeline.stages` 中消费同一清洗输出的评测组：两个成员分别挂载各自的机器人描述目录。

```yaml
- id: evaluation
  kind: eval-group
  depends_on: [cleaning]
  input_from: [cleaning]
  fail_fast: false
  parallel_group:
    - id: quality
      operator: 数据集质量评测-LeRobot
      params:
        inputs:
          - name: ROBOT_CONFIG_PATH
            url_path: obs://example-bucket/config/quality-robot/
    - id: diversity
      operator: 数据集多样性评测-LeRobot
      params:
        inputs:
          - name: ROBOT_CONFIG_PATH
            url_path: obs://example-bucket/config/diversity-robot/
```

不需要描述目录的成员省略 `params.inputs`，按算子内置/默认配置执行；单独的 `kind: eval` 步骤同样写在自身 `params.inputs`。
挂载名必须与当次查询到的算子 `ext_metadata.inputs` 一致（上例名称仅为参考）。
这不改变评测的单数据集输入规则；目录应由用户提供，并与该成员的算子契约、数据和机器人描述匹配。
预览逐项展示各成员的挂载。执行时将各成员的挂载展开为完整的算子 inputs 元素写入其 `task_config.inputs`，
不能将另一成员的目录复制过来。

只有产生新数据集的步骤才需要数据输出名。`pipeline.output.from_stage` 指定最终数据来源，
`pipeline.output.asset_name` 作为该步骤的输出名；其他步骤名放在 authoring.output_names。
唯一未被其他处理步骤消费的末端 proc 输出可自动补全 from_stage（只等待不算消费），并在预览中展示；多个数据输出需让用户选，不能固定取清洗输出。
仅评测时保留输入数据并生成报告，不要求创建另一个数据集名称。

### 短唯一命名

默认任务名与新数据产物名使用 `管线名-步骤短名-MMDDHHmmss`，例如 `teleop-clean-1018102430`。
按管线名前缀即可查找该管线的步骤/产物；步骤用短 ID，完整算子名及 ID 另存元数据。
选完工作流后运行 `python scripts/custom_pipeline.py suggest-names --pipeline-name teleop --stage convert --stage clean`，
只传实际选中的产数据步骤；新注册输入可用 input。默认不加随机串；同进程同秒撞名才加 -2/-3。
这不保证跨进程/机器唯一：确认前通过选中工作空间 catalog 的 list-assets --exact-name 核实，
占名时换时间戳或短序号并复核。**完整名称含时间戳/序号总长 ≤64**；超长提示缩短管线名或步骤短名，不能静默裁剪。
最终名写 pipeline.output.asset_name，中间名写 authoring.output_names，在整体计划中一起确认。

用户明确指定的合法精确名保留；修改草案只改请求部分。新执行建议新名，已有 run 的恢复/检查/导出沿用已确认名。
仅评测、复用已有资产和已核实旁路不改输入名、不造新版本。output_path 须由用户提供确认，不能猜路径。
交付目录可另用 suggest-names --base teleop-config（默认总长 ≤32）；目录内标准三文件名不变、旧文件不覆盖。
该命令不访问平台或写文件。

### 审阅与修改

给出简短预览：数据来源/阶段、处理链与每步算子来源、评测范围、输入挂载、资源/输出名、失败策略、尚未确认项。
用户说“把多样性评测去掉”“清洗后加脱敏”“改用专属池”时，修改草案并重算依赖、资源汇总和校验，不要求重填全部信息。
移除某一步时检查所有引用；仅在仍能传递同一个数据集且符合用户意图时重接后继，否则指出需要明确的新来源。

完成所有可确定内容后直接生成可审阅文件。仅创建配置不需要再设置“确认才能写文件”的门槛；
若用户随后要求执行，再按原 skill 完成包含真实算子元数据的执行计划确认。

## 本地脚本 Local Helper

Agent 将整理好的字段写成下面的 JSON 结构，用户无需手写。示例展示内置转换接空间标准化，
没有清洗或评测步骤；空间算子名、路径均为用户选择的示意，仍需内网查询验证：

```json
{
  "pipeline": {
    "name": "custom-h5-normalize",
    "inputs": [{"source_type": "obs", "obs_path": "obs://example-bucket/raw/", "data_source_type": "h5", "robot_type": "a2d"}],
    "output": {"asset_name": "normalized-data", "from_stage": "normalize"},
    "stages": [
      {"id": "convert", "operator": "数据转换--H5转LeRobotV3"},
      {"id": "normalize", "operator": "我的格式标准化", "operator_source": "workspace", "depends_on": ["convert"]}
    ]
  },
  "authoring": {
    "input_stage": "raw",
    "roles": {"convert": "conversion", "normalize": "processing"},
    "resources": {
      "resource_pool_type": "PUBLIC_POOL",
      "worker_spec": {"cpu": 4, "memory": 8, "gpu": 0, "npu": 0},
      "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
      "worker_num": 1
    },
    "output_names": {"convert": "custom-converted"}
  }
}
```

authoring 的 resources/output_names 只写用户选择或已明确接受的建议。input_stage 必填；
roles 记录已确认的业务用途。常见标准算子能按精确名称识别用途；自定义算子需显式记录其用途，
避免把阶段 ID 或模糊关键词当成算子语义。

部分管线另带：

```json
{
  "input_stage": "cleaned",
  "upstream": {"target_path": "obs://example-bucket/cleaned/", "asset_id": "<asset_id>", "version_id": "<version_id>", "asset_name": "cleaned-data"},
  "roles": {"evaluation": "evaluation"}
}
```

该对象是 authoring 的示意；pipeline.inputs 同时选择 asset 并使用相同资产/版本。

在 skill 根目录执行：

```bash
python3 scripts/custom_pipeline.py check --input /path/to/choices.json
python3 scripts/custom_pipeline.py export --input /path/to/choices.json --output-dir /path/to/new-pipeline

# 用户愿意先保存缺项草案时：
python3 scripts/custom_pipeline.py export --input /path/to/choices.json \
  --output-dir /path/to/new-draft --allow-incomplete
```

脚本仅用标准库，输入 JSON、输出可由标准 YAML 解析器读取的 YAML。字符串均正确引用，避免 true、数字、
冒号、换行或特殊字符改变 env 值。用户已有 YAML 时由 Agent 读取并转成 JSON 输入，不给脚本加不完整的 YAML 解析器。
导出不覆盖任何已有文件；修订可输出新目录。资源偏好和上游交接只进入 draft.json/preview，不污染可执行 YAML。

| 状态 / 退出码 | 含义 |
|---|---|
| STRUCTURE_VALID / 0 | 本地结构通过；仍须真实算子发现、数据版本/参数复核和执行确认 |
| INCOMPLETE / 2 | 缺少用户选择或含占位符；check/普通 export 不通过 |
| INCOMPLETE / 0（仅允许缺项导出时） | 已保存带 DRAFT 标记与待补清单的草案；不可直接执行 |
| INVALID / 1 | schema、类型、命名、依赖环、数据交接或失败策略错误；即使 allow-incomplete 也不导出 |

## 交接执行与 Web 监控 Execution Handoff

若用户仅要求创建，交付以上三个文件并说明调用方式，例如“执行 `/path/to/pipeline.yaml`”。
没有运行则不打开一个假运行页面，也不初始化已确认状态。

用户要求执行后，重新读取 YAML 和 companion draft.json：

1. 重查算子/输入版本，校验 role 与真实子类型及输入输出是否一致；env/input 声明不能只依赖草案中的旧查询结果。
2. 由 depends_on 构造等待顺序，按 input_from 构造每步真实输入；将 authoring.resources/output_names 映射到 task_config。
   proc 按顺序生成多项 dataset_configs；评测保留顶层数据集字段并附带单项 dataset_configs，资产输入必须包含确切 version_id。CLI 核实算子支持后才能执行，多输入处理仍只交接一个输出数据集。
   评测成员各自按 `params.inputs` 解析配置挂载；未提供时不写 `inputs`、不补造挂载，任务中不写 `robot_config`。
   执行计划展示各成员挂载或“未挂载（使用算子内置/默认配置）”，并核实指标范围。
   同组共享数据来源，不强制共享机器人描述目录。
3. 核实已转换/清洗/其他已处理输入的实际格式与来源。已有资产只读核对版本及路径；OBS/本地输入此时不上传或注册。
   已有来源的已核实资产、版本、asset_name 与版本 url 可写入对应的 plan.inputs 项；待注册来源保留真实路径，
   不编造 asset_id/version_id。authoring.upstream 的 target_path 对应这里的 obs_path。
   表示已核实的外部输入时使用 external，不伪造已执行的转换/清洗任务。
4. 按原 Stage 0 展示完整执行计划并使用已有的明确授权；确认后保存实例化监控 plan，调用 pipeline_state.py init。
5. init 后立即按 Web Monitor 规则询问一次是否打开本次运行监控，早于上传/注册、发布或提交首个任务。
   此前已有打开授权则直接打开；用户选择打开时先定位本次 run，再进入下一步。未回复或仅终端跟踪不暂停编排，
   不设置 await-decision，也不重复问演示/真实模式；只说明计划已确认、准备执行，不声称已提交云端任务。
6. 本地输入先查阅 `huawei-cloud-cloudrobo-asset` 的导入资产流程，使用 `cloudrobo asset import-asset`
   一次完成上传和注册，不先搜索通用 OBS 命令。OBS 输入只走资产注册，已有资产只核对复用；不要重复创建。
   沿用已确认计划和 CLI 编排方式，核实每个来源的资产、版本、asset_name 和版本 url，通过已核实的
   resolved-inputs.json 按 ID 交接。先用 [record-inputs](web-monitor.md#record-inputs) 将登记结果写入本地 state.inputs，
   全部输入登记完整后 upload 才完成；再使用 [Web Monitor 的 resolve-inputs](web-monitor.md#resolve-inputs)
   生成输入片段。resolve-inputs 的 inputs-file 只是只读补充，不会自动把登记信息保存到 Web。
   实时核实每个版本/路径后再提交。后续 reserve-task/resolve-action、心跳、结果和摘要沿用 Web Monitor。
7. 运行时统一转换为任务图，通过 `pipeline_state.py --run <run_id> ready-tasks` 取得同一就绪集合。
   parallel_group 只是兼容输入形式，成员与普通步骤共用调度路径，不让用户选择两种执行模式。
   action=submit 时先提交所有已就绪任务；每次 resolve 后重查，直到 action=poll 才进入状态轮询。
   A 的返回任务 ID 核实并 resolve 后立即提交 B，不以 A 成功作为释放提交事务的条件。
   多分支运行时按短周期轮询全部活跃任务，每轮核实结果后再提交新就绪步骤，避免在单个任务上 wait 300 秒。
   用户要求共享输入的并行分支时，两者明确使用相同 input_from；不要漏写 B 的来源而误变为依赖 A。

普通自定义处理输出、未评测数据和 TrainingReady 产物按实际已执行/核实的范围标注，不能因为草案结构通过就声称训练数据合格。
输出核实与完成摘要读取 from_stage；评测报告另外汇总，Web 使用通用的“管线产物”名称。

## 引导验证 Scenarios

在没有云端写权限的环境，用以下请求走读 skill，检查实际生成的草案与预览：

- “OBS 的 H5，帮我建一条只做清洗和质量评测的管线，不执行。”应提示必要转换、仅质量评测，不提交任务。
- “我不会写 YAML，先引导我。”应从目标/数据开始，不预填模板或处理步骤。
- “只用查询到的两个内置算子做筛选和抽样，不清洗不评测。”只组合用户选择的算子，核对格式和最终输出来源。
- “只有我的空间算法 A → B，直接处理 H5。”核实 A 能否接收 H5，不因其名称像清洗就插入内置转换。
- “内置转换后接我的空间标准化，不做评测。”混合两个来源，最终输出来自标准化步骤。
- “已有转换后的 LeRobotV3，只做质量评测。”可直接评测，不强制添加清洗；保留实际处理历史和评测覆盖说明。
- “已经清洗，只有 asset_id；我只做多样性评测。”补齐版本、OBS 路径/资产名；按所选指标决定是否需要挂载机器人描述目录，不补造转换/清洗任务。
- “清洗后加我的工作空间脱敏算子，暂时连不上内网。”记录自定义步骤/依赖与待查项，保留草案，不改用预置算子。
- “保留原文件，把两项评测改成仅质量，改用专属池。”只调整相关字段、补池 ID/name，导出新版本，保留原文件。

自动结构与导出测试与 Web 的离线测试共用命令，详见 [Verification Method](verification-method.md)。

- “A 与 B 各处理一个数据集，再交给空间合并算子 C，最后只评测 C。”应明确两条分支来源、C 的输入顺序、单输出及评测单输入；不因多数据集拒绝。
- “C 等待质量检查但只消费 A、B。”检查报告不能进入 dataset_configs；失败/跳过的 A、B 不能作为可用数据。
