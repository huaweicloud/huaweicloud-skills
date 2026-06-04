---
name: huawei-cloud-cli-guidance
description: >-
  Provides guidance for Huawei Cloud KooCLI command-line tool operations.
  Covers KooCLI installation, IAM authentication configuration, access credential configuration, command construction, common error troubleshooting.
  Use this skill when users ask about any cloud-related services or wants to operate Huawei Cloud services from the terminal.
  Triggers: Huawei Cloud, huaweiyun, "华为云"，"华为cli", "命令行"， KooCLI, hcloud, huaweiyunCLI, Huawei Cloud command line, OBS, ECS, VPC, "云", yun， huaweiyun tool, huawei tool, "华为云工具", "云工具", "工具"

allowed-tools: Bash, KooCLI
tags: [KooCLI, Huawei Cloud, cli, command line]
---

# huawei cloud cli guidance

## Overview

Huawei Cloud KooCLI command-line tool guidance skill, providing comprehensive KooCLI usage guide. This skill covers core functionalities including KooCLI installation, authentication configuration, command construction, common error troubleshooting, helping users efficiently manage Huawei Cloud resources.

## Attention 
1. Any issues encountered during the use of koocli must be addressed by prioritizing the guidance steps provided in this skill. [MUST][IMPORTANT]
2. It is essential to read this document in its entirety and make full use of its guidance during the process.[MUST][IMPORTANT]


## Prerequisites

- **KooCLI Version**: 7.2.2 or higher
- **Huawei Cloud Account**: Valid Huawei Cloud account with corresponding access permissions
- **Authentication Credentials**: Access Key (AK) and Secret Key (SK) or IAM user credentials
- **Network Connection**: Accessible Huawei Cloud service endpoints
- **Operating System**: Linux, macOS, or Windows (WSL supported)

## KooCLI Command Format Standard

Huawei Cloud KooCLI adopts a unified command format:
```bash
hcloud <service> <operation> [parameters] [options]
```

### Command Structure
- `hcloud`: Command-line tool name
- `<service>`: Cloud service name (e.g., ECS, VPC, OBS, etc.)
- `<operation>`: API operation name (e.g., ListInstances, CreateVpc, etc.)
- `[parameters]`: Operation parameters (e.g., instance_id, vpc_name, etc.)
- `[options]`: Global options (e.g., --cli-region, --cli-output, etc.)

### Parameter Format Rules
1. **Required parameters**: Directly specified in the command, e.g., `--instance_id i-12345678`
2. **Optional parameters**: Represented with square brackets, e.g., `[--description "instance description"]`
3. **Authentication parameters**: Use `--cli-` prefix, e.g., `--cli-profile`, `--cli-region`
4. **Output parameters**: Use `--cli-output` to specify output format (json/table/tsv)
5. **Query parameters**: Use `--cli-query` to perform JMESPath query filtering

## Scenario Routing

### Installation Scenario
1. User asks about KooCLI installation → Jump to "1. Install KooCLI"
2. User needs to verify installation → Check version command `hcloud version`

### Authentication Scenario
1. User needs to configure authentication → Jump to "2. Configure koocli"
2. User asks about different authentication modes → Choose Profile mode, explicit parameter mode, etc. based on requirements

### Command Execution Scenario
1. User needs to execute specific operations → Guide to use `hcloud <service> --help` to query available operations
2. User encounters errors → Jump to "8. Common issues" for troubleshooting

### Output Formatting Scenario
1. User needs specific format output → Use `--cli-output=json/table/tsv`
2. User needs to filter results → Use `--cli-query` for JMESPath querying

## Core Commands

#### refer to '../references/core-commands.md'

## Architecture:
```markdown
Cloud Service OpenAPI
    |
    | ECS API / VPC API / RDS API / OBS API / IAM API ...
    v
Service Metadata JSON API Definition
    |
    | Description:
    | - Service name
    | - API version
    | - Request method GET / POST / PUT / DELETE...
    | - URI path
    | - Request parameters
    | - Response structure
    | - Authentication method
    | - Region and Endpoint
    v
KooCLI Core
    |
    | Read metadata
    | Generate commands
    | Validate parameters
    | Assemble HTTP requests
    | Signature authentication
    | Call OpenAPI
    v
Dynamically Generated Commands
    |
    | hcloud <service name> <API operation name> [parameters]
    v
Unified Execution Engine
    |
    | Execute requests
    | Return results
    v
Huawei Cloud Resource Operation Results
```

#### Understand the logic and process of KooCLI managing Huawei Cloud resources. Every time Huawei Cloud service is called or problems are encountered during the process, you must refer to and understand the architecture again, clarifying current steps and subsequent steps. [Required]

## Applicable Scenarios
1. Install koocli
2. Configure IAM, AK, SK, region, profile
3. Manage Huawei Cloud resources

## 1. Install KooCLI

1. Check local version
```bash
hcloud version
```
##### Expected output: Current KooCLI version: 7.2.2 or higher.

2. One-click installation (skip this step if local version check passes)

```bash
# Universal for all platforms
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh

# Non-interactive installation
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o ./hcloud_install.sh && bash ./hcloud_install.sh -y
```
##### After installation completes, check if local installation was successful.
Important: No additional operations allowed!!! Any file content changes must obtain user permission.

**If more detailed installation guidance is needed, refer to `./references/installation-guide.md`**

## 2. Configure koocli

### Credential Configuration

***After koocli download is complete, ask the user which way they want to use koocli*** [Required]
#### 1. koocli provides a configuration-free usage method, only requiring passing current user authentication-related parameters directly in commands.

#### 2. If the user chooses non-interactive method to add configuration items, execute hcloud configure init, guide the user to input each parameter value.

When using koocli to manage Huawei Cloud resources requires other permissions, refer to '../references/iam-policies.md'

#### 3. ecsAgency 
When the user has successfully established a delegation to Elastic Cloud Server (ECS), when using KooCLI within the ECS server, you can specify "--cli-mode=ecsAgency" in commands. KooCLI will automatically obtain temporary AK/SK and SecurityToken for authentication based on ECS delegation.

#### 4. AssumeRole 
When the delegator user creates a delegation and hands over resources to another account for management, the delegatee can add "--cli-agency-domain-id"/"--cli-agency-domain-name", "--cli-agency-name" and "--cli-source-profile" options to commands, using the configuration-free method to AssumeRole and call cloud service APIs, managing and using the delegator's resources:
```markdown
hcloud VPC ListAddressGroup/v3 --cli-region="cn-north-4" --project_id="2cc60****************caefa5019ef" --cli-agency-domain-id=13534326******************5cf67b --cli-agency-name=****** --cli-source-profile=test
{
  "request_id": "29ec21****************6d6b4cdd82",
  "address_groups": [],
  "page_info": {
  "current_count": 0
   }
}
```

#### 5. SSO Login
KooCLI's SSO login command stores user authentication information in configuration files by completing SSO login, avoiding frequent input of these fixed information during operation execution. SSO login can be performed with the following command:
hcloud configure sso
```bash
# SSO profile name (configuration item name to save after SSO login, required), SSO start URL (user portal URL, required), SSO region (region where IAM Identity Center is opened, required), Region (default or commonly used region, optional)
hcloud configure sso
? Input SSO profile name [required]:  sso
? Input SSO start URL [required]:  https://idcenter.huaweicloud.com/d-3********6/portal
? Input SSO region [required]:  cn-north-4
? Input Region:  cn-north-4
Browser page has been opened, waiting for you to complete SSO login...
? Choose account name: ACCOUNT_01
? Choose permission set name: PERMISSION_01
SSO login successful
```

#### 6. Authentication Modes
KooCLI configuration item authentication mode values are AKSK, ecsAgency, SSO, AssumeRole. AKSK is recommended. When the configuration item being used has multiple authentication mode-related parameters configured simultaneously, use the "--cli-mode" option to specify the configuration item's authentication mode:
>When setting configuration items, you need to specify the configuration item name with "--cli-profile", and also add corresponding authentication parameters based on the authentication mode "--cli-mode":
>
>If the configuration item's authentication mode is "AKSK", then the values of "--cli-access-key" and "--cli-secret-key" in the configuration command cannot be empty;  
>If the configuration item's authentication mode is "ecsAgency", then specify "--cli-mode=ecsAgency" in the configuration command;  
>If the configuration item's authentication mode is "SSO", then the values of "--cli-sso-start-url" and "--cli-sso-region" in the configuration command cannot be empty;  
>If the configuration item's authentication mode is "AssumeRole", then the values of "--cli-agency-domain-id"/"--cli-agency-domain-name", "--cli-agency-name", "--cli-source-profile" in the configuration command cannot be empty.  

#### 7. Authentication Mode Selection
Use and only use one authentication method:

| Mode | Applicable Scenario | Start Command | Cleanup |
|------|----------|----------|------|
| **Profile Mode** | Agent sessions, multiple calls | `hcloud configure init --cli-profile agent-profile` | Temporary profiles need cleanup |
| **Explicit Parameter Mode** | One-time commands, CI/CD | Pass authentication parameters in each command | No local configuration |
| **Existing Profile Mode** | User already configured | `--cli-profile <profile-name>` | Do not modify configuration |

##### Profile Mode Configuration
```bash
# Create dedicated profile
hcloud configure init --cli-profile agent-profile

# View configuration
hcloud configure list

# Execute commands using profile
hcloud <service> <operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=json
```

##### Explicit Parameter Mode
```bash
# Using permanent AK/SK
hcloud <service> <operation> \
  --cli-access-key <AccessKeyId> \
  --cli-secret-key <SecretAccessKey> \
  --cli-region cn-north-4

# Using temporary credentials
hcloud <service> <operation> \
  --cli-access-key <AccessKeyId> \
  --cli-secret-key <SecretAccessKey> \
  --cli-security-token <SecurityToken> \
  --cli-region cn-north-4
```

##### Multi-Environment Management
Create independent profiles for different environments:
- `dev`: Development environment
- `test`: Test environment  
- `prod`: Production environment

Explicitly specify when calling:
```bash
hcloud <service> <operation> \
  --cli-profile dev \
  --cli-region cn-north-4
```

## 3. Consult `--help` before constructing any command

##### Help output is the authoritative source. [Important]
Execute help output as follows:
1. Use `hcloud --help` command to query the list of cloud services supported by KooCLI. After obtaining accurate cloud service names, proceed to next step.
2. Use `hcloud <service> --help` command to query the service's `operation` list. Find out what operations the service has, obtain the operation the user needs, then continue.
3. Use `hcloud <service> <operation> --help` to query the help information for the specific cloud service `operation`.
4. After executing the API call command, print the output result to the user

## 4. Ensure service availability

#### When users ask about or want to execute corresponding service management, you should also execute the previous step's help query to ensure the service exists and is available.

## 5. OBS usage commands
In KooCLI, some functionality of the `obsutil` tool for managing OBS data via command line has been integrated. Specific functions and commands strictly refer to and execute according to the help output steps mentioned above.  
If the operation is not found, you need to prompt the user to install `obsutil` to obtain complete functionality and explain the reason.

*** OBS Command Explanation: ***
```markdown
OBS-related commands in KooCLI may exist in two forms:
1. OpenAPI style:
   hcloud OBS <operation>
2. OBS integrated commands / obsutil style:
   hcloud obs <command>
The two have different parameter systems, must check help separately before execution:
hcloud OBS --help
hcloud OBS <operation> --help
hcloud obs help
hcloud obs help <command>
```

## 6. Filter and format output

KooCLI supports three output formats: json, table, tsv. Default output is in json format.  
You can use the "--cli-output" parameter to specify any of the aforementioned output formats, and you can also use the "--cli-query" option with JMESPath expression to perform JMESPath query on json results, filtering out information the user needs.

| Parameter | Parameter Purpose |
|----|------------------------------------------------|
| cli-output | cli-o response data output format, can be one of: json, table, tsv |
| cli-query | cli-query JMESPath path for filtering response data |
| cli-output-num | cli-output-num whether to print line numbers in table output. Values: true or false |

### Output Format Control
```bash
# JSON format (recommended for Agent)
hcloud <service> <operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=json

# Table format (suitable for manual viewing)
hcloud <service> <operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=table

# Text format
hcloud <service> <operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=text
```

### JMESPath Filtering
Use `--cli-query` to extract specific fields:
```bash
# Extract specific fields
hcloud <service> <list-operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=json \
  --cli-query "items[].{ID:id,Name:name,Status:status}"

# Filter specific status
hcloud <service> <list-operation> \
  --cli-profile agent-profile \
  --cli-region cn-north-4 \
  --cli-output=json \
  --cli-query "items[?status=='ACTIVE'].{ID:id,Name:name,Status:status}"
```
***Note:*** JMESPath query fields must be written according to actual JSON return structure, cannot assume all list interfaces return items.

## 7. Debugging

When troubleshooting KooCLI command failures, first add `--cli-debug=true` after the specific execution command to view underlying requests, responses, endpoints, parameter parsing, and authentication-related information.

## 8. Common issues
KooCLI divides errors encountered during command calls into five types, declaring their specific type at the beginning of error prompt messages. The positioning methods for various errors are as follows:

1. [NETWORK_ERROR]: Usually HTTP request exceptions, please check network connection;  
2. [CLI_ERROR]: Usually errors caused by KooCLI's own exceptions during command processing, please contact KooCLI oncall for assistance;  
3. [USE_ERROR]: Usually errors caused by incorrect parameters in commands, please make corresponding modifications according to error prompts;  
4. [OPENAPI_ERROR]: Usually errors occurring when calling cloud service APIs, please contact relevant cloud service oncall for assistance;  
5. [APIE_ERROR]: Usually errors occurring when calling API Explorer to obtain metadata, please contact API Explorer cloud service oncall for assistance.  

When encountering errors, query help based on error type and interact with users step by step to resolve.

## 9. Security
### Credential Security
1. **Never expose AK/SK values in conversations or commands** (`echo $ACCESS_KEY_ID` is prohibited)
2. **Never let users directly input AK/SK in conversations**
3. **Never use `hcloud configure set` to pass plaintext credentials**
4. **Only use `hcloud configure list` to check credential status**
5. **Cloud environments recommend using IAM users rather than main accounts**
6. **Enable MFA (Multi-Factor Authentication) for sensitive operations**

### Operation Security
1. **Must obtain user confirmation before modification operations** (security group rules, restart, deletion, etc.)
2. **Prefer read-only APIs**, avoid modifying resource status
3. **Production environment operations require risk warnings**
4. **Sensitive information must never appear in report output** (AK/SK, passwords, etc.)

### Configuration Security
- Use independent profiles for different environments
- Regularly rotate credentials
- Use principle of least privilege
- Clean up temporary profiles
- Encrypt sensitive configuration information

## Parameter Verification

### Global Parameters
| Parameter | Description | Example |
|------|------|------|
| `--cli-profile` | Configuration file name | `--cli-profile dev` |
| `--cli-region` | Region | `--cli-region cn-north-4` |
| `--cli-output` | Output format | `--cli-output=json` |
| `--cli-query` | JMESPath query | `--cli-query "items[].{ID:id,Name:name}"` |
| `--cli-debug` | Debug mode | `--cli-debug=true` |

### Authentication Parameters
| Authentication Mode | Required Parameters | Optional Parameters |
|----------|----------|----------|
| **AKSK** | `--cli-access-key`, `--cli-secret-key` | `--cli-security-token` |
| **Profile** | `--cli-profile` | `--cli-mode`, `--cli-region` |
| **ECS Agency** | `--cli-mode=ecsAgency` | `--cli-region` |
| **SSO** | `--cli-sso-start-url`, `--cli-sso-region` | `--cli-profile`, `--cli-region` |
| **AssumeRole** | `--cli-agency-domain-id`, `--cli-agency-name`, `--cli-source-profile` | `--cli-region` |

### Service-Specific Parameters
Use `hcloud <service> <operation> --help` to view parameter list for specific operations.

## Output Format

KooCLI supports three output formats:

### JSON Format (Default)
```bash
hcloud ECS ListInstances/v3 --cli-region=cn-north-4 --cli-output=json
```
**Applicable Scenarios**: Automated scripts, API integration, data extraction

### Table Format
```bash
hcloud ECS ListInstances/v3 --cli-region=cn-north-4 --cli-output=table
```
**Applicable Scenarios**: Manual viewing, quick browsing

### TSV Format
```bash
hcloud ECS ListInstances/v3 --cli-region=cn-north-4 --cli-output=tsv
```
**Applicable Scenarios**: Import to spreadsheets, data processing

### JMESPath Query
```bash
hcloud ECS ListInstances/v3 --cli-region=cn-north-4 --cli-output=json --cli-query "servers[?status=='ACTIVE'].{ID:id,Name:name,Status:status}"
```

## Verification Methods

### Installation Verification
1. **Version check**: `hcloud version` should return 7.2.2 or higher
2. **Help verification**: `hcloud --help` should display available service list

### Authentication Verification
1. **Profile verification**: `hcloud configure list` displays configured profile
2. **Permission verification**: `hcloud IAM ListUsers/v3 --cli-profile <profile>` tests IAM permissions

### Command Verification
1. **Help verification**: Execute `hcloud <service> --help` for each service to confirm available operations
2. **Parameter verification**: Use `--cli-debug=true` to view parameter parsing results
3. **Response verification**: Check HTTP status codes and error messages returned by commands

### Environment Verification
1. **Network connectivity**: `curl -s https://ecs.cn-north-4.myhuaweicloud.com` tests service endpoint
2. **Certificate verification**: Ensure system clock synchronization, certificates are valid

## Best Practices

### Authentication Management
1. **Use Profile mode** for long-term session management
2. **Create independent Profiles** for different environments (dev/test/prod)
3. **Regularly rotate AK/SK**, avoid using the same credentials long-term
4. **Use IAM users instead of main account** for daily operations

### Command Construction
1. **First query help**: `hcloud <service> --help` → `hcloud <service> <operation> --help`
2. **Use `--cli-debug=true`** for initial command debugging
3. **Gradually add parameters**, avoid constructing complex commands at once
4. **Use `--cli-query`** to filter and format output

### Error Handling
1. **Read error type prefixes**: [NETWORK_ERROR], [CLI_ERROR], [USE_ERROR], [OPENAPI_ERROR], [APIE_ERROR]
2. **Check network connectivity**: for [NETWORK_ERROR]
3. **Verify parameter format**: for [USE_ERROR]
4. **Check API documentation**: for [OPENAPI_ERROR]

### Performance Optimization
1. **Use `--cli-output=json`** for automated processing
2. **Properly use `--cli-query`** to reduce data transfer
3. **Use scripts instead of interactive commands** for batch operations
4. **Cache frequently used configurations** to avoid repetitive input

## Notes

### Usage Limitations
1. **Version compatibility**: Ensure KooCLI version is compatible with service API versions
2. **Regional restrictions**: Some services are only available in specific regions
3. **API quotas**: Pay attention to API call frequency limits
4. **Network requirements**: Some operations require specific network environments

### Common Pitfalls
1. **Parameter order**: Some services are sensitive to parameter order
2. **JSON format**: Complex parameters require correct JSON format
3. **Region settings**: Forgetting to set `--cli-region` results in operations in default region
4. **Output parsing**: Table format output may be truncated due to terminal width

### Troubleshooting
1. **Enable debugging**: `--cli-debug=true` displays detailed request information
2. **Check logs**: View log files in `~/.hcloud/logs/`
3. **Version check**: Ensure KooCLI version is up to date
4. **Network diagnostics**: Use `curl` to test service endpoint reachability

## Reference Documents

- `./references/installation-guide.md` — Installation guide
- `./references/cli-troubleshooting.md` — Error troubleshooting
- `./references/common-workflows.md` — Common workflows
- `./references/parameter-format.md` — Parameter format rules
- `./references/service-catalog.md` — Service catalog
- `./references/iam-policies.md` — IAM policies
- `./references/acceptance-criteria.md` — Acceptance criteria
- `./references/core-commands.md` — Core commands

