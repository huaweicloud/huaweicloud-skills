# Huawei OBS CDN DNS Stack Example

这个示例把 OBS 静态网站、CDN 加速域名和 DNS CNAME 记录放在一个受控链路里。

设计取舍：
- 不读取本地证书私钥，不默认启用 HTTPS 证书配置。
- CDN CNAME 目标由用户在 CDN 创建后通过 hcloud/CDN 控制台确认，再显式填入 `cdn_cname_target`。
- DNS zone/record 默认关闭，避免误改生产域名。

推荐流程：
1. 先用 hcloud 确认 bucket 命名、CDN 域名归属、DNS zone 和备案/域名状态。
2. 首次 plan 可以只创建 OBS + CDN。
3. CDN 返回 CNAME 目标后，再打开 `create_dns_record` 并填写 `cdn_cname_target`。
4. apply 后验证 OBS website endpoint、CDN 域名状态、DNS 解析和 HTTP 可访问性。
