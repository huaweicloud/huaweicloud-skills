# Security Design - Password Lifecycle & Tool Separation

Detailed security architecture for Kunpeng DevKit WebUI installation. Referenced by SKILL.md.

## Tool Separation for Security

| Operation | Tool | Reason |
|-----------|------|--------|
| ECS creation | Python SDK | `adminPass` as API parameter, not visible in `ps -ef` |
| KMS encrypt/decrypt/delete | Python SDK | Password stays in Python process memory, never exported |
| SSH connection | Python paramiko | `password=` param in `SSHClient.connect()`, not visible in `ps -ef` |
| DevKit installation | Python paramiko | Script execution via SSH channel, no password on CLI |
| EIP create/bind | hcloud CLI | No password involved |
| VPC/security group | hcloud CLI | No password involved |

## Password Leakage Risk Elimination

| Risk Point | Old Method (Insecure) | New Method (Secure) |
|------------|----------------------|---------------------|
| ECS creation | `hcloud --server.adminPass` → leaked via `ps -ef` | Python SDK `adminPass` param → process memory only |
| Password storage | `DEVKIT_ECS_PASSWORD` env var → readable | KMS encrypted via Python SDK → IAM-controlled access |
| Password export | Password exported to shell variable → visible in `ps` | Only `kms_key_id` + `kms_cipher_text_file` exported → cipher text in file (mode 600), password never leaves Python |
| SSH connection | `sshpass -p` / `expect` + env var → leaked via `ps -ef` | Python paramiko `connect(password=)` → process memory only |
| DevKit install | `scp` + `ssh` with password on CLI | paramiko SFTP upload + SSH exec_command → no CLI password |
| Password lifetime | Persists indefinitely in env var | KMS key scheduled for deletion only after verified success; preserved on failure for retry |
| Session persistence | Relies on password, must re-enter | Single-use: decrypt → SSH → install → verify → if passed: delete KMS key; if failed: preserve KMS key for retry |

## Security Flow: Password Lifecycle

```
1. Python generates random 26-char password (in memory only)
2. Python SDK creates ECS with adminPass (API param → no ps -ef leakage)
3. Python SDK creates KMS key and encrypts password (password stays in Python process)
4. Python writes cipher text to file (mode 600) and outputs kms_key_id + kms_cipher_text_file (password NEVER exported)
5. [hcloud CLI binds EIP and opens security group — no password involved]
6. Python SDK decrypts password from KMS (in process memory)
7. Python paramiko SSH connects with decrypted password (password param → no ps -ef leakage)
8. paramiko uploads install scripts via SFTP and executes install.sh
9. Python deletes password variable (del password) — always, even on failure
10. Agent verifies DevKit installation (Task 3): checks services, plugins, ports, WebUI access
11. IF install verification PASSED (Task 4 — cleanup-kms, independent Python method):
    a. Python SDK disables KMS key (password immediately unrecoverable)
    b. Python SDK schedules KMS key deletion (7 days, API minimum)
    c. KMS key permanently deleted after 7 days
12. IF install verification FAILED:
    a. KMS key is PRESERVED (not disabled, not deleted)
    b. User can retry install using same kms_key_id + kms_cipher_text_file
    c. After successful retry + verification, run cleanup-kms to clean up KMS key
```

> **⚠️ Critical: KMS key is only destroyed after successful installation**
>
> If installation fails, the KMS key is preserved so the user can retry SSH access.
> This is a deliberate trade-off: retry-ability vs. immediate key destruction.
> After a successful retry, the user must manually disable and schedule deletion of the KMS key.