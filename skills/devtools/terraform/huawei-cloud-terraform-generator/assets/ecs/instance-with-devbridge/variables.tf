# Variable definitions for authentication
# NOTE: AK/SK are read from environment variables (HW_ACCESS_KEY / HW_SECRET_KEY) at
# provider level — they are NOT stored in the FunctionGraph function's user_data, NOT in
# ECS user_data, and NOT written into any Terraform artifact. See ecs-devbridge-option.md
# Step 0: the DevBridge API Key is pre-created in the sandbox and passed via
# devbridge_api_key below (the function only forwards it).

variable "region_name" {
  description = "The region where the ECS instance is located"
  type        = string
}

variable "security_token" {
  description = "The security token for STS temporary credentials. Leave empty for permanent AK/SK."
  type        = string
  default     = null
  sensitive   = true
}

variable "devbridge_api_key" {
  description = "DevBridge API Key (REQUIRED — pre-create it in the sandbox before apply; see ecs-devbridge-option.md Step 0). It is passed to the FunctionGraph function which returns it directly to the ECS (function holds NO AK/SK). No default: the function never creates the key itself, so a key must always be supplied."
  type        = string
  sensitive   = true
}

# Variable definitions for resources/data sources
variable "availability_zone" {
  description = "The availability zone to which the ECS instance belongs"
  type        = string
  default     = ""
}

variable "instance_flavor_id" {
  description = "The flavor ID of the ECS instance"
  type        = string
  default     = ""
}

variable "instance_flavor_performance_type" {
  description = "The performance type of the ECS instance flavor"
  type        = string
  default     = "normal"
}

variable "instance_flavor_cpu_core_count" {
  description = "The number of the vCPUs in the ECS instance flavor"
  type        = number
  default     = 2
}

variable "instance_flavor_memory_size" {
  description = "The memory size(GB) in the ECS instance flavor"
  type        = number
  default     = 4
}

variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block of the VPC"
  type        = string
  default     = "192.168.0.0/16"
}

variable "subnet_name" {
  description = "The name of the subnet"
  type        = string
}

variable "subnet_cidr" {
  description = "The CIDR block of the subnet"
  type        = string
  default     = ""
}

variable "subnet_gateway_ip" {
  description = "The gateway IP address of the subnet"
  type        = string
  default     = ""
}

variable "security_group_name" {
  description = "The name of the security group"
  type        = string
}

variable "instance_image_id" {
  description = "The image ID of the ECS instance"
  type        = string
  default     = ""
}

variable "instance_image_name" {
  description = "The operating system of the image"
  type        = string
  default     = "Ubuntu 22.04 server 64bit"
}

variable "keypair_name" {
  description = "The keypair name for the ECS instance"
  type        = string
}

variable "keypair_public_key" {
  description = "The public key for the keypair"
  type        = string
  default     = null
}

variable "instance_name" {
  description = "The name of the ECS instance"
  type        = string
}

# --- EIP variables ---
variable "eip_type" {
  description = "The type of the EIP"
  type        = string
  default     = "5_bgp"
}

variable "bandwidth_name" {
  description = "The name of the bandwidth"
  type        = string
}

variable "bandwidth_size" {
  description = "The size of the bandwidth (Mbit/s)"
  type        = number
  default     = 5
}

variable "bandwidth_share_type" {
  description = "The share type of the bandwidth"
  type        = string
  default     = "PER"
}

variable "bandwidth_charge_mode" {
  description = "The charge mode of the bandwidth"
  type        = string
  default     = "traffic"
}

# --- IAM Agency (for ECS to invoke FunctionGraph via metadata STS) ---
variable "agency_delegated_service_name" {
  description = "The delegated service name for the IAM agency. Typically 'op_svc_ecs' for ECS cloud service agencies."
  type        = string
  default     = "op_svc_ecs"
}

# --- IAM Role mode: custom role (least privilege) or predefined role ---
variable "use_custom_role" {
  description = "true = create a custom IAM role with only functiongraph:invokeFunction permission (least privilege, requires IAM role creation permission). false = use a predefined role (broader permissions but works without IAM role creation permission)."
  type        = bool
  # Custom role with functiongraph:invokeFunction is not registered on Huawei Cloud.
  # Use predefined role instead.
  default = false
}

variable "predefined_role_name" {
  description = "The predefined role name to use when use_custom_role = false. Must be a valid Huawei Cloud predefined role that includes FunctionGraph invoke permission, e.g. 'FunctionGraph Administrator'. Only used when use_custom_role = false."
  type        = string
  default     = "FunctionGraph Administrator"
}

# --- Windows admin password ---
variable "admin_pass" {
  description = "Administrator password for Windows ECS. Required for Windows images. Ignored for Linux."
  type        = string
  default     = null
  sensitive   = true
}