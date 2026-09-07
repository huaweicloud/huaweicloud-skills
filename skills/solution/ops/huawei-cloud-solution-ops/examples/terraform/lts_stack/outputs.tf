output "lts_group_id" {
  description = "ID of the created LTS log group."
  value       = huaweicloud_lts_group.this.id
}

output "lts_stream_id" {
  description = "ID of the created LTS log stream."
  value       = huaweicloud_lts_stream.this.id
}
