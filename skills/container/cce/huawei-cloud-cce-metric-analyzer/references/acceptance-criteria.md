# Acceptance Criteria

## Functional Acceptance

| ID | Area | Acceptance Standard |
| --- | --- | --- |
| AC-01 | Tool registration | All dispatcher actions listed in `SKILL.md` are registered in `scripts/huawei_cloud/dispatcher.py` |
| AC-02 | Pod metrics | Pod TopN and single Pod tools return `success=true` or a clear permission/configuration error |
| AC-03 | Node metrics | Node TopN and single Node tools return CPU, memory, and disk sections |
| AC-04 | GPU metrics | Node/Pod GPU tools return empty non-GPU summaries cleanly and do not fail on non-GPU clusters |
| AC-05 | Component metrics | CoreDNS, nginx-ingress, autoscaler, apiserver, etcd, controller-manager, and scheduler tools return structured summaries |
| AC-06 | Cloud metrics | ECS, ELB, EIP, and NAT tools use hcloud/CES and return structured metric keys |
| AC-07 | Aggregation | Cluster aggregation returns `summary`, component summaries, cloud resource sections, and anomaly counts |
| AC-08 | kubectl scope | kubectl is used only for Pod label filtering, Ingress TLS Secret checks, and LoadBalancer Service association |

## Security Acceptance

| ID | Area | Acceptance Standard |
| --- | --- | --- |
| SAF-01 | Read-only boundary | No tool creates, updates, deletes, restarts, scales, or remediates resources |
| SAF-02 | Secret handling | AK/SK, security tokens, kubeconfig content, and TLS Secret content are not printed or persisted |
| SAF-03 | Credential priority | hcloud calls use explicit parameters, then hcloud profile, then environment fallback |
| SAF-04 | AOM signing | AOM Prometheus HTTP uses explicit/environment credentials and supports temporary security tokens |
| SAF-05 | Query scope | PromQL defaults include `cluster="<cluster_id>"` or a cluster-equivalent selector |

## Documentation Acceptance

| ID | Area | Acceptance Standard |
| --- | --- | --- |
| DOC-01 | SKILL size | `SKILL.md` is at or below 500 lines |
| DOC-02 | Required references | `cli-installation-guide.md`, `iam-policies.md`, `verification-method.md`, and `acceptance-criteria.md` exist under `references/` |
| DOC-03 | kubectl-cce guide | kubectl-cce installation and usage details are in `references/kubectl-cce.md`, not expanded in the main SKILL |
| DOC-04 | Risk rules | Read-only risk boundaries are documented in `references/risk-rules.md` |

## Quality Acceptance

| ID | Area | Acceptance Standard |
| --- | --- | --- |
| QA-01 | Static checks | `python3 -m compileall -q scripts/huawei_cloud` passes |
| QA-02 | Whitespace checks | `git diff --check` passes |
| QA-03 | JSON output | Tool outputs parse with strict JSON clients and do not contain non-finite values |
| QA-04 | Error clarity | Permission, missing AOM instance, missing resource ID, and kubectl failures return actionable errors |

## Acceptance Decision

The skill is accepted when all functional, security, documentation, and quality criteria above pass for a non-production CCE cluster with AOM Prometheus integrated.
