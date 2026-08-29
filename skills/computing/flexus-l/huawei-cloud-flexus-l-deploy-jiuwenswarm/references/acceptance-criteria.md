# Acceptance Criteria

## Overview

This document defines the acceptance criteria for a successful JiuwenSwarm deployment on Huawei Cloud Flexus L instances. All criteria must be met before the deployment is considered complete.

## Pre-Deployment Acceptance Criteria

### Credentials
- [ ] Huawei Cloud AK/SK configured via environment variables
- [ ] Credentials have sufficient IAM permissions (see [iam-policies.md](iam-policies.md))
- [ ] Credential validation passed via IAM API

### Environment
- [ ] Python 3.8+ installed
- [ ] All required Python packages installed
- [ ] Network access to Huawei Cloud APIs confirmed

### Resources
- [ ] Flexus L instance quota available in target region
- [ ] Target region is supported (cn-north-4/cn-east-3/cn-south-1/cn-southwest-2)
- [ ] Customer confirmation obtained for resource creation

## Deployment Acceptance Criteria

### Instance Creation
- [ ] Flexus L instance created successfully
- [ ] Instance status is `RUNNING`
- [ ] Public IP assigned and accessible
- [ ] Instance ID and ECS instance ID obtained

### Dependency Installation
- [ ] COC dependency installation task status is `FINISHED`
- [ ] Base tools installed: git, curl, vim, wget, net-tools
- [ ] Python and Node.js environment available on instance

### Service Deployment
- [ ] COC service deployment task status is `FINISHED`
- [ ] JiuwenSwarm application installed
- [ ] systemd service `jiuwenswarm` configured for auto-start
- [ ] Service started without errors

### Deployment Verification
- [ ] `jiuwenswarm` service is active (`systemctl is-active jiuwenswarm` returns `active`)
- [ ] `.env` file has `FRONTEND_HOST=0.0.0.0`
- [ ] All ports bound to `0.0.0.0`:
  - [ ] Port 5173 (Frontend)
  - [ ] Port 18092
  - [ ] Port 19000
  - [ ] Port 19001
- [ ] Local health check passed (`curl localhost:5173` returns HTTP 200)
- [ ] Web access URL generated: `http://{public_ip}:5173`

## Post-Deployment Acceptance Criteria

### Model Configuration (Phase 6)
- [ ] `API_BASE` configured in `.env`
- [ ] `API_KEY` configured in `.env`
- [ ] `MODEL_NAME` configured in `.env`
- [ ] `MODEL_PROVIDER` configured in `.env`
- [ ] Original `.env` file backed up
- [ ] File permission set to 600
- [ ] JiuwenSwarm service restarted successfully

### Message Channel Configuration (Phase 7)
- [ ] Channel type selected (xiaoyi/feishu/dingtalk)
- [ ] Channel-specific credentials configured in `config.yaml`
- [ ] Original `config.yaml` file backed up
- [ ] File permission set to 644
- [ ] JiuwenSwarm service restarted successfully

### Security Group Configuration
- [ ] Inbound TCP port 5173 allowed in security group
- [ ] External web access verified: `curl http://{public_ip}:5173` returns HTTP 200

## Final Acceptance Sign-off

All of the following must be true for deployment acceptance:

1. **Instance**: Flexus L instance is RUNNING with valid public IP
2. **Service**: `jiuwenswarm` systemd service is active and enabled for auto-start
3. **Ports**: All required ports (5173, 18092, 19000, 19001) bound to `0.0.0.0`
4. **Health**: Local health check returns HTTP 200
5. **Access**: Web interface accessible at `http://{public_ip}:5173` (after security group configuration)
6. **Model**: Model configuration applied and service restarted (if Phase 6 executed)
7. **Channel**: Message channel configured and service restarted (if Phase 7 executed)
8. **Logs**: No critical errors in systemd logs (`journalctl -u jiuwenswarm`)

## Rejection Criteria

Deployment is rejected if any of the following occur:

1. Instance creation fails or instance status is not `RUNNING`
2. COC task status is `ABNORMAL` or `CANCELED`
3. `jiuwenswarm` service is not active
4. Any required port is not bound to `0.0.0.0`
5. Local health check does not return HTTP 200
6. Model or channel configuration fails to apply
7. Service restart fails after configuration update
