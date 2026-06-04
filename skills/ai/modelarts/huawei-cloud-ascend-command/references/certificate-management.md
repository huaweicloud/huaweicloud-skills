# Certificate Management Reference

## Certificate Information

### Get Certificate Status

**Command:** `npu-smi info -t cert -i <npu_id>`

**Natural Language:** `Certificate status`, `Certificate info`

**Output:** Certificate status and expiration date

### Get Certificate Details

**Command:** `npu-smi info -t cert-detail -i <npu_id>`

**Natural Language:** `Certificate details`

**Output:** Detailed certificate information

## Certificate Installation

### Install Certificate

**Command:** `npu-smi set -t cert-install -i <npu_id> -f <cert_file>`

**Natural Language:** `Install certificate`, `Import certificate`

**Sensitive:** Requires confirmation

**Parameters:** Path to certificate file

### Install CA Certificate

**Command:** `npu-smi set -t cert-ca-install -i <npu_id> -f <ca_file>`

**Natural Language:** `Install CA certificate`

**Sensitive:** Requires confirmation

## Certificate Removal

### Remove Certificate

**Command:** `npu-smi set -t cert-remove -i <npu_id>`

**Natural Language:** `Remove certificate`

**Sensitive:** Requires confirmation

### Remove CA Certificate

**Command:** `npu-smi set -t cert-ca-remove -i <npu_id>`

**Natural Language:** `Remove CA certificate`

**Sensitive:** Requires confirmation

## Certificate Renewal

### Renew Certificate

**Command:** `npu-smi set -t cert-renew -i <npu_id>`

**Natural Language:** `Renew certificate`, `Update certificate`

**Sensitive:** Requires confirmation

### Generate Certificate Signing Request

**Command:** `npu-smi set -t cert-csr-generate -i <npu_id> -f <output_file>`

**Natural Language:** `Generate CSR`, `Certificate signing request`

**Sensitive:** Requires confirmation

**Parameters:** Output file path for CSR

## Certificate Verification

### Verify Certificate

**Command:** `npu-smi info -t cert-verify -i <npu_id>`

**Natural Language:** `Verify certificate`

**Output:** Certificate verification result

### Check Certificate Expiry

**Command:** `npu-smi info -t cert-expiry -i <npu_id>`

**Natural Language:** `Certificate expiry`, `Certificate expiration`

**Output:** Days until certificate expires

## Security Configuration

### Enable HTTPS

**Command:** `npu-smi set -t https-enable -i <npu_id> -d 1`

**Natural Language:** `Enable HTTPS`, `Enable secure connection`

**Sensitive:** Requires confirmation

### Disable HTTPS

**Command:** `npu-smi set -t https-enable -i <npu_id> -d 0`

**Natural Language:** `Disable HTTPS`

**Sensitive:** Requires confirmation

## Certificate Best Practices

### Certificate Management Checklist

1. **Check certificate expiration regularly:**
   ```bash
   npu-smi info -t cert-expiry -i 0
   ```

2. **Verify certificate validity:**
   ```bash
   npu-smi info -t cert-verify -i 0
   ```

3. **Backup certificates:**
   ```bash
   # Export certificates to safe location
   ```

4. **Use strong certificate encryption:**
   - Prefer SHA-256 or higher
   - Use 2048-bit or larger keys

### Security Recommendations

- Replace default certificates with custom ones
- Use certificates signed by trusted CA
- Regularly renew certificates before expiration
- Store certificate files securely
- Restrict certificate file permissions

## Troubleshooting Certificate Issues

### Issue: Certificate expired

**Symptom:** `Certificate expired`

**Solution:** Renew or install new certificate

### Issue: Certificate verification failed

**Symptom:** `Certificate verification failed`

**Possible causes:**
1. Certificate corrupted
2. CA certificate not installed
3. Certificate mismatch

**Solution:**
1. Reinstall certificate
2. Install CA certificate
3. Verify certificate file

### Issue: Cannot install certificate

**Symptom:** `Certificate installation failed`

**Possible causes:**
1. Invalid certificate format
2. Insufficient permissions
3. Certificate file not found

**Solution:**
1. Use valid certificate format (PEM/DER)
2. Run as root
3. Verify certificate file path
