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
| 风险检测/评估 | `✓ risk_assessment.json` + "风险评估总览" | ✅ |
| 准备报告生成 | `✓ readiness_report.html/md`（含风险章节） | ✅ |
| 检查结论 | `✅ 准备就绪` | ✅ 必需项全通过 |

**输出文件验证**：

```bash
ls experiments/
# 预期: experiment.json  iam_policy.json  monitoring.json
#       risk_assessment.json  readiness_report.html  readiness_report.md

# 检查风险评估结果
python3 -c "
import json
with open('experiments/risk_assessment.json') as f:
    r = json.load(f)
print(f'overall: {r[\"overall_level\"]}  block: {r[\"block_execution\"]}')
assert r['overall_level'] in ('low', 'medium', 'blocked')
assert len(r['items']) > 0
print('risk_assessment.json OK')
" 
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
| 风险预警 | `[风险提示] 总体风险等级: xxx` | ✅ 读取 risk_assessment.json |
| 实例一致性校验 | `[风险拦截] risk_assessment.json 与当前待倒换实例不一致！` | ✅ 不一致时 --yes 退出且不触发倒换 |
| 执行前实时复核 | `[实时复核] 倒换前复核主备复制状态与复制延迟...` | ✅ 位于 StartFailover 调用之前 |

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
# 检查 execution_result.json — 通过角色(role)字段判断主备是否切换
# 华为云 RDS HA 实例的主备节点 name 不同（如 node0/node1），
# 但更可靠的方式是比较 role 字段：倒换前 master 节点的 role 应从 master 变为 slave
python3 -c "
import json
with open('experiments/execution_result.json') as f:
    r = json.load(f)
print(f'result: {r[\"result\"]}')
print(f'duration: {r[\"duration_seconds\"]}s')
print(f'before_master: {r[\"before_master\"][\"name\"]} (role={r[\"before_master\"][\"role\"]})')
print(f'after_master: {r[\"after_master\"][\"name\"]} (role={r[\"after_master\"][\"role\"]})')
# 比较 role 字段：倒换前主节点的 role=master，倒换后该节点应变为 slave
assert r['before_master']['role'] == 'master', '倒换前主节点 role 应为 master'
assert r['after_master']['role'] == 'master', '倒换后主节点 role 应为 master'
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

### 实时复核函数验证（只读，验证不误报）

```bash
python3 - <<'_PYEOF_'
import sys; sys.path.insert(0, 'scripts')
import risk
rt = risk.realtime_safety_check('<region>', '<instance_id>', '<master_node_id>')
print('blocked:', rt['blocked'])  # 健康实例应 False
_PYEOF_
```

### 实例一致性校验验证（安全，`--yes` 也会在 StartFailover 前退出）

```bash
# 1. 备份并伪造不一致
cp experiments/risk_assessment.json /tmp/risk.bak.json
python3 -c "
import json
d = json.load(open('experiments/risk_assessment.json'))
d['instance_id'] = '00000000000000000000000000000000in01'
json.dump(d, open('experiments/risk_assessment.json','w'), ensure_ascii=False, indent=2)
"
# 2. 应被拦截：退出码非 0，且输出无 '调用 StartFailover'
python3 scripts/execute.py --config-dir experiments --yes
# 3. 恢复
cp /tmp/risk.bak.json experiments/risk_assessment.json
```

### 风险模块单元验证（不触云）

验证两个核心不变量：

1. **有严重项 → 阻止**：合成 `replication abnormal / 存储 96% / 无备份` 等检测结果，
   `assess_risks` 应返回 `overall_level=blocked, block_execution=True`。
2. **数据缺失不误判**：将全部实时探测置为 `available=False`，
   `assess_risks` 不得产生任何 critical/warning（全部标记为未知 unknown），总体等级升为中。

```bash
python3 - <<'PYEOF'
import sys
sys.path.insert(0, 'scripts')
import risk
# 构造严重场景
det_critical = {"status": "BUILD", "replication": {"available": True, "status": "abnormal"},
                "storage": {"available": True, "used_pct": 96.0},
                "backups": {"available": True, "latest_age_hours": None, "failed_recent": 0},
                "recent_errors": {"available": True, "error_count": 60},
                "ces": {"replication_delay": {"available": True, "value": 60.0}}}
a = risk.assess_risks(det_critical)
assert a['block_execution'] is True
assert a['overall_level'] == 'blocked'
# 构造缺数据场景
det_empty = {"status": "ACTIVE", "replication": {"available": False, "status": None},
             "storage": {"available": False, "used_pct": None},
             "backups": {"available": False, "latest_age_hours": None},
             "recent_errors": {"available": False, "error_count": None},
             "ces": {"replication_delay": {"available": False, "value": None}}}
a2 = risk.assess_risks(det_empty)
assert a2['summary']['critical'] == 0
assert a2['overall_level'] == 'medium'
print('risk module invariants OK')
PYEOF
```

风险模型阈值与业务含义见 `references/risk-model.md`。

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
