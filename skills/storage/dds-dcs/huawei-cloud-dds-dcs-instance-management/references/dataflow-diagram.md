# Data Flow Diagram

```mermaid
graph TD
    User[User / Agent] --> Router{Action Router}
    
    Router -->|DDS Actions| DDS_CLI[hcloud DDS CLI]
    Router -->|DCS Actions - CLI| DCS_CLI[hcloud DCS CLI]
    Router -->|DCS Actions - SDK| DCS_SDK[huaweicloudsdkdcs SDK]
    
    DDS_CLI --> DDS_List[List DDS Instances]
    DDS_CLI --> DDS_Get[Get DDS Instance]
    DDS_CLI --> DDS_Create[Create DDS Instance]
    DDS_CLI --> DDS_AddReadonly[Add ReadOnly Node]
    DDS_CLI --> DDS_AddSharding[Add Sharding Node]
    DDS_CLI --> DDS_Backup[Create Backup]
    DDS_CLI --> DDS_Delete[Delete Instance]
    DDS_CLI --> DDS_Analyze[Deployment Analysis]
    
    DCS_CLI --> DCS_List[List DCS Instances]
    DCS_CLI --> DCS_Show[Get DCS Instance]
    DCS_CLI --> DCS_Delete[Delete DCS Instance]
    DCS_CLI --> DCS_Restart[Restart DCS Instance]
    DCS_CLI --> DCS_Analyze[Security Analysis]
    
    DCS_SDK --> DCS_Nodes[Get Node Information]
    DCS_SDK --> DCS_Templates[List|Create Templates]
    DCS_SDK --> DCS_Create[Create DCS Instance]
    
    DDS_List & DDS_Get & DDS_Create & DDS_AddReadonly --> DDS_API[Huawei Cloud DDS API]
    DDS_AddSharding & DDS_Backup & DDS_Delete --> DDS_API
    
    DCS_List & DCS_Show & DCS_Delete & DCS_Restart --> DCS_API[Huawei Cloud DCS API]
    DCS_Nodes & DCS_Templates & DCS_Create --> DCS_API
    
    DDS_API --> DDS_Result[Query Results / Operation Status]
    DCS_API --> DCS_Result[Query Results / Operation Status]
    
    DDS_Result & DCS_Result --> Formatter[Result Formatter]
    Formatter --> User
    
    subleg Authentication
        AK_SK[AK/SK Env Vars] --> hcloud_Profile[hcloud CLI Profile]
        AK_SK --> SDK_Creds[SDK BasicCredentials]
        hcloud_Profile --> DDS_CLI
        hcloud_Profile --> DCS_CLI
        SDK_Creds --> DCS_SDK
    end
```

## Execution Flow

1. **Action Router** receives the request and determines target service (DDS/DCS)
2. **CLI execution** for operations supported by hcloud CLI (most DDS + basic DCS operations)
3. **SDK fallback** for DCS operations not exposed via CLI (create instance, node info, templates)
4. **Huawei Cloud API** processes the request and returns results
5. **Result Formatter** normalizes output for the user/agent

## Authentication Flow

- AK/SK discovered from `HUAWEI_ACCESS_KEY`/`HUAWEI_SECRET_KEY` or `HWC_AK`/`HWC_SK` env vars
- CLI operations use hcloud profile or env-based authentication
- SDK operations construct `BasicCredentials` from the same env vars
- No hardcoded credentials in any script or configuration file