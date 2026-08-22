#!/usr/bin/env python3
"""Create Kunpeng ECS, encrypt password in KMS, install DevKit via paramiko SSH.

Security design:
- Password is randomly generated (never typed by user)
- Password is passed to ECS API as a parameter (not CLI arg -> no ps -ef leakage)
- Password is encrypted and stored in KMS (via Python SDK, never leaves process memory)
- Password is decrypted from KMS and passed to paramiko SSH (in Python memory, not CLI arg)
- Password NEVER appears in command line, shell variables, ps -ef, or conversation
- KMS key is scheduled for deletion after DevKit installation

Usage:
  # Phase 1: Create ECS + KMS encrypt (no EIP yet)
  python create_ecs_and_setup_devkit.py \
    --region cn-north-4 \
    --vpc-id <vpc_id> \
    --subnet-id <subnet_id> \
    --flavor kc1.large.2 \
    --image-id <image_id> \
    --az cn-north-4a \
    --ecs-name devkit-kunpeng

  # Phase 2: SSH install DevKit (after EIP bound via hcloud CLI)
  python create_ecs_and_setup_devkit.py \
    --region cn-north-4 \
    --eip <eip_address> \
    --kms-key-id <key_id> \
    --kms-cipher-text-file <cipher_text_file> \
    --devkit-url <download_url>
"""

import argparse
import json
import os
import random
import string
import sys
import tempfile
import time
import uuid

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
from huaweicloudsdkecs.v2 import (
    NovaListServersDetailsRequest,
)
from huaweicloudsdkecs.v2 import (
    CreatePostPaidServersRequest, CreatePostPaidServersRequestBody,
    PostPaidServer, PostPaidServerNic, PostPaidServerRootVolume,
    PostPaidServerSecurityGroup,
)
from huaweicloudsdkkms.v2 import KmsClient
from huaweicloudsdkkms.v2.region.kms_region import KmsRegion
from huaweicloudsdkkms.v2 import (
    CreateKeyRequest,
    CreateKeyRequestBody,
    EncryptDataRequest,
    EncryptDataRequestBody,
    DecryptDataRequest,
    DecryptDataRequestBody,
    DeleteKeyRequest,
    ScheduleKeyDeletionRequestBody,
    ListKeysRequest,
    ListKeysRequestBody,
)

DEVKIT_DEFAULT_URL = (
    "https://kunpeng-repo.obs.cn-north-4.myhuaweicloud.com/"
    "Kunpeng%20DevKit/Kunpeng%20DevKit%2026.1.RC1/"
    "DevKit-All-26.1.RC1-Linux-Kunpeng.tar.gz"
)


def generate_password(length=26):
    chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        pwd = "".join(random.choices(chars, k=length))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*()-_=+" for c in pwd)):
            return pwd


def get_credentials():
    ak = os.environ.get("HW_ACCESS_KEY") or os.environ.get("HUAWEICLOUD_SDK_AK")
    sk = os.environ.get("HW_SECRET_KEY") or os.environ.get("HUAWEICLOUD_SDK_SK")
    security_token = os.environ.get("HW_SECURITY_TOKEN") or os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN")
    project_id = os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
    if not ak or not sk:
        print("ERROR: AK/SK not found. Set HW_ACCESS_KEY/HW_SECRET_KEY env vars.", file=sys.stderr)
        sys.exit(1)
    creds = BasicCredentials(ak, sk, project_id)
    if security_token:
        creds.security_token = security_token
    return creds


def create_ecs(ecs_client, args, password):
    server = PostPaidServer(
        name=args.ecs_name,
        flavor_ref=args.flavor,
        image_ref=args.image_id,
        admin_pass=password,
        vpcid=args.vpc_id,
        nics=[PostPaidServerNic(subnet_id=args.subnet_id)],
        root_volume=PostPaidServerRootVolume(volumetype="SSD", size=40),
        availability_zone=args.az,
    )
    if args.security_group_id:
        server.security_groups = [PostPaidServerSecurityGroup(id=args.security_group_id)]
    body = CreatePostPaidServersRequestBody(server=server)
    req = CreatePostPaidServersRequest(body=body)
    resp = ecs_client.create_post_paid_servers(req)
    return resp


def wait_for_ecs_active(ecs_client, server_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = NovaListServersDetailsRequest()
            resp = ecs_client.nova_list_servers_details(req)
            for s in resp.servers:
                if s.id == server_id and s.status == "ACTIVE":
                    return True
        except Exception:
            pass
        time.sleep(10)
    return False


def get_server_private_ip(ecs_client, server_id):
    try:
        req = NovaListServersDetailsRequest()
        resp = ecs_client.nova_list_servers_details(req)
        for s in resp.servers:
            if s.id == server_id:
                for net_name, addr_list in (s.addresses or {}).items():
                    for addr in addr_list:
                        if getattr(addr, 'os_ext_ip_stype', None) == "fixed":
                            return addr.addr
    except Exception:
        pass
    return None


def kms_create_key(kms_client):
    key_alias = f"devkit-ecs-pwd-{uuid.uuid4().hex[:8]}"
    try:
        body = CreateKeyRequestBody(
            key_alias=key_alias,
            key_spec="AES_256",
            key_usage="ENCRYPT_DECRYPT",
        )
        req = CreateKeyRequest(body=body)
        resp = kms_client.create_key(req)
        if resp.key_info and resp.key_info.key_id:
            return resp.key_info.key_id
    except Exception as e:
        print(f"  WARNING: KMS key creation failed ({e}), trying existing keys...", file=sys.stderr)
    try:
        list_body = ListKeysRequestBody(limit=10)
        list_req = ListKeysRequest(body=list_body)
        list_resp = kms_client.list_keys(list_req)
        keys = list_resp.keys if hasattr(list_resp, "keys") else []
        if keys:
            return keys[0].key_id
    except Exception:
        pass
    return None


def kms_encrypt(kms_client, key_id, plaintext):
    body = EncryptDataRequestBody(
        key_id=key_id,
        plain_text=plaintext.encode("utf-8").hex(),
    )
    req = EncryptDataRequest(body=body)
    resp = kms_client.encrypt_data(req)
    return resp.cipher_text


def kms_decrypt(kms_client, key_id, cipher_text):
    body = DecryptDataRequestBody(
        key_id=key_id,
        cipher_text=cipher_text,
    )
    req = DecryptDataRequest(body=body)
    resp = kms_client.decrypt_data(req)
    return bytes.fromhex(resp.plain_text).decode("utf-8")


def kms_disable_key(kms_client, key_id):
    from huaweicloudsdkkms.v2 import DisableKeyRequest, OperateKeyRequestBody
    body = OperateKeyRequestBody(key_id=key_id)
    req = DisableKeyRequest(body=body)
    kms_client.disable_key(req)


def kms_schedule_deletion(kms_client, key_id, delay_days=7):
    body = ScheduleKeyDeletionRequestBody(
        key_id=key_id,
        pending_days=str(delay_days),
    )
    req = DeleteKeyRequest(body=body)
    kms_client.delete_key(req)


def ssh_install_devkit(eip, password, devkit_url, install_path="", install_port="", wait=False):
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(eip, port=22, username="root", password=password, timeout=30)
    except Exception as e:
        print(f"  ERROR: SSH connection to {eip} failed: {e}", file=sys.stderr)
        return False

    try:
        _upload_install_scripts(ssh)
        _start_devkit_install(ssh, devkit_url, install_path, install_port)
        if not wait:
            # Quick return: remote nohup install runs independently of this process.
            # Caller polls progress via the 'status' subcommand.
            print("  DevKit installation started in background on remote ECS (nohup).")
            print("  The remote process is independent of this command; safe to exit.")
            return None
        _poll_install_status(ssh, timeout=900, interval=30)
        verify_passed = _run_devkit_verify(ssh)
        if not verify_passed:
            print("  ERROR: DevKit verification failed. KMS key will be preserved for retry.", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"  ERROR: DevKit installation failed: {e}", file=sys.stderr)
        return False
    finally:
        ssh.close()


def _upload_install_scripts(ssh):
    sftp = ssh.open_sftp()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for fname in ["install_devkit_webui.sh", "auto_install_devkit.expect", "verify_devkit.sh"]:
        local_path = os.path.join(script_dir, fname)
        remote_path = f"/tmp/{fname}"
        try:
            sftp.put(local_path, remote_path)
            sftp.chmod(remote_path, 0o755)
        except Exception as e:
            print(f"  WARNING: Failed to upload {fname}: {e}", file=sys.stderr)
    sftp.close()


def _start_devkit_install(ssh, devkit_url, install_path, install_port):
    install_cmd = f"nohup bash /tmp/install_devkit_webui.sh '{devkit_url}'"
    if install_path:
        install_cmd += f" '{install_path}'"
    if install_port:
        install_cmd += f" '{install_port}'"
    install_cmd += " > /tmp/devkit_install_wrapper.log 2>&1 & echo $!"

    stdin, stdout, stderr = ssh.exec_command(install_cmd, timeout=15)
    pid = stdout.read().decode("utf-8", errors="replace").strip().split("\n")[-1]
    print(f"  Install started, PID: {pid}")


def _poll_install_status(ssh, timeout=900, interval=30):
    start = time.time()
    last_lines = 0
    while time.time() - start < timeout:
        time.sleep(interval)
        try:
            stdin, stdout, stderr = ssh.exec_command(
                "if [ -f /tmp/devkit_install.pid ]; then "
                "  pid=$(cat /tmp/devkit_install.pid 2>/dev/null); "
                "  if [ -n \"$pid\" ] && kill -0 $pid 2>/dev/null; then echo RUNNING; else echo DONE; fi; "
                "else echo WAITING; fi",
                timeout=10,
            )
            status = stdout.read().decode("utf-8", errors="replace").strip()
        except Exception:
            status = "UNKNOWN"

        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] Install status: {status}")

        if status == "DONE":
            print("  Installation process finished.")
            break
        if status == "WAITING" and elapsed > 120:
            print("  WARNING: No PID file found after 120s, checking log...", file=sys.stderr)
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    "tail -5 /tmp/devkit_install_wrapper.log 2>/dev/null || echo 'No log yet'",
                    timeout=10,
                )
                log = stdout.read().decode("utf-8", errors="replace").strip()
                print(f"  Log: {log}")
            except Exception:
                pass
    else:
        print(f"  WARNING: Install still running after {timeout}s timeout.", file=sys.stderr)

    try:
        stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/devkit_install.log 2>/dev/null", timeout=10)
        log = stdout.read().decode("utf-8", errors="replace").strip()
        if log:
            for line in log.splitlines()[-15:]:
                print(f"  {line}")
    except Exception:
        pass


def _run_devkit_verify(ssh):
    stdin, stdout, stderr = ssh.exec_command("bash /tmp/verify_devkit.sh", timeout=60)
    output = stdout.read().decode("utf-8", errors="replace")
    if output:
        for line in output.splitlines():
            print(f"  {line}")
    fail_count = 0
    for line in output.splitlines():
        if line.strip().startswith("\u274c"):
            fail_count += 1
    passed = fail_count == 0
    if not passed:
        print(f"  WARNING: {fail_count} verification check(s) FAILED.", file=sys.stderr)
    else:
        print("  All verification checks PASSED.")
    return passed


def phase_create(args):
    credentials = get_credentials()

    ecs_client = EcsClient.new_builder().with_credentials(credentials).with_region(
        EcsRegion.value_of(args.region)
    ).build()
    kms_client = KmsClient.new_builder().with_credentials(credentials).with_region(
        KmsRegion.value_of(args.region)
    ).build()

    password = generate_password()

    if args.server_id:
        server_id = args.server_id
        print(f"[1/5] Skipping ECS creation, using existing server_id: {server_id}")
        print("[2/5] Skipping ECS wait (assuming ACTIVE).")
    else:
        print(f"[1/5] Creating ECS '{args.ecs_name}' (flavor={args.flavor}, az={args.az})...")
        try:
            resp = create_ecs(ecs_client, args, password)
            server_id = None
            if hasattr(resp, 'server_ids') and resp.server_ids:
                server_id = resp.server_ids[0]
            elif hasattr(resp, 'job_id') and resp.job_id:
                print(f"  job_id: {resp.job_id}, waiting for server_id...")
                for _ in range(30):
                    time.sleep(10)
                    try:
                        req = NovaListServersDetailsRequest()
                        list_resp = ecs_client.nova_list_servers_details(req)
                        for s in list_resp.servers:
                            if s.name == args.ecs_name:
                                server_id = s.id
                                break
                    except Exception:
                        pass
                    if server_id:
                        break
            if not server_id:
                print("ERROR: Could not extract server_id from response", file=sys.stderr)
                sys.exit(1)
            print(f"  server_id: {server_id}")
        except Exception as e:
            print(f"ERROR: ECS creation failed: {e}", file=sys.stderr)
            sys.exit(1)

        print("[2/5] Waiting for ECS to become ACTIVE...")
        if not wait_for_ecs_active(ecs_client, server_id):
            print("ERROR: ECS did not become ACTIVE within timeout.", file=sys.stderr)
            sys.exit(1)
        print("  ECS is ACTIVE.")

    private_ip = get_server_private_ip(ecs_client, server_id)
    print(f"  private_ip: {private_ip}")

    print("[3/5] Encrypting password in KMS...")
    key_id = kms_create_key(kms_client)
    if not key_id:
        print("ERROR: No KMS key available.", file=sys.stderr)
        sys.exit(1)
    cipher_text = kms_encrypt(kms_client, key_id, password)
    print(f"  KMS key_id: {key_id}")

    del password

    print("[4/5] Writing cipher text to file (never passed via command line)...")
    cipher_file = os.path.join(
        tempfile.gettempdir(), f"devkit_kms_cipher_{server_id}.txt"
    )
    with open(cipher_file, "w", encoding="utf-8") as f:
        f.write(cipher_text)
    os.chmod(cipher_file, 0o600)
    print(f"  Cipher text saved to: {cipher_file}")

    result = {
        "server_id": server_id,
        "region": args.region,
        "ecs_name": args.ecs_name,
        "private_ip": private_ip,
        "kms_key_id": key_id,
        "kms_cipher_text_file": cipher_file,
    }
    print(json.dumps(result))

    print("\n[5/5] Next steps:", file=sys.stderr)
    print("  1. Bind EIP:  hcloud EIP CreatePublicip + UpdatePublicip", file=sys.stderr)
    print("  2. Open security group ports 22 and 8086", file=sys.stderr)
    print(f"  3. Install DevKit:  python {__file__} install --eip <EIP> --kms-key-id {key_id} --kms-cipher-text-file {cipher_file}", file=sys.stderr)

    return result


def _read_cipher_text(cipher_text_file):
    if not cipher_text_file or not os.path.isfile(cipher_text_file):
        print(f"ERROR: Cipher text file not found: {cipher_text_file}", file=sys.stderr)
        sys.exit(1)
    with open(cipher_text_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def _ssh_connect_with_kms(eip, kms_key_id, kms_cipher_text_file, region):
    import paramiko
    credentials = get_credentials()
    kms_client = KmsClient.new_builder().with_credentials(credentials).with_region(
        KmsRegion.value_of(region)
    ).build()
    cipher_text = _read_cipher_text(kms_cipher_text_file)
    try:
        password = kms_decrypt(kms_client, kms_key_id, cipher_text)
    except Exception as e:
        print(f"ERROR: KMS decryption failed: {e}", file=sys.stderr)
        sys.exit(1)
    del cipher_text
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(eip, port=22, username="root", password=password, timeout=15)
    except Exception as e:
        print(f"ERROR: SSH connection to {eip} failed: {e}", file=sys.stderr)
        del password
        sys.exit(1)
    del password
    return ssh


def phase_install(args):
    credentials = get_credentials()
    kms_client = KmsClient.new_builder().with_credentials(credentials).with_region(
        KmsRegion.value_of(args.region)
    ).build()

    print("[1/3] Decrypting password from KMS...")
    cipher_text = _read_cipher_text(args.kms_cipher_text_file)
    try:
        password = kms_decrypt(kms_client, args.kms_key_id, cipher_text)
    except Exception as e:
        print(f"ERROR: KMS decryption failed: {e}", file=sys.stderr)
        sys.exit(1)
    del cipher_text

    print("[2/3] Installing DevKit via paramiko SSH...")
    try:
        result = ssh_install_devkit(
            args.eip, password, args.devkit_url,
            args.install_path, args.install_port, wait=args.wait,
        )
    finally:
        del password

    if result is True:
        print(f"\nDevKit installed successfully! Access: https://{args.eip}:8086", file=sys.stderr)
        print("  NOTE: KMS key is still active. Run 'cleanup-kms' subcommand after verifying installation.", file=sys.stderr)
        print(f"  Cleanup: python {__file__} cleanup-kms --region {args.region} --kms-key-id {args.kms_key_id}", file=sys.stderr)
        if args.server_id:
            print(f"  ECS console: https://console.huaweicloud.com/ecm/?region={args.region}#/detail/{args.server_id}", file=sys.stderr)
        else:
            print(f"  ECS console: https://console.huaweicloud.com/ecm/?region={args.region}", file=sys.stderr)
    elif result is False:
        print("\nDevKit installation FAILED. KMS key preserved for retry.", file=sys.stderr)
        print(f"  Retry: python {__file__} install --region {args.region} --eip {args.eip} "
              f"--kms-key-id {args.kms_key_id} --kms-cipher-text-file {args.kms_cipher_text_file}", file=sys.stderr)
        print(f"  Or check status: python {__file__} status --region {args.region} --eip {args.eip} "
              f"--kms-key-id {args.kms_key_id} --kms-cipher-text-file {args.kms_cipher_text_file}", file=sys.stderr)
        sys.exit(1)
    else:
        # result is None: background install started, quick return
        print(f"\nDevKit installation started in background on {args.eip}.", file=sys.stderr)
        print("  The remote nohup process is independent of this command.", file=sys.stderr)
        print(f"  Poll progress: python {__file__} status --region {args.region} --eip {args.eip} "
              f"--kms-key-id {args.kms_key_id} --kms-cipher-text-file {args.kms_cipher_text_file}", file=sys.stderr)
        print(f"  When status shows install_process=DONE and all services active, verify WebUI at https://{args.eip}:8086", file=sys.stderr)
        print("  After verification passes, run cleanup-kms to disable the KMS key.", file=sys.stderr)


def phase_cleanup_kms(args):
    credentials = get_credentials()
    kms_client = KmsClient.new_builder().with_credentials(credentials).with_region(
        KmsRegion.value_of(args.region)
    ).build()

    print(f"[1/2] Disabling KMS key {args.kms_key_id} (password immediately unrecoverable)...")
    try:
        kms_disable_key(kms_client, args.kms_key_id)
        print(f"  KMS key {args.kms_key_id} disabled. Password no longer recoverable.")
    except Exception as e:
        print(f"  WARNING: KMS key disable failed ({e}).", file=sys.stderr)
        if not args.force:
            print("  Use --force to continue with deletion scheduling despite disable failure.", file=sys.stderr)
            sys.exit(1)

    print(f"[2/2] Scheduling KMS key deletion ({args.delay_days} days, API minimum is 7)...")
    try:
        kms_schedule_deletion(kms_client, args.kms_key_id, delay_days=args.delay_days)
        print(f"  KMS key {args.kms_key_id} scheduled for deletion in {args.delay_days} days.")
        print(f"\nKMS cleanup completed. Key {args.kms_key_id} will be permanently deleted after {args.delay_days} days.")
    except Exception as e:
        print(f"  ERROR: KMS key deletion scheduling failed ({e}).", file=sys.stderr)
        sys.exit(1)


def phase_status(args):
    ssh = _ssh_connect_with_kms(args.eip, args.kms_key_id, args.kms_cipher_text_file, args.region)
    try:
        result = {}

        pid_status = "UNKNOWN"
        try:
            stdin, stdout, stderr = ssh.exec_command(
                "if [ -f /tmp/devkit_install.pid ]; then "
                "  pid=$(cat /tmp/devkit_install.pid 2>/dev/null); "
                "  if [ -n \"$pid\" ] && kill -0 $pid 2>/dev/null; then echo RUNNING; else echo DONE; fi; "
                "else echo NO_PID_FILE; fi",
                timeout=10,
            )
            pid_status = stdout.read().decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        result["install_process"] = pid_status
        result["current_stage"] = ""
        wrapper_log = ""

        # When PID file does not exist yet, the install script is in early
        # stages ([1/6]-[4/6]): env check, dependency install, package
        # download, extraction. Read the wrapper log to report progress.
        if pid_status == "NO_PID_FILE":
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    "tail -15 /tmp/devkit_install_wrapper.log 2>/dev/null", timeout=10
                )
                wrapper_log = stdout.read().decode("utf-8", errors="replace").strip()
            except Exception:
                wrapper_log = ""
            if wrapper_log:
                result["install_process"] = "PREPARING"
                # Parse the last stage marker (e.g. "=== [2/6] Install Dependencies ===")
                for line in wrapper_log.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("===") and "[" in stripped and "]" in stripped:
                        marker = stripped.strip("= ").strip()
                        if marker:
                            result["current_stage"] = marker
            else:
                result["install_process"] = "NOT_STARTED"

        services = {}
        for svc in ["devkit_nginx", "gunicorn_framework", "gunicorn_plugin"]:
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    f"systemctl is-active {svc} 2>/dev/null || echo unknown", timeout=10
                )
                services[svc] = stdout.read().decode("utf-8", errors="replace").strip()
            except Exception:
                services[svc] = "error"
        result["services"] = services

        plugins = {}
        for plugin in ["porting", "affinity", "devtools", "debugger", "sys_perf", "java_perf", "sys_diagnosis"]:
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    f"test -d /opt/DevKit/devkitplugins/{plugin} && echo installed || echo missing", timeout=10
                )
                plugins[plugin] = stdout.read().decode("utf-8", errors="replace").strip()
            except Exception:
                plugins[plugin] = "error"
        result["plugins"] = plugins

        try:
            stdin, stdout, stderr = ssh.exec_command(
                "ss -tlnp 2>/dev/null | grep -E ':8086 |:8002 |:7996 ' | awk '{print $4}' | sort", timeout=10
            )
            ports = stdout.read().decode("utf-8", errors="replace").strip()
            result["ports"] = ports if ports else "none"
        except Exception:
            result["ports"] = "error"

        if result["install_process"] == "PREPARING":
            # Early stages: report wrapper log (env check, yum install, wget download)
            result["last_log_lines"] = wrapper_log
        else:
            try:
                stdin, stdout, stderr = ssh.exec_command(
                    "tail -10 /tmp/devkit_install.log 2>/dev/null || echo 'No install log yet'", timeout=10
                )
                result["last_log_lines"] = stdout.read().decode("utf-8", errors="replace").strip()
            except Exception:
                result["last_log_lines"] = "error reading log"

        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        ssh.close()


def main():
    parser = argparse.ArgumentParser(description="Create Kunpeng ECS + KMS + DevKit (paramiko SSH)")
    subparsers = parser.add_subparsers(dest="phase", help="Phase to run")

    create_p = subparsers.add_parser("create", help="Phase 1: Create ECS + KMS encrypt")
    create_p.add_argument("--region", required=True)

    create_p.add_argument("--vpc-id", required=True)
    create_p.add_argument("--subnet-id", required=True)
    create_p.add_argument("--flavor", required=True)
    create_p.add_argument("--image-id", required=True)
    create_p.add_argument("--az", required=True)
    create_p.add_argument("--ecs-name", default="devkit-kunpeng")
    create_p.add_argument("--server-id", default=None, help="Existing server_id to skip ECS creation")
    create_p.add_argument("--security-group-id", default=None, help="Security group ID to attach to ECS")

    install_p = subparsers.add_parser("install", help="Phase 2: SSH install DevKit")
    install_p.add_argument("--region", required=True)

    install_p.add_argument("--eip", required=True, help="ECS public IP for SSH")
    install_p.add_argument("--kms-key-id", required=True, help="KMS key ID from phase 1")
    install_p.add_argument("--kms-cipher-text-file", required=True, help="Path to file containing KMS cipher text from phase 1")
    install_p.add_argument("--devkit-url", default=DEVKIT_DEFAULT_URL, help="DevKit download URL")
    install_p.add_argument("--install-path", default="", help="Custom install path")
    install_p.add_argument("--install-port", default="", help="Custom install port")
    install_p.add_argument("--server-id", default=None, help="ECS server ID (for console URL in success message)")
    install_p.add_argument("--wait", action="store_true", help="Wait for install to complete (poll + verify). Default: return immediately after starting background install.")

    status_p = subparsers.add_parser("status", help="Check DevKit install progress (poll every 30s)")
    status_p.add_argument("--region", required=True)

    status_p.add_argument("--eip", required=True, help="ECS public IP for SSH")
    status_p.add_argument("--kms-key-id", required=True, help="KMS key ID from phase 1")
    status_p.add_argument("--kms-cipher-text-file", required=True, help="Path to file containing KMS cipher text from phase 1")

    cleanup_p = subparsers.add_parser("cleanup-kms", help="Phase 3: Disable + schedule KMS key deletion (run after verified success)")
    cleanup_p.add_argument("--region", required=True)

    cleanup_p.add_argument("--kms-key-id", required=True, help="KMS key ID to disable and schedule for deletion")
    cleanup_p.add_argument("--delay-days", type=int, default=7, help="Days until deletion (API minimum: 7)")
    cleanup_p.add_argument("--force", action="store_true", help="Continue with deletion scheduling even if disable fails")

    args = parser.parse_args()

    if args.phase == "create":
        phase_create(args)
    elif args.phase == "install":
        phase_install(args)
    elif args.phase == "status":
        phase_status(args)
    elif args.phase == "cleanup-kms":
        phase_cleanup_kms(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()