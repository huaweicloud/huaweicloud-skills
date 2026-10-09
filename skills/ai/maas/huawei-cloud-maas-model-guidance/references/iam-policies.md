# IAM Policies - MaaS Model Invocation

This document describes the IAM (Identity and Access Management) policies and authorization configuration required for using MaaS services.

## 1. Overview

MaaS service access authorization is managed through ModelArts. When a user already has ModelArts access authorization, no separate MaaS authorization is needed. When a user does not have ModelArts access authorization, it must be configured before using MaaS services.

ModelArts needs to access other services on behalf of the user (e.g., OBS for training data), which requires a "delegation" process - the user authorizes ModelArts to access specific cloud services on their behalf.

## 2. Authorization Methods

### 2.1 One-click Auto Authorization (Recommended for Individual Users)

This is the simplest and fastest way to get started with MaaS.

**Steps**:
1. Log in to ModelArts management console
2. Navigate to authorization:
   - New version: Left sidebar → "Permission Management"
   - Old version: Left sidebar → "System Management > Permission Management"
3. Click "Add Authorization" on the right side
4. Configure authorization:
   - **Authorization Object Type**: Select "All Users" for individual users
   - **Delegation Selection**: Select "New Delegation" for first-time users
   - **New Delegation > Permission Configuration > Normal Mode**: Select "MaaS" permission template
5. Click "Create", enter "YES", click "OK"

**Note**: The one-click auto authorization creates a delegation with broad permissions. If your Huawei Cloud account already meets your requirements, you don't need to create a separate IAM user.

### 2.2 Fine-grained IAM Authorization (For Enterprise Users)

For enterprises requiring precise permission control, create IAM users with fine-grained permissions.

#### Step 1: Create User Group

1. Admin logs in to IAM console → "User Groups"
2. Click "Create User Group", enter name and description, click "OK"

#### Step 2: Configure User Group Permissions

1. Click "Authorize" for the new user group
2. Configure ModelArts permissions (choose one):
   - **ModelArts CommonOperations** (Recommended): No create/update/delete permissions for dedicated resource pools, only usage permissions
   - **ModelArts FullAccess**: Includes create/update/delete permissions for dedicated resource pools (use cautiously)
3. Configure dependent service permissions (see Section 3)
4. Click "Next" → "Expand Other Schemes" → "Specify Region Project Resources" → select region → "OK"
5. Authorization takes 15-30 minutes to take effect

#### Step 3: Create IAM Sub-user

1. Admin logs in to IAM console → "Users"
2. Click "Create User", fill in user info, select "Management Console Access" as access method
3. Add the sub-user to the user group created in Step 1

#### Step 4: Verify Permissions

1. Sub-user logs in to Huawei Cloud
2. Verify ModelArts access in the authorized region
3. Verify OBS access if applicable

## 3. Required Service Permissions

### 3.1 Mandatory Permissions

| Service | Description | IAM Policy | Policy Type |
|---------|-------------|------------|-------------|
| ModelArts | Use ModelArts service | ModelArts CommonOperations | System Policy |
| OBS (Object Storage) | Data management, development environment, training, and model deployment all require OBS for data transfer | OBS OperateAccess | System Policy |
| SWR (Container Registry) | Custom image functionality depends on SWR | SWR OperateAccess | System Policy |
| CES (Cloud Eye Service) | View ModelArts online service status and monitoring | CES FullAccess | System Policy |
| SMN (Simple Message Notification) | Used with CES monitoring alerts | SMN FullAccess | System Policy |

### 3.2 Optional Permissions

| Service | Description | IAM Policy | Policy Type |
|---------|-------------|------------|-------------|
| ModelArts | Create/update/delete dedicated resource pools | ModelArts FullAccess | System Policy |
| VPC (Virtual Private Cloud) | Custom network configuration for dedicated resource pools | VPC FullAccess | System Policy |

### 3.3 Required Custom Policy for IAM

IAM sub-users require a custom policy to detect missing delegation permissions:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:permissions:listRolesForAgencyOnDomain",
        "iam:permissions:listRolesForAgencyOnProject",
        "iam:permissions:listRolesForAgency",
        "iam:agencies:getAgency",
        "iam:agencies:listAgencies"
      ]
    }
  ]
}
```

If this policy is not configured, IAM sub-users will see a permission missing popup when entering the MaaS console.

## 4. Delegation Authorization Configuration

### 4.1 Authorization Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| Authorization Object Type | IAM sub-user, federated user, delegated user, all users | Select "IAM sub-user" |
| Authorization Object | The specific user to authorize | Select the target IAM sub-user |
| Delegation Selection | Existing delegation or new delegation | Select "New Delegation" for first-time users |
| New Delegation > Delegation Name | System auto-generates, can be modified manually | - |
| New Delegation > Permission Configuration > Normal Mode | Select "MaaS" permission template | Select "MaaS" |

### 4.2 Constraints and Limitations

- Only Huawei Cloud accounts can use delegation authorization
- Multiple IAM users can use the same delegation
- Maximum 100 delegations per account
- IAM sub-users with admin permissions can also configure delegation authorization for themselves or other sub-users
- If a sub-user hasn't received delegation authorization, they must contact their admin account

## 5. Managing Missing Permissions

### 5.1 Scenario 1: Missing Dependency Service Authorization

If MaaS console shows a dependency service authorization prompt:
- **Main user**: Click the link to navigate to ModelArts "Permission Management" page and add the dependency service permissions
- **Sub-user**: Contact the administrator to configure

### 5.2 Scenario 2: Main User Missing Permissions

If the main user has insufficient permissions:
1. Click the link in the prompt
2. In "Service Permission Missing" dialog, choose "Append to Existing Permissions" or "Configure New Authorization"
3. Click "OK"

### 5.3 Scenario 3: Sub-user Missing Permissions

If a sub-user sees "Access Restricted" dialog:
1. Sub-user clicks "One-click Copy" to save the missing permission content
2. Administrator creates a custom policy in IAM console with the copied content
3. Administrator adds the custom policy to the sub-user's user group
4. Sub-user verifies the permission in MaaS console

## 6. API Key Permission Management

### 6.1 Strict Authorization Mode

When the administrator hasn't configured API Key operation permissions for IAM sub-users, MaaS follows the ModelArts console's "Strict Authorization Mode" switch:

- **Strict mode ON**: Sub-users without API Key permissions cannot manage API Keys
- **Strict mode OFF**: Sub-users without API Key permissions can manage API Keys

### 6.2 Configuring API Key Permissions for Sub-users

1. Administrator creates a custom policy in IAM console
2. Administrator adds the custom policy to the target user group
3. Sub-user is added to the user group

## 7. Billing for Authorization

- IAM service itself is free - no charges for authorization operations
- Charges apply only for resources used (compute, storage, etc.)
- For billing details, see: https://www.huaweicloud.com/pricing/calculator.html#/maas

## 8. Common Questions

**Q: How to configure authorization for first-time ModelArts usage?**
A: Simply select "New Delegation" with "Normal User" permissions. This includes all necessary function permissions for using ModelArts.

**Q: How to obtain AK/SK access keys?**
A: See [How to Obtain Access Keys](https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html)

**Q: How to delete an existing delegation?**
A: Navigate to IAM console → Delegations page to delete. See [Delete or Modify a Delegation](https://support.huaweicloud.com/usermanual-iam/iam_08_0004.html)

**Q: Why does MaaS console show "Insufficient Permissions"?**
A: Possible reasons: insufficient delegation permissions or module capability upgrade. Follow the console prompt to add the missing authorization.
