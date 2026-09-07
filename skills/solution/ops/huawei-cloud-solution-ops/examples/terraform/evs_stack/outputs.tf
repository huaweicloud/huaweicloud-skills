output "volume_id" {
  description = "Created EVS volume ID."
  value       = huaweicloud_evs_volume.this.id
}

output "availability_zone" {
  description = "Availability zone selected for the EVS volume."
  value       = huaweicloud_evs_volume.this.availability_zone
}
