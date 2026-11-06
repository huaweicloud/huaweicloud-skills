# 验证方法

## 功能验证

### 0.5. KooCLI 版本检查验证（非阻塞）

```bash
python scripts/check-koocli.py
```

**预期结果**（脚本始终以退出码 0 结束，不阻塞后续流程）：
- 环境已安装较新版本 `hcloud`（≥ 3.0.0）→ 无任何输出（静默通过）
- 环境已安装但版本过旧（< 3.0.0）→ 输出升级提醒（`hcloud update -y`）
- 环境未安装 `hcloud` → 输出安装提醒（附官方安装指南链接）

### 1. 关键词搜索验证

```bash
python scripts/search-skills.py -k "ecs"
```

**预期结果**：
- 输出包含 "Found N skill(s)" 的提示
- 每个结果包含名称、分类/服务、描述，并按评分降序排列
- 命中关键词会在结果中标注 `matched: ...`
- 搜索结果的每个 skill 名称均通过安装计数接口上报（fire-and-forget，失败静默，不阻塞输出）

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
python scripts/search-skills.py -c "<top-level>"       # 一级类目: 前缀匹配
python scripts/search-skills.py -c "<top>/<sub>"   # 二级路径: 精确匹配
python scripts/search-skills.py -l                   # 列出可用类目
```

**预期结果**：
- 一级类目返回其全部子类目下的 skill（条数以当前索引为准）
- 二级路径只返回该子路径下的 skill
- 一级类目不会误配同名前缀的其它类目（前缀比较以 `/` 结尾判定）
- `-l` 输出一级类目 + 技能数 + 二级路径明细

### 4. 无结果场景验证

```bash
python scripts/search-skills.py -k "不存在的关键词xyz123"
python scripts/search-skills.py -c "nonexistent-category"
```

**预期结果**：
- 输出 "No results for keyword=..." 提示
- 仅关键词无结果 → 输出 Fallback suggestions（含 `-l` 浏览类目入口）
- `-c` 值不存在 → 提示 "Category '...' was not found in the index."，给出近似类目候选并列出可用类目清单（由 `index.json` 聚合，不写死任何类目）
- `-c` 存在但关键词无命中 → 提示该类目下的技能数并建议不带关键词浏览

### 5. 缺少参数场景验证

```bash
python scripts/search-skills.py
```

**预期结果**：
- 输出 Usage 提示（`-k` / `-c` / `-l` 三种用法）
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
  `https://gitcode.com/developer-skill/skills-group-contribution`（branch `test-for-index`）中的
  `skills-index/index.json` 内容比对
- **预期结果**：脚本输出的 skill 名称、分类、服务与索引文件一致（数据为每次
  运行实时拉取，无本地缓存）