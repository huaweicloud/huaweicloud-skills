variable "region_name" {
  description = "Huawei Cloud region used by this stack."
  type        = string
}

variable "migration_project_name" {
  description = "Name of the SMS migration project."
  type        = string
}

variable "migration_project_region" {
  description = "Target region of the migration project."
  type        = string
}

variable "migration_project_use_public_ip" {
  description = "Whether the migration project uses a public IP address."
  type        = bool
}

variable "migration_project_exist_server" {
  description = "Whether the destination server already exists."
  type        = bool
}

variable "migration_project_type" {
  description = "Type of the migration project."
  type        = string
}

variable "migration_project_syncing" {
  description = "Whether the migration project keeps syncing after the first copy."
  type        = bool
}
