# Acceptance Criteria

## Overview

This document defines the acceptance criteria for successful JiuwenSwarm deployment.

## Acceptance Items

### Functional Acceptance

| Acceptance Item | Description | Verification Method | Pass Criteria |
|----------------|-------------|-------------------|---------------|
| Trigger word matching | Skill correctly recognizes deployment requests | User inputs trigger word | Skill is loaded correctly |
| Dependency check | Automatically check and install missing dependencies | Run phase scripts | All dependencies installed successfully |
| Image download | Successfully download 308MB image file | Check file existence | File size approximately 308MB |
| Image extraction | Successfully extract image to specified directory | Check directory structure | jiuwenswarm_runtime directory exists |
| Environment configuration | Correctly configure .env file | Check file content | Contains API_BASE, API_KEY, MODEL_NAME, MODEL_PROVIDER |
| Service startup | Successfully start all service processes | Check port status | All 4 ports are in LISTEN state |
| URL output | Correctly output Web access URL | Check output content | Correctly formatted URL |

### Performance Acceptance

| Acceptance Item | Description | Verification Method | Pass Criteria |
|----------------|-------------|-------------------|---------------|
| Download speed | 308MB image download time | Timing | ≤ 60 seconds (normal network) |
| Extraction speed | Image extraction time | Timing | ≤ 30 seconds |
| Startup speed | Service startup time | Timing | ≤ 60 seconds |
| Total time | Complete deployment time | Timing | ≤ 180 seconds |

### Security Acceptance

| Acceptance Item | Description | Verification Method | Pass Criteria |
|----------------|-------------|-------------------|---------------|
| Credential protection | API_KEY plaintext not exposed | Check logs and output | No plaintext API_KEY in logs |
| File permissions | .env file permissions | `ls -la` | Permission set to 600 |
| Network security | Only allow local access | Check firewall | Service only listens on local ports |

### Reliability Acceptance

| Acceptance Item | Description | Verification Method | Pass Criteria |
|----------------|-------------|-------------------|---------------|
| Error retry | Automatic retry after failure | Simulate network interruption | Maximum 3 retries |
| Port detection | Automatically detect port status | Wait for ports to be ready | Complete only after all ports are ready |
| Idempotency | Repeated execution has no side effects | Run phase scripts multiple times | Second run skips download and extraction |

## Acceptance Process

### Automated Acceptance

1. Run the verification script:
   ```bash
   Verification script from bash references/verification-method.md
   ```

2. Check output results:
   - All checks passed (✅)
   - No errors (❌)

### Manual Acceptance

1. **Visual check**: Access the Web URL, confirm the interface displays normally
2. **Functional test**: Try sending requests, confirm the service responds normally
3. **Log check**: View service logs, confirm no ERROR-level errors

## Acceptance Pass Criteria

Acceptance is considered passed when all of the following conditions are met:

1. ✅ All functional acceptance items passed
2. ✅ All security acceptance items passed
3. ✅ All reliability acceptance items passed
4. ✅ Performance acceptance items within reasonable range (network fluctuations allowed)
5. ✅ Final output format is correct: `[5/5] ✅ Web URL: https://{WEB_PORT}-{devenvd_id}.workspace.developer.huaweicloud.com`

## Acceptance Failure Handling

| Failure Type | Handling Method |
|--------------|----------------|
| Functional acceptance failure | Check corresponding step logs, fix issues, then redeploy |
| Security acceptance failure | Stop use immediately, fix security issues |
| Performance acceptance failure | Analyze bottlenecks, optimize scripts or network configuration |
| Reliability acceptance failure | Fix retry mechanism or port detection logic |