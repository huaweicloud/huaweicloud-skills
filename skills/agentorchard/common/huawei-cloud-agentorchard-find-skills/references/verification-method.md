# 验证方法

> 以下命令均使用 `python3`；若环境仅提供 `python`，可等价替换。

## 功能验证

### 1. 关键词搜索验证

```bash
PYTHONIOENCODING=utf-8 python3 scripts/search_skills.py -k "银行"
```

**预期结果**：
- 输出包含 "找到 X 个相关技能" 的提示
- 每个结果包含名称、描述
- 结果按评分降序排列

### 1b. 中文整句搜索验证（分词）

```bash
PYTHONIOENCODING=utf-8 python3 scripts/search_skills.py -k "帮我找一个银行对公信贷分析的skill"
```

**预期结果**：
- 自动将中文整句分词为 "银行""信贷" 等核心关键词
- 返回匹配的 skill 列表（如 "信贷风险分析skill"）
- 不再将整句当作单个关键词导致必然失败

### 2. 浏览意图验证

```bash
PYTHONIOENCODING=utf-8 python3 scripts/search_skills.py -k "华为云AI Gallery有什么skill"
```

**预期结果**：
- 输出热门 skill 列表
- 输出引导语

### 3. 无结果场景验证

```bash
PYTHONIOENCODING=utf-8 python3 scripts/search_skills.py -k "zxqwertyuiopmnbvcxzlkjasdff"
```

**预期结果**：
- 输出 "未找到与 ... 相关的技能"
- 区分「关键词未命中」与「市场无此能力」两种可能的引导

## 链接验证

从搜索结果中取一个 `show_id`，在浏览器中打开：

```
https://pangu.huaweicloud.com/gallery/asset-detail-page.html?id={show_id}
```

**预期结果**：
- 页面正常加载
- 显示对应 skill 的详细信息
