# Troubleshooting Guide

## Common Issues

### 1. Instance Creation Failed

**Symptoms**:
- Cannot create Flexus L instance
- Authentication error returned
- Quota insufficient error returned

**Troubleshooting Steps**:
1. Check if AK/SK are configured correctly
2. Verify AK/SK has Flexus L instance creation permission
3. Check account Flexus L quota
4. Confirm target region is available

**Solutions**:
```bash
# Check credential configuration
echo $HUAWEICLOUD_SDK_AK
echo $HUAWEICLOUD_SDK_SK

# Check quota (via Huawei Cloud Console)
# Visit: https://console.huaweicloud.com/flexus/
```

### 2. COC Script Execution Unresponsive

**Symptoms**:
- COC task status remains PROCESSING
- Execution timeout
- Cannot get execution result

**Troubleshooting Steps**:
1. Check if execute_uuid is correct
2. Confirm instance status is RUNNING
3. Verify COC service permissions
4. Check network connectivity

**Solutions**:
```bash
# Check COC task status
python scripts/query_coc_status.py --uuid <execute_uuid>

# Manually check instance status
curl -H "X-Auth-Token: <token>" https://rms.cn-north-4.myhuaweicloud.com/v1/resource-manager/domains/{domain_id}/resources
```

### 3. Web Service Unaccessible

**Symptoms**:
- Cannot access http://{ip}:5173
- Connection refused
- Timeout

**Troubleshooting Steps**:
1. Check security group rules (port 5173 open)
2. Confirm service is started
3. Check firewall settings
4. Verify port listening

**Solutions**:
```bash
# Check service status
systemctl status jiuwenswarm

# Check port listening
netstat -tlnp | grep 5173

# View service logs
journalctl -u jiuwenswarm --no-pager | tail -50

# Check firewall
ufw status
```

### 4. Service Startup Failed

**Symptoms**:
- systemd service startup failed
- Service status is failed
- Cannot run normally

**Troubleshooting Steps**:
1. View system logs
2. Check Python environment
3. Verify dependency installation
4. Check configuration files

**Solutions**:
```bash
# View service logs
journalctl -u jiuwenswarm --no-pager

# Check Python environment
source /opt/jiuwenswarm-env/bin/activate
python --version

# Verify dependencies
pip list | grep jiuwenswarm

# Test manual startup
cd /opt/jiuwenswarm-env/jiuwenswarm
python -m jiuwenswarm
```

### 5. Model Configuration Invalid

**Symptoms**:
- Model invocation failed
- API request timeout
- Authentication failed

**Troubleshooting Steps**:
1. Check .env file configuration
2. Verify API_KEY validity
3. Confirm network can access model service
4. Check proxy configuration

**Solutions**:
```bash
# View configuration file
cat /opt/jiuwenswarm-env/jiuwenswarm/.env

# Test API connection
curl -v -H "Authorization: Bearer <api_key>" <api_base>/models

# Check network connectivity
ping api.openai.com
```

### 6. Message Channel Configuration Failed

**Symptoms**:
- Messages cannot be sent
- Channel authentication failed
- Webhook verification failed

**Troubleshooting Steps**:
1. Check config.yaml configuration
2. Verify channel credentials
3. Confirm network can access channel service
4. Check callback URL

**Solutions**:
```bash
# View configuration file
cat /opt/jiuwenswarm-env/jiuwenswarm/config.yaml

# Test network connectivity
ping api.xiaoyi.com
ping open.feishu.cn
ping oapi.dingtalk.com
```

## Log Locations

### Service Logs
```
# systemd service logs
journalctl -u jiuwenswarm

# Application logs
/opt/jiuwenswarm-env/jiuwenswarm/logs/
```

### COC Execution Logs
```
# Query execution logs via COC API
# Use query_coc_status.py script
python scripts/query_coc_status.py --uuid <execute_uuid>
```

## Emergency Recovery

### Manual Deployment Steps
```bash
# 1. Login to instance
ssh root@<public_ip>

# 2. Install dependencies
apt-get update && apt-get install -y python3.11 python3.11-dev python3.11-venv git

# 3. Create virtual environment
python3.11 -m venv /opt/jiuwenswarm-env
source /opt/jiuwenswarm-env/bin/activate

# 4. Install JiuwenSwarm
pip install jiuwenswarm

# 5. Initialize
mkdir -p /opt/jiuwenswarm-env/jiuwenswarm
cd /opt/jiuwenswarm-env/jiuwenswarm
python -m jiuwenswarm init

# 6. Start service
python -m jiuwenswarm
```

### Instance Deletion
```bash
# Delete instance via Huawei Cloud Console
# Or use Flexus L API
curl -X DELETE "https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances/{instance_id}" \
  -H "X-Auth-Token: <token>"
```

## Contact Support

If the issue persists, collect the following information and contact Huawei Cloud support:

1. **Error Messages**: Complete error output
2. **Log Files**: systemd logs and application logs
3. **Environment Info**: Instance specifications, region, OS version
4. **Configuration Files**: .env and config.yaml (hide sensitive information)
5. **Timestamp**: Time when the issue occurred

## Recovery Process

```
1. Confirm root cause
2. Backup current configuration
3. Execute fix
4. Verify fix result
5. Update deployment documentation
6. Document issue and solution
```
