# gitcode-security-scanner Usage

Source: `https://gitcode.com/developer-skill/DTSE-SKILL/tree/main/gitcode-security-scanner` (⚠️ 建议固定到已 review 的 commit/tag, 不要长期跟踪 main 分支; 导入前校验 security_scanner.py 的 SHA-256/签名)

## Overview

A regex-based security scanner for GitCode repos. Detects hardcoded tokens, password leaks, sensitive info, SQL injection, path traversal, debug leakage in source code files (.py, .js, .md, .json, .yaml, etc.).

## Relationship to huawei-cloud-skill-audit

**These two tools are complementary, with intentional overlap in credential detection.** Running only one gives a false sense of security.

> 边界说明: skillspector 的凭据类检测(cloud API key 格式、PWD1 password-literal)与
> gitleaks 的 43 类凭据规则存在**刻意重叠(纵深防御)**: 密码字面量的**权威判定源是 gitleaks**
> (password-literal 发现以 gitleaks 输出为准); skillspector 的 PWD1 作为 AI 安全类别的
> 本地补充检测保留, 但**不单独维护密码规则清单** —— 若两份规则需演进, 只改 gitleaks_rules.json,
> skillspector 侧不额外引入密码模式, 避免两处维护不一致。

| Aspect | huawei-cloud-skill-audit (skillspector + gitleaks) | gitcode-security-scanner |
|--------|---------------------------------------------------|------------------------|
| **Risk domain** | AI safety (reverse shell, command injection, prompt injection, eval/exec) | InfoSec (credential leak, SQL injection, path traversal, debug leakage) |
| **Credential detection** | gitleaks: 43 credential rules; skillspector: cloud API key formats + password-literal (PWD1) 等硬编码凭据检测 | Regex-based: api_key, password, secret, token, auth + Chinese keywords |
| **Chinese keywords** | Not detected | Detected: 授权码/密码/密钥/令牌/口令/秘钥/凭证 |
| **while True / eval / nc -l** | Detected by skillspector | Not detected |

## Running the Scanner

```python
import sys
# ⚠️ 安全要求: 不要使用 /tmp 等全局可写路径作为模块搜索路径 —— 攻击者可在
# /tmp 预置同名 security_scanner.py 劫持 import, 导致任意代码执行。
# 从受控的克隆目录导入, 并校验文件来源/完整性: 固定到已 review 的 commit/tag
# (git checkout <commit>) 并校验 security_scanner.py 的 SHA-256/签名, 升级须人工
# review 后显式切换新 commit, 不要自动/定期 git pull 跟踪 main。
sys.path.insert(0, '/path/to/gitcode-security-scanner/scripts')  # 替换为实际克隆路径
from security_scanner import SecurityScanner

scanner = SecurityScanner('config_custom.json')
issues = scanner.scan_project('project-name', '/path/to/my-skill-repo')
# issues = {'high': [...], 'medium': [...], 'low': [...]}
```

## Recommended Combined Usage

For complete security coverage, run **both**:

1. `huawei-cloud-skill-audit` — AI safety + quality gates + credential leak detection
2. `gitcode-security-scanner` — InfoSec (Chinese keyword credentials, SQL injection, path traversal, debug leakage)
