#!/usr/bin/env bash
# Read-only smoke check for the quoting path: resolve service/resource/spec, then price it.
# It never creates, updates or deletes any cloud resource; every call is a BSS/IAM read API.
# Usage: bash scripts/quote-smoke.sh {services|resources|specs|units|price|all}
set -uo pipefail

STEP="${1:-all}"
BSS_REGION="${BSS_REGION:-cn-north-1}"          # BSS pricing endpoint is fixed to cn-north-1
DEPLOY_REGION="${DEPLOY_REGION:-cn-north-4}"    # resource region, overridable
SERVICE="${SERVICE_TYPE_CODE:-hws.service.type.ec2}"
RTYPE="${RESOURCE_TYPE_CODE:-hws.resource.type.vm}"
SPEC="${RESOURCE_SPEC:-ac6.12xlarge.2.linux}"

CONFIG="$HOME/.hcloud/config.json"

# The English KooCLI catalog omits BSS and answers "Unsupported service: BSS"; switch the catalog
# language to cn for this run only and restore the previous value on exit. No other setting is touched.
ORIG_LANG="$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.hcloud/config.json"))).get("language") or "en")' 2>/dev/null || echo en)"
if [ "$ORIG_LANG" != "cn" ]; then
  hcloud configure set --cli-lang=cn >/dev/null 2>&1 || { echo "SKIP hcloud catalog language not configurable (environment limit)"; exit 2; }
  trap 'hcloud configure set --cli-lang="$ORIG_LANG" >/dev/null 2>&1 || true' EXIT
fi

need_cli() {
  command -v hcloud >/dev/null 2>&1 || { echo "SKIP hcloud (KooCLI) not installed (environment limit)"; exit 2; }
}
need_creds() {
  [ -f "$CONFIG" ] || { echo "SKIP no hcloud credentials configured (environment limit)"; exit 2; }
}

step_services() {
  local out n
  out="$(hcloud BSS ListServiceTypes --limit=10 --cli-region="$BSS_REGION" --cli-output=json 2>&1)" || {
    echo "FAIL ListServiceTypes call failed: ${out:0:200}"; exit 1; }
  n="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("total_count",0))')"
  [ "${n:-0}" -gt 0 ] || { echo "FAIL ListServiceTypes returned an empty catalog (total_count=$n)"; exit 1; }
  echo "PASS ListServiceTypes total_count=$n region=$BSS_REGION"
}

step_resources() {
  local out n
  out="$(hcloud BSS ListServiceResources --service_type_code="$SERVICE" --limit=10 --cli-region="$BSS_REGION" --cli-output=json 2>&1)" || {
    echo "FAIL ListServiceResources call failed: ${out:0:200}"; exit 1; }
  n="$(printf '%s' "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("total_count",0))')"
  [ "${n:-0}" -gt 0 ] || { echo "FAIL ListServiceResources returned nothing for service_type_code=$SERVICE"; exit 1; }
  printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("PASS ListServiceResources total_count=%s first=%s" % (d.get("total_count"), d["infos"][0]["basic_info"]["resource_type_code"]))'
}

step_specs() {
  local out
  out="$(hcloud BSS ListResourceSpecs --charge_mode=1 --cloud_service_type="$SERVICE" --resource_type="$RTYPE" \
        --region_code="$DEPLOY_REGION" --limit=10 --cli-region="$BSS_REGION" --cli-output=json 2>&1)" || {
    echo "FAIL ListResourceSpecs call failed: ${out:0:200}"; exit 1; }
  printf '%s' "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
rows=d.get("cloud_service_basics") or []
if not rows: print("FAIL ListResourceSpecs found no sellable spec in region=%s" % sys.argv[1]); sys.exit(1)
spec=rows[0]["resource_spec"]
print("PASS ListResourceSpecs specs=%d first=%s" % (len(rows), spec))' "$DEPLOY_REGION"
}

step_units() {
  local out n
  out="$(hcloud BSS ListMeasureUnits --cli-region="$BSS_REGION" --cli-output=json 2>&1)" || {
    echo "FAIL ListMeasureUnits call failed: ${out:0:200}"; exit 1; }
  n="$(printf '%s' "$out" | python3 -c 'import json,sys;print(len(json.load(sys.stdin).get("measure_units") or []))')"
  [ "${n:-0}" -gt 0 ] || { echo "FAIL ListMeasureUnits returned no units"; exit 1; }
  echo "PASS ListMeasureUnits units=$n"
}

step_price() {
  local pid out
  pid="$(hcloud IAM KeystoneListAuthProjects --cli-region="$BSS_REGION" --cli-output=json 2>/dev/null \
        | python3 -c 'import json,sys;ps=[p for p in json.load(sys.stdin).get("projects") or [] if p.get("name")==sys.argv[1]];print(ps[0]["id"] if ps else "")' "$DEPLOY_REGION")"
  [ -n "$pid" ] || { echo "SKIP no accessible project in $DEPLOY_REGION (environment limit)"; exit 2; }
  out="$(hcloud BSS ListRateOnPeriodDetail --project_id="$pid" \
      --product_infos.1.id=1 --product_infos.1.cloud_service_type="$SERVICE" \
      --product_infos.1.resource_type="$RTYPE" --product_infos.1.resource_spec="$SPEC" \
      --product_infos.1.region="$DEPLOY_REGION" --product_infos.1.period_type=2 \
      --product_infos.1.period_num=1 --product_infos.1.subscription_num=1 \
      --cli-region="$BSS_REGION" --cli-output=json 2>&1)" || {
    echo "FAIL ListRateOnPeriodDetail call failed: ${out:0:200}"; exit 1; }
  printf '%s' "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
amt=(d.get("official_website_rating_result") or {}).get("official_website_amount")
cur=d.get("currency") or ""
if not amt or float(amt) <= 0:
    print("FAIL pricing returned no amount: %s" % str(d)[:200]); sys.exit(1)
print("PASS ListRateOnPeriodDetail spec=%s amount=%s currency=%s period=month num=1" % (sys.argv[1], amt, cur))' "$SPEC"
}

need_cli
case "$STEP" in
  services)  step_services ;;
  resources) need_creds; step_resources ;;
  specs)     need_creds; step_specs ;;
  units)     need_creds; step_units ;;
  price)     need_creds; step_price ;;
  all)       step_services; step_resources; step_specs; step_units; step_price ;;
  *) echo "unknown step: $STEP"; exit 2 ;;
esac