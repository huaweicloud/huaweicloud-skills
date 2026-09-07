# Huawei Terraform Skill Status And Roadmap

这份文档只回答 3 个问题：
- 现在这个 skill 到了什么阶段
- 当前真正还缺什么
- 后面应该按什么顺序做

## 当前状态

`huawei-cloud-solution-ops` 的 Terraform 资产面当前已经具备以下特征：
- 自包含，不依赖 `terraform-skill` 或外部参考仓库作为运行前提
- 同时兼容 `HW_*` 和 `HUAWEI_*` 环境变量语义
- 支持和 `hcloud` 联动，适合“先查现网，再沉淀 Terraform”
- 已经形成 discovery-first 的默认工作流，而不是直接硬编码华为云参数
- 已经提供统一示例校验脚本 `examples/terraform/validate_examples.sh`
- 已经建立支持矩阵，开始按批次扩服务覆盖面
- 已经把参考仓库中高价值的高级变体和 provider 能力面沉淀到内部 references，不再只有服务名和最小示例
- 已经补齐第一档深化资料：服务变体选择和 data source 选型规则
- 已经把参考仓库中的 examples、resources、data-sources 全量目录索引搬进 skill 内部

## 当前成果

- 73 套已吸收示例
- 全量 `Full support`
- 一套较完整的 discovery-first 规则体系
- 一套较完整的变体选择和 data source 选型规则
- 三份完整 inventory，保证删掉参考仓库后也不会丢 provider 覆盖面记忆

## 当前能力边界

当前 skill 已经足够支撑以下常见任务：
- 从零生成华为云基础 Terraform 模板
- 按示例改造成项目内可审查的 Terraform 代码
- 评审 `huaweicloud_*` 资源写法是否符合当前约束
- 先查询现网，再生成复用型 Terraform 配置

但以下能力还没有系统补齐：
- CCE autopilot。当前参考资产中没有可直接吸收的 autopilot 示例，不能把 `turbo-cluster` 当成 autopilot。
- 多 region / 多 provider alias 的成体系示例
- `enterprise_project_id` 场景
- APIG、DMS、DCS 等高频中间件/接入层的高价值变体
- 将高级变体持续整理成更统一的增强版 example

## 当前文档分层

- `examples/README.md`: 找 starter example 和按场景浏览示例
- `provider-auth.md`、`discovery-workflow.md`、`resource-mapping.md`、`troubleshooting.md`: 核心工作流
- `advanced-variant-catalog.md`、`service-variant-guide.md`、`data-source-selection-guide.md`: 深化规则
- `reference-example-inventory.md`、`provider-resource-inventory.md`、`provider-data-source-inventory.md`: 全量回查入口

## 下一阶段建议

### 第一阶段：根据真实用户测试挑重点做深
建议优先从以下方向选高频命中项：
- 复用型示例
- 组合型业务拓扑
- 合规与治理服务的更完整 example
- 现网联动更强的场景

原因：
- 广覆盖和全量 `Full support` 已完成
- 现在最重要的是根据真实测试数据决定哪些服务要继续做深，而不是继续扩服务名录

### 第二阶段：补“复用型”和“组合型”示例
已补齐第一批高收益场景：
- 复用现网 CCE 依赖后创建 node pool
- 复用现网 ELB 或 NAT 资源后补入口规则
- 端到端业务拓扑示例，例如 `ECS + ELB + RDS`、`OBS + CDN + DNS`

原因：
- 这类场景最贴近真实项目改造
- 最能体现和 `hcloud` 联动的价值
- 能减少用户从零拼装多个示例的成本

### 第三阶段：补 CCE 高阶能力
建议逐步补：
- CCE autopilot，但需要先确认 provider 是否已有稳定资源/schema 或官方推荐实现
- 节点池更细的伸缩和磁盘配置

这部分可以优先参考 `advanced-variant-catalog.md` 中已经沉淀的 addon、partition、cluster 形态差异。

原因：
- 当前 CCE 已有主链路，但还停留在基础交付层
- 如果目标是上生产环境，CCE 往往会很快进入 addon 和运维配置

### 第四阶段：补跨环境和企业级约束
建议关注：
- 多 region / 多 provider alias
- `enterprise_project_id`
- 更清晰的环境隔离模板
- 状态管理与 CI 集成建议

原因：
- 这些能力决定 skill 是否适合长期维护型项目
- 也是 Terraform 从“示例”走向“工程资产”的关键一步

## 推荐迭代顺序

如果按收益和风险平衡，推荐顺序如下：

已完成：
- 复用型 ELB / NAT / CCE node pool 示例
- 组合型业务拓扑示例：`ECS + ELB + RDS`、`OBS + CDN + DNS`
- CCE coredns / turbo / partition 和 RDS 形态矩阵

下一步建议：
1. APIG、DMS、DCS 等高频中间件/接入层变体
2. CCE autopilot 可行性确认
3. 多 region / provider alias
4. `enterprise_project_id`
5. CI 和更细粒度自动验证
6. 对 imported examples 做进一步标准化统一
7. 再判断是否进入新的能力族

## 维护建议

后续继续迭代时，建议保持这些约束：
- 每新增一个示例，都补 `terraform.tfvars.example`
- 每新增一个示例，都跑 `examples/terraform/validate_examples.sh`
- provider 版本约束调整后，重新跑全量示例校验
- 不要把本机绝对路径写进 skill 文档
- 不要把 `task_plan.md`、`findings.md`、`progress.md` push 到 GitHub

## 何时考虑收束而不是继续扩张

如果后续出现以下情况，建议先停下来整理，而不是继续加新服务：
- 示例数量明显增加，但 references 没有同步更新
- 多个示例开始出现重复逻辑却没有模块化总结
- 同一类资源已经有多个变体，但选择标准不清楚
- 校验时间明显变长，维护者开始不愿意跑全量验证

这时更值得投入的是：
- 做示例归类
- 做模块蓝图
- 做验证分层
- 做更清晰的路线图和边界定义
