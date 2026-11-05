# Huawei Cloud MGC/SMS Cross-Region Migration (Mexico City2 -> Santiago)

This Terraform package executes migration via OpenAPI calls:

1. `POST /v3/privacy-agreements` (service onboarding/authorization acceptance)
2. `POST /v3/migprojects`
3. `GET /v3/sources?id=<source_server_id>`
4. `POST /v1.1/{project_id}/cloudservers` (create target ECS in `vpc-migration` and bind EIP)
5. `POST /v3/tasks`
6. `POST /v3/tasks/{task_id}/action` with `operation=start`

## Preconditions

- Source server has been registered in SMS/MgC and is `available/connected` (`/v3/sources` can query it).
  - If you provide an ECS ID, the script will also try `/v3/sources?vm_id=<ecs_id>`.
- AK/SK has permissions for IAM, SMS, ECS, and VPC APIs.
- Destination image ID (`target_image_id`) is available in `la-south-2`.
- If target VPC may be auto-created, target-region VPC quota must have free capacity.

## Usage

```bash
cd skills/migrationom/oos/huawei-cloud-mgc-migration-ecs-gcp-to-hw
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars
terraform init
terraform apply -auto-approve
```

Result file:

- `out/migration_result.json`

For in-flight tasks, always verify current state by querying SMS task detail/API.

## Notes

- MgC and SMS are free. Billing is for dependent resources used during migration (ECS/EIP/EVS/snapshots/bandwidth, etc.).
- `domain_name` is kept as context; AK/SK signed requests do not require it in this script.
- This script defaults to `source_region=la-north-2` (LA-Mexico City2) and `target_region=la-south-2` (LA-Santiago).
- Default target VPC is `vpc-migration`.
- EIP is created as dedicated bandwidth (`share_type=PER`) with `extendparam.chargingMode=postPaid` for ECS.

## Troubleshooting

- `VPC.0114`
  - Meaning: target region VPC quota exceeded when creating `vpc-migration`.
  - Action: delete an unused VPC or increase quota, then rerun `terraform apply -auto-approve`.

- `SMS.7703`
  - Meaning: queried `task_id` does not exist (commonly a stale ID from older output).
  - Action: do not rely on historical `out/migration_result.json`; use latest run output and live task query.

- `RUNNING` with `progress=null`
  - Meaning: SMS task progress field may be empty even when migration is active.
  - Action: keep polling task `state` until terminal (`*_SUCCESS`/`*_FAIL`) and verify target ECS status in parallel.

## Field Case (2026-04-17)

- First `terraform apply` failed with `VPC.0114` because VPC quota in `la-south-2` was full (`used=5`, `quota=5`).
- After deleting one unused VPC (`used=4`, `quota=5`), rerun succeeded.
- Final task reached `MIGRATE_SUCCESS`, target ECS became `ACTIVE`.
