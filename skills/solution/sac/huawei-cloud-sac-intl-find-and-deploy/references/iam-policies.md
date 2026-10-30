# IAM Policies — sac-intl-find-and-deploy-skill

Least-privilege guidance. No fabricated Action names — verify exact actions in console before apply.

## Principles

- Use an IAM user, never the primary account.
- Prefer short-lived temporary credentials (AK + SK + SecurityToken).
- Scope the user to the services the chosen template provisions (typically ECS, VPC, EIP, EVS).
- Start with read + deploy in one test region; expand only after validation.

## Verify before use

1. Console → IAM → Permissions → locate the system role covering compute + network provisioning for the target region.
2. Attach it to the deploy user; confirm `terraform plan` shows no `403` before `apply`.
3. After `destroy` succeeds, detach or rotate credentials.

## Failure handling

- `403` on plan → missing permission: add the service-specific policy in console and re-plan.
- Never paste credentials in chat; use env vars `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN` or manual tfvars edit.
