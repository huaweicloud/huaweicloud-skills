#!/usr/bin/env bash
# ==============================================================================
# remediate-restored-workloads.sh
# Post-restore automated remediation for Huawei Cloud CCE:
# 1. Rewrites containers AND initContainers images to target SWR organization.
# 2. Injects imagePullSecrets for private SWR authentication.
# 3. Scales application workloads from maintenance scale-down (replicas 0 -> target).
# 4. Detects EVS RWO volume bindings to assist in node pinning.
# ==============================================================================

set -euo pipefail

NAMESPACE="${1:-}"
SWR_PREFIX="${2:-}"
PULL_SECRET="${3:-default-secret}"
TARGET_REPLICAS="${4:-1}"

if [[ -z "${NAMESPACE}" || -z "${SWR_PREFIX}" ]]; then
  echo "Usage: $0 <namespace> <swr_prefix> [pull_secret_name] [target_replicas]"
  echo "Example: $0 dify swr.ap-southeast-3.myhuaweicloud.com/dify-migration default-secret 1"
  exit 1
fi

echo "[INFO] Starting workload remediation for namespace: ${NAMESPACE}"
echo "[INFO] Target SWR Registry: ${SWR_PREFIX}"

for KIND in deployment statefulset; do
  ITEMS=$(kubectl get "${KIND}" -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
  for ITEM in ${ITEMS}; do
    if [[ "${ITEM}" == "placeholder" ]]; then
      continue
    fi
    echo "[INFO] Remediating ${KIND}/${ITEM}..."

    MANIFEST=$(kubectl get "${KIND}" "${ITEM}" -n "${NAMESPACE}" -o json)

    # 1. Patch containers image
    CONTAINER_COUNT=$(echo "${MANIFEST}" | jq '.spec.template.spec.containers | length')
    for (( i=0; i<CONTAINER_COUNT; i++ )); do
      CURRENT_IMG=$(echo "${MANIFEST}" | jq -r ".spec.template.spec.containers[$i].image")
      IMG_NAME=$(echo "${CURRENT_IMG}" | awk -F'/' '{print $NF}')
      NEW_IMG="${SWR_PREFIX}/${IMG_NAME}"
      if [[ "${CURRENT_IMG}" != "${NEW_IMG}" ]]; then
        echo "  - Container $i: ${CURRENT_IMG} -> ${NEW_IMG}"
        kubectl patch "${KIND}" "${ITEM}" -n "${NAMESPACE}" --type=json \
          -p="[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/${i}/image\", \"value\": \"${NEW_IMG}\"}]" >/dev/null
      fi
    done

    # 2. Patch initContainers image
    INIT_COUNT=$(echo "${MANIFEST}" | jq '.spec.template.spec.initContainers // [] | length')
    for (( i=0; i<INIT_COUNT; i++ )); do
      CURRENT_IMG=$(echo "${MANIFEST}" | jq -r ".spec.template.spec.initContainers[$i].image")
      IMG_NAME=$(echo "${CURRENT_IMG}" | awk -F'/' '{print $NF}')
      NEW_IMG="${SWR_PREFIX}/${IMG_NAME}"
      if [[ "${CURRENT_IMG}" != "${NEW_IMG}" ]]; then
        echo "  - InitContainer $i: ${CURRENT_IMG} -> ${NEW_IMG}"
        kubectl patch "${KIND}" "${ITEM}" -n "${NAMESPACE}" --type=json \
          -p="[{\"op\": \"replace\", \"path\": \"/spec/template/spec/initContainers/${i}/image\", \"value\": \"${NEW_IMG}\"}]" >/dev/null
      fi
    done

    # 3. Inject imagePullSecrets
    HAS_SECRET=$(echo "${MANIFEST}" | jq -r ".spec.template.spec.imagePullSecrets // [] | map(select(.name == \"${PULL_SECRET}\")) | length")
    if [[ "${HAS_SECRET}" -eq 0 ]]; then
      echo "  - Injecting imagePullSecret: ${PULL_SECRET}"
      kubectl patch "${KIND}" "${ITEM}" -n "${NAMESPACE}" --type=json \
        -p="[{\"op\": \"add\", \"path\": \"/spec/template/spec/imagePullSecrets\", \"value\": [{\"name\": \"${PULL_SECRET}\"}]}]" >/dev/null
    fi

    # 4. Scale replicas
    echo "  - Restoring replicas to ${TARGET_REPLICAS}"
    kubectl scale "${KIND}" "${ITEM}" -n "${NAMESPACE}" --replicas="${TARGET_REPLICAS}" >/dev/null
  done
done

# 5. Audit EVS RWO Volume node affinity
echo "[INFO] Inspecting volume node affinity bindings..."
BOUND_NODES=$(kubectl get pvc -n "${NAMESPACE}" -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.metadata.annotations.volume\.kubernetes\.io/selected-node}{"\n"}{end}' 2>/dev/null | grep -v ': $' || true)
if [[ -n "${BOUND_NODES}" ]]; then
  echo "[NOTICE] Detected PVC node selections:"
  echo "${BOUND_NODES}"
fi

echo "[SUCCESS] Workload remediation complete for namespace: ${NAMESPACE}"
