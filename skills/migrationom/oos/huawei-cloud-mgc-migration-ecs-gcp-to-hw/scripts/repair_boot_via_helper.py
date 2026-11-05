#!/usr/bin/env python3
import argparse
import base64
import json
import re
import time
from pathlib import Path

from scripts.mgc_migrate import (
    HcApiClient,
    find_server_id_by_name,
    wait_ecs_job_success,
    wait_server_status,
    write_json_file,
)


def parse_tfvar(path: Path, key: str, default: str = "") -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'%s\s*=\s*"([^"]*)"' % re.escape(key), text)
    return m.group(1).strip() if m else default


def now_local() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime())


def get_target_server_id(workdir: Path) -> str:
    candidates = [
        workdir / "out" / "target_access_recovery_latest.json",
        workdir / "out" / "migration_result.json",
        workdir / "out" / "target_boot_diagnosis_latest.json",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = str(data.get("target_server_id") or "").strip()
        if sid:
            return sid
    return ""


def ecs_get_server(client: HcApiClient, region: str, project_id: str, server_id: str) -> dict:
    rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s" % (region, project_id, server_id),
    )
    return rsp.get("server") or {}


def ecs_get_server_detail_v21(client: HcApiClient, region: str, project_id: str, server_id: str) -> dict:
    rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v2.1/%s/servers/%s" % (region, project_id, server_id),
    )
    return rsp.get("server") or {}


def get_fixed_port_id(server: dict) -> str:
    addresses = server.get("addresses") or {}
    for _, items in addresses.items():
        for item in items:
            if str(item.get("OS-EXT-IPS:type") or "").lower() == "fixed":
                pid = str(item.get("OS-EXT-IPS:port_id") or "").strip()
                if pid:
                    return pid
    return ""


def get_vpc_id(server: dict) -> str:
    addresses = server.get("addresses") or {}
    for k in addresses.keys():
        if k:
            return str(k)
    return ""


def vpc_get_port(client: HcApiClient, region: str, project_id: str, port_id: str) -> dict:
    rsp = client.request_json(
        "GET",
        "https://vpc.%s.myhuaweicloud.com/v1/%s/ports/%s" % (region, project_id, port_id),
    )
    return rsp.get("port") or {}


def get_boot_volume_id(server: dict) -> str:
    vols = server.get("os-extended-volumes:volumes_attached") or []
    for v in vols:
        if str(v.get("bootIndex") or "") == "0":
            return str(v.get("id") or "").strip()
    if vols:
        return str(vols[0].get("id") or "").strip()
    return ""


def list_attached_volume_ids(server: dict) -> list:
    vols = server.get("os-extended-volumes:volumes_attached") or []
    out = []
    for v in vols:
        vid = str(v.get("id") or "").strip()
        if vid:
            out.append(vid)
    return out


def evs_get_volume(client: HcApiClient, region: str, project_id: str, volume_id: str) -> dict:
    rsp = client.request_json(
        "GET",
        "https://evs.%s.myhuaweicloud.com/v2/%s/volumes/%s" % (region, project_id, volume_id),
    )
    return rsp.get("volume") or {}


def batch_stop_server(client: HcApiClient, region: str, project_id: str, server_id: str) -> dict:
    return client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/action" % (region, project_id),
        body={"os-stop": {"servers": [{"id": server_id}], "type": "HARD"}},
    )


def batch_start_server(client: HcApiClient, region: str, project_id: str, server_id: str) -> dict:
    return client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/action" % (region, project_id),
        body={"os-start": {"servers": [{"id": server_id}]}},
    )


def batch_delete_server(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    delete_publicip: bool = True,
    delete_volume: bool = True,
) -> dict:
    return client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/delete" % (region, project_id),
        body={
            "servers": [{"id": server_id}],
            "delete_publicip": bool(delete_publicip),
            "delete_volume": bool(delete_volume),
        },
    )


def detach_volume(client: HcApiClient, region: str, project_id: str, server_id: str, volume_id: str) -> dict:
    return client.request_json(
        "DELETE",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s/detachvolume/%s"
        % (region, project_id, server_id, volume_id),
    )


def attach_volume(
    client: HcApiClient,
    region: str,
    project_id: str,
    server_id: str,
    volume_id: str,
    device: str,
) -> dict:
    body = {"volumeAttachment": {"volumeId": volume_id, "device": device}}
    return client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s/attachvolume" % (region, project_id, server_id),
        body=body,
    )


def get_console_output(client: HcApiClient, region: str, project_id: str, server_id: str, length: int = 2000) -> str:
    rsp = client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v2.1/%s/servers/%s/action" % (region, project_id, server_id),
        body={"os-getConsoleOutput": {"length": int(length)}},
    )
    return str(rsp.get("output") or "")


def get_novnc_url(client: HcApiClient, region: str, project_id: str, server_id: str) -> str:
    rsp = client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v2.1/%s/servers/%s/action" % (region, project_id, server_id),
        body={"os-getVNCConsole": {"type": "novnc"}},
    )
    return str(((rsp.get("console") or {}).get("url") or "")).strip()


def create_helper_user_data(target_root_password: str) -> str:
    pwd = str(target_root_password or "").strip()
    # Keep shell-quoted single-quoted string safe.
    pwd_escaped = pwd.replace("'", "'\"'\"'")
    script = r"""#!/bin/bash
set -euxo pipefail
exec > >(tee -a /var/log/boot-repair.log /dev/ttyS0) 2>&1
echo "[BOOT-REPAIR] helper boot $(date -Is)"

TARGET_DISK=""
for i in $(seq 1 240); do
  for d in /dev/vdb /dev/sdb; do
    if [ -b "$d" ]; then
      TARGET_DISK="$d"
      break
    fi
  done
  if [ -n "$TARGET_DISK" ]; then
    break
  fi
  sleep 5
done

if [ -z "$TARGET_DISK" ]; then
  echo "[BOOT-REPAIR] ERROR no target disk attached"
  poweroff -f
  exit 1
fi
echo "[BOOT-REPAIR] found disk $TARGET_DISK"
lsblk -o NAME,FSTYPE,SIZE,TYPE,MOUNTPOINT || true

partprobe "$TARGET_DISK" || true
udevadm settle || true
mkdir -p /mnt/target
ROOT_DEV=""

for p in ${TARGET_DISK}p* ${TARGET_DISK}[0-9]*; do
  [ -b "$p" ] || continue
  mount "$p" /mnt/target 2>/dev/null || continue
  if [ -f /mnt/target/etc/os-release ]; then
    ROOT_DEV="$p"
    break
  fi
  umount /mnt/target || true
done

if [ -z "$ROOT_DEV" ]; then
  echo "[BOOT-REPAIR] direct partition root not found, trying LVM"
  vgchange -ay || true
  for lv in /dev/mapper/*; do
    [ -b "$lv" ] || continue
    mount "$lv" /mnt/target 2>/dev/null || continue
    if [ -f /mnt/target/etc/os-release ]; then
      ROOT_DEV="$lv"
      break
    fi
    umount /mnt/target || true
  done
fi

if [ -z "$ROOT_DEV" ]; then
  echo "[BOOT-REPAIR] ERROR root filesystem not found"
  poweroff -f
  exit 2
fi
echo "[BOOT-REPAIR] root fs $ROOT_DEV"
ROOT_UUID="$(blkid -s UUID -o value "$ROOT_DEV" || true)"
echo "[BOOT-REPAIR] root uuid ${ROOT_UUID:-unknown}"

BOOT_DEV=""
EFI_DEV=""
if [ -f /mnt/target/etc/fstab ]; then
  BOOT_UUID="$(awk '$2=="/boot" {print $1}' /mnt/target/etc/fstab | sed -n '1p' | sed 's/^UUID=//')"
  EFI_UUID="$(awk '$2=="/boot/efi" {print $1}' /mnt/target/etc/fstab | sed -n '1p' | sed 's/^UUID=//')"
  if [ -n "${BOOT_UUID:-}" ]; then
    BOOT_DEV="$(blkid -U "$BOOT_UUID" || true)"
  fi
  if [ -n "${EFI_UUID:-}" ]; then
    EFI_DEV="$(blkid -U "$EFI_UUID" || true)"
  fi
fi

if [ -z "$BOOT_DEV" ]; then
  for p in ${TARGET_DISK}p* ${TARGET_DISK}[0-9]*; do
    [ -b "$p" ] || continue
    if blkid "$p" | grep -qi 'TYPE="ext'; then
      if [ "$p" != "$ROOT_DEV" ]; then
        BOOT_DEV="$p"
        break
      fi
    fi
  done
fi

if [ -z "$EFI_DEV" ]; then
  for p in ${TARGET_DISK}p* ${TARGET_DISK}[0-9]*; do
    [ -b "$p" ] || continue
    if blkid "$p" | grep -qi 'TYPE="vfat"'; then
      EFI_DEV="$p"
      break
    fi
  done
fi

if [ -n "$BOOT_DEV" ]; then
  mkdir -p /mnt/target/boot
  mount "$BOOT_DEV" /mnt/target/boot 2>/dev/null || true
  echo "[BOOT-REPAIR] boot fs $BOOT_DEV"
fi

if [ -n "$EFI_DEV" ]; then
  mkdir -p /mnt/target/boot/efi
  mount "$EFI_DEV" /mnt/target/boot/efi 2>/dev/null || true
  echo "[BOOT-REPAIR] efi fs $EFI_DEV"
fi

for d in dev proc sys run; do
  mount --bind /$d /mnt/target/$d
done

chroot /mnt/target /usr/bin/env TARGET_DISK="${TARGET_DISK}" /bin/bash -c "set -eux; mkdir -p /etc/default/grub.d; printf 'GRUB_DISABLE_LINUX_UUID=true\nGRUB_DISABLE_LINUX_PARTUUID=true\n' > /etc/default/grub.d/99-force-rootdev.cfg; mkdir -p /etc/ssh/sshd_config.d; printf 'PermitRootLogin yes\nPasswordAuthentication yes\nKbdInteractiveAuthentication yes\nChallengeResponseAuthentication no\nUsePAM yes\n' > /etc/ssh/sshd_config.d/99-codex-password-login.conf; for f in /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf; do [ -f \"\$f\" ] || continue; sed -ri 's/^#?PasswordAuthentication[[:space:]]+.*/PasswordAuthentication yes/g; s/^#?PermitRootLogin[[:space:]]+.*/PermitRootLogin yes/g; s/^#?KbdInteractiveAuthentication[[:space:]]+.*/KbdInteractiveAuthentication yes/g; s/^#?ChallengeResponseAuthentication[[:space:]]+.*/ChallengeResponseAuthentication no/g' \"\$f\" || true; done; if [ -f /etc/cloud/cloud.cfg ]; then sed -ri 's/^[[:space:]]*disable_root:[[:space:]]*.*/disable_root: false/g; s/^[[:space:]]*ssh_pwauth:[[:space:]]*.*/ssh_pwauth: true/g' /etc/cloud/cloud.cfg || true; grep -Eq '^[[:space:]]*disable_root:[[:space:]]*false[[:space:]]*$' /etc/cloud/cloud.cfg || echo 'disable_root: false' >> /etc/cloud/cloud.cfg; grep -Eq '^[[:space:]]*ssh_pwauth:[[:space:]]*true[[:space:]]*$' /etc/cloud/cloud.cfg || echo 'ssh_pwauth: true' >> /etc/cloud/cloud.cfg; fi; echo 'root:__TARGET_ROOT_PASSWORD__' | chpasswd || true; passwd -u root || true; for f in /etc/default/grub /etc/default/grub.d/*.cfg /boot/grub/grub.cfg /boot/efi/EFI/*/grub.cfg; do [ -f \"\$f\" ] || continue; sed -ri 's#/dev/vdb#/dev/vda#g; s#root=[^ ]+#root=/dev/vda1#g' \"\$f\" || true; done; if [ -d /boot/efi ] && [ -n \"\$(ls -A /boot/efi 2>/dev/null || true)\" ]; then grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu --recheck || true; grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu --removable --recheck || true; fi; grub-install --target=i386-pc ${TARGET_DISK} || grub-install --target=i386-pc --force ${TARGET_DISK} || true; update-initramfs -u || true; grub-mkconfig -o /boot/grub/grub.cfg || update-grub || true; for f in /boot/grub/grub.cfg /boot/efi/EFI/*/grub.cfg; do [ -f \"\$f\" ] || continue; sed -ri 's#root=[^ ]+#root=/dev/vda1#g' \"\$f\" || true; done; systemctl enable ssh || true; systemctl enable sshd || true"
sync
touch /mnt/target/root/BOOT_REPAIR_DONE
echo "[BOOT-REPAIR] COMPLETE"

for d in run sys proc dev; do
  umount -lf /mnt/target/$d || true
done
umount -lf /mnt/target/boot/efi || true
umount -lf /mnt/target/boot || true
umount -lf /mnt/target || true
poweroff -f
"""
    script = script.replace("__TARGET_ROOT_PASSWORD__", pwd_escaped)
    return base64.b64encode(script.encode("utf-8")).decode("ascii")


def create_helper_server(
    client: HcApiClient,
    region: str,
    project_id: str,
    helper_name: str,
    az: str,
    image_id: str,
    flavor_id: str,
    admin_password: str,
    vpc_id: str,
    subnet_id: str,
    security_group_id: str,
    root_volume_type: str,
    target_root_password: str,
) -> str:
    body = {
        "server": {
            "availability_zone": az,
            "name": helper_name,
            "imageRef": image_id,
            "flavorRef": flavor_id,
            "adminPass": admin_password,
            "vpcid": vpc_id,
            "nics": [{"subnet_id": subnet_id}],
            "root_volume": {"volumetype": root_volume_type, "size": 10},
            "security_groups": [{"id": security_group_id}],
            "user_data": create_helper_user_data(target_root_password),
            "extendparam": {"chargingMode": "postPaid"},
            "metadata": {"repair": "boot-grub"},
        }
    }
    rsp = client.request_json(
        "POST",
        "https://ecs.%s.myhuaweicloud.com/v1.1/%s/cloudservers" % (region, project_id),
        body=body,
    )
    job_id = str(rsp.get("job_id") or "").strip()
    if job_id:
        job_rsp = wait_ecs_job_success(client, region, project_id, job_id)
        ids = rsp.get("serverIds") or rsp.get("server_ids") or []
        if isinstance(ids, list):
            for sid in ids:
                if sid:
                    return str(sid)
        sid = str(((job_rsp.get("entities") or {}).get("sub_jobs") or [{}])[0].get("entities", {}).get("server_id") or "").strip()
        if sid:
            return sid
    return find_server_id_by_name(client, region, project_id, helper_name)


def wait_job_and_get_id(job_rsp: dict) -> str:
    return str(job_rsp.get("job_id") or "").strip()


def list_boot_repair_servers(client: HcApiClient, region: str, project_id: str) -> list:
    rsp = client.request_json(
        "GET",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/detail" % (region, project_id),
        params={"limit": "200"},
    )
    out = []
    for s in rsp.get("servers", []) or []:
        name = str(s.get("name") or "")
        if not name.startswith("boot-repair-"):
            continue
        out.append(s)
    return out


def cleanup_boot_repair_helpers(
    client: HcApiClient,
    region: str,
    project_id: str,
    keep_ids: list,
) -> dict:
    keep = set([str(x).strip() for x in keep_ids if str(x).strip()])
    deleted = []
    skipped = []
    for s in list_boot_repair_servers(client, region, project_id):
        sid = str(s.get("id") or "").strip()
        name = str(s.get("name") or "").strip()
        status = str(s.get("status") or "").upper()
        vols = [str(v.get("id") or "").strip() for v in (s.get("os-extended-volumes:volumes_attached") or []) if str(v.get("id") or "").strip()]

        if not sid:
            continue
        if sid in keep:
            skipped.append({"id": sid, "name": name, "reason": "protected"})
            continue
        # Safety: only clear SHUTOFF helpers that look detached from target disk.
        if status != "SHUTOFF":
            skipped.append({"id": sid, "name": name, "reason": "status_%s" % status.lower()})
            continue
        if len(vols) > 1:
            skipped.append({"id": sid, "name": name, "reason": "multi_volume_attached", "volumes": vols})
            continue

        try:
            delete_rsp = batch_delete_server(client, region, project_id, sid, delete_publicip=True, delete_volume=True)
            delete_job = wait_job_and_get_id(delete_rsp)
            if delete_job:
                wait_ecs_job_success(client, region, project_id, delete_job)
            deleted.append({"id": sid, "name": name, "job_id": delete_job})
        except Exception as exc:
            skipped.append({"id": sid, "name": name, "reason": "delete_failed", "error": str(exc)})

    return {"deleted": deleted, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair target ECS boot disk via helper ECS.")
    parser.add_argument("--target-server-id", required=True, help="Target ECS ID to repair.")
    parser.add_argument("--helper-password", required=True, help="Temporary helper admin password (must be strong; no default).")
    parser.add_argument("--target-reset-password", required=True, help="Password reset for target after repair (must be strong; no default).")
    parser.add_argument("--wait-repair-seconds", type=int, default=1800, help="Max wait seconds for helper auto repair.")
    parser.add_argument("--keep-helper", action="store_true", help="Keep helper ECS after repair for manual inspection.")
    parser.add_argument("--skip-cleanup-old-helpers", action="store_true", help="Skip cleaning old SHUTOFF boot-repair helpers.")
    args = parser.parse_args()

    workdir = Path(__file__).resolve().parent.parent
    tfvars = workdir / "terraform.tfvars"
    if not tfvars.exists():
        raise RuntimeError("terraform.tfvars not found: %s" % tfvars)

    ak = parse_tfvar(tfvars, "destination_access_key")
    sk = parse_tfvar(tfvars, "destination_secret_key")
    region = parse_tfvar(tfvars, "destination_region")
    project_id = parse_tfvar(tfvars, "destination_project_id")
    default_image_id = parse_tfvar(tfvars, "target_image_id")

    if not all([ak, sk, region, project_id]):
        raise RuntimeError("Missing destination credentials/region/project in terraform.tfvars")

    target_server_id = str(args.target_server_id or "").strip() or get_target_server_id(workdir)
    if not target_server_id:
        raise RuntimeError("Cannot determine target_server_id; pass --target-server-id")

    client = HcApiClient(ak, sk)
    artifact = {
        "started_at_local": now_local(),
        "region": region,
        "project_id": project_id,
        "target_server_id": target_server_id,
        "steps": [],
    }

    if not args.skip_cleanup_old_helpers:
        cleanup_before = cleanup_boot_repair_helpers(
            client=client,
            region=region,
            project_id=project_id,
            keep_ids=[target_server_id],
        )
        artifact["steps"].append({"cleanup_old_helpers_before": cleanup_before})

    target_v1 = ecs_get_server(client, region, project_id, target_server_id)
    target_v21 = ecs_get_server_detail_v21(client, region, project_id, target_server_id)
    target_name = str(target_v1.get("name") or target_v21.get("name") or target_server_id)
    az = str(target_v1.get("OS-EXT-AZ:availability_zone") or target_v21.get("OS-EXT-AZ:availability_zone") or "")
    flavor_id = str((target_v1.get("flavor") or {}).get("id") or (target_v21.get("flavor") or {}).get("id") or "")
    vpc_id = get_vpc_id(target_v1) or get_vpc_id(target_v21)
    port_id = get_fixed_port_id(target_v1) or get_fixed_port_id(target_v21)
    if not port_id:
        raise RuntimeError("Cannot locate target fixed port id")

    port = vpc_get_port(client, region, project_id, port_id)
    subnet_id = str(port.get("network_id") or "").strip()
    sg_ids = port.get("security_groups") or []
    sg_id = str(sg_ids[0] if sg_ids else "").strip()
    if not all([az, flavor_id, vpc_id, subnet_id, sg_id]):
        raise RuntimeError(
            "Missing target topology info az=%s flavor=%s vpc=%s subnet=%s sg=%s"
            % (az, flavor_id, vpc_id, subnet_id, sg_id)
        )

    boot_volume_id = get_boot_volume_id(target_v1)
    if not boot_volume_id:
        raise RuntimeError("Cannot locate target boot volume")

    vol = {}
    image_id = default_image_id
    root_volume_type = "SSD"
    try:
        vol = evs_get_volume(client, region, project_id, boot_volume_id)
        root_volume_type = str(vol.get("volume_type") or root_volume_type)
        image_id = str(((vol.get("volume_image_metadata") or {}).get("image_id") or "")).strip() or image_id
    except Exception as exc:
        artifact["steps"].append({"warn": "evs_get_volume_failed", "error": str(exc)})
    if not image_id:
        raise RuntimeError("Cannot determine helper image_id")

    helper_name = "boot-repair-%s-%d" % (target_name[:18], int(time.time()))
    helper_id = create_helper_server(
        client=client,
        region=region,
        project_id=project_id,
        helper_name=helper_name,
        az=az,
        image_id=image_id,
        flavor_id=flavor_id,
        admin_password=args.helper_password,
        vpc_id=vpc_id,
        subnet_id=subnet_id,
        security_group_id=sg_id,
        root_volume_type=root_volume_type,
        target_root_password=args.target_reset_password,
    )
    artifact["helper_server_id"] = helper_id
    artifact["helper_server_name"] = helper_name
    artifact["steps"].append({"create_helper": {"helper_id": helper_id}})

    wait_server_status(client, region, project_id, helper_id, "ACTIVE", timeout_sec=1200, interval_sec=10)
    artifact["steps"].append({"helper_status": "ACTIVE"})

    target_status = str(target_v1.get("status") or "").upper()
    if target_status != "SHUTOFF":
        stop_rsp = batch_stop_server(client, region, project_id, target_server_id)
        stop_job = wait_job_and_get_id(stop_rsp)
        if stop_job:
            wait_ecs_job_success(client, region, project_id, stop_job)
        wait_server_status(client, region, project_id, target_server_id, "SHUTOFF", timeout_sec=1200, interval_sec=10)
        artifact["steps"].append({"stop_target": {"job_id": stop_job}})

    detach_rsp = detach_volume(client, region, project_id, target_server_id, boot_volume_id)
    detach_job = wait_job_and_get_id(detach_rsp)
    if detach_job:
        wait_ecs_job_success(client, region, project_id, detach_job)
    artifact["steps"].append({"detach_from_target": {"volume_id": boot_volume_id, "job_id": detach_job}})

    attach_helper_rsp = attach_volume(
        client, region, project_id, helper_id, boot_volume_id, "/dev/vdb"
    )
    attach_helper_job = wait_job_and_get_id(attach_helper_rsp)
    if attach_helper_job:
        wait_ecs_job_success(client, region, project_id, attach_helper_job)
    artifact["steps"].append({"attach_to_helper": {"job_id": attach_helper_job}})

    complete = False
    repair_console_tail = ""
    start_wait = time.time()
    while time.time() - start_wait < int(args.wait_repair_seconds):
        time.sleep(15)
        helper_now = ecs_get_server(client, region, project_id, helper_id)
        helper_status = str(helper_now.get("status") or "").upper()
        try:
            console_out = get_console_output(client, region, project_id, helper_id, length=4000)
        except Exception:
            console_out = ""
        repair_console_tail = "\n".join(console_out.splitlines()[-120:])
        if "[BOOT-REPAIR] COMPLETE" in console_out:
            complete = True
        if complete and helper_status == "SHUTOFF":
            break
        if helper_status == "ERROR":
            break
    artifact["steps"].append(
        {
            "helper_repair_observe": {
                "complete_flag": complete,
                "console_tail": repair_console_tail[-8000:],
            }
        }
    )

    helper_now = ecs_get_server(client, region, project_id, helper_id)
    if str(helper_now.get("status") or "").upper() != "SHUTOFF":
        stop_h_rsp = batch_stop_server(client, region, project_id, helper_id)
        stop_h_job = wait_job_and_get_id(stop_h_rsp)
        if stop_h_job:
            wait_ecs_job_success(client, region, project_id, stop_h_job)
        wait_server_status(client, region, project_id, helper_id, "SHUTOFF", timeout_sec=1200, interval_sec=10)
        artifact["steps"].append({"stop_helper": {"job_id": stop_h_job}})

    detach_helper_rsp = detach_volume(client, region, project_id, helper_id, boot_volume_id)
    detach_helper_job = wait_job_and_get_id(detach_helper_rsp)
    if detach_helper_job:
        wait_ecs_job_success(client, region, project_id, detach_helper_job)
    artifact["steps"].append({"detach_from_helper": {"job_id": detach_helper_job}})

    attach_target_rsp = attach_volume(
        client, region, project_id, target_server_id, boot_volume_id, "/dev/vda"
    )
    attach_target_job = wait_job_and_get_id(attach_target_rsp)
    if attach_target_job:
        wait_ecs_job_success(client, region, project_id, attach_target_job)
    artifact["steps"].append({"attach_back_to_target": {"job_id": attach_target_job}})

    start_rsp = batch_start_server(client, region, project_id, target_server_id)
    start_job = wait_job_and_get_id(start_rsp)
    if start_job:
        wait_ecs_job_success(client, region, project_id, start_job)
    wait_server_status(client, region, project_id, target_server_id, "ACTIVE", timeout_sec=1200, interval_sec=10)
    artifact["steps"].append({"start_target": {"job_id": start_job}})

    reset_rsp = client.request_json(
        "PUT",
        "https://ecs.%s.myhuaweicloud.com/v1/%s/cloudservers/%s/os-reset-password"
        % (region, project_id, target_server_id),
        body={"reset-password": {"new_password": args.target_reset_password}},
    )
    artifact["steps"].append({"target_reset_password": reset_rsp})

    if args.keep_helper:
        artifact["steps"].append({"cleanup_current_helper": {"kept": True, "helper_id": helper_id}})
    else:
        delete_rsp = batch_delete_server(
            client=client,
            region=region,
            project_id=project_id,
            server_id=helper_id,
            delete_publicip=True,
            delete_volume=True,
        )
        delete_job = wait_job_and_get_id(delete_rsp)
        if delete_job:
            wait_ecs_job_success(client, region, project_id, delete_job)
        artifact["steps"].append({"cleanup_current_helper": {"deleted": True, "helper_id": helper_id, "job_id": delete_job}})

    if not args.skip_cleanup_old_helpers:
        cleanup_after = cleanup_boot_repair_helpers(
            client=client,
            region=region,
            project_id=project_id,
            keep_ids=[target_server_id],
        )
        artifact["steps"].append({"cleanup_old_helpers_after": cleanup_after})

    novnc = get_novnc_url(client, region, project_id, target_server_id)
    target_console = get_console_output(client, region, project_id, target_server_id, length=4000)
    artifact["novnc_url"] = novnc
    artifact["target_console_tail"] = "\n".join(target_console.splitlines()[-120:])
    artifact["target_reset_password"] = args.target_reset_password
    artifact["finished_at_local"] = now_local()
    artifact["result"] = "SUCCESS"

    out_latest = workdir / "out" / "target_boot_repair_latest.json"
    out_ts = workdir / "out" / ("target_boot_repair_%s.json" % time.strftime("%Y%m%d-%H%M%S", time.localtime()))
    write_json_file(str(out_latest), artifact)
    write_json_file(str(out_ts), artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
