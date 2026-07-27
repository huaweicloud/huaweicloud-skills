# Acceptance Criteria — huawei-cloud-swr-enterprise-instance

Criteria for successful SWR enterprise instance management operations.

## Prerequisites

- [ ] hcloud CLI installed (version >= 7.2.2)
- [ ] AK/SK credentials configured via environment variables or `hcloud configure`
- [ ] SWR enterprise service activated via console (`https://console.huaweicloud.com/swr-instance`)
- [ ] Target region supports SWR enterprise instances and the desired spec
- [ ] IAM permissions granted for SWR enterprise instance operations
- [ ] User informed of hourly billing costs before instance creation

## Instance Lifecycle

- [ ] CreateInstance returns valid `instance_id`
- [ ] ListInstance shows the created instance with status `Running`
- [ ] ShowInstance returns full instance details
- [ ] UpdateInstanceConfiguration applies new settings without error
- [ ] DeleteInstance removes the instance and all associated resources

## Namespace Management

- [ ] CreateInstanceNamespace creates namespace with specified security scanning settings
- [ ] ListInstanceNamespaces returns all namespaces for the instance
- [ ] UpdateInstanceNamespace modifies security scanning configuration
- [ ] DeleteInstanceNamespace removes namespace and all repositories under it

## Credential Management

- [ ] CreateInstanceLtCredential returns username and encoded password
- [ ] Credentials are stored securely and never exposed in logs
- [ ] CreateInstanceTempCredential returns short-lived credentials with expiry
- [ ] DeleteInstanceLtCredential invalidates the credential immediately

## Network Access

- [ ] CreateInstanceEndpoint creates internal or public endpoint
- [ ] Public access whitelist correctly restricts IP access
- [ ] Custom domain resolves to the instance endpoint

## Security

- [ ] No AK/SK or security tokens exposed in any output
- [ ] Credential passwords are base64-encoded and handled securely
- [ ] Risk confirmation obtained before all destructive operations
- [ ] Instance deletion confirmed before removing all data
