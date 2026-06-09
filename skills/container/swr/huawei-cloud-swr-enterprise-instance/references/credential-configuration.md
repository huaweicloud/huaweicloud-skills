# Credential Configuration for hcloud CLI

hcloud CLI (KooCLI) supports two credential modes via environment variables, automatically detected at runtime.

> **Security Rules**:
> - 🚫 Never expose AK/SK/SecurityToken values in conversation, commands, or output
> - ✅ Prefer environment variables or hcloud CLI profile mode
> - ✅ Use `hcloud configure list` to check credential status (presence only, not values)

## Mode A — Long-term AK/SK

Suitable for permanent access, CI/CD pipelines, and long-running automation.

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Characteristics**:
- Credentials are valid until manually revoked in IAM console
- Recommended for service accounts, CI/CD pipelines, and automation scripts
- Rotate regularly following security best practices

## Mode B — Temporary AK/SK + SecurityToken

Recommended for temporary, delegated, or fine-grained access scenarios.

```bash
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

**Characteristics**:
- Credentials expire after a configured duration (typically 15 minutes to 24 hours)
- Obtained via IAM `CreateTemporaryAccessKeyByToken` or `CreateTemporaryAccessKeyByAgency` APIs
- Supports scoped permissions via agency delegation
- When `HUAWEI_CLOUD_SECURITY_TOKEN` is present, hcloud CLI automatically uses temporary credential authentication
- When only AK/SK are set, it uses long-term credential authentication

## Validation

After configuring credentials, verify they work:

```bash
# Check credential presence (shows profile name, NOT credential values)
hcloud configure list

# Verify connectivity with a simple query
hcloud SWR ListNamespaces --cli-region=cn-north-4 --cli-output=json
```

## Important Notes

- Never commit credentials to version control
- Use IAM users with minimal required permissions (least privilege principle)
- Enable MFA for sensitive operations
- Rotate long-term AK/SK regularly
- For temporary credentials, use appropriate expiration duration — too short causes frequent re-authentication, too long increases risk
