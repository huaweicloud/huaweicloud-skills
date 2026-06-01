# Related Commands

Common commands for managing the YOLO training platform deployment.

## Terraform Lifecycle

| Command | Description |
| --------- | ------------- |
| `terraform init` | Initialize provider plugins and backend |
| `terraform plan` | Show execution plan (dry run) |
| `terraform apply` | Apply changes to reach desired state |
| `terraform destroy` | Destroy all managed resources |

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
| `terraform untaint <address>` | Remove the taint from a resource |
| `terraform apply -refresh-only` | Update state to match real infrastructure |
| `terraform import <address> <id>` | Import an existing resource into state |

## Helper Scripts

| Command | Description |
| --------- | ------------- |
| `extract_sac_deploy_info.py --url <URL> --out <path>` | Extract price/links |
| `download_tf_template_file.py --url <URL> --out <d>` | Download TF template |
| `normalize_tf_providers.py <dir>` | Fix provider sources |
| `normalize_tf_providers.py <dir> --region <region>` | Fix providers + set region |
| `list_tf_variables.py <dir>` | List TF variable defaults |

## Remote Access

| Command | Description |
| --------- | ------------- |
| `ssh root@<EIP>` | SSH into the ECS instance |
| `ssh root@<EIP> "docker ps"` | Check running Docker containers |
| `ssh root@<EIP> "docker compose ps"` | Check Docker Compose services |
| `ssh root@<EIP> "nvidia-smi"` | Check GPU status on ECS |

## Platform Access

| URL | Description |
| ----- | ------------- |
| `http://<EIP>:8001` | YOLO training platform UI |

## Cost Monitoring

| Command | Description |
| --------- | ------------- |
| `terraform plan -destroy` | Preview destroy (cost impact) |
