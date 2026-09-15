# 验收标准

## 核心功能

### AC-0: CLI 上报就绪

- [ ] `bash scripts/ensure_cli.sh` 幂等执行成功（`skill-quality-cli` 已装则跳过，未装则自动安装，离线静默跳过）
- [ ] `skill-quality-cli run/report` 与内置 `scripts/cli/cli_entry.py` 至少一个可用
- [ ] 上报 fire-and-forget，失败/超时不影响搜索结果输出与退出码

### AC-1: 关键词搜索

- [ ] 输入自然语言关键词，返回相关 skill 列表
- [ ] 结果按评分降序排列
- [ ] 每个结果包含：名称、分类/服务、描述
- [ ] 未提供关键词且未提供分类时，输出 Usage 与分类列表并提示参数错误

### AC-2: 中英文扩展

- [ ] 输入中文关键词可命中英文 skill（如 "对象存储" → obs）
- [ ] 输入英文关键词可命中中文描述（通过 `cn-en-map.json` 双向扩展）
- [ ] 输出中标注扩展后的关键词集合

### AC-3: 分类过滤

- [ ] `-c <category>` 过滤生效，只返回指定分类的结果
- [ ] 分类与关键词可组合使用

### AC-4: 无结果引导

- [ ] 无结果时输出 "No results" 提示
- [ ] 输出 Fallback suggestions 引导语（换关键词/去分类/中英切换/全部列出）

### AC-4b: KooCLI 版本检查（非阻塞）

- [ ] 执行 `python scripts/check-koocli.py` 始终以退出码 0 结束
- [ ] `hcloud` 未安装 → 输出安装提醒，流程继续
- [ ] `hcloud` 版本过旧（< 3.0.0）→ 输出升级提醒，流程继续
- [ ] `hcloud` 版本正常（≥ 3.0.0）→ 静默通过（无输出）

### AC-4c: 搜索结果曝光上报

- [ ] 搜索返回多个结果时，每个结果的 skill 名称均通过安装计数接口上报
  （`skills/<category>/<service>/<name>`，fire-and-forget）
- [ ] 上报失败或超时不影响搜索结果输出与退出码
- [ ] Step 3 安装计数接口逻辑保持不变

### AC-4d: 质量上报（Unified CLI）

- [ ] `search-skills.py` 不依赖任何内置 SDK / `skill_quality_sdk.py`
- [ ] **硬绑定（不可跳过）**：**裸运行** `python scripts/search-skills.py -k ...` 也会自动触发质量上报
  （载体解析：PATH `skill-quality-cli` → `~/.local/bin/skill-quality-cli` → 内置 `scripts/cli/cli_entry.py`），
  成功→`success`；异常→`sys_fail`；缺 keyword+category→`biz_fail(U02)`；fire-and-forget，失败/超时不影响输出与退出码
- [ ] 推荐以 `skill-quality-cli run --skill-name huawei-cloud-find-skills -- python scripts/search-skills.py ...` 包裹执行，每次运行自动上报一条质量记录（脚本检测 SKILL_TRACE_ID 去重，不双报）
- [ ] 搜索有结果 → `status=success`；缺 keyword+category → 非零退出；无匹配 → 输出 No results 引导；索引拉取失败 → `sys_fail`（由脚本或 CLI 包裹判定）
- [ ] 上报失败/超时静默，不阻塞主流程
- [ ] `ensure_cli.sh` 安装后 `~/.local/bin` 可加入 PATH（`export PATH="$HOME/.local/bin:$PATH"`），裸命令 `skill-quality-cli` 不报 127

## 数据准确性

### AC-5: 数据实时性

- [ ] 每次执行实时拉取 GitCode 公开索引（index.json + cn-en-map.json）
- [ ] 不依赖本地缓存或静态数据

## 安全合规

### AC-6: 只读操作

- [ ] 不创建、修改、删除任何云资源
- [ ] 不需要 IAM 认证（公开 API）
- [ ] 不要求用户输入 AK/SK 或任何凭证

### AC-7: 无硬编码凭证

- [ ] 脚本和文档中不包含任何 AK/SK、Token、密码
- [ ] 不包含任何 `HUAWEI_`、`HW_`、`HWC_` 开头的环境变量引用
- [ ] 依赖的凭据类工具（`npx skills add`）由用户侧自身配置管理

## 文件规范

### AC-8: 尺寸约束

- [ ] 文件总数 <= 30
- [ ] SKILL.md <= 500 行
- [ ] 目录总大小 <= 40MB
- [ ] 文件类型均在白名单内