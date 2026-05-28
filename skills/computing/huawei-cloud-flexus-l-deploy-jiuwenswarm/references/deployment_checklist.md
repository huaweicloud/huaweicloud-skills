# Deployment Checklist

## Pre-Deployment Checks

### Credential Checks
- [ ] Huawei Cloud AK/SK configured
- [ ] Credentials have Flexus L instance creation permission
- [ ] Credentials have COC script execution permission

### Environment Checks
- [ ] Python 3.10+ installed
- [ ] Huawei Cloud SDK installed
- [ ] Network can access Huawei Cloud services

### Resource Checks
- [ ] Sufficient Flexus L quota
- [ ] Target region available
- [ ] Security group rules configured

## Deployment Step Checks

### Phase 1: Environment Preparation
- [ ] Credential validation passed
- [ ] Dependency module check passed

### Phase 2: Create Instance
- [ ] Customer confirmed creation
- [ ] Instance created successfully
- [ ] Instance status is RUNNING
- [ ] Public IP obtained

### Phase 3: Install Dependencies
- [ ] Base tools installed
- [ ] Python environment configured

### Phase 4: Deploy Service
- [ ] JiuwenSwarm installed
- [ ] systemd service configured
- [ ] Service started successfully

### Phase 5: Verify Deployment
- [ ] Port 5173 listening
- [ ] Service health check passed
- [ ] Web interface accessible

### Phase 6: Model Configuration
- [ ] API_BASE configured
- [ ] API_KEY configured
- [ ] MODEL_NAME configured
- [ ] MODEL_PROVIDER configured
- [ ] Service restarted successfully

### Phase 7: Message Channel Configuration
- [ ] Channel configured
- [ ] Service restarted successfully

## Post-Deployment Checks

- [ ] Service auto-start configured correctly
- [ ] Log files generated normally
- [ ] Security group rules correct
- [ ] Backup strategy configured

## Rollback Checks

- [ ] Instance can be deleted normally
- [ ] Configuration files backed up completely
- [ ] Data can be migrated normally
