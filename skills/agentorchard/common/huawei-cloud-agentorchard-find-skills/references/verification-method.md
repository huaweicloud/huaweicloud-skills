# 验证方法

## 功能验证

### 1. 关键词搜索验证

```bash
PYTHONIOENCODING=utf-8 python scripts/search_skills.py -k "银行"
```

**预期结果**：
- 输出包含 "找到 X 个相关技能" 的提示
- 每个结果包含名称、描述
- 结果按评分降序排列

### 2. 浏览意图验证

```bash
PYTHONIOENCODING=utf-8 python scripts/search_skills.py -k "华为云AI Gallery有什么skill"
```

**预期结果**：
- 输出热门 skill 列表
- 输出引导语

### 3. 无结果场景验证

```bash
PYTHONIOENCODING=utf-8 python scripts/search_skills.py -k "不存在的关键词xyz123"
```

**预期结果**：
- 输出 "未找到与 ... 相关的技能"
- 提供引导语

## 链接验证

从搜索结果中取一个 `show_id`，在浏览器中打开：

```
https://pangu.huaweicloud.com/gallery/asset-detail.html?id={show_id}
```

**预期结果**：
- 页面正常加载
- 显示对应 skill 的详细信息
