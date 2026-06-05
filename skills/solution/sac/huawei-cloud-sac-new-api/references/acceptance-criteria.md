# Acceptance Criteria

Criteria for a successful NewAPI LLM Gateway deployment.

## Infrastructure

- [ ] All Terraform resources created without error (`terraform apply` exits 0)
- [ ] VPC and subnet exist with expected CIDR blocks
- [ ] Security group exists with rules for SSH (port 22) and HTTP (port 3000)
- [ ] Elastic IP assigned and reachable
- [ ] ECS instance status is `ACTIVE` (running)
- [ ] System disk attached and formatted

## Application

- [ ] NewAPI service running on port 3000
- [ ] NewAPI web UI accessible at `http://<EIP>:3000`
  (allow ~10 minutes for cloud-init)
- [ ] Docker containers running on ECS (`docker ps` shows NewAPI container)
- [ ] API endpoint responds to requests (`/api/status` returns 200)

## Cost

- [ ] Actual monthly cost aligns with the estimated price confirmed in Step 2
- [ ] Billing mode matches `charging_unit`/`charging_period` settings

## Security

- [ ] `ecs_password` meets complexity requirements (8-26 chars,
  upper + lower + digit + special)
- [ ] AK/SK stored only in `terraform.auto.tfvars.json`, not in `.tf` files
  or version control
- [ ] SSH access restricted to specified IP (configured via `remote_ip_prefix` in template)
- [ ] Security group does not expose unnecessary ports

## Cleanup

- [ ] `terraform destroy` successfully removes all resources when no longer needed
- [ ] No orphaned resources remain after destroy
- [ ] `terraform.auto.tfvars.json` is deleted after destroy
