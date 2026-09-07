# Examples

本目录保存 `huawei-cloud-solution-ops` 的示例模板，主要给 Agent、skill 维护者和本地验证使用。它不是普通用户操作指南。

普通用户不需要复制这些文件，也不需要直接执行脚本。用户只需要在对话里描述目标、提供资源 ID、配置要求，或在需要时粘贴创建参数 JSON；Agent 会参考这些模板完成参数整理、风险检查和 dry-run 规划。

## 作用

这些示例主要解决三件事：

1. 给复杂创建类 API 提供稳定的 `cli-jsonInput` 骨架。
2. 帮助 Agent 判断 ECS 创建任务缺少哪些关键参数。
3. 支持维护者做本地 dry-run、参数校验和回归验证。

## 当前示例

- `ecs-create-servers.cli-jsonInput.json`
  - 适合 ECS `CreateServers` 的请求体参考。
- `ecs-create-postpaid-servers.cli-jsonInput.json`
  - 适合 ECS `CreatePostPaidServers` 的请求体参考。
- `ecs-create-servers-password.cli-jsonInput.json`
  - 适合使用 `adminPass` 密码登录的 ECS `CreateServers` 请求体参考；密码必须先保存到受限权限 artifact。
- `ecs-create-dryrun.md`
  - 说明维护者如何配合 dry-run 检查这些模板。
- `eip-acceptance-closure.md`
  - 展示 EIP lifecycle plan、probe plan、evidence status 和验收结果判定的离线闭环。

## 普通用户怎么用

在对话里这样告诉 Agent 即可：

```text
我准备创建一台 ECS，配置包括镜像、规格、VPC、子网、安全组、密钥对、
系统盘和实例数量。请使用 huawei-cloud-solution-ops 先检查参数是否完整、安全、
幂等；如果还缺信息，请列出来。不要直接创建云服务器。
```

如果已经有 ECS 创建参数 JSON，可以直接粘贴给 Agent：

```text
下面是我准备使用的 ECS 创建参数 JSON。请使用 huawei-cloud-solution-ops 先检查
占位符、必填字段、资源 ID、实例数量和费用风险。不要直接创建云服务器。
```

## Agent 和维护者怎么用

这些模板可以作为内部参考，但不能当作已经验证过的现网配置。

使用时建议：

1. 先复制模板，不要直接修改原始示例。
2. 替换所有占位值，例如 `<project_id>`、`<availability_zone>`、`<flavor_id>`、`<image_id>`、`<subnet_id>`、`<vpc_id>`、`<security_group_id>` 和 `<key_name>`。
3. 创建 Linux ECS 前确认登录方式：密钥对路线必须有本地私钥；密码路线必须先把 `adminPass` 保存到受限权限 artifact，不能依赖日志事后找回。
4. 先做本地参数校验和 dry-run 规划。
5. 只有在依赖资源、费用、配额、登录凭证和回滚方式都确认后，才考虑真实创建。

## 注意

- 模板字段是可复用骨架，不是所有字段都必须保留。
- 删除不需要的字段，比保留一堆不确定字段更稳。
- 模板里的字段名保持华为云 API 原生风格，可能同时出现 `camelCase`、`snake_case` 和类似 `vpcid` 的供应商字段；不要擅自规范化重命名。
- 创建类任务涉及费用和资源变更，默认不要跳过 dry-run。
