# Verification Method

## Functional Verification

### 1. Verify CLI Access

```bash
hcloud CC ListCentralNetworks --cli-region=cn-north-4 --domain_id={domain_id} --limit=1
```

Expected: JSON response with `central_networks` array (may be empty if no instances exist).

### 2. Verify Show Operation

```bash
# Use an ID from the list result
hcloud CC ShowCentralNetwork --cli-region=cn-north-4 --domain_id={domain_id} --central_network_id={central_network_id}
```

Expected: JSON response with central network details including `planes`, `er_instances`, and `connections` arrays.

### 3. Verify Attachments

```bash
hcloud CC ListCentralNetworkAttachments --cli-region=cn-north-4 --domain_id={domain_id} --central_network_id={central_network_id} --limit=1
```

Expected: JSON response with `attachments` array. Each entry has `attachment_instance_type` (`GDGW` or `ER_ROUTE_TABLE`).

### 4. Verify Connections

```bash
hcloud CC ListCentralNetworkConnections --cli-region=cn-north-4 --domain_id={domain_id} --central_network_id={central_network_id} --limit=1
```

Expected: JSON response with `connections` array.

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `DomainId is not valid` | Incorrect domain_id | Obtain from IAM → My Credentials → Account ID |
| `Unauthorized` | Missing IAM permissions | Assign policy with `cc:centralNetworks:list` and `cc:centralNetworks:get` |
| `Central network not found` | Wrong ID or region | Verify with ListCentralNetworks first |
| Empty results | No resources in account | Normal if no central networks have been created |
