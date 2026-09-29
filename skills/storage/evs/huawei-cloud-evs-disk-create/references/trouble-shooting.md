## Error Handling

### Common Errors and Solutions

#### Error 1: Insufficient Permissions
```
Error: Insufficient permissions
```
**Solution**:
1. Check if Access Key has EVS FullAccess permission
2. Check if Access Key has expired
3. Verify if credential configuration is correct

#### Error 2: Availability Zone Unavailable
```
Error: Specified availability zone is unavailable
```
**Solution**:
- Check if availability zone code is correct
- Confirm account has access permission in that availability zone
- Try other availability zones

#### Error 3: Disk Quota Exceeded
```
Error: Quota exceeded for resources
```
**Solution**:
1. Check account's EVS disk quantity quota
2. Check account's EVS total capacity quota
3. Apply for quota increase through Huawei Cloud console

#### Error 4: Invalid Disk Size
```
Error: Invalid disk size
```
**Solution**:
- Check if disk size is within the allowed range (10-32768 GB)
- Check if disk size matches the step size requirement
- Confirm disk type supports the specified size

#### Error 5: Network Connection Issue
```
Error: Connection timeout
```
**Solution**:
1. Check network connection
2. Verify endpoint is correct
3. Check firewall settings

#### Error 6: Disk Name Already Exists
```
Error: Disk name already exists
```
**Solution**:
- Choose a different disk name
- Add a timestamp or random suffix
- Check if the same name is already used in the same region