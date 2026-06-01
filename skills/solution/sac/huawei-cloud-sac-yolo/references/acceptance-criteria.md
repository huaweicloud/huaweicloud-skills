# Acceptance Criteria

Criteria for a successful YOLO training platform deployment.

## Infrastructure

- [ ] All Terraform resources created without error (`terraform apply` exits 0)
- [ ] VPC and subnet exist with expected CIDR blocks
- [ ] Security group exists with rules for ICMP, SSH (port 22), and HTTP (port 8001)
- [ ] Elastic IP assigned and reachable
- [ ] ECS instance status is `ACTIVE` (running)
- [ ] ECS flavor matches the selected GPU type (default: `p2s.2xlarge.8`)
- [ ] System disk (100 GB) and data disk (500 GB) attached
- [ ] CBR backup vault and policy created with correct schedule

## Application

- [ ] YOLO training platform UI accessible at `http://<EIP>:8001`
  (allow ~10 minutes for cloud-init)
- [ ] Docker containers running on ECS (`docker ps` shows GPU-related containers)
- [ ] `access_instructions` output contains a valid URL

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
