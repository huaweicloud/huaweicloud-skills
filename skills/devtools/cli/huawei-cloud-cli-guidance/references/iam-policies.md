# IAM Permission Policies
**Overview:**
> This document explains the permissions required for this skill based on IAM service;  
> Applicable scope: IAM permission policies, authentication, koocli, cli

## Required Permissions
This skill guides users in using koocli to manage Huawei Cloud resources, including installation, configuration initialization, formatted output, etc.  
Installing koocli itself does not require IAM permissions. Using KooCLI to call Huawei Cloud APIs requires assigning permissions according to operation type. Specific permission assignment follows these steps:  
***Important:***
1. Prioritize using Huawei Cloud official skills to manage Huawei Cloud resources, read the corresponding `../references/iam-policies` documents in Huawei Cloud official skills, and authorize as needed
2. When there is no corresponding Huawei Cloud skill, you must query help syntax to obtain corresponding command and service permission information, and authorize as needed according to help prompts.

***For all IAM function commands, you must first query help syntax to get corresponding commands, do not guess syntax structure***
```bash
# View all service help information
hcloud --help

# View all IAM service operations
hcloud IAM --help

# View detailed help for specific operation
hcloud IAM <operation> --help

# Generate parameter skeleton
hcloud IAM <operation> --skeleton

# Debug mode
hcloud IAM <operation> <parameters> --dryrun
hcloud IAM <operation> <parameters> --cli-debug
```
Permission failure handling process (MUST):
1. When any command fails due to permission error, read references/iam-policies-en.md
2. Show user the required permission list and policy JSON
3. Guide user to create custom policy and authorize in IAM console
4. Pause execution, wait for user confirmation that permissions have been granted

#### IAM Security Practices
To help you securely control access to Huawei Cloud resources, please follow recommendations for secure IAM usage.

1. Do not create access keys for Huawei account
2. Do not embed access keys in code
3. Create separate IAM users
   > If anyone needs to access resources in your Huawei account, do not share your account password with them. Instead, create separate IAM users in your account and assign appropriate permissions. Also, as the Huawei account owner, it is recommended that you do not use the account to access Huawei Cloud, but create an IAM user for yourself and grant administrative permissions to that user. Use this IAM user instead of the account for daily management work to protect account security.
4. Reasonably set access methods  
   IAM supports setting programming access and management console access methods for users. Please refer to the following instructions to set access methods for IAM users:  
   - If IAM user only needs to log into management console to access cloud services, it is recommended to choose management console access, credential type as password.
   - If IAM user only needs programming access to Huawei Cloud services, it is recommended to choose programming access, credential type as access key.
   - If IAM user needs to use password as credential for programming access (some APIs require), it is recommended to choose programming access, credential type as password.
   - If IAM user needs to verify access keys (entered by IAM user) in their console when using some cloud services, it is recommended to choose both programming access and management console access, credential type as password and access key. For example, when IAM user creates data migration using Cloud Data Migration (CDM) service in console, identity verification through access keys is required.
5. Grant minimum permissions
6. Enable virtual MFA function
7. Set strong password policy
8. Set sensitive operations
9. Regularly modify identity credentials
10. Delete unnecessary identity credentials
11. Use ECS delegation for applications running on ECS instances
12. Enable Cloud Trace Service

#### Secure Access
You can use IAM to generate identity credentials for users or applications, without sharing your account password with others. The system will allow users to securely access resources in your account through permission information carried in identity credentials.

#### Eventual Consistency
Eventual consistency means that operations you perform in IAM, such as creating users and user groups, authorizing user groups, etc., may have delayed effect due to IAM replicating data between various servers in Huawei Cloud data centers and implementing multi-region data synchronization. It is recommended that you confirm that submitted policy modifications have taken effect before performing operations.