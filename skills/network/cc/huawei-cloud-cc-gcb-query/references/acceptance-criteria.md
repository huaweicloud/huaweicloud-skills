# Acceptance Criteria

## Success Criteria for Each Query Type

### AC-01: Show GCB (Single Query)

| Criterion | Expected |
|-----------|----------|
| Command executes without error | Exit code 0 |
| Response contains GCB ID | `id` field matches requested `--id` |
| Response contains bandwidth size | `size` field is a positive integer |
| Response contains type | `type` field is one of: `TrsArea`, `Area`, `SubArea`, `Region` |
| Bound instance info present | If instances are bound, `instances` or `binding_service` is populated |

### AC-02: List GCBs

| Criterion | Expected |
|-----------|----------|
| Command executes without error | Exit code 0 |
| Response contains array | `globalconnection_bandwidths` is an array |
| Page info present | `page_info.current_count` matches array length |
| Filters respected | Results match applied filters (status, type, charge_mode, etc.) |
| Pagination works | `--marker` returns next/previous page correctly |

### AC-03: GCB Tenant Configs

| Criterion | Expected |
|-----------|----------|
| Command executes without error | Exit code 0 |
| Config object present | `configs` object exists in response |
| Size ranges present | `gcbSizeRange` or `size_range` array with min/max per charge mode |
| Quotas present | `quotas` array with `gcb.size` and `gcb.count` types |
| Charge modes listed | `charge_mode` array includes at least `bwd` |
| Services listed | `services` array includes at least `CC` |

### AC-04: Support Binding GCBs

| Criterion | Expected |
|-----------|----------|
| Command executes without error | Exit code 0 |
| Response contains array | `globalconnection_bandwidths` is an array |
| Page info present | `page_info.current_count` matches array length |
| Binding service required | Command fails if `--binding_service` is omitted |
| Area filter works | `--local_area` and `--remote_area` filter results correctly |

## Negative Test Criteria

| Criterion | Expected |
|-----------|----------|
| Missing `--domain_id` | Error: parameter required |
| Invalid GCB ID (too short) | Error: id length incorrect (min 32, max 36) |
| Missing `--binding_service` (Support Binding) | Error: parameter required |
| Invalid region | Error: region not supported |
