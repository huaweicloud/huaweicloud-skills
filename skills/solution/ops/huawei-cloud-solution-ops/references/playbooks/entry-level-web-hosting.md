# Entry-Level Web Hosting Playbook

## 目标

面向小白用户、小企业和低预算试运行场景，先用最少复杂度完成网站上线与可验证访问，再按流量、后端、运维和成本需求升级到更重的架构。不要因为用户说“网站”就默认购买 ECS；也不要因为 agent 能生成静态页面，就覆盖用户明确指定的机器、ECS 或公网 IP。

## 适用场景

- 静态官网、落地页、作品集、活动页、独立站前台。
- 小企业希望“便宜跑起来”“先上线看看”“不要太复杂”。
- 用户在 OBS、CDN、DNS、Flexus L、轻量服务器、ECS 之间犹豫。
- Web 应用还不确定是否需要数据库、后台任务、登录态或长期运维。

## 架构选择硬规则

1. 先运行 `hcloud_scenario_router.py`，先读 `architecture_decision`，再读路由排名。
2. 用户指定机器、主机、ECS、云服务器、SSH、Nginx、Docker 或返回公网 IP 时，选择 ECS/计算实例路径；不能用 OBS 代替。
3. 用户指定 OBS/对象存储，同时又指定机器或服务端动态能力时，必须澄清，确认前不创建任何资源。
4. 购物车、订单、支付、库存、用户登录、管理后台、服务端、后端或数据库属于动态能力，不能按 OBS-only 方案执行。
5. 只有“电商/商城”但没有说明功能时，先确认是静态展示页还是真实电商系统。
6. 一般网站没有说明运行载体时，询问 OBS 静态托管、Flexus 还是 ECS；不要静默选择。
7. 架构必须依据用户原始需求确定。不能先生成静态文件，再以“产物是静态的”为由倒推 OBS。

## 选型顺序

1. 已确认纯静态、没有显式计算约束且用户接受静态托管时，优先 OBS 静态网站托管。
   - 适合纯 HTML/CSS/JS、图片、下载页、文档站。
   - 成本和运维复杂度最低。
   - 自定义域名、CNAME、匿名访问和 403/404 排障按 `obs-static-website-hosting.md` 处理。
   - 搭配 CDN/DNS/SCM 时再进入对应 playbook。
2. 需要简单后端或现成镜像时考虑 Flexus L/轻量服务器。
   - 适合低预算、小团队、简单博客、小程序后端、低并发管理后台。
   - 按 `flexus-l-readiness.md` 先做产品选型、费用确认、hcloud metadata/help 发现和 planner-only 方案。
3. 需要更强可控性、规格选择、ELB、RDS、弹性扩展或 IaC 管理时考虑 ECS。
   - 进入 `ecs-create-readiness.md`、`ecs-ssh-access-readiness.md`、`vpc-network-readiness.md`。
   - 用户明确要长期复制环境或团队协作时，再进入 Terraform router。
4. 需要公网加速、HTTPS、全球访问或域名解析时补 CDN/DNS/SCM。
   - 先有源站，再加 CDN。
   - 先验证源站直连，再验证 CDN 域名。

## 前置体检

先运行环境体检，不自动安装、不改认证：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need hcloud \
  --need obsutil \
  --pretty
```

如果用户明确要 Terraform/IaC：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need terraform \
  --pretty
python3 scripts/hcloud_terraform_context_inspect.py --pretty
python3 scripts/hcloud_terraform_router.py "低成本网站托管" --pretty
```

Terraform 只用于生成和评审可重复资产，不替代现网发现、部署后协议验收和成本边界说明；发现优先
使用 hcloud/obsutil，也允许等价 SDK/API 或 provider data source 证据。

## OBS 静态站路径

先读取 `obs-static-website-hosting.md`，再按下面流程执行。OBS 静态站不是“桶创建成功”就完成，OBS 默认域名也只能用于临时源站验证；正式上线至少要确认自定义域名、DNS 解析、匿名访问和 HTTP/浏览器行为。

1. 检查 OBS 能力和桶边界：

```bash
python3 scripts/hcloud_obs_readonly.py \
  --operation ListBuckets \
  --limit=20 \
  --pretty
```

2. 设计桶名、region、公开访问策略、静态网站索引页和错误页。
3. 写操作必须走 `hcloud_obs_change_plan.py` 或人工确认后的 obsutil 命令，不要直接在对话里拼未知 OpenAPI 形态。
4. 上传前确认本地站点目录：
   - `index.html` 存在。
   - 资源路径相对可用。
   - 没有 `.env`、私钥、真实 tfvars、后台源码密钥。
5. 上线后验收：
   - 自定义域名解析到 OBS website endpoint。
   - OBS 静态网站 endpoint 只作为源站临时验证，不能单独作为正式交付 URL。
   - 自定义域名返回 200/3xx，`Content-Type` 符合网页/资源类型。
   - 首页、关键资源、桌面端和移动端截图可用。
   - 缺失路径返回 404 或配置的 error document。
   - 如有 CDN/DNS，分别验证源站直连和 CDN 域名。

## Flexus L / 轻量服务器路径

先读取 `flexus-l-readiness.md`。Flexus L 适合作为低门槛产品选型建议，但当前本 skill 不把它伪装成成熟执行面：

- 用 `entry-level-web-hosting` route 告诉用户它是“小预算简单后端”的候选。
- 如果需要实际创建、联网、登录和部署，按 ECS/VPC/SSH/COC 的已验证路径拆解能力需求。
- 不要承诺当前 skill 已有 Flexus L 专用 submit 脚本或完整参数映射。
- 如果用户坚持 Flexus L，先通过 hcloud metadata/help 确认 service/operation，再生成 planner-only 方案。
- 创建、续费、退订都必须先确认费用、订单/资源、数据影响和验收方式。

## ECS 简单 Web 路径

1. 先路由和选择 playbook：

```bash
python3 scripts/hcloud_scenario_router.py \
  "低成本网站，需要简单后端服务" \
  --pretty
```

2. 准备 ECS 创建和登录闭环：
   - `ecs-create-readiness.md`
   - `ecs-ssh-access-readiness.md`
   - `ecs-user-data-service-readiness.md`
   - `eip-public-ip-readiness.md`
   - `coc-readiness.md`
3. 部署服务时优先使用幂等脚本或 cloud-init。
4. 如果采用 EIP 直连 ECS，并且用户已经查看并确认公网暴露方案：
   - 安全组只为网站入口创建精确 TCP `80`、`443` 规则；不要直接暴露应用开发端口。
   - 使用通用 VPC 变更计划或 guarded flow 时传 `--allow-public-web`；该参数只允许生成计划，不替代 `--confirm-submit` 和当前 plan token。
   - SSH `22` 仍限制到管理员固定 IP、办公网或 VPN CIDR。
   - 如果 ECS 位于 ELB/CDN/WAF 后面，后端规则限制到上游来源，不使用 `--allow-public-web`。
5. 验收必须包含：
   - ECS `ACTIVE`。
   - SSH 或 COC/机内命令成功。
   - 服务进程和监听端口存在。
   - 安全组规则已读回；公网只暴露确认过的精确 TCP `80/443`。
   - EIP 状态正常，并回读确认绑定到目标 ECS/port。
   - 公网 HTTP/HTTPS 协议探测成功。
   - 用户要求返回 IP 时，输出已验收的 EIP 公网地址；不能用私网 IP、OBS 域名或未绑定 EIP 代替。

## 成本和运维提示

对小白和小企业用户，最终建议里要说明：

- 哪些费用会持续产生：ECS/Flexus、EIP 带宽、EVS、OBS 存储和请求、CDN 流量、DNS/证书。
- 哪些资源可以先不买：ELB、RDS、NAT、多 AZ、复杂 Terraform remote state。
- 哪些能力后续再补：监控告警、备份、日志、CDN、证书自动续期、IaC。
- 不能仅凭“现在访问量小”省略安全组、备份和基本监控。

## 输出格式建议

给用户的方案不要只给一个产品名。至少给出：

- 推荐路径：OBS 静态站 / Flexus L / ECS。
- 用户原始约束以及最终路径是否完全满足这些约束。
- 为什么：是否需要后端、预算、运维复杂度、后续扩展。
- 本轮要做的最小步骤。
- 需要用户确认的费用、域名、region、公开访问范围。
- 验收证据：访问 URL、HTTP 状态、关键页面、日志/监控摘要。
