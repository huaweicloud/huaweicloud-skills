# OBS Guide

OBS 不走普通 `hcloud <Service> <Operation>` 形态，而是走 `hcloud obs`/obsutil。普通 OpenAPI 风格脚本不应直接生成 `hcloud OBS Operation`。

## hcloud-first 路径

1. 读取 `references/playbooks/obs-boundary.md`；静态站资产场景再读 `static-site-generated-assets-readiness.md`。
2. 用 `hcloud_obs_readonly.py` 做 bucket 列表、bucket stat、lifecycle、policy 等只读查询计划或显式查询。
3. bucket/lifecycle/policy 变更只用 `hcloud_obs_change_plan.py` 生成 planner-only 命令和验证建议。
4. 静态站图片资产如需生成，读取 `references/maas-image-generation.md`，只用华为云 ModelArts MaaS 作为资产生成入口。
5. 对公网静态站，继续验证自定义域名、CDN/DNS/HTTPS、响应头、浏览器渲染和缓存刷新状态；OBS 默认域名只能作为临时源站证据。

## SDK 补充

- 当前不登记 OBS SDK runner。
- OBS 的补充方向应先解决 obsutil 输出解析和 hcloud obs 错误分桶，而不是新增通用 SDK 执行面。

## 不要做

- 不要用普通 `hcloud_resource_query.py` 生成 OBS OpenAPI 风格命令。
- 不要用 OBS 替代用户明确指定的机器/ECS，也不要把 OBS 默认域名或普通 API endpoint 当作正式站点交付。
- 不要输出 bucket policy 中的敏感主体或临时凭证。
- 不要把图片生成失败自动降级到非华为云图像 API。
