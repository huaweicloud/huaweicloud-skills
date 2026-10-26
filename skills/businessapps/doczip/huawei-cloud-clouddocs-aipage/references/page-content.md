# page 内容规范（markdown 生成 + JSON block 兜底）

`clouddocs-cli page +create --content <c>` 的 content 接受**纯 Markdown 文本**（与 page-cli 同后端契约一致），模型生成 markdown 直传即可。仅当后端明确拒绝 markdown（报内容格式错误）时才考虑本页底部的 block JSON 兜底。

## 一、markdown 生成规范（主路径）

模型按用户描述生成 markdown，直接落 `<项目工作目录>/drafts/page.md`（drafts 一律建在当前项目工作目录下，禁止写入技能目录；规则见 `SKILL.md`「草稿目录约定」）或作为 `--content` 传入。规则：

1. **首行是文档标题**：`# <标题>`，与 `--title` 一致。
2. **标题层级**：`##` 起做章节，`###` 起做小节；层级从 1 递增，禁止跳级（`##` 后直接 `####`）。
3. **正文**：用 `paragraph` 对应段落文本；一个自然段一行，段落间空一行。
4. **列表**：无序用 `-`，有序用 `1.`；列表项之间不空行；嵌套列表用 2 空格缩进。
5. **表格**：`| 列1 | 列2 |` 首行 + `|---|---|` 分隔行 + 数据行。
6. **代码块**：` ```语言 ` 围栏；代码块内不再嵌套 markdown 标记。
7. **行内强调**：`**加粗**`、`*斜体*`、`` `行内代码` ``。
8. **图片/链接**：链接写 `[文字](url)`；图片写 `![alt](url)`（外链图床需确保可访问）。
9. **禁止连续重复空行**：正文中不允许出现两个及以上连续 `\n`。
10. **禁止 markdown 代码块标记混入 JSON 输出**：content 是纯文本，不要包裹 ``` ``` ```。
11. **内容完整性**：覆盖用户描述的全部要点，段落化组织；不编造用户未提供的数据。

### 示例

```markdown
# 云文档产品分析

## 一、市场背景

云文档是面向企业协作的在线文档服务，支持多人实时协同编辑。

## 二、核心能力

- 多人实时协同编辑
- 版本历史与回溯
- 分享与权限管理

| 能力 | 说明 |
|---|---|
| 协同编辑 | 毫秒级同步 |
| 版本管理 | 全量历史回溯 |

## 三、技术架构

采用前后端分离架构，编辑链路基于 ProseMirror：

```js
const doc = editor.document;
doc.appendChild(block);
```
```

## 二、block JSON 兜底（仅当后端拒绝 markdown）

若 `page +create --content <markdown>` 报"内容格式错误"，改为传 **JSON 文档结构**（对象数组，每个元素是一个 block）。与浏览器 SDK 的文档树一致：

```json
[
  {"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "文档标题"}]},
  {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "章节标题"}]},
  {"type": "paragraph", "content": [{"type": "text", "text": "正文段落"}]},
  {"type": "bulletList", "content": [
    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "列表项"}]}]}
  ]}
]
```

要点：

- block 的 `type` 与 `content`（子节点数组）遵循编辑器文档树；`text` 节点必须非空。
- 标题 `level` 取 1~6；正文用 `paragraph`。
- 列表用 `bulletList`/`orderedList` + `listItem`，`listItemV2` 必须扁平排列，禁止嵌套 `listItemV2`。
- 优先整篇 JSON 一次传入；长度超过 CLI 参数上限（约 30KB）时提示拆段或精简内容。

> 注意：CLI 帮助中出现的 `--content '{"title":"第一页"}'` / `'[{"title":"第一页"}]'` 是 **slide +create/+add** 的页面数组示例（每页一个对象），**不是** page 的 content 格式；page 的 content 是 markdown 文本或上述 block 数组，两者不要混用。
