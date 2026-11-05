# IAM Policies - Huawei Cloud CCE Kubectl Installer

This skill installs the local `kubectl` and `kubectl-cce` binaries only. It does **not** call any Huawei Cloud OpenAPI and does **not** require IAM permissions or Huawei Cloud credentials.

## Required IAM Permissions

None. The installer operates entirely on the local filesystem:

- It downloads the public `kubectl` package from Huawei Cloud OBS (`obs.cn-north-4.myhuaweicloud.com`, public read) and the public `kubectl-cce` asset from Gitee Releases, then extracts and copies binaries into `--bin-dir` (default installation directory).
- It never signs a request with AK/SK, never requests an IAM token, and never touches a cloud resource.
- Huawei Cloud credentials are not read, forwarded, or required by `scripts/install_kubectl_cce.sh`.

## Equivalent Access Controls

Because no cloud-side authorization applies, the effective access surface of this skill is local and network based. Review these instead of IAM policies:

| Control | Requirement | Notes |
| --- | --- | --- |
| Target directory write permission | The invoking user must be able to create and replace files in `--bin-dir` (default installation directory). | `/usr/local/bin` usually needs elevated local permission; the skill never uses `sudo` automatically. |
| Outbound network reachability | HTTPS egress to the Huawei Cloud OBS package host and the Gitee Release host must be available. | The source-build fallback additionally needs Go module and Git remote access. |
| Local execution permission | The user must be allowed to run `curl`, `tar`, `cp`, `chmod`, and the installed binaries. | Source-build fallback also requires `git` and Go. |

No resource-level or action-level IAM grant makes this skill succeed or fail; only local permissions and network reachability do.

## Least-Privilege Guidance

- Point `--bin-dir` at a user-owned directory when possible to avoid elevated local permission.
- Do not grant broad cloud permissions for the purpose of running this installer; none are used.
- Keep the default download timeouts and verify the installed version with `kubectl version --client` and `kubectl plugin list`.

## Verification

Confirm no credentials were needed by running the installer in an environment without Huawei Cloud environment variables:

```bash
bash scripts/install_kubectl_cce.sh --check
```

The check and installation plan must complete without AK/SK, project ID, or region context.