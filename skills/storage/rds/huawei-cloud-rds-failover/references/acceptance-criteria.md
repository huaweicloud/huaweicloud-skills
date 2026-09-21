# 验收标准

## 功能验收

### prepare 阶段

| 验收项 | 预期结果 | 验证方式 |
|--------|---------|---------|
| 读取 config.json | 正确加载 region 和 instance_id | `python3 scripts/prepare.py` 输出配置信息 |
| 查询 RDS 实例 | 列出区域内所有 HA 实例 | 输出实例列表，标记选定实例 |
| 检查 IAM 权限 | 输出 AK/SK/RDS 权限状态 | 输出 4 项权限检查结果 |
| 生成 experiment.json | 文件存在且格式正确 | `cat experiments/experiment.json` |
| 生成 iam_policy.json | 文件存在且格式正确 | `cat experiments/iam_policy.json` |
| 生成 monitoring.json | 文件存在且格式正确 | `cat experiments/monitoring.json` |
| 生成准备报告 | HTML + Markdown 报告生成 | `ls experiments/readiness_report.*` |
| 15 项检查 | 必需项全部通过 | 输出 "准备就绪" |

### execute 阶段

| 验收项 | 预期结果 | 验证方式 |
|--------|---------|---------|
| 加载配置 | 正确读取 3 个配置文件 | 输出实验名称和实例信息 |
| 预检查 | 实例存在、HA 类型、ACTIVE | 输出 "安全检查: 全部通过" |
| 预演模式 | 不执行实际倒换 | `python3 scripts/execute.py --config-dir <dir>` 无变更 |
| 执行倒换 | 调用 StartFailover 成功 | 输出 workflowId |
| 轮询等待 | 主备角色交换完成 | 输出 "倒换完成" 和耗时 |
| 收集日志 | 错误日志和慢 SQL 日志 | execution_result.json 含日志数据 |
| 收集监控 | 8 个 CES 指标数据 | execution_result.json 含 ces_metrics |
| 保存结果 | execution_result.json 生成 | 文件存在且格式正确 |

### report 阶段

| 验收项 | 预期结果 | 验证方式 |
|--------|---------|---------|
| 读取执行结果 | 正确加载 execution_result.json | 无 ERROR 输出 |
| 生成 HTML 报告 | 报告文件生成 | `ls report/failover_report_*.html` |
| 报告内容完整 | 包含所有板块 | 浏览器打开检查 |
| 报告独立可用 | 内联 CSS，无外部依赖 | 断网状态下浏览器可正常显示 |

### 统一入口 run.py

| 验收项 | 预期结果 | 验证方式 |
|--------|---------|---------|
| 一键全流程 | prepare→execute→report 顺序执行 | `python3 scripts/run.py --yes` |
| 分阶段执行 | 仅执行指定阶段 | `python3 scripts/run.py --phase prepare` |
| 预演模式 | 不实际倒换 | `python3 scripts/run.py`（无 --yes） |

## 报告内容验收

生成的 HTML 报告须包含以下板块：

- [ ] 结果横幅（成功/超时状态、耗时、工作流 ID）
- [ ] 实例信息（名称、ID、引擎、规格、时间）
- [ ] 安全检查（5 项检查结果）
- [ ] IAM 权限（最小权限集）
- [ ] 主备拓扑变化（倒换前后对比）
- [ ] 倒换时间线（轮询记录）
- [ ] CES 监控指标（8 个指标）
- [ ] 错误日志（如有）
- [ ] 慢 SQL 日志（如有）
- [ ] 告警规则状态

## 安全验收

- [ ] config.json 不含明文 AK/SK
- [ ] 倒换前实例状态必须为 ACTIVE
- [ ] 倒换前实例必须为 HA 类型
- [ ] execute 阶段默认预演，需 --yes 才实际执行
- [ ] 报告中不泄露敏感凭据信息
