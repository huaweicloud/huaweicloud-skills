# Live Regression Runbook

## 目标

用真实华为云账号验证 huawei-cloud-solution-ops 的核心上云、用云、管云场景。默认只生成回归计划；真实执行需要用户提供隔离测试账号、region、profile、资源 ID 和每个高风险步骤的确认。

## 生成回归计划

```bash
python3 scripts/hcloud_live_regression_plan.py --pretty
```

只看某个场景：

```bash
python3 scripts/hcloud_live_regression_plan.py \
  --scenario terraform-operations \
  --scenario cce-assessment \
  --region cn-north-4 \
  --profile <profile-name> \
  --pretty
```

## 服务级 live validation

在跑真实账号回归前，先用服务级 profile 列出高频服务的资源 ID、读回命令、probe 和晋级缺口：

```bash
python3 scripts/hcloud_live_validation_plan.py \
  --service ECS \
  --service VPC \
  --service EIP \
  --region cn-north-4 \
  --profile <profile-name> \
  --param server_id=<server-id> \
  --param publicip_id=<publicip-id> \
  --param probe_url=https://example.com/health \
  --pretty
```

这个命令只规划证据，不执行 `hcloud` 和网络 probe。真实采证仍然要通过 `hcloud_service_readiness.py --execute`、`hcloud_acceptance_closure.py` 或人工记录完成。执行 probe 时，公网入口可以直接按 evidence plan 跑；内网、loopback 或 `.local` 目标必须先确认属于租户验收路径，再加 `--allow-private-targets`。

## 需要用户协助

- 准备非生产账号或隔离项目。
- 本地配置 hcloud profile 或环境变量；不要把 AK/SK 发到对话里。
- 提供测试资源 ID、测试域名、测试 bucket、测试 cluster ID 等。
- 明确是否允许产生费用，例如 EIP、ELB、ECS、RDS、CCE、CDN。
- 明确是否允许 Terraform state-changing 操作，例如 `terraform import`。

## 证据保存规则

- 保存命令形态、状态码、资源 ID、状态 bucket 和脱敏摘要。
- 不保存 AK/SK、MaaS API Key、kubeconfig、token、私钥、数据库密码、Terraform state、完整账单明细。
- 失败项按 network、permission、region、quota、parameter、not_found、service_error 分类。

## 推荐回归顺序

1. Environment and credential readiness
2. ECS/VPC/EIP/OBS/ELB/RDS live validation profile
3. OBS static website and DNS/CDN handoff
4. Production Web/API closure
5. ECS/CES monitoring troubleshooting
6. EIP idle and cost governance
7. SWR to CCI/CCE container deployment readiness
8. FunctionGraph trigger/log readiness
9. CCE cloud-native assessment
10. MaaS usage governance
11. Terraform import/drift/remote state closure

## 完成标准

每个场景至少输出：

- 使用的 region/profile
- 执行的 planner 或 probe
- 通过、警告、缺失、阻塞的证据数
- 用户批准过的高风险动作
- 剩余缺口和下一步最小动作
