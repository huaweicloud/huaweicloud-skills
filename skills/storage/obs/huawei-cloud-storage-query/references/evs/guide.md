# EVS Python Script Usage Guide

---

## cinder_list_availability_zones.py — List Availability Zones

Purpose: List availability zones.
Usage: python scripts/evs/cinder_list_availability_zones.py -h

---

### cinder_list_quotas.py — List Quotas

Purpose: List quotas.
Usage: python scripts/evs/cinder_list_quotas.py -h

---

### cinder_list_volume_transfers.py — List Volume Transfer Records

Purpose: List volume transfer records.
Usage: python scripts/evs/cinder_list_volume_transfers.py -h

---

### cinder_list_volume_types.py — List Volume Types

Purpose: List volume types.
Usage: python scripts/evs/cinder_list_volume_types.py -h

---

### cinder_show_volume_transfer.py — Show Volume Transfer Record Details

Purpose: Show volume transfer record details.
Usage: python scripts/evs/cinder_show_volume_transfer.py -h

---

### list_snapshots.py — List Volume Snapshots

Purpose: List volume snapshots.
Usage: python scripts/evs/list_snapshots.py -h

---

### list_versions.py — List EVS API Version Information

Purpose: List EVS API version information.
Usage: python scripts/evs/list_versions.py -h

> **Note:** The output includes the raw version ID (e.g. `v3.0`) and a normalized
> usable version (e.g. `v3`). Pass the normalized version as-is to `show_version.py`.

---

### list_volume_tags.py — List Tags for All Volumes

Purpose: List tags for all volumes.
Usage: python scripts/evs/list_volume_tags.py -h

---

### list_volumes.py — List Volumes

Purpose: List volumes.
Usage: python scripts/evs/list_volumes.py -h

---

### list_volumes_in_recycle.py — List Volumes in Recycle Bin

Purpose: List volumes in the recycle bin.
Usage: python scripts/evs/list_volumes_in_recycle.py -h

> **Note:** The recycle bin feature may return `403 "Can not use the recycle bin"`.
> This is an account feature restriction, not a script defect. Enable the
> **recycle bin** in the EVS console first (帐号管理 → 回收站), then re-run the script.

---

### show_recycle_policy.py — Show Recycle Bin Policy

Purpose: Show recycle bin policy.
Usage: python scripts/evs/show_recycle_policy.py -h

---

### show_snapshot.py — Show Volume Snapshot Details

Purpose: Show volume snapshot details.
Usage: python scripts/evs/show_snapshot.py -h

---

### show_version.py — Show Specified EVS API Version Information

Purpose: Show specified EVS API version information.
Usage: python scripts/evs/show_version.py -h --version v3

> **Note:** `--version` accepts both `v3` and `v3.0` formats; trailing `.0` is
> normalized automatically, so the output of `list_versions.py` can be used directly.

---

### show_volume.py — Show Volume Details

Purpose: Show volume details.
Usage: python scripts/evs/show_volume.py -h

---

### show_volume_in_recycle.py — Show Volume Details in Recycle Bin

Purpose: Show volume details in the recycle bin.
Usage: python scripts/evs/show_volume_in_recycle.py -h

> **Note:** Same as `list_volumes_in_recycle.py`, a `403` here means the recycle bin
> feature is not enabled on the account. Enable it in the EVS console before use.

---

### show_volume_tags.py — Show Tags for a Specified Volume

Purpose: Show tags for a specified volume.
Usage: python scripts/evs/show_volume_tags.py -h
