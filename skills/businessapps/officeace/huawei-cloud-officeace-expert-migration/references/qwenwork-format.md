# 千问办公（QwenWork / QwenWorkCN）套件格式

安装位置：`~/.qwenworkcn/plugins/<name>/`（官方/市场）、`~/.qwenworkcn/plugins-custom/<name>/`（自建）
运行数据：`%APPDATA%/QwenWorkCN`（Electron 主目录）

## 目录结构

```
<name>/
├── .qwenwork-plugin/plugin.json    # 新格式清单（优先）
├── .qoder-plugin/plugin.json       # 旧格式清单（兼容保留，二选一，禁止并存合并）
├── .mcp.json                       # 可选：需 guided-setup 的第三方 MCP
├── CONNECTORS.md                   # 有外部工具时必备：品类 → 工具映射
├── README.md                       # 面向用户的说明（目标角色/快速命令/技能表/连接器表）
└── skills/
    └── <skill>/
        ├── SKILL.md                # 双语 frontmatter + 中文正文
        ├── references/             # 知识库
        ├── scripts/                # 可执行脚本
        └── templates/              # 输出模板
```

三种清单的优先级：`.qwenwork-plugin` > `.qoder-plugin` > `.claude-plugin`。并存时只认优先级最高的一个，另一个不得被合并。

## plugin.json

```json
{
  "name": "solution-presales",
  "displayName": "Solution Presales",
  "displayNameEn": "Solution Presales",
  "displayNameCn": "售前解决方案专家",
  "version": "1.0.0",
  "description": "English description",
  "descriptionEn": "English description",
  "descriptionZh": "中文描述",
  "author": { "name": "Custom" },
  "category": "sales",
  "tags": ["presales", "pricing"],
  "skills": ["skills/discovery-brief", "skills/pricing-model"]
}
```

要点：

- `name` 必须 ASCII kebab-case，与目录名一致。
- 中英双语元数据是强制的：`displayName`（英文兼容默认）+ `displayNameEn` + `displayNameCn`；`description` + `descriptionEn` + `descriptionZh`。
- `skills` 是**相对路径数组**，不带尾部斜杠。
- 自建套件 `author.name` 用 `Custom`；从内置套件改出来的加 `customizedFrom: "<原套件 displayName>"`。

## SKILL.md frontmatter

```yaml
---
name: pricing-model
version: 1.0.0
description: "English description"
name_en: Pricing Model
name_zh: 报价测算
description_en: "English description"
description_zh: "中文描述"
argument-hint: "给出方案范围与人天估算"
---
```

约定：

- `name` ASCII kebab-case；`name_zh` 是中文显示名（可含斜杠命令语义，如 `/报价测算`）。
- `description_zh` 决定中文环境下的路由判断，要写「何时用 + 覆盖什么 + 触发词」，不写功能罗列。
- `argument-hint` 是输入提示，出现在技能调用处。
- 正文中文（中文应用），可含 `## 何时用 / ## 铁律 / ## 执行流程 / ## 输出规范 / ## 交付前自检 / ## 连接器可用时的增强` 等段落。

## 连接器机制

- `.mcp.json` 只放**需要用户自己填凭据**的第三方服务，且用 `guided-setup` 类型：

```json
{ "mcpServers": { "钉钉文档": { "type": "guided-setup",
  "_setup": { "url": "https://<连接器服务地址>/#/mcp",
              "description": "English steps", "descriptionZh": "中文步骤" } } } }
```

- 产品内置/市场连接器**不写进** `.mcp.json`，只在 `CONNECTORS.md` 里列为「去设置页开启」。
- 禁止写死个人 MCP URL、禁止 marker-only 声明（运行时会当真实配置加载，加载失败）。

## 生效方式

放对目录后由应用扫描；容器/应用重启后出现在插件页。技能用 `@` 或 `/` 唤起。

## 迁移到 OfficeAce 时的注意点

| 点 | 处理 |
|---|---|
| 双描述 | 取 `description_zh` 作 OfficeAce 技能 `description` |
| `name_zh` | 用于补技能 H1（源正文缺 H1 时） |
| `version` + `name_en` + `argument-hint` | 丢弃（OfficeAce 不识别） |
| `.mcp.json` | 丢弃，内容转成技能里的降级说明 |
| `CONNECTORS.md` | 不迁文件，其信息应在技能「连接器增强」段已存在 |
| 无入口 agent | 需合成 persona 技能，并标注待复核 |
