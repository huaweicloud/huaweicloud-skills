# SWR Enterprise Instance - Parameter Reference

## Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--instance_id` | Context-dependent | Enterprise instance ID        | N/A                                  |
| `--project_id`  | Auto-filled       | Project ID                    | Auto from credentials or config      |

## Instance Creation Parameters

| Parameter                  | Required | Description                | Constraints                                    |
| -------------------------- | -------- | -------------------------- | ---------------------------------------------- |
| `--name`                   | Yes      | Instance name              | 3-48 chars, lowercase start, no consecutive hyphens |
| `--spec`                   | Yes      | Instance spec              | `swr.ee.basic` or `swr.ee.professional`        |
| `--charge_mode`            | Yes      | Billing mode               | `postPaid` (on-demand only)                    |
| `--vpc_id`                 | Yes      | VPC ID                     | Existing VPC                                   |
| `--subnet_id`              | Yes      | Subnet ID                  | Existing subnet within VPC                     |
| `--enterprise_project_id`  | Yes      | Enterprise project ID      | Use `0` for default project                    |
| `--description`            | No       | Instance description       | Free text                                      |
| `--enable_intranet_access` | No       | Create internal access     | Default `true`                                 |
| `--obs_encrypt`            | No       | Enable OBS encryption      | `true` or `false`                              |
| `--encrypt_type`           | No       | OBS encryption algorithm   | `gm` (Chinese national encryption SM), empty for AES-256 |
| `--obs_bucket_name`        | No       | Custom OBS bucket name     | If specified, OBS encryption not needed        |
| `--obs_enc_kms_key_id`     | No       | KMS key ID for OBS         | Required if obs_encrypt=true (no custom bucket) |

## Namespace Parameters

| Parameter              | Required | Description              | Constraints                                  |
| ---------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace_name`     | Yes      | Namespace name           | 1-64 chars, lowercase/digit start            |
| `--metadata.public`    | Yes      | Public/private           | `true` or `false`                            |
| `--metadata.auto_scan` | No       | Auto scan on upload      | `true` or `false`                            |
| `--metadata.prevent_vul` | No     | Block vulnerable images  | `true` or `false`                            |
| `--metadata.severity`  | No       | Blocking severity level  | `none`, `low`, `medium`, `high`, `critical`  |

## Registry Parameters

| Parameter                   | Required | Description              | Constraints                                  |
| --------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--name`                    | Yes      | Registry display name    | 1-64 chars                                   |
| `--type`                    | Yes      | Registry type            | `swr-pro`, `swr-pro-internal`, `huawei-SWR`  |
| `--url`                     | Yes      | Registry URL             | Target registry address                      |
| `--credential.type`         | Yes      | Auth type                | `basic` only                                 |
| `--credential.access_key`   | Yes      | Access ID/username       | Auth credential                               |
| `--credential.access_secret` | Yes    | Access secret/password   | Auth credential                               |
| `--insecure`                | Yes      | Verify remote cert       | `true` (skip) or `false` (verify)            |
| `--instance_id` (body)      | Cond.    | Target instance ID       | Required when type=swr-pro-internal          |
| `--project_id` (body)       | Cond.    | Target project ID        | Required when type=swr-pro-internal          |
| `--region_id`               | Cond.    | Target region ID         | Required when type=swr-pro-internal          |

## Endpoint Whitelist Parameters

| Parameter                    | Required | Description              | Constraints                                  |
| ---------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--ip_list.[N].ip`           | Yes      | IP or CIDR range         | Indexed array format                         |
| `--ip_list.[N].description`  | No       | Description for IP entry | Indexed array format                         |