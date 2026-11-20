# 验收标准

## 核心功能

### AC-1: 关键词搜索

- [ ] 输入自然语言关键词，返回相关 skill 列表
- [ ] 结果按评分降序排列
- [ ] 每个结果包含：名称、分类/服务、描述
- [ ] 多服务技能结果行展示 `覆盖: <services>` 全量服务清单（取自 index 的 `services` 数组）与 index `type` 能力类型（如 `[只读查询]`、`[管理]`）
- [ ] 关键词可映射为云服务代码时，主排序后追加「其他覆盖 <关键词> 的技能」分组，列出 coverage-only 技能（名称未体现该产品、但 `services` 覆盖它）
- [ ] 检索收敛：无关关键词不返回全量结果 —— `python3 scripts/search-skills.py -k 'zzz-nonsense-qqq-no-such-skill'` 输出 `No results`（不得返回全部技能）；纯虚词/垃圾关键词（`-k zzz`、`-k the`）同样输出 `No results`，不退化为全量浏览
- [ ] 英文虚词/垃圾 token（`no`/`the`/`such`/`zzz`/`qqq`）在关键词扩展前被剔除；有关键词时，仅命中泛词（`huawei`/`cloud`/`skill` 等）的技能不进入结果
- [ ] 验收样例：`python3 scripts/search-skills.py -k CCE`（及 `-k CCE --explain`）的输出中，`huawei-cloud-computing-query` 展示 `覆盖: ECS+BMS+IMS+AS+CCE+EVS [只读查询]`（含 `ECS+BMS+IMS+AS+CCE` 覆盖标注），且该技能出现在「其他覆盖 CCE 的技能」分组中
- [ ] 未提供关键词且未提供分类时，输出 Usage 与分类列表并提示参数错误

### AC-2: 中英文扩展

- [ ] 输入中文关键词可命中英文 skill（如 "对象存储" → obs）
- [ ] 输入英文关键词可命中中文描述（通过 `cn-en-map.json` 双向扩展）
- [ ] 输出中标注扩展后的关键词集合

### AC-3: 分类过滤

- [ ] `-c <category>` 过滤生效，只返回指定分类的结果
- [ ] 一级类目按前缀匹配（`-c <top-level>` → 全部 `<top-level>/*`），二级路径精确匹配（`-c <top>/<sub>` 只返回该路径）
- [ ] `-l/--list-categories` 可从 `index.json` 聚合输出可用类目清单（一级 + 二级）
- [ ] 分类与关键词可组合使用

### AC-4: 无结果引导

- [ ] 无结果时输出 "No results" 提示
- [ ] 输出 Fallback suggestions 引导语（换关键词/去分类/中英切换/浏览类目 `-l`）
- [ ] `-c` 值未命中时输出近似类目候选与可用类目清单，不回退到写死的类目

### AC-4b: KooCLI 版本检查（非阻塞）

- [ ] 执行 `python scripts/check-koocli.py` 始终以退出码 0 结束
- [ ] `hcloud` 未安装 → 输出安装提醒，流程继续
- [ ] `hcloud` 版本过旧（< 3.0.0）→ 输出升级提醒，流程继续
- [ ] `hcloud` 版本正常（≥ 3.0.0）→ 静默通过（无输出）

### AC-4c: 搜索结果曝光上报

- [ ] 搜索返回多个结果时，**按评分排序的前 3 个**结果名称通过安装计数接口上报
  （`skills/<category>/<name>`，fire-and-forget；第 4 名及以后不上报）
- [ ] 上报失败或超时不影响搜索结果输出与退出码
- [ ] Step 3 安装计数接口逻辑保持不变

### AC-4d: CLI 安装失败归类（外部依赖）

- [ ] `bash scripts/ensure_cli.sh` 为唯一安装入口：CLI 缺失时经官网 latest 接口取 OBS 预签名包、校验 `sha256` 后安装到 `~/.local/bin/`，成功输出 `skill-quality-cli vX.Y.Z 已安装` 且退出码 `0`
- [ ] 通道不可用 / 校验失败时仅打印告警，退出码 `0`，搜索与安装流程继续（不阻塞业务、不误报为版本号问题）
- [ ] SKILL.md / references 中不再出现 `scripts/install_cli.sh` 等已下线的手动安装脚本，安装指引与 `scripts/ensure_cli.sh` 实际行为一致
- [ ] 同场景 `bash scripts/ensure_cli.sh` 打印外部依赖告警并以退出码 `0` 结束（不阻塞检索/安装流程）
- [ ] 自托管镜像场景：`SQCLI_PKG_BASE=<镜像地址> ...` 可用；镜像 404 但非 `NoSuchBucket` 时仍提示「指定版本未发布（404 路径不存在）」

## 数据准确性

### AC-5: 数据实时性与缓存

- [ ] 首次检索实时拉取 GitCode 公开索引（`index.json` + `cn-en-map.json`），失败按 GitCode → Gitee 回退
- [ ] 命中本地缓存（`~/.cache/huawei-cloud-find-skills/`，TTL 默认 1h，`FIND_SKILLS_CACHE_TTL` 可调）时**不发起网络请求**，输出与实时拉取一致
- [ ] 同一进程内两个索引文件各只加载一次；整词命中不足时回退检索**至多一次**

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