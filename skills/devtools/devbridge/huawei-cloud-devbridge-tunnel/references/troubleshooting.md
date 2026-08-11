# Troubleshooting Guide

This document covers common issues and their solutions when using DevBridge CLI.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Authentication Issues](#authentication-issues)
3. [Tunnel Creation Issues](#tunnel-creation-issues)
4. [Port Management Issues](#port-management-issues)
5. [Host Issues](#host-issues)
6. [Connect Issues](#connect-issues)
7. [Network Issues](#network-issues)
8. [Permission Issues](#permission-issues)

---

## Installation Issues

### Problem: `command not found: devbridge`

**Cause:** The CLI binary is not in PATH.

**✅ Correct fix:**

```bash
# Check if binary exists
ls -la ~/.huawei/bin/devbridge

# If exists, add to PATH
echo 'export PATH="$HOME/.huawei/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**❌ Incorrect fix (forgetting to source the config):**

```bash
echo 'export PATH="$HOME/.huawei/bin:$PATH"' >> ~/.bashrc
# Forgot to run 'source ~/.bashrc' — PATH not updated in current session
```

### Problem: `permission denied: devbridge`

**Cause:** The binary lacks execute permission.

**Solution:**

```bash
chmod +x ~/.huawei/bin/devbridge
```

### Problem: Installation script fails

**Cause:** Network issues or unsupported platform.

**Solution:**

1. Verify network connectivity: `curl -I https://res-hd.hc-cdn.cn`
2. Check if proxy is needed: `export https_proxy=<proxy-url>`
3. Verify OS and architecture: `uname -m` (should be `x86_64` or `aarch64`)

---

## Authentication Issues

### Problem: `devbridge auth login` does not open browser

**Cause:** No default browser configured or headless environment.

**Solution:**

1. The CLI will display a URL — copy and open it manually in a browser.
2. For headless environments, use AK/SK authentication:

```bash
devbridge auth login --access-key <AK> --secret-key <SK>
```

### Problem: `Authentication failed: invalid credentials`

**Cause:** Invalid AK/SK or expired token.

**Solution:**

1. Verify AK/SK are correct.
2. For STS tokens, verify the security token has not expired.
3. Re-login: `devbridge auth logout && devbridge auth login`

### Problem: `Authentication failed: access denied`

**Cause:** IAM user lacks required permissions.

**Solution:**

1. Check current permissions with an account admin.
2. Apply the minimum DevBridge policy (see [IAM Policies](iam-policies.md)).
3. Re-authenticate after permissions are granted.

**✅ Correct approach:**

```bash
# Check auth status, identify missing permissions, grant policy, then retry
devbridge auth status
# → Review iam-policies.md for required permissions
# → Grant policy in IAM console
devbridge auth login
```

**❌ Incorrect approach:**

```bash
# Repeatedly retrying without fixing permissions
devbridge create my-tunnel -d "测试" -e 8
# → Error: access denied
devbridge create my-tunnel -d "测试" -e 8
# → Error: access denied (still fails)
```

---

## Tunnel Creation Issues

### Problem: `Failed to create tunnel: quota exceeded`

**Cause:** Account has reached the maximum number of tunnels.

**Solution:**

1. List existing tunnels: `devbridge list`
2. Delete unused tunnels: `devbridge delete <tunnelId>`
3. Contact Huawei Cloud support to request a quota increase.

### Problem: `Failed to create tunnel: invalid name`

**Cause:** Tunnel name contains invalid characters.

**Solution:**

- Use only letters, numbers, and hyphens.
- Name must be 3-64 characters long.
- Example: `devbridge create my-tunnel-001`

### Problem: `Failed to create tunnel: network error`

**Cause:** Cannot reach DevBridge service.

**Solution:**

1. Check network connectivity.
2. Verify the correct region is configured.
3. Try a different region: `devbridge create my-tunnel --region cn-north-4`

---

## Port Management Issues

### Problem: `Port already exists`

**Cause:** The port number is already in use on the tunnel.

**Solution:**

1. List existing ports: `devbridge port list <tunnelId>`
2. Use a different port number, or delete the existing port first:

```bash
devbridge port delete <tunnelId> -p 8080
devbridge port create <tunnelId> -p 8080 --protocol http
```

### Problem: `Invalid port number`

**Cause:** Port number is out of valid range.

**Solution:**

- Use port numbers between 1 and 65535.
- Ports below 1024 may require elevated privileges.

---

## Host Issues

### Problem: `Host failed: local service not reachable`

**Cause:** No service is running on the specified local port.

**Solution:**

1. Verify the local service is running:

```bash
curl http://localhost:8080
```

2. Start the service before running `devbridge host`.

### Problem: `Host failed: tunnel expired`

**Cause:** The tunnel has reached its expiration time.

**Solution:**

1. Check tunnel status: `devbridge show <tunnelId>`
2. If expired, create a new tunnel and reconfigure ports.

### Problem: `Host disconnected unexpectedly`

**Cause:** Network interruption or service crash.

**Solution:**

1. Check local service status.
2. Check network connectivity.
3. Restart host: `devbridge host <tunnelId>`
4. Use `--log-level debug` for detailed logs:

```bash
devbridge host <tunnelId> --log-level debug
```

---

## Connect Issues

### Problem: `Connect failed: tunnel not found`

**Cause:** The tunnel ID is incorrect or the tunnel has been deleted.

**Solution:**

1. Verify the tunnel ID: `devbridge show <tunnelId>`
2. If deleted, request the correct tunnel ID from the host operator.

### Problem: `Connect failed: local port in use`

**Cause:** The local port is already occupied by another process.

**Solution:**

1. Find and stop the process using the port:

```bash
lsof -i :8080
kill <PID>
```

2. Or use a different local port:

```bash
devbridge connect <tunnelId> --port 8080 --local-port 9090
```

### Problem: `Connection drops frequently`

**Cause:** Unstable network or idle timeout.

**Solution:**

1. Check network stability.
2. The CLI automatically reconnects on transient failures.
3. If issues persist, restart the connect session.

---

## Network Issues

### Problem: `Connection timeout`

**Cause:** Firewall or network restrictions blocking DevBridge traffic.

**Solution:**

1. Check firewall rules for outbound HTTPS (443) access.
2. Configure proxy if needed:

```bash
export https_proxy=http://<proxy-host>:<proxy-port>
devbridge host <tunnelId>
```

### Problem: `SSL certificate verification failed`

**Cause:** Corporate proxy intercepting SSL traffic.

**Solution:**

1. Configure the proxy's CA certificate.
2. Contact your network administrator for the CA certificate.
3. Set the certificate path:

```bash
export SSL_CERT_FILE=/path/to/ca-bundle.crt
```

---

## Permission Issues

### Problem: `403 Forbidden: insufficient permissions`

**Cause:** IAM user lacks required DevBridge permissions.

**Solution:**

1. Review required permissions in [IAM Policies](iam-policies.md).
2. Ask an account admin to grant the DevBridge policy.
3. Re-authenticate: `devbridge auth logout && devbridge auth login`

### Problem: `403 Forbidden: token expired`

**Cause:** IAM token has expired.

**Solution:**

```bash
devbridge auth logout
devbridge auth login
```

---

## Getting Help

If the issue persists after trying the solutions above:

1. **Enable debug mode** for detailed logs:

```bash
devbridge --debug <command>
```

2. **Check version** — ensure you are using the latest version:

```bash
devbridge version
```

3. **Collect diagnostic information:**

```bash
devbridge auth status
devbridge list
devbridge --debug <failing-command>
```

4. **Contact Huawei Cloud support** with the diagnostic information.
