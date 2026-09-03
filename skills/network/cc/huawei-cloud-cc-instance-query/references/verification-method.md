# Verification Method

## How to Verify Query Results

### 1. Cloud Connection Query Verification

After running `ListCloudConnections`, verify the output:

- **Non-empty list** — If the account has cloud connections, the response should contain a `cloud_connections` array with entries.
- **Each entry has** — `id`, `name`, `status`, `instance_id`, `cloud_connection_id` fields.
- **Status check** — `status` should be `ACTIVE` for available connections.

After running `ShowCloudConnection --id=<id>`, verify:

- The returned `id` matches the requested `--id`.
- `status` is a valid value (`ACTIVE`, `BUILDING`, `FAILED`, etc.).

### 2. Bandwidth Package Query Verification

- `ListBandwidthPackages` returns a `bandwidth_packages` array.
- Each entry has `id`, `name`, `status`, `bandwidth`, `cloud_connection_id`.
- `ShowBandwidthPackage --id=<id>` returns details including `bandwidth` (size in Mbit/s) and `billing_mode`.

### 3. Inter-Region Bandwidth Query Verification

- `ListInterRegionBandwidths` returns an `inter_region_bandwidths` array.
- Each entry has `id`, `cloud_connection_id`, `bandwidth_package_id`, `source_region_id`, `destination_region_id`.
- Verify that `bandwidth` does not exceed the parent bandwidth package's total bandwidth.

### 4. Network Instance Query Verification

- `ListNetworkInstances` returns a `network_instances` array.
- Each entry has `id`, `name`, `status`, `type` (e.g., `VPC`, `VGW`), `instance_id`, `region_id`.
- Cross-reference `cloud_connection_id` with cloud connection queries to verify topology.

### 5. Cloud Connection Route Query Verification

- `ListCloudConnectionRoutes` returns a `cloud_connection_routes` array.
- Each entry has `id`, `cloud_connection_id`, `destination`, `next_hop`, `status`.
- `ShowCloudConnectionRoutes --id=<id>` returns detailed route information including source and destination.

## Common Verification Patterns

| Pattern | How to Verify |
|---------|--------------|
| Pagination works | Call list with `--limit=1`, get `marker`, call again with `--marker=<marker>` |
| Filter works | Call list with `--status.1=ACTIVE`, verify all results have `status=ACTIVE` |
| Show matches list | Get an ID from list result, call Show with that ID, verify fields match |
| Cross-resource consistency | Network instance's `cloud_connection_id` should exist in cloud connection list |
