# Provider Capability Index

这份文档用于吸收参考仓库 `docs/resources` 和 `docs/data-sources` 里更宽的 provider 能力面。

它不是要把所有能力都立刻做成新示例，而是先把“这个 provider 还覆盖了什么方向”沉淀到 skill 内部，方便后续：
- 回答用户“这个服务 Terraform 支不支持”
- 判断某个服务是否值得从 `Full support` 继续做深
- 在删除参考仓库后，仍然保留扩展入口

如果要查看完整清单，而不是这里的摘要索引，直接看：
- `reference-example-inventory.md`
- `provider-resource-inventory.md`
- `provider-data-source-inventory.md`

## 读这份索引的方式

- 如果用户问的是当前已经有 example 的服务，优先仍使用现有 `*_stack`。
- 如果用户问的是更偏平台、治理、AI、开发工具的服务，先查本索引判断 provider 是否已有资源和 data source 家族。
- 如果某个能力只在本索引里出现，还没有 example，说明它是“provider 已支持，但 skill 尚未做深”的候选方向。

## 已经吸收到 examples 的主能力族

当前已有较完整本地沉淀的能力族包括：
- 网络与入口: `vpc`、`nat`、`elb`、`vpn`、`vpcep`、`dns`、`er`、`cc`、`dc`、`esw`
- 计算与平台: `ecs`、`bms`、`cce`、`obs`、`evs`、`rds`、`dcs`、`dms`、`swr`
- 安全与治理: `waf`、`antiddos`、`iam`、`identity-center`、`ram`、`organizations`、`rgc`、`rms`、`secmaster`
- 运维与迁移: `aom`、`ces`、`coc`、`cts`、`lts`、`sms`、`oms`
- 其他: `apig`、`cbr`、`fgs`、`ims`、`hss`、`cbh`、`deh`、`dew`、`sfs-turbo`、`tms`

## 参考仓库里仍值得关注的额外能力族

下面这些能力族在 provider 文档里已经能看到明显资源和 data source 覆盖，但当前 skill 还没有作为主路径沉淀成示例。

### 1. 边界安全与流量防护

- `aad`: 高防、黑白名单、转发规则、域名防护、解封统计
- `access-analyzer`: 访问分析器与归档规则
- `cnad` / `cfw`: 更细的云防火墙和网络防护能力

适合的未来场景：
- 企业公网暴露面的统一治理
- 攻击事件、流量防护和告警联动

### 2. 应用运行平台与开发工具

- `cae`: 应用托管、环境、组件、域名、定时规则
- `servicestage` / `servicestagev3`: 应用运行时与发布能力
- `codearts`: DevOps、流水线、工件、项目治理
- `dataarts`: 数据开发和数据治理

适合的未来场景：
- 从基础设施延伸到应用托管和交付平台
- 和 ADK agent、CI/CD、平台工程场景联动

### 3. 数据与分析平台

- `gaussdb`
- `dds`
- `ddm`
- `dli`
- `dws`
- `css`
- `cdm`
- `mapreduce`

适合的未来场景：
- 数据仓库、NoSQL、流式分析、大数据集群
- 作为 `RDS / OBS / DMS` 之外的进阶数据栈

### 4. 身份、证书与密钥扩展能力

- `identity` / `identityv5`
- `kms`
- `csms`
- `kps`
- `ccm`

当前 skill 已经覆盖 `iam`、`identity-center`、`dew` 的最小路径，但如果后续用户开始大量命中：
- 更细的委托关系
- 证书托管与部署
- 密钥对、Secrets Manager、私有 CA

就应优先从这些能力族里继续扩展。

### 5. AI、IoT 与行业平台

- `modelarts` / `modelartsv2`
- `iotda`
- `live`
- `ga`

这些能力不一定适合马上做 Terraform 示例，但 provider 已经有资源和 data source 面，可以作为后续行业化场景入口。

### 6. Workspace 与终端场景

- `workspace`
- `cph`
- `bcs`
- `iec`

这些能力更偏终端工作桌面、手机云或边缘场景。

如果后续用户从“云资源部署”转向“桌面工作区”“终端托管”或“边缘接入”，这几类值得优先重新评估。

## 如何把这些能力转成 skill 资产

建议按下面顺序处理：
1. 先看 provider 是否已经有清晰的 resource 和 data source 家族
2. 再判断有没有稳定的最小业务闭环
3. 最后再决定是补 reference、补 `*_stack`，还是补组合型示例

不要因为 provider 文档里有资源，就立刻把它做成新 example。

## 对后续迭代的意义

这份索引的价值在于：
- 后面删掉参考仓库时，skill 仍然保留“provider 能力面”的记忆
- 后续接用户测试时，可以更快判断“这个需求 provider 是否有覆盖”
- 做组合型示例前，可以先知道还缺哪些底层零件
