# CCI Workload Readiness Playbook

## 目标

帮助用户用云容器实例 CCI 部署或排查容器应用前，先确认 namespace、Network、镜像、Deployment/Pod、Service、公网入口、日志和监控证据。CCI 类 Kubernetes API 看起来像普通 K8s，但它没有用户自管节点，网络和规格限制必须前置确认。

## 适用场景

- 用户说要“无服务器容器”“云容器实例”“不用买服务器跑容器”。
- 用户要把 SWR 镜像部署到 CCI。
- 用户要查询 CCI Pod/Deployment/Service 状态。
- 用户遇到 CCI 镜像拉取失败、Service 暴露失败、Pod 不 Ready、日志查不到。

## 推荐入口：先生成前置检查与验收计划

先使用 CCI 专用 planner 收集输入和生成只读证据命令。它不会执行任何云资源变更；Windows 请将命令中的 `python3` 替换为当前 Python 环境的 `python`。

```bash
python3 scripts/hcloud_cci_workload_plan.py \
  --namespace <namespace> \
  --namespace-flavor general-computing \
  --vpc-id <vpc-id> \
  --subnet-id <subnet-id> \
  --neutron-network-id <neutron-network-id> \
  --subnet-cidr <subnet-cidr> \
  --security-group-id <security-group-id> \
  --network-name <network-name> \
  --workload-name <workload-name> \
  --image <image:tag-or-digest> \
  --cpu-request <cpu> --cpu-limit <same-cpu> \
  --memory-request <memory> --memory-limit <same-memory> \
  --service-name <service-name> \
  --region <region> \
  --pretty
```

planner 输出按依赖顺序组织证据：namespace → Network → quota/events → workload → Pod → Service → 协议探测。它只生成 `hcloud_resource_query.py` 的计划命令，不会自动运行命令。`readiness=ready_to_review` 也不等于变更授权。

## 标准只读检查

1. 查询 CCI namespace：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service CCI \
  --operation listNamespaces \
  --region=<region> \
  --pretty
```

2. 查询 namespace 下的 Network：

```bash
python3 scripts/hcloud_resource_query.py \
  --service CCI \
  --operation listNamespacedNetworks \
  --region=<region> \
  --param namespace=<namespace> \
  --pretty
```

3. 查询 Deployment、Pod、Service：

```bash
python3 scripts/hcloud_resource_query.py \
  --service CCI \
  --operation listNamespacedDeployments \
  --region=<region> \
  --param namespace=<namespace> \
  --pretty
```

```bash
python3 scripts/hcloud_resource_query.py \
  --service CCI \
  --operation listNamespacedPods \
  --region=<region> \
  --param namespace=<namespace> \
  --pretty
```

```bash
python3 scripts/hcloud_resource_query.py \
  --service CCI \
  --operation listNamespacedServices \
  --region=<region> \
  --param namespace=<namespace> \
  --pretty
```

4. 如需确认镜像，先进入 `swr-image-readiness.md`。

## 已知 CLI 阻塞与只读降级

### 包含点号的 annotation key

CCI Network 等对象可能依赖包含点号的 annotation key。某些 hcloud 版本中，普通嵌套参数或 `--cli-jsonInput` 的 dry-run 看起来保留了该 key，但真实请求可能把它拆成错误层级或直接遗漏。

遇到这类对象时按以下证据顺序判断：

1. 记录当前 hcloud 版本和 operation shape。
2. 检查 dry-run 或请求摘要里的 annotation，而不是只看命令退出码。
3. 创建后必须回读对象，确认完整 key 和 value 真实存在。
4. 升级 hcloud 后重新验证，不能把一次复现写成所有版本的长期事实。

如果 dry-run 有值、真实回读却缺少 annotation，只能报告“当前版本相关的 CLI 序列化阻塞”，并停止后续 workload 创建。不要据此宣称 CCI API 不支持，也不要自动切换到 Python、裸 HTTP、SDK 或 kubectl 写入旁路。

### Pod exec 不可用时

Pod exec 依赖交互式 WebSocket，批处理环境或当前 hcloud 入口可能无法稳定建立会话。exec 失败不等于容器故障；此时先降级到只读证据：

1. workload / Pod status 和 container state；
2. events、restart count 和 termination reason；
3. 有限时间窗的 stdout/stderr 或 LTS 日志；
4. Service/Ingress 状态和外部协议探测。

只有这些证据仍不足，并且用户明确确认交互访问时，才考虑受控 exec。日志可读也不等于应用健康，仍需 Service/Ingress 或协议证据。

## 创建或更新前检查

CCI 的 namespace、Network、Deployment、Service、Secret、Ingress、EIPPool 创建/更新都是写操作。生成计划前必须确认：

- region / project / enterprise project。
- namespace 名称、用途和规格类型（通用算力或 GPU）。
- Network 先于工作负载存在，并绑定正确的 VPC、subnet、`neutronNetwork` 和安全组。
- subnet CIDR 不得与 CCI 保留网段 `10.247.0.0/16` 重叠。
- 镜像地址、tag/digest、拉取凭证。
- CPU、内存、GPU、临时存储、环境变量、Secret/ConfigMap；CCI 的 CPU/内存 request 和 limit 必须一致。
- 副本数、健康检查、端口、Service 类型。
- 是否需要 EIP、ELB、DNS、HTTPS、访问源限制。
- 日志是否进入 LTS，指标是否进入 CES。
- 费用和释放策略。

## 风险边界

- 不自动创建 Deployment、Service、Secret、Network 或 EIPPool。
- 不生成 namespace、Network、工作负载或 EIPPool 的删除命令；namespace 删除必须先盘点其下资源、确认备份/回滚与依赖，并在独立受控流程中二次确认。
- 不在最终输出里展示镜像拉取密码、token、Secret value。
- 不把 Pod Running 当成业务可用；必须补协议探测或 Service/Ingress 访问证据。
- 不建议直接创建裸 Pod 承载长期服务；优先 Deployment/Job/StatefulSet，按用户目标选择。
- EIP/ELB 公网暴露必须提供业务理由和受限来源 CIDR；不接受 `0.0.0.0/0` 作为 planner 的通过条件。
- 变更前先用 planner 或 Terraform route，真实执行必须二次确认。

## 常见问题

| 现象 | 常见原因 | 下一步 |
| --- | --- | --- |
| Pod Pending | namespace 网络未就绪、规格不可用、配额不足 | 查 namespace/network/events，再确认资源规格。 |
| ImagePullBackOff | SWR tag 不存在、私有仓库无权限、镜像架构不匹配 | 进入 `swr-image-readiness.md`。 |
| Service 没公网入口 | Service 类型、EIP/ELB、Network 或安全组未配置 | 进入 `eip-public-ip-readiness.md` 和 `vpc-network-readiness.md`。 |
| 无日志 | 应用未输出 stdout/stderr，或 LTS 未配置 | 进入 `lts-log-readiness.md`。 |
| 健康检查失败 | 端口、路径、启动时间或协议不匹配 | 先读 Pod/Service 状态，再生成 probe 计划。 |
| dry-run 有 annotation、回读却缺失 | 当前 hcloud 版本可能错误序列化包含点号的 key | 记录版本和请求/回读差异，停止 workload 创建，不自动切换执行器。 |
| Pod exec 失败 | WebSocket/交互通道不可用，或权限/网络失败 | 先查 status、events、container state 和有限日志；不要直接判容器故障。 |

## 验收

CCI 应用可用至少需要：

- namespace 和 Network 已存在且绑定到正确 VPC/subnet。
- Deployment/Pod 状态、重启次数、事件清楚。
- 镜像 tag/digest 可追溯。
- Service/Ingress/EIP/ELB/DNS 路径清楚。
- 日志、指标、访问探测至少有一种可验证证据。
- 如果是生产服务，还要有回滚镜像、资源上限、成本和清理策略。
