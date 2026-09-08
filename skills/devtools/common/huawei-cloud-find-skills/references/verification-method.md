# 验证方法

## 功能验证

### 1. 关键词搜索验证

```bash
python scripts/search-skills.py -k "ecs"
```

**预期结果**：
- 输出包含 "Found N skill(s)" 的提示
- 每个结果包含名称、分类/服务、描述，并按评分降序排列
- 命中关键词会在结果中标注 `matched: ...`

### 2. 中英文关键词扩展验证

```bash
python scripts/search-skills.py -k "对象存储"
```

**预期结果**：
- 通过 `cn-en-map.json` 自动扩展到 "obs" 等英文关键词
- 输出的扩展列表包含原关键词与扩展关键词
- 命中 obs 相关 skill

### 3. 分类过滤验证

```bash
python scripts/search-skills.py -c "computing"
```

**预期结果**：
- 只返回 `computing` 分类下的 skill
- 不包含其他分类的结果

### 4. 无结果场景验证

```bash
python scripts/search-skills.py -k "不存在的关键词xyz123"
```

**预期结果**：
- 输出 "No results for keyword=..." 提示
- 输出 Fallback suggestions 引导语

### 5. 缺少参数场景验证

```bash
python scripts/search-skills.py
```

**预期结果**：
- 输出 Usage 提示与可用分类列表
- 脚本以非零状态退出（参数错误）

## 安装流程验证

1. 执行关键词搜索，从结果中取一个 skill 名
2. 按 SKILL.md Step 3 执行安装命令：
   ```bash
   npx skills add https://gitcode.com/huaweicloud/huaweicloud-skills.git#master --skill <skill-name> -y
   ```
3. **预期结果**：
   - 安装命令执行成功，无报错
   - 安装前已调用 install-count API（fire-and-forget，失败不阻塞安装）

## 与官方索引一致性验证

- 将脚本输出与
  `https://gitcode.com/2501_91318609/skills-for-index`（branch `main`）中的
  `skills-index/index.json` 内容比对
- **预期结果**：脚本输出的 skill 名称、分类、服务与索引文件一致（数据为每次
  运行实时拉取，无本地缓存）

## 质量上报验证（可选）

设置 `SKILL_QUALITY_DISABLE=1` 可关闭上报；默认每次运行会向
`SKILL_QUALITY_ENDPOINT` 发送一条 fire-and-forget 运行记录（3s 超时，
失败静默，不阻塞主流程）。