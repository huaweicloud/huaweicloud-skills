# SCM Certificate Readiness Playbook

## 目标

确认证书列表、证书详情和部署目标，避免把证书申请、推送和删除当作普通低风险变更。

## 适用场景

- 查询证书清单和详情
- 为 CDN、ELB、WAF 等服务选择证书
- 申请、推送或删除证书前的计划审查

## 标准检查

```bash
python3 scripts/hcloud_resource_discovery.py --service SCM --operation ListCertificates --pretty
```

有证书 ID 时：

```bash
python3 scripts/hcloud_resource_query.py --service SCM --operation ShowCertificate --param certificate_id=<certificate-id> --pretty
```

## 风险边界

- 证书私钥、CSR 私钥和 token 输出必须脱敏。
- Apply/Push/Delete 证书默认 planner-only，并要求人工确认目标域名、服务、证书有效期和回滚路径。
- 不要把证书状态正常等同于目标服务已经启用证书；部署目标需要单独验证。

## 验收

成功时输出证书 ID、域名、状态、有效期、算法、部署目标和后续 HTTPS 探测结论。失败时区分证书未签发、域名不匹配、过期、未部署和目标服务配置未生效。
