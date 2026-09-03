# Related Commands

Common commands for managing the Dify platform deployment.

## Terraform Lifecycle

| Command | Description |
| --------- | ------------- |
| `terraform init` | Initialize provider plugins and backend |
| `terraform plan` | Show execution plan (dry run) |
| `terraform apply` | Apply changes to reach desired state |
| `terraform destroy` | Destroy all managed resources; if it succeeds, delete `<temp_dir>/dify-workdir/terraform.auto.tfvars.json` |

## State Inspection

| Command | Description |
| --------- | ------------- |
| `terraform state list` | List all resources in state |
| `terraform state show <address>` | Show details of a specific resource |
| `terraform output` | Print all output values |
| `terraform output -json` | Print all output values as JSON |
| `terraform output access_instructions` | Print access instructions |

## State Manipulation

| Command | Description |
| --------- | ------------- |
| `terraform taint <address>` | Force re-creation of a resource on next apply |
| `terraform untaint <address>` | Remove taint from a resource |
| `terraform apply -refresh-only` | Update state to match real infrastructure |
| `terraform import <address> <id>` | Import an existing resource into state |

## Helper Scripts

| Command | Description |
| --------- | ------------- |
| `extract_sac_deploy_info.py --url <URL> --out <path>` | Extract price and deployment links |
| `normalize_tf_providers.py <dir>` | Normalize provider source declarations |
| `normalize_tf_providers.py <dir> --region <region>` | Normalize providers and write region to tfvars |
| `list_tf_variables.py <dir>` | List Terraform variable defaults (with masking for sensitive values) |

## Remote Access

| Command | Description |
| --------- | ------------- |
| `ssh root@<EIP>` | SSH into the ECS instance |
| `ssh root@<EIP> "docker ps"` | Check running containers |
| `ssh root@<EIP> "docker compose ps"` | Check Docker Compose services |

## Platform Access

| URL | Description |
| ----- | ------------- |
| `http://<EIP>` | Dify platform UI |

## Cost Monitoring

| Command | Description |
| --------- | ------------- |
| `terraform plan -destroy` | Preview destroy changes (resource and cost impact) |
