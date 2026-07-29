# gitcode-security-scanner Usage

Source: `https://gitcode.com/developer-skill/DTSE-SKILL/tree/main/gitcode-security-scanner`

## Overview

A regex-based security scanner for GitCode repos. Detects hardcoded tokens, password leaks, sensitive info, SQL injection, path traversal, debug leakage in source code files (.py, .js, .md, .json, .yaml, etc.).

## Complementary to huawei-cloud-skill-audit

**These two tools are complementary, NOT overlapping.** Running only one gives a false sense of security.

| Aspect | huawei-cloud-skill-audit (skillspector + gitleaks) | gitcode-security-scanner |
|--------|---------------------------------------------------|------------------------|
| **Risk domain** | AI safety (reverse shell, command injection, prompt injection, eval/exec) | InfoSec (credential leak, SQL injection, path traversal, debug leakage) |
| **Credential detection** | gitleaks: 800+ credential formats; skillspector: cloud API key formats only | Regex-based: api_key, password, secret, token, auth + Chinese keywords |
| **Chinese keywords** | Not detected | Detected: 授权码/密码/密钥/令牌/口令/秘钥/凭证 |
| **while True / eval / nc -l** | Detected by skillspector | Not detected |

## Running the Scanner

```python
import sys
sys.path.insert(0, '/tmp/DTSE-SKILL/gitcode-security-scanner/scripts')
from security_scanner import SecurityScanner

scanner = SecurityScanner('config_custom.json')
issues = scanner.scan_project('project-name', '/path/to/local/repo')
# issues = {'high': [...], 'medium': [...], 'low': [...]}
```

## Recommended Combined Usage

For complete security coverage, run **both**:

1. `huawei-cloud-skill-audit` — AI safety + quality gates + credential leak detection
2. `gitcode-security-scanner` — InfoSec (Chinese keyword credentials, SQL injection, path traversal, debug leakage)
