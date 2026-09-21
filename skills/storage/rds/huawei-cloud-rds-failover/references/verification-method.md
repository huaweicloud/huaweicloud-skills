# 验证方法

## 环境验证

### 1. hcloud CLI 验证

```bash
# 版本检查
hcloud version
# 预期: 当前KooCLI版本:7.x.x

# 认证验证 — 列出 RDS 实例
hcloud RDS ListInstances --cli-region=cn-north-1
# 预期: 返回 JSON 格式的实例列表
```

### 2. Python 环境验证

```bash
python3 --version
# 预期: Python 3.8+

# 验证脚本可导入
cd huawei-cloud-rds-failover
python3 -c "import scripts.config; print('config module OK')"
```

### 3. 配置文件验证

```bash
# 检查 config.json 存在且字段完整
python3 -c "
import json
with open('config/config.json') as f:
    cfg = json.load(f)
assert cfg.get('region'), 'region missing'
assert cfg.get('instance_id'), 'instance_id missing'
print(f'config OK: region={cfg[\"region\"]}, instance_id={cfg[\"instance_id\"]}')
"
```

## 功能验证

### prepare 阶段验证

```bash
python3 scripts/prepare.py
```

**验证检查清单**：

| 检查项 | 预期输出 | 判定 |
|--------|---------|------|
| 配置读取 | `[配置] region=xxx, instance_id=xxx` | ✅ |
| RDS 实例查询 | `找到 N 个 HA 实例` | ✅ N ≥ 1 |
| IAM 权限检查 | `RDS 读权限: 是` | ✅ |
| 配置文件生成 | `✓ experiment.json` 等 3 个文件 | ✅ |
| 准备报告生成 | `✓ readiness_report.html/md` | ✅ |
| 检查结论 | `✅ 准备就绪` | ✅ 必需项全通过 |

**输出文件验证**：

```bash
ls experiments/
# 预期: experiment.json  iam_policy.json  monitoring.json
#       readiness_report.html  readiness_report.md
```

### execute 阶段验证

**预演模式**（不实际倒换）：

```bash
python3 scripts/execute.py --config-dir experiments
```

| 检查项 | 预期输出 | 判定 |
|--------|---------|------|
| 配置加载 | `[配置] 实验名称: xxx` | ✅ |
| 预检查 | `安全检查: 全部通过` | ✅ |
| 预演模式 | `[预演] 传入 --yes 执行倒换` | ✅ 未做变更 |

**实际执行**：

```bash
python3 scripts/execute.py --config-dir experiments --yes
```

| 检查项 | 预期输出 | 判定 |
|--------|---------|------|
| 倒换提交 | `[OK] 倒换命令已提交, workflowId=xxx` | ✅ |
| 轮询完成 | `[成功] 倒换完成! 耗时 N 秒` | ✅ |
| 日志收集 | `[日志] 收集错误日志/慢SQL日志` | ✅ |
| 监控收集 | `[监控] 收集 CES 指标` | ✅ |
| 结果保存 | `[完成] 执行结果已保存` | ✅ |

**输出文件验证**：

```bash
# 检查 execution_result.json
python3 -c "
import json
with open('experiments/execution_result.json') as f:
    r = json.load(f)
print(f'result: {r[\"result\"]}')
print(f'duration: {r[\"duration_seconds\"]}s')
print(f'before_master: {r[\"before_master\"][\"name\"]}')
print(f'after_master: {r[\"after_master\"][\"name\"]}')
assert r['before_master']['name'] != r['after_master']['name'], '主备未切换!'
print('验证通过: 主备角色已切换')
"
```

### report 阶段验证

```bash
python3 scripts/report.py --config-dir experiments
```

| 检查项 | 预期输出 | 判定 |
|--------|---------|------|
| 报告生成 | `[完成] HTML 报告已生成: xxx` | ✅ |
| 文件存在 | `report/failover_report_*.html` | ✅ |
| 文件非空 | 文件大小 > 1KB | ✅ |

```bash
# 验证报告文件
REPORT=$(ls -t report/failover_report_*.html | head -1)
echo "报告: $REPORT"
echo "大小: $(du -h "$REPORT" | cut -f1)"
# 检查关键内容
grep -c "主备倒换" "$REPORT"  # 预期 ≥ 1
grep -c "拓扑变化" "$REPORT"  # 预期 ≥ 1
grep -c "时间线" "$REPORT"    # 预期 ≥ 1
```

### 统一入口验证

```bash
# 一键预演（prepare + execute 预演 + report）
python3 scripts/run.py
# 预期: 三阶段顺序执行，全部完成

# 分阶段
python3 scripts/run.py --phase prepare   # 仅准备
python3 scripts/run.py --phase execute   # 仅预演
python3 scripts/run.py --phase report    # 仅报告
```

## 端到端验证流程

```bash
#!/bin/bash
# 完整验证脚本
set -e
cd huawei-cloud-rds-failover

echo "=== 1. 环境检查 ==="
hcloud version
python3 --version

echo "=== 2. prepare ==="
python3 scripts/run.py --phase prepare

echo "=== 3. execute (预演) ==="
python3 scripts/run.py --phase execute

echo "=== 4. execute (实际倒换) ==="
python3 scripts/run.py --phase execute --yes

echo "=== 5. report ==="
python3 scripts/run.py --phase report

echo "=== 6. 验证报告 ==="
ls -lh report/failover_report_*.html | tail -1

echo "=== 全部验证通过 ==="
```
