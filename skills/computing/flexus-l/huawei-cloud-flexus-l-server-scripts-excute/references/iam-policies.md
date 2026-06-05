# IAM Permission Policies

## COC Skill Required Permissions

### Script Management Permissions

| Permission Name | Permission Description | Applicable Operations |
|-----------------|------------------------|----------------------|
| `coc:script:create` | Create script | Create custom scripts |
| `coc:script:list` | List scripts | Query script list |
| `coc:script:get` | Get script details | View script content |
| `coc:script:update` | Update script | Modify script content |
| `coc:script:delete` | Delete script | Delete specified script |

### Script Execution Permissions

| Permission Name | Permission Description | Applicable Operations |
|-----------------|------------------------|----------------------|
| `coc:execution:create` | Create execution task | Execute scripts |
| `coc:execution:list` | List execution tasks | Query execution history |
| `coc:execution:get` | Get execution details | View execution status |
| `coc:execution:cancel` | Cancel execution task | Terminate running tasks |

### Instance Access Permissions

| Permission Name | Permission Description | Applicable Operations |
|-----------------|------------------------|----------------------|
| `coc:instance:list` | List target instances | Get list of instances where scripts can be executed |
| `coc:instance:get` | Get instance details | View instance information |

## Recommended IAM Roles

### COC Script Administrator (Recommended)

Includes all script management and execution permissions:
- `coc:script:*`
- `coc:execution:*`
- `coc:instance:*`

### COC Script Executor

Includes only script execution permissions:
- `coc:script:list`
- `coc:script:get`
- `coc:execution:create`
- `coc:execution:list`
- `coc:execution:get`
- `coc:instance:list`

## Permission Configuration Steps

1. Log in to Huawei Cloud Console
2. Navigate to IAM Service
3. Create or select user/role
4. Attach COC-related permission policies to the user/role
5. Save configuration and verify permissions

## Permission Verification

You can verify if permissions are correctly configured by running the following commands:

```bash
# Verify script list permission
python {baseDir}/scripts/caller.py list

# Verify instance list permission
python {baseDir}/scripts/caller.py instances
```

If the commands return normal results, the permission configuration is correct.