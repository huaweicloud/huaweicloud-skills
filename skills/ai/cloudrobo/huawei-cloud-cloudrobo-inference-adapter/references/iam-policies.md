# Authentication & Access Control

> Follows the `iam-policies.md` structure of the sibling CloudRobo skills.
> **This skill calls no Huawei Cloud or CloudRobo API**, so it needs no IAM
> policy and no AK/SK.

## Authentication Model

All work happens locally in the user's model/deployment environment:

| Component | What it does | Cloud authentication |
| --------- | ------------ | -------------------- |
| `references/adapter_template.py` | converts wire observations to model input and actions back | none |
| `references/server_template.py` | serves the adapter over WSS (WebSocket over TLS) | none (local TLS only) |
| `scripts/test_client.py` | connects to the server, reads the handshake metadata, sends test observations | none |
| `scripts/verify_adapter.py` | server-less unit checks of an adapter class | none |

## Required Credentials

None. Do not export `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` for this skill, and
never write credentials into the adapter or server code.

## Least-Privilege Model

No IAM permissions or workspace roles are required. Deploying the adapted
model as a CloudRobo inference service is out of scope here; it is done with
`huawei-cloud-cloudrobo-infer`, whose `references/iam-policies.md` lists the
credentials and access it needs.

## Service Endpoints

No Huawei Cloud endpoints are contacted. The only network endpoint is the
local inference server started from `server_template.py`:

| Endpoint | Default | Notes |
| -------- | ------- | ----- |
| Transport server (WSS) | binds `0.0.0.0:8000` | change `host`/`port` in `TransportServer(...)` as needed |
| Test client target | `127.0.0.1:8000` | `scripts/test_client.py --host ... --port ...` |

## Security Constraints

- **Network exposure**: the server binds all interfaces by default and has
  no request authentication. Bind it to `127.0.0.1`, or restrict access
  with a firewall or security group, unless remote robot clients need to
  reach it. Never expose it to the public internet.
- **TLS**: the template generates a self-signed certificate (CN=`localhost`)
  for WSS. Replace it with a certificate the clients trust before using it
  outside a test environment.
- **Untrusted input**: observations come from the network. Keep the
  adapter's shape and dtype validation (image keys, state dimension), which
  rejects malformed frames before they reach the model.
