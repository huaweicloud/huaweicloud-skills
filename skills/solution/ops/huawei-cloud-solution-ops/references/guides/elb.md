# ELB Guide

ELB 任务必须区分云侧资源存在、后端 member 健康和最终协议可达。只有 listener、pool、member、健康检查和入口协议都通过，才能说负载均衡任务完成。

## hcloud-first 路径

1. 读取 `references/playbooks/elb-http-backend-readiness.md` 和 `vpc-network-readiness.md`。
2. 先用 discovery 查询 ELB、listener、pool、member、EIP/VPC 依赖。
3. 已知负载均衡 ID 后，用 `hcloud_resource_query.py --service ELB --operation ShowLoadBalancer` 读取目标状态。
4. 创建或修改 listener/pool/member 前，用 `hcloud_service_change_plan.py` 或 `hcloud_guarded_change_flow.py` 生成计划和验证命令。
5. 变更后必须确认 member `operating_status=ONLINE`，再做入口 HTTP/TCP 探测。

## SDK 补充

- 可用 SDK 补充：`ELB:ShowLoadBalancer`。
- 用途：补充 `loadbalancer_id` 类型、path 证据和请求结构。
- 不用途：不要用 SDK runner 创建 listener、pool、member 或改健康检查。

## 不要做

- 不要把 ELB `ACTIVE` 说成后端业务可用。
- 不要忽略后端 ECS 安全组、服务监听端口、member subnet 和健康检查路径。
- 不要把跨 VPC 后端当成默认修复策略。

## 删除依赖

- 先读取当前 listener、pool、member 和 health monitor 拓扑，再构造删除计划。
- member 与 health monitor 都会阻止其 pool 删除；它们是 pool 的并列依赖，不应被误写成永远固定的一条线性链。
- pool、listener 等子资源清理并回读后，才删除 load balancer；每一步都以新的 List/Show 结果为准。
- 任一步发生 transport timeout 时，先回查目标是否仍存在，禁止原样重复删除。
