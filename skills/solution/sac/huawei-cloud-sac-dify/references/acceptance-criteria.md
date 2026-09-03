# Acceptance Criteria

Criteria for a successful Dify platform deployment.

## Infrastructure

- [ ] All Terraform resources are created without error (`terraform apply` exits 0)
- [ ] VPC and subnet exist with expected CIDR blocks
- [ ] Security group has required ingress rules for ICMP, HTTP (80), and HTTPS (443)
- [ ] Elastic IP is assigned to the ECS instance and is reachable
- [ ] ECS instance status is `ACTIVE` (running)
- [ ] ECS flavor matches the selected value (default: `t6.xlarge.2`)
- [ ] System disk size matches `system_disk_size`

## Application

- [ ] Dify UI is accessible at `http://<EIP>` (allow ~10 minutes for cloud-init)
- [ ] `terraform output -json` contains `access_instructions`
- [ ] `access_instructions` contains a valid access URL

## Cost

- [ ] Estimated price has been shown and confirmed before apply
- [ ] Billing mode matches `charging_mode` and, if prepaid, `charging_unit`/`charging_period`

## Security

- [ ] `ecs_password` meets complexity requirements
- [ ] AK/SK are stored only in environment variables or local `<workdir>/terraform.auto.tfvars.json`
- [ ] Sensitive values are not printed in clear text in variable review output
- [ ] `<workdir>/terraform.auto.tfvars.json` is not committed to version control
- [ ] `<workdir>/terraform.auto.tfvars.json` is deleted after successful destroy so credentials are not left on disk

## Cleanup

- [ ] `terraform destroy` successfully removes all managed resources when no longer needed
- [ ] No orphaned resources remain after destroy
- [ ] `<workdir>/terraform.auto.tfvars.json` is removed only after successful destroy
