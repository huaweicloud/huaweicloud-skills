# Verification Method

## How to Verify Query Results

### 1. Show GCB — Verify Single Query

```bash
hcloud CC ShowGlobalConnectionBandwidth --cli-region=cn-north-4 --domain_id=<account_id> --id=<gcb_id>
```

**Success criteria:**
- Response contains `id` matching the requested GCB ID
- Response includes `name`, `size`, `type`, `admin_state` fields
- If instances are bound, `instances` or `binding_service` field is populated

### 2. List GCBs — Verify List Query

```bash
hcloud CC ListGlobalConnectionBandwidths --cli-region=cn-north-4 --domain_id=<account_id> --limit=10
```

**Success criteria:**
- Response contains `globalconnection_bandwidths` array
- Response contains `page_info` with `current_count`
- `current_count` matches the number of items in the array
- If `current_count` > 0, each item has `id`, `name`, `size` fields

### 3. GCB Tenant Configs — Verify Config Query

```bash
hcloud CC ListGlobalConnectionBandwidthConfigs --cli-region=cn-north-4 --domain_id=<account_id>
```

**Success criteria:**
- Response contains `configs` object
- `configs` includes `gcbSizeRange` (or `size_range`) with min/max per charge mode
- `configs` includes `quotas` with `gcb.size` and `gcb.count` quota types
- `configs` includes `charge_mode` and `services` arrays

### 4. Support Binding GCBs — Verify Binding Query

```bash
hcloud CC ListSupportBindingConnectionBandwidths --cli-region=cn-north-4 --domain_id=<account_id> --binding_service=CC --limit=10
```

**Success criteria:**
- Response contains `globalconnection_bandwidths` array
- Response contains `page_info` with `current_count`
- Each GCB in the list is eligible for binding to the specified `binding_service`

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Parameter domain_id is required` | Missing `--domain_id` | Provide account ID from IAM → My Credentials |
| `Parameter id length incorrect` | GCB ID too short/long | Ensure ID is 32–36 characters |
| `Unauthorized` | AK/SK lacks CC permissions | Assign `CC ReadOnlyAccess` or custom policy |
| Empty list | No GCBs exist or filters too restrictive | Remove filters or create GCBs first |
