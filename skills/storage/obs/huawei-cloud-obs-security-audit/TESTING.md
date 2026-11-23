# 测试方法 — huawei-cloud-obs-security-audit

## 1. 环境准备

### 1.1 工具版本要求

```bash
python3 --version          # >= 3.8
hcloud version             # >= 3.2.0
obsutil version            # >= 5.5.0（通过 hcloud obs passthrough）
```

### 1.2 凭据配置

```bash
# 方式一：交互式配置（推荐）
hcloud obs config
# 按提示输入 AK、SK、endpoint

# 方式二：环境变量
export HUAWEICLOUD_SDK_AK="your-ak"
export HUAWEICLOUD_SDK_SK="your-sk"
```

### 1.3 安装 skill-quality-cli

```bash
cd skills/storage/obs/huawei-cloud-obs-security-audit
bash scripts/ensure_cli.sh
```

### 1.4 IAM 权限确认

执行审计的 IAM 用户需要以下 13 个只读权限（详见 `references/iam-policies.md`）：

```
obs:bucket:GetBucketAcl, GetBucketPolicy, GetBucketCors, GetBucketEncryption,
GetBucketReplication, GetBucketLogging, GetBucketReferer,
GetBucketBlockPublicAccess, GetBucketVersioning, GetBucketLocation,
GetBucketStorage, ListAllMyBuckets, obs:object:ListObject
```

---

## 2. 静态验证（无需 OBS 桶）

### 2.1 语法检查

```bash
cd skills/storage/obs/huawei-cloud-obs-security-audit

# Python 脚本语法
python3 -c "import py_compile; py_compile.compile('scripts/obs_security_auditor.py', doraise=True)"
# 预期：无输出，退出码 0

# Bash 脚本语法
bash -n scripts/ensure_cli.sh
bash -n scripts/install_cli.sh
# 预期：无输出，退出码 0
```

### 2.2 参数解析

```bash
# --help 输出
python3 scripts/obs_security_auditor.py --help
# 预期：显示 audit 子命令及所有参数说明

# 缺少必填参数
python3 scripts/obs_security_auditor.py audit
# 预期：报错 "the following arguments are required: --bucket"，退出码 2
```

### 2.3 安全检查

```bash
# 检查无硬编码 AK/SK
grep -rniE "access[_-]?key[[:space:]]*=[[:space:]]*['\"]?[A-Z0-9]{8,}" . || echo "clean"
grep -rniE "(AK|SK|secret[_-]?key)[[:space:]]*=[[:space:]]*['\"]" scripts/ || echo "clean"
# 预期：clean
```

### 2.4 评分模型验证

```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('auditor', 'scripts/obs_security_auditor.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
total = sum(v['max'] for v in mod.SCORING_MODEL.values())
print(f'Scoring model total: {total}')
assert total == 110, f'Expected 110, got {total}'
print(f'Grade levels: {mod.GRADE_LEVELS}')
print('PASS')
"
# 预期：Scoring model total: 110, PASS
```

---

## 3. skill-gate 审计

### 3.1 运行审计

```bash
cd D:/sdk/sikll/202611/huaweicloud-skills

AUDIT_DIR="skills/devtools/common/huawei-cloud-skill-audit"
python3 "$AUDIT_DIR/scripts/skill_audit.py" \
  --target skills/storage/obs/huawei-cloud-obs-security-audit \
  --scan-level deep
```

### 3.2 预期结果

```
  [1/3] gitleaks ... OK
  [2/3] runtime_security ... OK
  [3/3] skillspector ... OK

Gate Verdict: PASS  |  gitleaks OK  runtime_security OK  skillspector OK
```

---

## 4. skill-tester 功能测试

### 4.1 运行测试

使用 `huawei-cloud-skill-tester` 对 skill 执行三级八阶段测试：

```
huawei-cloud-skill-tester(
  task_description="对 huawei-cloud-obs-security-audit Skill 执行端到端功能测试..."
)
```

### 4.2 预期结果

| 阶段 | 检查内容 | 预期结果 |
|------|---------|---------|
| Phase 0 | 目录完整性 + 生命周期 | PASS |
| Phase 1 | 元数据 + 命令 + 文档检查 | PASS |
| Phase 2 | CLI→SDK→API 可用性 | PASS 或 SKIP（无 hcloud 时） |
| Phase 3 | 脚本语法 + 参数解析 | PASS |
| Phase 4 | 安全验证 + 离线功能 | PASS |
| Phase 5 | 多技能编排 + 触发词冲突 | PASS |
| Phase 6 | 命令映射一致性 | PASS |
| Phase 7 | 汇总报告 | 完成 |

---

## 5. 单项命令验证（需要真实 OBS 桶）

将 `{bucket}` 替换为目标桶名，`{endpoint}` 替换为对应 endpoint。

### 5.1 逐项查询

```bash
SKILL="huawei-cloud-obs-security-audit"

# TC-01: 桶元数据（ACL、版本状态）
skill-quality-cli run --skill-name $SKILL -- hcloud obs stat obs://{bucket}
# 预期：返回桶元数据，包含 ACL、版本状态、存储类型

# TC-02: 桶策略（HTTPS 强制传输检查）
skill-quality-cli run --skill-name $SKILL -- hcloud obs bucketpolicy -method=get obs://{bucket}
# 预期：返回桶策略 JSON，或 "no policy" 消息

# TC-03: CORS 规则
skill-quality-cli run --skill-name $SKILL -- hcloud obs cors -method=get obs://{bucket}
# 预期：返回 CORS 配置 JSON，或 "no CORS" 消息

# TC-04: 对象列表（命名模式检查）
skill-quality-cli run --skill-name $SKILL -- hcloud obs ls -s -limit=1000 obs://{bucket}
# 预期：返回对象 key 列表

# TC-05: 加密配置
skill-quality-cli run --skill-name $SKILL -- hcloud OBS GetBucketEncryption --bucket={bucket}
# 预期：返回加密配置 JSON，或 404（未配置）

# TC-06: 跨区域复制
skill-quality-cli run --skill-name $SKILL -- hcloud OBS GetBucketReplication --bucket={bucket}
# 预期：返回复制配置 JSON，或 404（未配置）

# TC-07: 日志记录
skill-quality-cli run --skill-name $SKILL -- hcloud OBS GetBucketLogging --bucket={bucket}
# 预期：返回日志配置 JSON，或 404（未配置）

# TC-08: 防盗链 Referer
skill-quality-cli run --skill-name $SKILL -- hcloud OBS GetBucketReferer --bucket={bucket}
# 预期：返回 Referer 配置 JSON，或 404（未配置）

# TC-09: BPA 阻止公共访问
skill-quality-cli run --skill-name $SKILL -- hcloud OBS GetBucketBlockPublicAccess --bucket={bucket}
# 预期：返回 BPA 状态 JSON，或 404（未配置）
```

---

## 6. 完整审计验证（需要真实 OBS 桶）

### 6.1 文本格式审计

```bash
cd skills/storage/obs/huawei-cloud-obs-security-audit

python3 scripts/obs_security_auditor.py audit --bucket {bucket}
```

**预期输出**：

```
============================================================
  OBS Security Audit Report
  Bucket: {bucket}
  Generated: 2026-11-18 12:00:00 UTC
============================================================

Summary:
  Total Score: 75/110
  Grade: Good

Check Results:
  [PASS]  ACL Permissions          15/15  Private
  [WARN]  BPA Status                0/15  Not enabled
  [PASS]  Encryption               15/15  SSE-KMS
  [PASS]  Versioning               10/10  Enabled
  [WARN]  Replication               0/10  Not configured
  [PASS]  HTTPS Enforcement        15/15  SecureTransport enforced
  [WARN]  Bucket Logging            0/10  Not enabled
  [PASS]  Referer Anti-hotlink      5/5   Configured
  [PASS]  CORS Rules                5/5   No wildcard
  [PASS]  Object Naming            10/10  Random prefix

Risk Items:
  [CRITICAL] BPA not enabled
    Current: Block Public Access is not enabled
    Fix: Enable BPA to block all public access
    Priority: P0

  [WARN] Replication not configured
    Current: No cross-region replication rules
    Fix: Configure replication for disaster recovery
    Priority: P1
  ...

Remediation Recommendations (sorted by priority):
  P0: Enable BPA (Block Public Access)
  P0: Enable bucket logging
  P1: Configure cross-region replication
  ...
============================================================
```

退出码：`0`（无 CRITICAL）或 `1`（存在 CRITICAL）。

### 6.2 JSON 格式审计

```bash
python3 scripts/obs_security_auditor.py audit --bucket {bucket} --format json --output /tmp/report.json

# 验证 JSON 格式正确
python3 -m json.tool /tmp/report.json > /dev/null && echo "JSON valid"
```

**预期**：`/tmp/report.json` 文件存在，JSON 格式合法，退出码 0 或 1。

### 6.3 JSON 结构示例

```json
{
  "bucket": "my-bucket",
  "timestamp": "2026-11-18T12:00:00Z",
  "total_score": 75,
  "max_score": 110,
  "grade": "Good",
  "checks": [
    {
      "name": "ACL Permissions",
      "score": 15,
      "max_score": 15,
      "status": "PASS",
      "detail": "Private",
      "remediation": null
    },
    ...
  ],
  "risk_items": [
    {
      "name": "BPA not enabled",
      "severity": "CRITICAL",
      "current": "Block Public Access is not enabled",
      "fix": "Enable BPA to block all public access",
      "priority": "P0"
    },
    ...
  ]
}
```

---

## 7. 错误处理验证

### 7.1 不存在的桶

```bash
python3 scripts/obs_security_auditor.py audit --bucket non-existent-bucket-12345
```

**预期**：脚本不崩溃，生成报告（所有检查项为 ERROR），退出码 1。

### 7.2 404 处理（未配置的服务）

对一个已知未配置加密的桶执行审计：

```bash
python3 scripts/obs_security_auditor.py audit --bucket {bucket-without-encryption}
```

**预期**：加密检查项显示 `CRITICAL "No encryption configured"`，而非脚本崩溃。

### 7.3 权限不足

使用缺少 `obs:bucket:GetBucketEncryption` 权限的 IAM 用户执行审计：

**预期**：加密检查项显示 `ERROR "Access denied"`，其他检查正常执行，退出码 1。

---

## 8. 测试用例汇总

| 用例 | 类型 | 需要桶 | 验证内容 |
|------|------|--------|---------|
| TC-01 | 单项查询 | ✅ | `hcloud obs stat` 返回桶元数据 |
| TC-02 | 单项查询 | ✅ | `hcloud obs bucketpolicy -method=get` 返回桶策略 |
| TC-03 | 单项查询 | ✅ | `hcloud obs cors -method=get` 返回 CORS 规则 |
| TC-04 | 单项查询 | ✅ | `hcloud obs ls -s -limit=1000` 返回对象列表 |
| TC-05 | 单项查询 | ✅ | `hcloud OBS GetBucketEncryption` 返回加密配置或 404 |
| TC-06 | 单项查询 | ✅ | `hcloud OBS GetBucketReplication` 返回复制配置或 404 |
| TC-07 | 单项查询 | ✅ | `hcloud OBS GetBucketLogging` 返回日志配置或 404 |
| TC-08 | 单项查询 | ✅ | `hcloud OBS GetBucketReferer` 返回防盗链配置或 404 |
| TC-09 | 单项查询 | ✅ | `hcloud OBS GetBucketBlockPublicAccess` 返回 BPA 状态或 404 |
| TC-10 | 完整审计 | ✅ | text 格式报告，含 10 项检查 + 评分 + 风险项 + 修复建议 |
| TC-11 | 完整审计 | ✅ | JSON 格式报告写入文件，`json.tool` 验证通过 |
| TC-12 | 错误处理 | ❌ | 不存在的桶，脚本优雅处理不崩溃 |
| TC-13 | 错误处理 | ✅ | 404 响应显示"未配置"而非崩溃 |

---

## 9. skill-tester + skill-gate 完整流程

```bash
# 步骤 1：skill-gate 审计（静态分析）
python3 skills/devtools/common/huawei-cloud-skill-audit/scripts/skill_audit.py \
  --target skills/storage/obs/huawei-cloud-obs-security-audit \
  --scan-level deep
# 预期：Gate Verdict: PASS

# 步骤 2：skill-tester 功能测试（三级八阶段）
# 通过 Relay Agent 调用 huawei-cloud-skill-tester
# 预期：所有 Phase PASS

# 步骤 3：真实环境验证（可选，需要 OBS 桶）
python3 scripts/obs_security_auditor.py audit --bucket {real-bucket}
# 预期：完整安全报告，退出码 0 或 1
```