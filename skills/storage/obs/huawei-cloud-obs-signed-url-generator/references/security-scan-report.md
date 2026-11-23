# Security Scan Report

## Skill Information

| Field | Value |
|-------|-------|
| **Skill Name** | huawei-cloud-obs-signed-url-generator |
| **Skill Path** | `skills/storage/obs/huawei-cloud-obs-signed-url-generator` |
| **Scan Date** | 2026-11-15 |
| **Scan Tool** | `skill-audit 0.1.0` (installed from https://skills.developer.huaweicloud.com/detail/huawei-cloud-skill-audit) |
| **Platform** | Windows (win32), Python 3.12.10 |

## Scan Summary

| Metric | Value |
|--------|-------|
| **Final Verdict** | ✅ PASSED — No errors found |
| Errors | 0 |
| Warnings | 2 (false positives) |
| Info | 0 |

## Scanner Execution Results

| Scanner | Status | Findings | Description |
|---------|--------|----------|-------------|
| **prompt** | ✅ Executed | 2 WARN | Detects prompt injection risks in skill documentation |
| **semgrep** | ✅ Executed | 0 | Static analysis of Python code, no security issues |
| **secrets** | ⚠️ Skipped | 0 | `detect-secrets` not recognized by skill-audit (tool integration limitation) |
| **shellcheck** | ⚠️ Skipped | 0 | `shellcheck` not available on Windows |

## Findings Detail

### Finding 1

| Field | Value |
|-------|-------|
| **Severity** | WARN |
| **Scanner** | prompt |
| **Rule** | `prompt/(read\|access\|get\|ext` |
| **Message** | Attempts to access sensitive data |
| **File** | `SKILL.md` |
| **Line** | 39 |
| **Verdict** | **False Positive** |

**Analysis**: Line 39 describes reading AK/SK from environment variables:
```
- **OBS credentials** — AK/SK obtained from Huawei Cloud Console (IAM > My Credentials > Access Keys). Read from environment variables: `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`...
```
This is documentation describing the correct practice of reading credentials from environment variables, not actual code accessing sensitive data.

### Finding 2

| Field | Value |
|-------|-------|
| **Severity** | WARN |
| **Scanner** | prompt |
| **Rule** | `prompt/(read\|access\|get\|ext` |
| **Message** | Attempts to access sensitive data |
| **File** | `references/dataflow-diagram.md` |
| **Line** | 9 |
| **Verdict** | **False Positive** |

**Analysis**: Line 9 is part of a Mermaid data flow diagram:
```
B -->|2. Read AK/SK from env vars| C[Environment Variables]
```
This is a documentation diagram describing the data flow of reading credentials from environment variables, not actual code.

## Security Assessment

### Credential Management

| Check | Status | Detail |
|-------|--------|--------|
| No hardcoded credentials | ✅ PASS | AK/SK/SecurityToken all read from environment variables |
| Environment variable fallback | ✅ PASS | Supports multiple env var names (ACCESS_KEY_ID, OBS_ACCESS_KEY_ID, HUAWEICLOUD_SDK_AK, etc.) |
| Temporary credential support | ✅ PASS | Supports SecurityToken for temporary AK/SK |
| Credential error handling | ✅ PASS | Explicit error message and exit(1) when AK/SK missing |

### Code Security (semgrep)

| Check | Status | Detail |
|-------|--------|--------|
| No command injection | ✅ PASS | Uses argparse for parameter parsing, no string concatenation |
| No path traversal | ✅ PASS | No file path operations on user input |
| No SQL injection | ✅ PASS | No database operations |
| No XSS | ✅ PASS | No web output |
| No encoding injection | ✅ PASS | JSON output uses ensure_ascii=False with proper encoding |

### IAM Least Privilege

| Check | Status | Detail |
|-------|--------|--------|
| IAM policy documented | ✅ PASS | `references/iam-policies.md` provides least-privilege policy |
| No admin permissions required | ✅ PASS | Only requires `obs:object:GetObject` for signed URL generation |

### Prompt Injection

| Check | Status | Detail |
|-------|--------|--------|
| No prompt injection in SKILL.md | ✅ PASS | 2 warnings are false positives (documentation only) |
| No hidden instructions | ✅ PASS | All commands are transparent and documented |

## SARIF Format

The scan result is also available in SARIF format for integration with CI/CD pipelines:

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "skill-audit",
        "version": "0.1.0"
      }
    },
    "results": [
      {
        "ruleId": "prompt/(read|access|get|ext",
        "message": {"text": "Attempts to access sensitive data"},
        "level": "warning",
        "locations": [{"physicalLocation": {"artifactLocation": {"uri": "SKILL.md"}, "region": {"startLine": 39}}}]
      },
      {
        "ruleId": "prompt/(read|access|get|ext",
        "message": {"text": "Attempts to access sensitive data"},
        "level": "warning",
        "locations": [{"physicalLocation": {"artifactLocation": {"uri": "references/dataflow-diagram.md"}, "region": {"startLine": 9}}}]
      }
    ]
  }]
}
```

## Scan Conclusion

✅ **PASSED** — No errors, no security vulnerabilities. 2 warnings are false positives from documentation descriptions of environment variable credential reading. The skill follows security best practices: no hardcoded credentials, argparse input validation, least-privilege IAM policy, and temporary credential support.
