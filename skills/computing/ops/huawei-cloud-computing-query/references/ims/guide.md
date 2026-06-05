# IMS Python Script Usage Guide

---

### list_images.py — Query Image List

Purpose: Query the list of IMS images, including ID, name, OS type, OS bit, status, imagetype, visibility.
Usage: python scripts/ims/list_images.py -h

---

### list_image_by_tags.py — Query Images by Tag

Purpose: Query IMS images by tag, including resource ID, resource name, and status.
Usage: python scripts/ims/list_image_by_tags.py -h

---

### list_image_members.py — Query Image Member List

Purpose: Query the list of IMS image members, including member_id, status, member_type, and creation time.
Usage: python scripts/ims/list_image_members.py -h

---

### list_image_tags.py — Query Image Tags

Purpose: Query IMS image tags, including key and value.
Usage: python scripts/ims/list_image_tags.py -h

---

### list_images_tags.py — Query All Tenant Image Tags

Purpose: Query all IMS image tags for a tenant, including key and values.
Usage: python scripts/ims/list_images_tags.py -h

---

### list_os_versions.py — Query OS Version List Supported by Images

Purpose: Query the list of OS versions supported by IMS images, including platform, os_version_key, OS version, OS bit, and OS type.
Usage: python scripts/ims/list_os_versions.py -h

---

### list_tags.py — Query Tenant Image Tag List

Purpose: Query the list of tenant IMS image tags, including tag.
Usage: python scripts/ims/list_tags.py -h

---

### show_image_quota.py — Query Image Quota

Purpose: Query IMS image quota, including type, used, quota, minimum, and maximum.
Usage: python scripts/ims/show_image_quota.py -h

---

### show_job.py — Query Asynchronous Task Information

Purpose: Query IMS asynchronous task information.
Usage: python scripts/ims/show_job.py -h

---

### show_job_progress.py — Query Asynchronous Task Progress

Purpose: Query IMS asynchronous task progress.
Usage: python scripts/ims/show_job_progress.py -h

---

### show_image.py — Query Image Details

Purpose: Query IMS image details, including id, name, status, visibility, imagetype, protected, os_type, os_bit, os_version, platform, disk_format, min_disk, min_ram, image_size, created_at, updated_at, support_kvm, support_xen, etc.
Usage: python scripts/ims/show_image.py -h

---

### show_image_member.py — Query Image Member Details

Purpose: Query IMS image member details, including image_id, member_id, status, member_type, created_at, updated_at.
Usage: python scripts/ims/show_image_member.py -h
