output "vault_id" {
  description = "ID of the created CBR vault."
  value       = huaweicloud_cbr_vault.this.id
}

output "vault_name" {
  description = "Name of the created CBR vault."
  value       = huaweicloud_cbr_vault.this.name
}

output "ecs_instance_id" {
  description = "ID of the ECS instance bound to the CBR vault."
  value       = huaweicloud_compute_instance.this.id
}
