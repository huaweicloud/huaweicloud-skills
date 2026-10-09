# Verification Method

Verify that the skill's diagnosis results are correct and complete.

## Verification Steps

### 1. Verify Credential Configuration

```bash
hcloud configure list
```

Check that the output contains a valid AK/SK configuration (mode=AKSK).

### 2. Verify Domain Permission Validation

```bash
hcloud CDN ShowDomainDetailByName --cli-region=<region> --domain_name=<test domain>
```

Check that the return is 200 and contains a domain_id, confirming the domain belongs to the current account.

### 3. Verify Origin Configuration Query

```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=<region> --domain_name=<test domain>
```

Check that the return contains the configs.sources field, and parse the following information:
- `origin_addr`: origin address
- `origin_type`: origin type (ipaddr/domain/obs_bucket)
- `http_port`: HTTP back-to-source port
- `https_port`: HTTPS back-to-source port
- `origin_protocol`: back-to-source protocol (http/https/follow)

If configs.sources is empty, report "origin not configured".

### 4. Verify Origin Probe (HTTP)

```bash
python scripts/origin_probe.py --scheme http --host <origin_addr> --port <http_port>
```

The script emits a JSON object on stdout. Verify the following fields:
- `data.connected=true` with `data.http_status` 200 / 3xx → origin reachable
- `data.connected=true` with `data.http_status` 5xx, OR `data.connected=false` with `data.error.reason=connect_failed` → origin unreachable (with IP whitelist prompt)
- `data.connected=false` with `data.error.reason=connect_timeout` → probe timeout

Expected JSON shape (success):
```json
{"result":"success","data":{"scheme":"http","host":"<origin_addr>","port":<http_port>,"connected":true,"http_status":200,"is_private_address":false,"duration_ms":12,"error":null},"error_msg":""}
```

### 5. Verify Origin Probe (HTTPS, if origin_protocol=https or follow)

```bash
python scripts/origin_probe.py --scheme https --host <origin_addr> --port <https_port>
```

The decision logic is the same as for the HTTP probe; the `scheme` field in the output JSON reflects `https`.

Expected JSON shape (success):
```json
{"result":"success","data":{"scheme":"https","host":"<origin_addr>","port":<https_port>,"connected":true,"http_status":200,"is_private_address":false,"duration_ms":210,"error":null},"error_msg":""}
```

### 6. Verify Report Format

Check that the output report contains:
- Analysis time and target domain
- Origin configuration info (origin_addr, origin_type, http_port, https_port, origin_protocol)
- Diagnosis item list (each item includes a name, status ✅/❌/⚠️, and detail)
- Conclusion and remediation suggestion
- If the origin is unreachable, an IP whitelist prompt is included

## Expected Output

### Origin Reachable Example

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:00:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: 192.168.1.100
origin_type: ipaddr
http_port: 80
https_port: 443
origin_protocol: http

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxx
[Origin Configuration Query]: ✅ Pass
  Detail: Origin configuration found, origin_addr=192.168.1.100
[Origin Connectivity Probe]: ✅ Pass
  Detail: HTTP 200, origin reachable

--- Conclusion ---
Status: Origin diagnosis passed
Suggestion: Origin connectivity is normal. If back-to-source failures persist, check the back-to-source configuration consistency in the CDN console.
```

### Origin Unreachable Example (with IP whitelist prompt)

```
==================== CDN Origin Server Diagnosis Report ====================
Analysis Time: 2026-08-12T10:05:00+08:00
Target Domain: www.example.com

--- Origin Configuration ---
origin_addr: 192.168.1.100
origin_type: ipaddr
http_port: 80
https_port: 443
origin_protocol: http

--- Diagnosis Items ---
[Domain Permission Validation]: ✅ Pass
  Detail: Domain belongs to the current account, domain_id=xxx
[Origin Configuration Query]: ✅ Pass
  Detail: Origin configuration found, origin_addr=192.168.1.100
[Origin Connectivity Probe]: ❌ Fail
  Detail: HTTP 502, origin unreachable

--- Conclusion ---
Status: Origin unreachable
Suggestion: The origin may have a whitelist configured. Please confirm that the CDN back-to-source IP ranges have been added to the origin whitelist.
```
