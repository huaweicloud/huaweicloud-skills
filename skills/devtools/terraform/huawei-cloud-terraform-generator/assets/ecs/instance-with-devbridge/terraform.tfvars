# Authentication
# AK/SK are read from environment variables (HW_ACCESS_KEY / HW_SECRET_KEY) — they are
# NOT stored in this file, NOT in the FunctionGraph function, and NOT in any Terraform
# artifact. The DevBridge API Key is pre-created in the sandbox and passed via
# devbridge_api_key (see ecs-devbridge-option.md Step 0).
#
# For temporary/STS credentials, set security_token here (the provider does not reliably
# resolve it from env vars). For permanent AK/SK, leave it out.
region_name = "cn-north-4"
# security_token = ""

# Network
vpc_name    = "tf_devbridge_vpc"
vpc_cidr    = "192.168.0.0/16"
subnet_name = "tf_devbridge_subnet"

# Security Group (zero inbound rules — only egress)
security_group_name = "tf_devbridge_sg_no_ingress"

# ECS Instance
instance_name       = "tf_devbridge_ecs"
instance_image_name = "Ubuntu 22.04 server 64bit"
keypair_name        = "tf_devbridge_keypair"
# keypair_public_key = null  #.auto-generate if not provided

# DevBridge API Key (pre-created in the sandbox before apply)
# devbridge_api_key = ""

# EIP (for outbound access — DevBridge tunnel needs to connect out)
bandwidth_name = "tf_devbridge_bw"

# IAM Agency (ECS uses this to get STS credentials from metadata service)
# agency_delegated_service_name = "op_svc_ecs"

# IAM Role: custom (least privilege) or predefined (no IAM perms needed)
# use_custom_role = true   # default: create custom role with only functiongraph:invokeFunction
# If you get 403 on identity_role, set this to false:
# use_custom_role       = false
# predefined_role_name  = "FunctionGraph Administrator"
