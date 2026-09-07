# CDN Domain Readiness Playbook

## 目标

确认 CDN 域名、源站、证书和缓存配置的云侧状态，并把 hcloud CLI region 限制显式记录下来。

## 适用场景

- 查询 CDN 域名列表和详情
- 创建或修改域名、源站、证书、缓存规则前的计划审查
- 排查 CDN 访问异常、源站回源异常或证书配置问题

## 标准检查

CDN CLI discovery 不使用普通业务 region，优先使用 registry 中的 `cn-north-1`：

```bash
python3 scripts/hcloud_resource_discovery.py --service CDN --operation ListDomains --region=cn-north-1 --limit=20 --pretty
```

有域名时：

```bash
python3 scripts/hcloud_resource_query.py --service CDN --operation ShowDomainDetail --region=cn-north-1 --param domain_name=<domain> --pretty
```

## 风险边界

- CDN 变更可能影响公网访问、证书、缓存命中和回源，默认只生成 planner。
- 修改源站、HTTPS 证书或缓存规则前，必须输出变更前后差异和回滚方式。
- 不要把 CDN 可访问性等同于源站健康；需要分别验证 CDN 入口和源站入口。

## 验收

成功时输出域名状态、源站、HTTPS 配置、缓存关键配置和 HTTP 探测结果。失败时区分域名未启用、DNS 未解析、CDN 配置异常和源站不可达。
