# IAM Policies for ELB Monitoring Skill

## Overview

This document describes the Identity and Access Management (IAM) policies required for the Huawei Cloud ELB Monitoring skill. Proper IAM permissions are essential for the skill to function correctly.

## Required Permissions

### Minimum Required Permissions

The following permissions are required for basic ELB monitoring functionality:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elb:loadbalancers:list",
        "elb:loadbalancers:get",
        "elb:listeners:list",
        "elb:pools:list",
        "elb:members:list",
        "ces:metrics:list",
        "ces:metricData:get"
      ]
    }
  ]
}
```

### Recommended Permissions (Full Monitoring)

For full monitoring capabilities including alarm management:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elb:loadbalancers:list",
        "elb:loadbalancers:get",
        "elb:loadbalancers:stats",
        "elb:listeners:list",
        "elb:listeners:get",
        "elb:pools:list",
        "elb:pools:get",
        "elb:members:list",
        "elb:members:get",
        "ces:metrics:list",
        "ces:metricData:get",
        "ces:metricData:list",
        "ces:alarms:list",
        "ces:alarms:get",
        "ces:alarmTemplates:list",
        "ces:alarmRules:list",
        "ces:alarmRules:get"
      ]
    }
  ]
}
```

## Permission Details

### ELB Permissions

| Permission | Description | Required For |
|------------|-------------|--------------|
| `elb:loadbalancers:list` | List ELB instances | Listing available load balancers |
| `elb:loadbalancers:get` | Get ELB instance details | Getting ELB specifications and type |
| `elb:loadbalancers:stats` | Get ELB statistics | Optional: Getting ELB statistics |
| `elb:listeners:list` | List ELB listeners | Listing listeners for listener-level metrics |
| `elb:listeners:get` | Get listener details | Optional: Getting listener details |
| `elb:pools:list` | List backend server groups | Listing pools for backend monitoring |
| `elb:pools:get` | Get pool details | Optional: Getting pool details |
| `elb:members:list` | List backend servers | Listing backend servers in pools |
| `elb:members:get` | Get member details | Optional: Getting member details |

### CES (Cloud Eye Service) Permissions

| Permission | Description | Required For |
|------------|-------------|--------------|
| `ces:metrics:list` | List available metrics | Discovering available ELB metrics |
| `ces:metricData:get` | Get metric data | Querying monitoring data |
| `ces:metricData:list` | List metric data | Optional: Listing metric data |
| `ces:alarms:list` | List alarms | Optional: Listing existing alarms |
| `ces:alarms:get` | Get alarm details | Optional: Getting alarm details |
| `ces:alarmTemplates:list` | List alarm templates | Optional: Listing alarm templates |
| `ces:alarmRules:list` | List alarm rules | Optional: Listing alarm rules |
| `ces:alarmRules:get` | Get alarm rule details | Optional: Getting alarm rule details |

## IAM Policy Configuration

### Method 1: Using Predefined Policies

Huawei Cloud provides predefined policies that can be attached to user groups:

1. **ELB ReadOnlyAccess**: Provides read-only access to ELB resources
2. **CES FullAccess**: Provides full access to CES resources
3. **CES ReadOnlyAccess**: Provides read-only access to CES resources

**Recommended combination:**

- `ELB ReadOnlyAccess`
- `CES ReadOnlyAccess`

### Method 2: Creating Custom Policy

1. **Log in to Huawei Cloud Console**
   - Navigate to **IAM > Policies**

2. **Create Custom Policy**
   - Click **Create Custom Policy**
   - Policy Name: `ELB-Monitoring-ReadOnly`
   - Policy Type: **Custom Policy**
   - Policy Content: Use the JSON from "Minimum Required Permissions" section

3. **Attach Policy to User/User Group**
   - Navigate to **IAM > Users** or **IAM > User Groups**
   - Select the target user or group
   - Click **Authorize**
   - Search for and select the custom policy `ELB-Monitoring-ReadOnly`

### Method 3: Using IAM Roles

For cross-account access or service-to-service authentication:

1. **Create IAM Role**
   - Navigate to **IAM > Roles**
   - Click **Create Role**
   - Select **Common User** or **Agency**
   - Attach the required policies

2. **Configure CLI with Assume Role**

   > **Credential configuration is the user's responsibility.** Please configure credentials in your terminal, then use `hcloud configure list` to verify.

   Reference configuration command:

   ```bash
   hcloud configure set --cli-profile=<profile-name> \
     --cli-mode=AssumeRole \
     --cli-access-key=<access-key> \
     --cli-secret-key=<secret-key> \
     --cli-region=<region> \
     --cli-agency-name=<agency-name>
   ```

## Permission Verification

### Verify Permissions via CLI

```bash
# Test ELB permissions
hcloud ELB ListLoadBalancers --cli-region=<region-id> --limit=1

# Test CES permissions
hcloud CES ListMetrics --namespace="SYS.ELB" --cli-region=<region-id> --limit=1
```

### Common Permission Errors

| Error Message | Possible Cause | Solution |
|---------------|----------------|----------|
| `Access denied` | Insufficient permissions | Attach required policies |
| `User does not have permission` | Policy not attached | Verify policy attachment |
| `The security token included in the request is invalid` | Invalid AK/SK | Reconfigure credentials |
| `The requested resource could not be found` | Resource doesn't exist | Check resource ID and region |

### Troubleshooting Steps

1. **Check Current Permissions**

   ```bash
   # Check configured profile
   hcloud configure list
   ```

2. **Verify Policy Attachment**
   - Log in to Huawei Cloud Console
   - Navigate to **IAM > Users > [Your User] > Permissions**
   - Verify required policies are attached

3. **Test with Minimal Command**

   ```bash
   # Test with simplest command
   hcloud ELB ListLoadBalancers --cli-region=cn-north-4 --limit=1
   ```

4. **Check Region Compatibility**
   - Ensure the region supports the requested services
   - Verify ELB and CES are available in the region

## Best Practices

### 1. Principle of Least Privilege

- Grant only necessary permissions
- Use read-only permissions for monitoring
- Avoid granting write permissions unless required

### 2. Regular Permission Review

- Review and audit permissions quarterly
- Remove unused permissions
- Update policies based on changing requirements

### 3. Use IAM Groups

- Assign permissions to groups, not individual users
- Add users to appropriate groups
- Simplify permission management

### 4. Monitor Permission Usage

- Enable IAM access logs
- Review access patterns
- Detect and investigate unusual access

### 5. Secure Credential Management

- Rotate access keys regularly (every 90 days)
- Use IAM roles for applications
- Never hardcode credentials in code

## Cross-Account Monitoring

For monitoring ELB instances across multiple accounts:

1. **Create Agency in Target Account**
   - In target account: **IAM > Agencies > Create Agency**
   - Grant `ELB ReadOnlyAccess` and `CES ReadOnlyAccess` to the agency

2. **Configure Assume Role**

   > **Credential configuration is the user's responsibility.** Please configure credentials in your terminal, then use `hcloud configure list` to verify.

   Reference configuration command:

   ```bash
   hcloud configure set --cli-profile=cross-account \
     --cli-mode=AssumeRole \
     --cli-access-key=<source-account-ak> \
     --cli-secret-key=<source-account-sk> \
     --cli-region=<region> \
     --cli-agency-name=<agency-name>
   ```

3. **Use Cross-Account Profile**

   ```bash
   hcloud ELB ListLoadBalancers --cli-region=<region-id> --cli-profile=cross-account
   ```

## Permission Examples for Different Scenarios

### Scenario 1: Basic Monitoring Only

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elb:loadbalancers:list",
        "elb:loadbalancers:get",
        "ces:metricData:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### Scenario 2: Full Monitoring with Alarm Management

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elb:*",
        "ces:*"
      ],
      "Resource": ["*"]
    }
  ]
}
```

### Scenario 3: Project-Specific Monitoring

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elb:loadbalancers:list",
        "elb:loadbalancers:get",
        "elb:listeners:list",
        "ces:metrics:list",
        "ces:metricData:get"
      ],
      "Resource": [
        "urn:huawei:elb:*:*:loadbalancer/*",
        "urn:huawei:ces:*:*:metric/*"
      ],
      "Condition": {
        "StringEquals": {
          "huawei:ProjectId": ["<project-id>"]
        }
      }
    }
  ]
}
```

## References

- [Huawei Cloud IAM Documentation](https://support.huaweicloud.com/iam/index.html)
- [ELB Permissions Reference](https://support.huaweicloud.com/productdesc-elb/zh-cn_topic_0171274900.html)
- [CES Permissions Reference](https://support.huaweicloud.com/productdesc-ces/ces_07_0009.html)
- [Creating Custom Policies](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)
