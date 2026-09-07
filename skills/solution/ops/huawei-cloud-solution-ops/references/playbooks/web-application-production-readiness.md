# Web Application Production Readiness Playbook

## 目标

把“Web 应用能上线”拆成租户能理解、能验收的闭环：计算承载、数据库、网络入口、域名 HTTPS、安全防护、可观测、备份和成本边界都要有证据。不要只完成某一个云资源的创建就宣布上线成功。

## 适用场景

- 企业官网、后台系统、API 服务、SaaS 原型或小型业务系统上线
- 用户同时提到 ECS/Flexus、ELB、RDS、域名、HTTPS、CDN、WAF、监控或备份
- 已有资源需要接入公网入口、数据库或 HTTPS
- 从单机部署升级到带负载均衡、数据库和域名的更完整架构

## 总原则

- `hcloud` 是主路径：先查现网、生成计划、执行前确认、执行后读回验证。
- SDK 可补充 `hcloud` 不容易覆盖的连接探测、特定接口或脚本化校验；遇到复杂类型化处理或 hcloud
  实际覆盖/解析障碍时，也可以作为当前任务后端。
- Terraform 只用于长期纳管、可重复环境和 plan review；不要为了第一次上线强行引入 IaC。
- 面向用户输出“可访问、可回滚、可观测、可计费”的结果，不要只输出资源 ID。

## 标准闭环

### 1. 先定部署形态

先把用户目标归入一个简单路径：

- 用户明确指定机器、ECS、云服务器、公网 IP、SSH、Nginx 或 Docker：保留该计算约束，不能用 OBS 替换。
- 纯静态内容、没有显式计算约束且用户接受静态托管：优先 OBS 静态网站托管 + DNS/CDN/SCM。
- 轻量动态站点：Flexus L 或单台 ECS，确认备份和公网入口。
- 生产 Web/API：ECS/CCE/CCI + ELB + RDS + DNS/SCM，按本文继续。
- 需要边缘缓存或源站保护：CDN/WAF 放在入口链路前面。

购物车、订单、支付、库存、用户登录、管理后台、服务端、后端或数据库都属于动态能力，不能进入 OBS-only 路径。只有“电商/商城”而没有说明功能时，先确认是静态展示页还是真实电商系统。

不要把所有小网站都默认做成多服务高可用架构；也不要把明确生产目标降级成只开一台机器。架构选择必须基于用户原始需求，不能根据 agent 后来生成的静态文件反向推断。

### 2. 计算和应用进程

先确认应用在哪里运行：

```bash
python3 scripts/hcloud_resource_discovery.py --service ECS --operation ListServersDetails --pretty
```

需要创建或修复 ECS 时进入：

- `references/playbooks/ecs-create-readiness.md`
- `references/playbooks/ecs-ssh-access-readiness.md`
- `references/playbooks/ecs-user-data-service-readiness.md`
- `references/playbooks/coc-readiness.md`

验收不能只看 ECS `ACTIVE`，还要确认应用端口在机器内监听，并能从预期网络来源访问。

### 3. 数据库和连接

RDS 就绪和应用能连上数据库是两件事。先查实例和网络绑定：

```bash
python3 scripts/hcloud_resource_discovery.py --service RDS --operation ListInstances --pretty
```

需要输出这些证据：

- RDS 实例状态、引擎、版本、规格、存储
- VPC、子网、安全组、内网地址和端口
- 备份保留策略和维护窗口
- 应用侧只读连接探测，例如 `SELECT 1`

安全组放通要按来源收敛，不能为了连接数据库直接全网开放数据库端口。

### 4. 网络入口和负载均衡

公网入口优先明确用户选择：

- 单机临时入口：EIP 直连 ECS，适合低风险测试或小型场景。
- 正式 HTTP/HTTPS 入口：ELB listener + pool + member + health monitor。
- CDN/WAF 入口：需要区分用户访问域名、CDN/WAF、源站 ELB/ECS 三层证据。

ELB 路径先看：

- `references/playbooks/elb-http-backend-readiness.md`
- `references/playbooks/vpc-network-readiness.md`
- `references/playbooks/eip-public-ip-readiness.md`

上线验收至少要有：

- ELB、listener、pool、member ID
- member `ONLINE`
- health monitor 配置
- 从入口地址发起的 HTTP/HTTPS 探测结果

### 5. 域名、HTTPS、CDN 和 WAF

域名入口要分层验证：

1. DNS record 是否指向预期 CNAME/IP。
2. SCM 证书是否匹配域名、未过期、已部署到目标服务。
3. CDN/WAF 是否在线，源站配置是否指向正确 ELB/ECS/OBS。
4. 真实访问域名的 HTTP 状态、TLS 证书和重定向行为是否符合预期。

优先进入这些 playbook：

- `references/playbooks/dns-zone-record-readiness.md`
- `references/playbooks/scm-certificate-readiness.md`
- `references/playbooks/cdn-domain-readiness.md`
- `references/playbooks/waf-policy-readiness.md`

不要把“证书存在”当作 HTTPS 已生效；必须从用户访问域名做协议探测。

### 6. 可观测、备份和成本

上线完成前至少输出：

- CES 指标或告警计划：ECS CPU/内存/磁盘、ELB、RDS、EIP 带宽
- LTS 日志入口：应用日志、访问日志或函数/容器日志
- CTS 审计线索：关键变更能追溯
- CBR/RDS 备份姿态：备份开启、保留期、恢复点说明
- 成本边界：EIP、ELB、CDN 流量、RDS、EVS、带宽计费项

可参考：

- `references/playbooks/observability-readiness.md`
- `references/playbooks/billing-cost-governance.md`
- `references/playbooks/cbr-backup-posture.md`
- `references/playbooks/cts-audit-readiness.md`

## 变更边界

以下动作不应自动执行，必须先给计划并取得用户明确确认：

- 创建、删除或替换 ECS、ELB、RDS、WAF/CDN 配置
- 修改安全组入方向规则
- 修改 DNS 记录、证书部署、CDN 源站或 WAF 策略
- RDS 参数变更、规格变更、重启、账号密码变更
- Terraform import/apply/destroy 或 state 操作

## 最终输出

成功时输出一份上线验收摘要：

- 访问入口：域名、协议、HTTP 状态、TLS 证书结论
- 计算：实例或工作负载状态、应用端口和进程探测
- 数据库：实例状态、连接探测、备份姿态
- 网络：VPC/子网/安全组、ELB member 健康、EIP/CDN/WAF 状态
- 可观测：关键指标、日志、告警或缺口
- 成本和风险：主要计费项、未完成事项和下一步最小动作

失败时不要说“已上线”。输出当前通过的证据、卡住的层级和下一条最小排查命令。
