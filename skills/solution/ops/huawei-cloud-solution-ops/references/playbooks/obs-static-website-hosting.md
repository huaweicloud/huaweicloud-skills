# OBS Static Website Hosting Readiness

## 目标

面向官网、落地页、文档站、下载页和低成本静态站，把 OBS 静态网站托管从“桶存在”推进到“用户域名可访问、错误路径可解释、后续 CDN/DNS/证书可接入”的验收状态。

本 playbook 不把 OBS 默认域名访问当作完整上线或正式交付 URL。面向正式外部访问时，应优先使用自定义域名，并确认 DNS、备案、匿名访问、响应头和浏览器行为。华为云可能调整默认域名的网页预览限制，交付前必须核对当前[官方静态网站托管说明](https://support.huaweicloud.com/usermanual-obs/zh-cn_topic_0045829093.html)，不能只依赖 HTTP 200。

## 适用场景

- 用户要用 OBS 托管静态网站。
- 用户要把自定义域名绑定到 OBS 静态网站 endpoint。
- 用户遇到 OBS 网站访问 403、404、CNAME 或 endpoint 混用问题。
- 用户在 OBS 静态站、CDN、DNS、SCM 之间需要一条低成本上线链路。

## 不适用场景

- 用户明确要求部署到机器、主机、ECS、云服务器、SSH、Nginx 或 Docker。
- 用户要求返回租户计算实例的公网 IP。
- 站点需要购物车、订单、支付、库存、用户登录、管理后台、后端、服务端进程、数据库、长连接或后台任务。

遇到以上任一项，返回 `entry-level-web-hosting.md` 或 `web-application-production-readiness.md` 做计算路径选型；不能因为当前页面文件是静态的就继续 OBS。

## 必须先确认

| 项 | 说明 |
| --- | --- |
| region | OBS 桶创建后 region 不可变，必须提前确认。 |
| bucket name | 全局唯一；3-63 字符；小写字母、数字、`-`、`.`；不能像 IP；不能首尾为 `-` 或 `.`。 |
| custom domain | 正式上线必填或明确记录为未完成；国内访问还要提醒备案状态。OBS 默认域名只用于临时源站验证。 |
| index document | 默认 `index.html`，必须确认对象已上传到正确路径。 |
| error document | 可选；没有时缺失路径通常表现为 404。 |
| public read boundary | 静态站需要匿名访问网站对象，但不能把管理权限或写权限公开。 |
| DNS ownership | 确认域名 DNS 是否在华为云 DNS，还是外部 DNS。 |

## 备案与许可问题的证据边界

备案、公安备案和经营性许可具有地域、主体、业务和时间条件。本 playbook 只定义回答方法，不保存静态规则、材料数量、时限、价格或联系电话。

回答前至少确认：

- 服务实际部署位置，尤其是否涉及中国大陆；
- 对象是网站、App、小程序还是其他互联网服务；
- 用户问的是首次备案、接入、变更、注销，还是既有备案迁移；
- 主体类型、所在省份、现有备案及当前接入服务商；
- 查询日期和当前官方证据来源。

结论必须组织成“**规则 × 适用范围 × 当前官方证据**”：

1. 先写适用条件，再写条件成立时的结论。
2. 分开 ICP 备案、公安备案和经营性许可，不把三者合成一个“备案完成”状态。
3. 当前官方来源之间冲突、来源过旧或适用范围不清时，标记 `evidence_gap`，说明需要用户确认的主管部门/服务商范围。
4. 本地历史知识、旧案例和固定数字只能作为待核验线索，不能作为最终事实。
5. 备案或许可状态只是网站上线链中的一层；OBS、DNS、HTTPS、匿名访问和 HTTP 验收仍需分别完成。

## hcloud / obsutil 边界

OBS 不走普通 OpenAPI-style `hcloud OBS <Operation>` 命令。默认按 `obs-boundary.md`：

- 只读：`scripts/hcloud_obs_readonly.py`
- 写类规划：`scripts/hcloud_obs_change_plan.py`
- 真实对象上传、桶属性、网站托管和自定义域名能力优先通过 `hcloud obs` / obsutil；其覆盖或解析存在
  实际障碍时，可使用已验证的官方 SDK/API 路径。

不要在未确认 obsutil 配置和 endpoint 前直接生成写命令。

## 推荐流程

1. 环境体检：

```bash
python3 scripts/hcloud_environment_doctor.py \
  --need hcloud \
  --need obsutil \
  --pretty
```

2. 查询 OBS 当前状态：

```bash
python3 scripts/hcloud_obs_readonly.py \
  --operation ListBuckets \
  --limit=20 \
  --pretty
```

3. 如果桶已存在，查询桶属性：

```bash
python3 scripts/hcloud_obs_readonly.py \
  --operation StatBucket \
  --bucket "<bucket_name>" \
  --pretty
```

4. 如果需要新建桶，只生成 planner：

```bash
python3 scripts/hcloud_obs_change_plan.py \
  --operation CreateBucket \
  --bucket "<bucket_name>" \
  --endpoint "<obs_endpoint>" \
  --pretty
```

5. 明确静态网站配置：
   - index document，例如 `index.html`
   - error document，例如 `error.html`
   - bucket website endpoint，而不是普通 OBS API endpoint
   - 自定义域名的 CNAME target
   - 默认域名只承担临时源站探测，不作为正式用户入口

6. DNS 接入：
   - 如果 DNS 在华为云，按 `dns-zone-record-readiness.md` 规划 CNAME。
   - 如果 DNS 在外部，给用户输出 record type、host/name、target/value、TTL 和验证命令。
   - 不把“已提供 CNAME 值”说成“DNS 已生效”。

7. 验收：
   - 自定义域名解析到 OBS website endpoint。
   - 首页返回 HTTP 200 或合理的 3xx。
   - 首页 `Content-Type` 是预期网页类型，并检查是否存在导致下载而不是展示的响应头或浏览器行为。
   - 缺失路径返回 404 或配置的 error document。
   - 关键 CSS/JS/图片路径不返回 403/404。
   - 使用真实浏览器验证桌面端和移动端渲染，而不是只执行 `curl -I`。
   - 如接入 CDN，分别验证源站直连和 CDN 域名。

## 403 / 404 排障

| 现象 | 常见原因 | 下一步 |
| --- | --- | --- |
| 403 | 对象未公开读、bucket policy 不允许匿名访问、访问了 API endpoint、AK/SK 权限不足 | 先确认是否匿名访问网站对象，再区分网站 endpoint 和 API endpoint。 |
| 404 | index document 名称不对、对象路径不对、上传目录多了一层、error document 未配置 | 查询对象路径，确认首页实际 key。 |
| CNAME 生效但打不开 | CNAME target 指向普通 OBS 域名或 DNS 未传播 | 用 `dig` / `nslookup` 查解析结果，确认 target 是 website endpoint。 |
| 默认域名可访问，自定义域名不可访问 | DNS 未配置、未在 OBS 绑定自定义域名、备案/证书边界未满足 | 分开验证 OBS 绑定和 DNS 解析。 |
| 默认域名返回 200 但浏览器下载文件 | 默认域名网页预览限制或响应头不适合页面展示 | 核对当前官方限制并改用已绑定的自定义域名，不能把默认域名作为完成证据。 |

## 安全和成本提示

- 不要建议 `public-read-write`。
- 不要把 AK/SK、token、`.obsutilconfig` 内容贴到对话中。
- 上传目录前先排除 `.env`、私钥、真实 `terraform.tfvars`、数据库 dump、证书私钥。
- 成本主要来自存储、请求、外网流量、CDN 流量和域名/证书相关费用。
- 静态站不需要 ECS、ELB、RDS，除非用户明确需要后端服务。

## 输出给用户时

至少说明：

- 为什么推荐 OBS 静态站，或为什么不适合。
- 明确说明 OBS 不提供用户所期待的 ECS 公网 IP；用户要求返回 IP 时应改走 ECS + EIP。
- 还缺哪些事实：region、bucket、domain、DNS 归属、备案、index document。
- 涉及备案时，说明适用条件、当前官方证据日期和仍需确认的范围；不要输出无条件的全国统一结论。
- 下一步只读命令或 planner。
- 验收证据：正式自定义域名、DNS 解析、HTTP 状态、响应头、浏览器渲染、首页和缺失路径行为。OBS 默认域名只能列为临时源站证据。
