# 华为云 ICP 官网人工核验记录

核验日期：2026-09-24（Asia/Shanghai）
发行整理日期：2026-10-26（Asia/Shanghai）

本文件是随包的人工资料记录，不是运行时数据源。分析脚本不会自动联网或发布规则；规则运行时只读取 `huawei-rules.json`。本文件直接列出 2 个核心页和 31 个省级页，共 33 个规则来源 ID，用于来源追溯。

## 核验结论

- 导航根：<https://support.huaweicloud.com/prepare-icp/icp_02_0004.html>，页面标题为“学习各地管局政策”。
- 核心行业页当前显示更新时间 `2025-12-04 GMT+08:00`。
- 各省承诺书模板页当前显示更新时间 `2026-09-16 GMT+08:00`，页面结构已从大量独立行合并为按省份分组的模板表；其中“金融/保险/拍卖/网约车/新闻”等若干行明确显示“不支持承诺书”。
- 多个省级管局页当前显示更新时间 `2026-09-22 GMT+08:00`，包括北京、河北、山西、内蒙古、上海、江苏、安徽、福建、江西、广西、海南、湖北、湖南、陕西、甘肃、青海、宁夏、重庆、四川、贵州、云南、西藏、黑龙江、吉林和辽宁。
- 广东页为 `2026-01-19`；天津、浙江、山东、河南页仍显示 `2025-11-19`；新疆显示 `2025-12-15`；浙江和海南仍没有可用的模板矩阵条目。
- ICP“最新动态”页 <https://support.huaweicloud.com/wtsnew-icp/index.html> 当前页面更新时间为 `2025/10/30 GMT+08:00`，记录了 2024 年 12 月备案流程指引优化和 2023 年 9 月 APP 备案上线等动态；该页不属于 33 个规则来源。

本次人工复核已发布到 `huawei-rules.json`：规则版本为 `2026.09.24-huawei`，包含 224 条省级源规则和 16 条省级政策规则。运行时仍只读取随包静态文件，不联网、不自动刷新规则。

## 运行匹配口径补充（2026-10-23）

- 省级模板名称明确为“`不涉及前置审批承诺书`”“`不涉及前置审批项承诺书`”或“`不涉及相关审批的承诺书`”时，按该省通用模板处理。全国明确词和复核词命中任何前置审批类别后，如果该类别没有同省专用模板且没有官网排除规则，自动关联该通用模板。
- 山西的 `山西不涉及前置审批承诺书` 属于通用模板；因此 `游戏产品`、`游戏`、`动漫游戏开发` 等仅由全国规则命中的类别，也可以使用该模板，不再显示“未提供山西游戏类对应模板”。
- 全国规则与省级规则命中同一词但类别不同时分别保留，例如省级文化规则命中 `游戏` 或 `直播`，不得删除全国 `GAME` 或 `AUDIOVISUAL` 类别；同名词只在同一类别内去重。该口径已覆盖云南、吉林、安徽、山东、新疆、江苏、青海的游戏类，以及山西、广西、河北、河南、湖南、甘肃、福建、西藏、辽宁、陕西的视听类冲突。
- 带类别限定的模板仍不跨类别使用，例如 `北京不涉及校外培训承诺书`、`四川不涉及网络文化承诺书`、`广西不涉及新闻&出版&广播承诺书` 和 `天津不涉及互联网金融承诺书`。
- 模板只在备案省份内匹配，禁止跨省借用；同名同链接的通用模板按官网规则顺序稳定去重。官网明确排除或“不支持承诺书”的规则优先，不使用通用模板覆盖排除结论。
- 吉林和四川不匹配药品和医疗器械类前置审批，包括全国明确词 `互联网药品信息服务`、`药品信息服务`，以及复核词 `药品`、`医疗器械`；两省省级医疗器械规则中的 `药` 也不参与运行匹配。
- `图书管理服务` 按全国非前置审批业务短语处理，单位名称或经营范围包含该完整短语时不使用其中的 `图书` 触发出版类；同一文本中的其他明确出版业务仍正常匹配。
- 本节是运行时模板归属和回退逻辑的补充，不改变 2026-09-24 的官网人工核验日期，也不恢复联网或自动更新功能。

## 本次规则变更

- 模板矩阵当前为 29 个省份分组、101 行（含表头）和 63 个下载链接；没有新增下载 URL，旧的细分行多数被合并为省级通用模板。
- 已按当前合并行更新模板名称和 URL，包括北京网约车/新闻、天津通用、云南/山东/吉林/安徽/新疆/青海/江苏/重庆等省的通用模板，以及四川游戏、广西新闻/出版/广播等合并模板。
- 已移除当前页面明确撤回或未提供的旧下载链接。共 11 条省级细分规则保留关键词审计、但模板数组为空：四川医疗、吉林医疗、内蒙古直播教育、内蒙古销售、陕西医疗、福建文化/网约车/新闻/出版/广播电视节目制作、广西文化；其中四川医疗和吉林医疗运行时不匹配，其余规则按现有复核逻辑处理。
- 西藏通用模板使用其页面实际 URL `1682309709816263123.docx`，不复用其他省份的通用 URL。

## 当前无承诺书行

模板页明确显示“不支持承诺书”的 7 个数据行已作为无模板省级政策写入规则，不会生成下载链接：

| 来源定位 | 省份/类型 | 处理 |
|---|---|---|
| `tables[0].rows[5]` | 北京金融 | 无模板政策，提示向主管部门及华为云确认 |
| `tables[1].rows[4]` | 天津保险 | 无模板政策，提示向主管部门及华为云确认 |
| `tables[5].rows[2]` | 山东网约车、危险化学品 | 拆为网约车和危险化学品两个无模板政策 |
| `tables[15].rows[2]` | 贵州金融 | 无模板政策，提示向主管部门及华为云确认 |
| `tables[19].rows[3]` | 河南拍卖 | 无模板政策，提示向主管部门及华为云确认 |
| `tables[21].rows[2]` | 江西网约车 | 无模板政策，提示向主管部门及华为云确认 |
| `tables[21].rows[3]` | 江西新闻 | 无模板政策，提示向主管部门及华为云确认 |

内蒙古 `直播教育 | /`（`tables[17].rows[3]`）和福建“其他通用”无下载列（`tables[24].rows[2]`）不是官网明确“不支持”，仅保留为待人工核验资料，不推断为可下载模板。

## 33 个来源

| 来源 ID | 页面更新时间（官网） | 官方 URL |
|---|---|---|
| HUAWEI-INDUSTRIES | 2025-12-04 | <https://support.huaweicloud.com/prepare-icp/zh-cn_topic_0000002085124433.html> |
| HUAWEI-PROVINCE-TEMPLATES | 2026-09-16 | <https://support.huaweicloud.com/prepare-icp/zh-cn_topic_0000001988829137.html> |
| HUAWEI-PROVINCE-BEIJING | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0007.html> |
| HUAWEI-PROVINCE-TIANJIN | 2025-11-19 | <https://support.huaweicloud.com/prepare-icp/icp_02_0008.html> |
| HUAWEI-PROVINCE-HEBEI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0009.html> |
| HUAWEI-PROVINCE-SHANXI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0010.html> |
| HUAWEI-PROVINCE-INNER-MONGOLIA | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0011.html> |
| HUAWEI-PROVINCE-SHANGHAI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0013.html> |
| HUAWEI-PROVINCE-JIANGSU | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0014.html> |
| HUAWEI-PROVINCE-ZHEJIANG | 2025-11-19 | <https://support.huaweicloud.com/prepare-icp/icp_02_0015.html> |
| HUAWEI-PROVINCE-ANHUI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0016.html> |
| HUAWEI-PROVINCE-FUJIAN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0017.html> |
| HUAWEI-PROVINCE-SHANDONG | 2025-11-19 | <https://support.huaweicloud.com/prepare-icp/icp_02_0018.html> |
| HUAWEI-PROVINCE-JIANGXI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0019.html> |
| HUAWEI-PROVINCE-GUANGDONG | 2026-01-19 | <https://support.huaweicloud.com/prepare-icp/icp_02_0021.html> |
| HUAWEI-PROVINCE-GUANGXI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0022.html> |
| HUAWEI-PROVINCE-HAINAN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0023.html> |
| HUAWEI-PROVINCE-HENAN | 2025-11-19 | <https://support.huaweicloud.com/prepare-icp/icp_02_0025.html> |
| HUAWEI-PROVINCE-HUBEI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0026.html> |
| HUAWEI-PROVINCE-HUNAN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0027.html> |
| HUAWEI-PROVINCE-SHAANXI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0029.html> |
| HUAWEI-PROVINCE-GANSU | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0030.html> |
| HUAWEI-PROVINCE-QINGHAI | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0031.html> |
| HUAWEI-PROVINCE-NINGXIA | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0032.html> |
| HUAWEI-PROVINCE-XINJIANG | 2025-12-15 | <https://support.huaweicloud.com/prepare-icp/icp_02_0033.html> |
| HUAWEI-PROVINCE-CHONGQING | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0035.html> |
| HUAWEI-PROVINCE-SICHUAN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0036.html> |
| HUAWEI-PROVINCE-GUIZHOU | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0037.html> |
| HUAWEI-PROVINCE-YUNNAN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0038.html> |
| HUAWEI-PROVINCE-TIBET | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0039.html> |
| HUAWEI-PROVINCE-HEILONGJIANG | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0041.html> |
| HUAWEI-PROVINCE-JILIN | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0042.html> |
| HUAWEI-PROVINCE-LIAONING | 2026-09-22 | <https://support.huaweicloud.com/prepare-icp/icp_02_0043.html> |

## 发行版说明

- 本发行包保留官方 URL、页面更新时间、核验结论和本地运行口径，供用户查看规则来源。
- 本发行包不包含开发测试目录和维护索引；如官网发生变更，应使用完整开发项目逐项复核、测试并重新生成发行包。
- 用户可运行 `python <技能目录>/scripts/check_preapproval.py --validate-only` 验证随包规则的结构和引用。运行时不会自动下载、覆盖或回滚规则文件。
