#!/bin/bash
#==============================================================================
# query-pricing.sh — ModelArts 专属资源池按需询价辅助脚本
#
# 用法:
#   bash query-pricing.sh --region <region> --billing <billing_code1> [--billing <billing_code2>] ...
#
# 示例:
#   bash query-pricing.sh --region cn-north-4 --billing modelarts.vm.cpu.8ud
#   bash query-pricing.sh --region cn-north-4 --billing modelarts.vm.cpu.8ud --billing modelarts.vm.cpu.16u64g.d --billing modelarts.vm.cpu.48u96g.d
#
# 依赖: hcloud CLI (已配置 AK/SK)
#==============================================================================

set -euo pipefail

# ── 颜色定义 ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── 询价失败处理（fail-loud）──────────────────────────────────────────────────
# 询价必须"失败即停止"：绝不输出 0 元或空价格表让用户误以为免费。
# 退出码: 2 = BSS 服务/CLI 不可用; 3 = 响应解析失败 / 结果为空 / 金额为 0
fail_pricing() {
    local code="$1"; shift
    echo -e "${RED}[!] 询价不可用：$*${NC}" >&2
    echo -e "${RED}[!] 已停止：不会输出 0 元或空价格表。${NC}" >&2
    echo -e "${YELLOW}[i] 官方 KooCLI 7.3.12 已不支持 BSS 服务（hcloud BSS → [USE_ERROR]Unsupported service: BSS.）。${NC}" >&2
    echo -e "${YELLOW}[i] 可执行替代方案（任选其一，确认价格后再执行写操作）：${NC}" >&2
    echo -e "${YELLOW}    1) 华为云控制台 → 费用中心，按规格查询按需价格${NC}" >&2
    echo -e "${YELLOW}    2) BSS API Explorer 在线调试 ListOnDemandResourceRatings${NC}" >&2
    echo -e "${YELLOW}    3) 由用户人工确认价格后继续（不得按 0 元 / 免费处理）${NC}" >&2
    exit "$code"
}

# ── 固定参数 (ModelArts BSS 询价) ─────────────────────────────────────────────
CLOUD_SERVICE_TYPE="hws.service.type.modelarts"
RESOURCE_TYPE="hws.resource.type.modelarts"
USAGE_FACTOR="Duration"
USAGE_MEASURE_ID=4    # 4 = 小时
USAGE_VALUE=1          # 查询 1 小时价格
SIZE_MEASURE_ID=14     # 14 = 个
RESOURCE_SIZE=1        # 1 个实例
BSS_REGION="cn-north-1"  # BSS API 固定使用 cn-north-1

# ── 参数解析 (命名参数 --region / --billing) ──────────────────────────────────
TARGET_REGION=""
BILLING_CODES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --region)
            TARGET_REGION="$2"
            shift 2
            ;;
        --region=*)
            TARGET_REGION="${1#--region=}"
            shift
            ;;
        --billing)
            BILLING_CODES+=("$2")
            shift 2
            ;;
        --billing=*)
            BILLING_CODES+=("${1#--billing=}")
            shift
            ;;
        -h|--help)
            echo -e "用法: bash $0 --region <region> --billing <billing_code1> [--billing <billing_code2> ..."
            echo -e "示例: bash $0 --region cn-north-4 --billing modelarts.vm.cpu.8ud"
            echo -e "      bash $0 --region cn-north-4 --billing modelarts.vm.cpu.8ud --billing modelarts.vm.cpu.16u64g.d"
            exit 0
            ;;
        *)
            echo -e "${RED}[!] 未知参数: $1${NC}"
            echo -e "用法: bash $0 --region <region> --billing <billing_code1> [--billing <billing_code2> ..."
            exit 1
            ;;
    esac
done

if [ -z "${TARGET_REGION}" ]; then
    echo -e "${RED}[!] 缺少必选参数 --region${NC}"
    echo -e "用法: bash $0 --region <region> --billing <billing_code1> [--billing <billing_code2> ..."
    exit 1
fi

if [ ${#BILLING_CODES[@]} -eq 0 ]; then
    echo -e "${RED}[!] 缺少必选参数 --billing${NC}"
    echo -e "用法: bash $0 --region <region> --billing <billing_code1> [--billing <billing_code2> ..."
    exit 1
fi

# ── 获取项目 ID ──────────────────────────────────────────────────────────────
echo -e "${BLUE}[*] 获取 ${TARGET_REGION} 的项目 ID...${NC}"
PROJECT_ID=$(hcloud IAM KeystoneListAuthProjects --cli-region="${TARGET_REGION}" 2>/dev/null | \
    python3 -c "
import sys, json, re
_raw = sys.stdin.read()
_match = re.search(r'\{.*\}', _raw, re.DOTALL)
data = json.loads(_match.group(0)) if _match else {}
for p in data.get('projects', []):
    if p.get('name') == '${TARGET_REGION}':
        print(p.get('id'))
        break
" 2>/dev/null)

if [ -z "${PROJECT_ID:-}" ]; then
    echo -e "${RED}[!] 无法获取项目 ID，请检查 hcloud CLI 认证配置。${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] 项目 ID: ${PROJECT_ID:0:8}...${NC}"

# ── 构建 BSS 询价参数（使用 bash 数组传参）────────────────────────────────────
echo -e "${BLUE}[*] 查询 ${#BILLING_CODES[@]} 个规格的按需价格 (region: ${TARGET_REGION})...${NC}"

ARGS=(--cli-region="${BSS_REGION}" --project_id="${PROJECT_ID}")
for i in "${!BILLING_CODES[@]}"; do
    IDX=$((i + 1))
    CODE="${BILLING_CODES[$i]}"
    ARGS+=(--product_infos.${IDX}.id=${IDX})
    ARGS+=(--product_infos.${IDX}.cloud_service_type=${CLOUD_SERVICE_TYPE})
    ARGS+=(--product_infos.${IDX}.resource_type=${RESOURCE_TYPE})
    ARGS+=(--product_infos.${IDX}.resource_spec=${CODE})
    ARGS+=(--product_infos.${IDX}.region=${TARGET_REGION})
    ARGS+=(--product_infos.${IDX}.usage_factor=${USAGE_FACTOR})
    ARGS+=(--product_infos.${IDX}.usage_measure_id=${USAGE_MEASURE_ID})
    ARGS+=(--product_infos.${IDX}.usage_value=${USAGE_VALUE})
    ARGS+=(--product_infos.${IDX}.subscription_num=1)
    ARGS+=(--product_infos.${IDX}.resource_size=${RESOURCE_SIZE})
    ARGS+=(--product_infos.${IDX}.size_measure_id=${SIZE_MEASURE_ID})
done

# ── 调用 BSS 询价 API（直接数组展开传参）──────────────────────────────────────
RESULT=$(hcloud BSS ListOnDemandResourceRatings "${ARGS[@]}" 2>&1) || true

# ── 响应校验：任何异常一律非 0 退出，禁止静默报 0 元 ─────────────────────────
if [ -z "${RESULT:-}" ]; then
    fail_pricing 2 "BSS 返回空响应（无法确认服务是否可用）"
fi

# hcloud 对业务/参数错误也返回 exit 0，错误只体现在 stdout/stderr 文本里
if printf '%s' "${RESULT}" | grep -qE '\[USE_ERROR\]|Unsupported service'; then
    _detail=$(printf '%s' "${RESULT}" | tr '\n' ' ' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    fail_pricing 2 "KooCLI 调用 BSS 失败：${_detail}"
fi

# 校验 JSON 结构、结果数组与金额（不使用 set -e 中断，改为显式错误码）
VALIDATION=$(RESULT_TEXT="${RESULT}" python3 - <<'PY'
import sys, os, json, re

raw = os.environ.get("RESULT_TEXT", "")
match = re.search(r'\{.*\}', raw, re.DOTALL)
if not match:
    print("NOT_JSON")
    sys.exit(0)

try:
    data = json.loads(match.group(0))
except Exception:
    print("NOT_JSON")
    sys.exit(0)

if "error_code" in data:
    print("API_ERROR|%s|%s" % (data.get("error_code"), data.get("error_msg", "")))
    sys.exit(0)

results = data.get("product_rating_results")
if not isinstance(results, list):
    print("NO_RESULTS")
    sys.exit(0)
if len(results) == 0:
    print("EMPTY_RESULTS")
    sys.exit(0)

total = data.get("amount")
try:
    total_f = float(total)
except (TypeError, ValueError):
    total_f = sum(float(r.get("amount") or 0) for r in results)

if total_f <= 0:
    print("ZERO_AMOUNT")
    sys.exit(0)

print("OK")
PY
)

case "${VALIDATION}" in
    OK)
        ;;
    NOT_JSON)
        fail_pricing 3 "BSS 响应不是合法 JSON，无法解析价格"
        ;;
    API_ERROR\|*)
        _code=$(printf '%s' "${VALIDATION}" | cut -d'|' -f2)
        _msg=$(printf '%s' "${VALIDATION}" | cut -d'|' -f3-)
        fail_pricing 3 "BSS 返回业务错误 ${_code}: ${_msg}"
        ;;
    NO_RESULTS)
        fail_pricing 3 "响应中缺少 product_rating_results 字段"
        ;;
    EMPTY_RESULTS)
        fail_pricing 3 "product_rating_results 为空数组（规格无报价或参数不匹配）"
        ;;
    ZERO_AMOUNT)
        fail_pricing 3 "解析出的价格合计为 0 或缺失，结果不可信"
        ;;
    *)
        fail_pricing 3 "未知的响应校验结果: ${VALIDATION}"
        ;;
esac

# ── 将 billing codes 转为 JSON 传给 Python ───────────────────────────────────
BILLING_JSON=$(printf '%s\n' "${BILLING_CODES[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")

# ── 解析并格式化输出 ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ModelArts 按需询价结果 (region: ${TARGET_REGION})${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "${RESULT}" | BILLING_CODES_JSON="${BILLING_JSON}" python3 -c "
import sys, json, os, re

billing_codes = json.loads(os.environ['BILLING_CODES_JSON'])

# 读取完整输出，用正则提取 JSON 片段，避免诊断表格行导致解析崩溃
_raw = sys.stdin.read()
_match = re.search(r'\{.*\}', _raw, re.DOTALL)
data = json.loads(_match.group(0)) if _match else {}

if 'error_code' in data:
    print(f'  询价失败: {data.get(\"error_msg\", \"未知错误\")}')
    sys.exit(1)

results = data.get('product_rating_results', [])
currency = data.get('currency', 'CNY')
total = data.get('amount', 0)
discount = data.get('discount_amount', 0)

# 表头
print(f'  {\"#\":<4} {\"规格 (billing_code)\":<35} {\"按需价格\":>12} {\"折扣\":>10}')
print(f'  {\"----\":<4} {\"-----------------------------------\":<35} {\"------------\":>12} {\"----------\":>10}')

for r in results:
    idx = int(r.get('id', 0))
    code = billing_codes[idx - 1] if idx - 1 < len(billing_codes) else f'unknown_{idx}'
    amount = r.get('amount', 0)
    disc = r.get('discount_amount', 0)
    disc_str = f'{disc:.2f}' if disc > 0 else '-'
    print(f'  {idx:<4} {code:<35} {amount:>10.2f} 元/h {disc_str:>10}')

print(f'  {\"----\":<4} {\"-----------------------------------\":<35} {\"------------\":>12} {\"----------\":>10}')
print(f'  {\"\":<4} {\"合计\":<35} {total:>10.2f} 元/h')
if discount > 0:
    print(f'  {\"\":<4} {\"折扣金额\":<35} {discount:>10.2f} 元/h')
print()
print(f'  币种: {currency}')
print(f'  计费模式: 按需 (小时)')
print(f'  说明: 以上为单节点价格，实际费用 = 单价 x 节点数 x 运行时长(小时)')
"

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
