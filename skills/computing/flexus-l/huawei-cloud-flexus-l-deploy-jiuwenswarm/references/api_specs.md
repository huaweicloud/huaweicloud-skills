# API Specification

## Huawei Cloud Service Endpoints

### Flexus L Service
- **Endpoint**: `https://hcss.cn-north-4.myhuaweicloud.com/v1/light-instances`
- **Method**: POST
- **Purpose**: Create Flexus L instance

### IAM Service
- **Endpoint**: `https://iam.{region}.myhuaweicloud.com/v3/projects`
- **Method**: GET
- **Purpose**: Get Project ID

### RMS Service
- **Endpoint**: `https://rms.{region}.myhuaweicloud.com/v1/resource-manager/domains/{domain_id}/resources`
- **Method**: GET
- **Purpose**: Query resource information

### COC Service
- **Endpoint**: `https://coc.{region}.myhuaweicloud.com`
- **Method**: POST
- **Purpose**: Remote script execution

## Flexus L Instance Specifications

| Name | Resource ID | CPU | Memory |
|------|-------------|-----|--------|
| small | hf.small.1.linux | 1 Core | 2GB |
| medium | hf.medium.1.linux | 2 Core | 4GB |
| large | hf.large.1.linux | 4 Core | 8GB |
| xlarge | hf.xlarge.1.linux | 8 Core | 16GB |
| 2xlarge | hf.2xlarge.1.linux | 16 Core | 32GB |

## COC Script Execution Status

| Status | Description |
|--------|-------------|
| PROCESSING | Running |
| FINISHED | Completed |
| ABNORMAL | Abnormal |

## Security Group Rules

The following ports need to be opened:
- **5173**: JiuwenSwarm Web service port
- **22**: SSH remote access port

## API Authentication

Using Huawei Cloud SDK for signature authentication:
1. Set environment variables `HUAWEICLOUD_SDK_AK` and `HUAWEICLOUD_SDK_SK`
2. SDK automatically handles request signing
3. Region configuration supported via `HUAWEICLOUD_REGION` environment variable
