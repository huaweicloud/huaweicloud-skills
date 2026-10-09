# Step 2: Query Origin Configuration

Retrieve the full configuration of the CDN domain via ShowDomainFullConfig/v2, and parse the origin configuration.

## 2.1 Query Full Domain Configuration

**Command**:
```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<domain>
```

**Decision Logic**:

| Return Code | Action |
|-------------|--------|
| 200 | Continue to 2.2 to parse origin configuration |
| 404 | Abort; return "Domain does not exist" |
| 403 | Abort; return "No permission to query domain configuration. Please contact the administrator to grant the CDN query permission (`cdn:*:query*`)." |
| Other errors | Abort; return "Origin configuration query failed: <error message>" |

## 2.2 Parse Origin Configuration

Parse the `configs.sources` field from the returned result.

### Determine Whether sources Is Empty

| configs.sources Status | Action |
|------------------------|--------|
| Non-empty array (contains at least one element) | Continue to parse origin fields |
| Empty array `[]` | Report "Origin not configured. Please configure the origin in the CDN console." and abort Step 3 (probe step) |
| Field does not exist | Report "Origin not configured. Please configure the origin in the CDN console." and abort Step 3 (probe step) |

### Parse Origin Fields

Parse the following fields from `configs.sources[0]`:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `origin_addr` | string | Origin address (IP or domain) | `192.168.1.100` / `origin.example.com` |
| `origin_type` | string | Origin type | `ipaddr` / `domain` / `obs_bucket` |
| `http_port` | integer | HTTP back-to-source port | `80` |
| `https_port` | integer | HTTPS back-to-source port | `443` |

Parse the back-to-source protocol from `configs`:

| Field | Type | Description | Possible Values |
|-------|------|-------------|-----------------|
| `origin_protocol` | string | Back-to-source protocol | `http` / `https` / `follow` |

### origin_protocol Description

| origin_protocol | Meaning | Probe Strategy |
|-----------------|---------|----------------|
| http | CDN always uses HTTP for back-to-source | Probe http://<origin_addr>:<http_port> |
| https | CDN always uses HTTPS for back-to-source | Probe https://<origin_addr>:<https_port> |
| follow | CDN follows the client protocol for back-to-source | Probe both http and https |

## 2.3 Output Records

After parsing is complete, record the following information for subsequent steps and the report:
- origin_addr
- origin_type
- http_port (default 80 if missing)
- https_port (default 443 if missing)
- origin_protocol (default http if missing)

## Exception Handling

| Exception Scenario | Handling |
|--------------------|----------|
| ShowDomainFullConfig/v2 call failed | Report "Origin configuration query failed. Manual confirmation recommended." and abort subsequent steps |
| sources field format abnormal | Report "Origin configuration parsing failed." and abort Step 3 |
| http_port / https_port missing | Use default values (80 / 443); note in report "Port not configured; using default value" |
| origin_protocol missing | Use default value http; note in report "Back-to-source protocol not configured; defaulting to http" |

## Example

```bash
# Query origin configuration
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=www.example.com

# Return example:
# {
#   "configs": {
#     "sources": [
#       {
#         "origin_addr": "192.168.1.100",
#         "origin_type": "ipaddr",
#         "http_port": 80,
#         "https_port": 443
#       }
#     ],
#     "origin_protocol": "http"
#   }
# }

# Parsed result:
# origin_addr=192.168.1.100, origin_type=ipaddr
# http_port=80, https_port=443, origin_protocol=http
```
