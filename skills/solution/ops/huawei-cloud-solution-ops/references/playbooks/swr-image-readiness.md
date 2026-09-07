# SWR Image Readiness Playbook

## 目标

帮助用户把“我有一个 Docker 镜像，想部署到华为云”拆成可验证步骤：镜像来源、SWR namespace/repository/tag、登录凭证、推送/拉取权限、运行目标和镜像清理策略。不要把镜像构建、登录 token、仓库公开权限和运行时部署混成一步。

## 适用场景

- 用户要把本地镜像推到 SWR。
- 用户要确认 CCE/CCI 能否拉取某个镜像。
- 用户遇到镜像仓库、tag、ImagePullBackOff、拉取失败或权限失败。
- 用户要整理镜像保留策略、共享权限或长期访问凭证。

## 标准只读检查

1. 查询 namespace：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service SWR \
  --operation ListNamespaces \
  --region=<region> \
  --pretty
```

2. 查询 repository：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service SWR \
  --operation ListReposDetails \
  --region=<region> \
  --pretty
```

3. 查询指定镜像 tag：

```bash
python3 scripts/hcloud_resource_query.py \
  --service SWR \
  --operation ListRepositoryTags \
  --region=<region> \
  --param namespace=<namespace> \
  --param repository=<repository> \
  --pretty
```

4. 查询 repository 详情：

```bash
python3 scripts/hcloud_resource_query.py \
  --service SWR \
  --operation ShowRepository \
  --region=<region> \
  --param namespace=<namespace> \
  --param repository=<repository> \
  --pretty
```

这些路径来自 metadata-backed catalog；如果某个 operation 在当前 KooCLI 版本不可用，先输出 operation、参数和失败分类，不要改用高风险凭证绕过。

## 镜像引用检查

用户给出镜像地址时，至少确认：

- region 是否和运行目标一致。
- namespace / repository / tag 是否存在。
- tag 是否可变；生产建议使用不可变 tag、digest 或 release tag。
- 仓库是否私有；CCE/CCI 是否有拉取凭证或同账号访问能力。
- 镜像架构是否匹配运行节点或 CCI 规格。
- 是否需要公网访问 SWR，或能走 VPC/内网服务终结点。

## 登录和推送边界

SWR 登录 token、临时凭证、长期凭证、repository 创建和权限调整都不是只读查询：

- 不把 token、AK/SK、docker login password 写入最终输出。
- 不自动执行 `CreateAuthorizationToken`、`CreateRepo`、`CreateNamespace`、`UpdateRepo`、权限共享或 retention 写操作。
- 如果用户明确要推送镜像，先输出所需信息清单：region、namespace、repository、tag、镜像大小、镜像来源、是否覆盖已有 tag。
- 如果需要生成变更计划，走 `hcloud_service_change_plan.py` 或 Terraform route；真实执行仍需二次确认。

## 镜像治理清单

SWR 治理类请求优先走只读盘点，再生成 review plan：

- Namespace：owner、环境、成本中心、是否长期无人维护。
- Repository：公开/私有状态、共享域名、授权对象、最近推送时间。
- Tag：版本命名、不可变策略、digest、架构、是否被 CCE/CCI/FunctionGraph 使用。
- Retention：保留多少 release、是否保留最近 N 个 tag、是否跳过 `prod` / `stable` / digest 引用。
- Permission：namespace/repo 级授权、临时 token、跨账号共享和回收计划。
- Risk：删除镜像前必须确认运行中 workload、回滚需求、制品来源和备份。

禁止把“镜像很多”直接变成批量删除命令。正确顺序是列出候选、标注证据、确认 owner 和运行依赖，再进入 guarded cleanup。

## 和运行目标联动

| 运行目标 | 重点 |
| --- | --- |
| CCE | 先确认集群、节点、namespace、imagePullSecret、Service/Ingress/ELB 和 LTS/CES 证据。 |
| CCI | 先确认 CCI namespace、Network、Deployment/Pod、Service、EIP/ELB 暴露方式和资源规格。 |
| FunctionGraph Custom Image | 先确认 runtime 为 Custom Image，镜像地址、xrole/agency、日志和触发器。 |

## 常见问题

| 现象 | 常见原因 | 下一步 |
| --- | --- | --- |
| tag 查不到 | region、namespace、repository 或 tag 错误 | 先查 `ListNamespaces`、`ListReposDetails`、`ListRepositoryTags`。 |
| ImagePullBackOff | 私有仓库无凭证、镜像架构不匹配、tag 不存在、网络不可达 | 进入 CCE/CCI readiness，确认运行目标事件和拉取配置。 |
| 本地能 push，云上不能 pull | 本地 docker 登录不等于 CCE/CCI 拉取授权 | 检查 imagePullSecret、运行时 agency、仓库权限。 |
| 镜像越来越多 | 无 retention 或 tag 策略混乱 | 先列 tag 和历史，再规划 retention，不能直接删除。 |

## 验收

成功输出应包括：

- 镜像完整地址和 tag/digest。
- namespace、repository、tag 是否存在。
- 镜像是否适合目标运行时。
- 拉取权限和网络路径是否明确。
- 如果要部署，下一步进入 `cce-cluster-readiness.md` 或 `cci-workload-readiness.md`。
