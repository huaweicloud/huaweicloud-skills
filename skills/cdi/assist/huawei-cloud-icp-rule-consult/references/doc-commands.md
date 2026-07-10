# ICP备案文档URL索引与命令模板

> 路由见 `catalog.yml`，事实定义见 `filing-rules.yml`，行为规则见 `SKILL.md`。

## 文档URL索引

### 是否需要备案

| 文档 | URL |
| --- | --- |
| 备案流程总入口 | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002127712329.html |
| 各地区管局备案要求 | https://support.huaweicloud.com/prepare-icp/icp_02_0005.html |

### 备案流程与材料

| 文档 | URL |
| --- | --- |
| 备案流程总入口 | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002127712329.html |
| 各地区管局备案要求 | https://support.huaweicloud.com/prepare-icp/icp_02_0005.html |
| 前置审批 | https://support.huaweicloud.com/prepare-icp/zh-cn_topic_0000002085124433.html |
| 准备可备案的服务器 | https://support.huaweicloud.com/prepare-icp/icp_02_0003.html |
| 基础信息校验 | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002127792637.html |

### 接入备案

| 文档 | URL |
| --- | --- |
| 接入备案流程 | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002581758204.html |
| 首次备案（注销后重新备案） | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002581754184.html |

### 变更备案

| 文档 | URL |
| --- | --- |
| 变更备案流程 | https://support.huaweicloud.com/pi-icp/icp_03_0007.html |

### 注销备案

| 文档 | URL |
| --- | --- |
| 注销主体 | https://support.huaweicloud.com/pi-icp/icp_03_0009.html |
| 注销互联网信息服务 | https://support.huaweicloud.com/pi-icp/icp_03_0003.html |

### 账号与主体限制

| 文档 | URL |
| --- | --- |
| 一个账号可以备案多个主体吗 | https://support.huaweicloud.com/icp_faq/icp_05_0829.html |
| 备案授权码 | https://support.huaweicloud.com/icp_faq/zh-cn_topic_0173231867.html |
| IAM备案权限 | https://support.huaweicloud.com/icprb-icp/zh-cn_topic_0000002063728361.html |
| 准备可备案的服务器 | https://support.huaweicloud.com/prepare-icp/icp_02_0003.html |

### APP备案

| 文档 | URL |
| --- | --- |
| APP特征信息及其获取方式 | https://support.huaweicloud.com/usermanual-icp/zh-cn_topic_0000002085120221.html |

### 迁移/转移备案

| 文档 | URL |
| --- | --- |
| 转移备案 | https://support.huaweicloud.com/pi-icp/icp_03_0016.html |
| 网站迁移 | https://support.huaweicloud.com/pi-icp/icp_03_0022.html |

---

## 命令模板

### web_fetcher（文档抓取，轻量HTTP）

抓取文档文本内容：

```bash
python {skill_dir}/scripts/web_fetcher.py fetch <URL> --mode text
```

抓取页面中的所有链接：

```bash
python {skill_dir}/scripts/web_fetcher.py fetch <URL> --mode links
```

抓取完整HTML：

```bash
python {skill_dir}/scripts/web_fetcher.py fetch <URL> --mode html
```

使用CSS选择器提取特定内容：

```bash
python {skill_dir}/scripts/web_fetcher.py fetch <URL> --mode text --selector ".doc-content"
```

### web_searcher（华为云文档搜索，Playwright）

搜索华为云文档：

```bash
python {skill_dir}/scripts/web_searcher.py search "ICP备案 <关键词>"
```

指定远程Chrome（可选）：

```bash
python {skill_dir}/scripts/web_searcher.py search "ICP备案 <关键词>" --remote-chrome-host http://host:port
```

### 工具选择优先级

1. **内嵌知识优先**：先查 `references/knowledge-base.md`
2. **直映射优先**：命中分类后直接 web_fetcher 抓核心文档（从上方URL索引取URL）
3. **搜索兜底**：分类不明确时才用 web_searcher

---

## Out of Scope（拒答路由）

| 类别 | 拒答原因 | 替代渠道 |
| --- | --- | --- |
| 公安备案 | 本技能仅覆盖ICP备案 | 公安备案相关流程 |
| 经营性备案 | 本技能仅覆盖非经营性ICP备案 | 对应主管部门 |
| 域名注册/DNS配置 | 非备案范畴 | 域名服务商 |
| 服务器购买/配置 | 非备案范畴 | 华为云控制台 |
| 账号实名认证 | 非备案范畴 | 华为云账号中心 |
| 价格/续费/退订 | 非备案范畴 | 华为云费用中心 |
