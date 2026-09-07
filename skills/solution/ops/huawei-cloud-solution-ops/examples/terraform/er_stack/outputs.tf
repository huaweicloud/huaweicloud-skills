output "er_instance_id" {
  description = "ID of the created ER instance."
  value       = huaweicloud_er_instance.this.id
}

output "er_vpc_attachment_id" {
  description = "ID of the ER VPC attachment."
  value       = huaweicloud_er_vpc_attachment.this.id
}
