#!/bin/bash
#==============================================================================
# query-pricing.sh — ModelArts Notebook 按需询价辅助脚本
#
# 用法:
#   bash query-pricing.sh <region> <flavor_id1> [flavor_id2] [flavor_id3] ...
#
# 示例:
#   bash query-pricing.sh cn-north-4 modelarts.vm.cpu.2u
#   bash query-pricing.sh cn-north-4 modelarts.vm.cpu.2u modelarts.vm.cpu.8u modelarts.bm.4xlarge.pro
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

# ── 固定参数 (ModelArts BSS 询价) ─────────────────────────────────────────────
CLOUD_SERVICE_TYPE="hws.service.type.modelarts"
RESOURCE_TYPE="hws.resource.type.modelarts"
USAGE_FACTOR="Duration"
USAGE_MEASURE_ID=4    # 4 = 小时
USAGE_VALUE=1          # 查询 1 小时价格
SIZE_MEASURE_ID=14     # 14 = 个
RESOURCE_SIZE=1        # 1 个实例
BSS_REGION="cn-north-1"  # BSS API 固定使用 cn-north-1

# ── 参数检查 ──────────────────────────────────────────────────────────────────
if [ $# -lt 2 ]; then
    echo -e "${RED}用法: bash $0 <region> <flavor_id1> [flavor_id2] ...${NC}"
    echo -e "示例: bash $0 cn-north-4 modelarts.vm.cpu.2u modelarts.vm.cpu.8u"
    exit 1
fi

TARGET_REGION="$1"
shift
FLAVOR_IDS=("$@")

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
echo -e "${BLUE}[*] 查询 ${#FLAVOR_IDS[@]} 个规格的按需价格 (region: ${TARGET_REGION})...${NC}"

ARGS=(--cli-region="${BSS_REGION}" --project_id="${PROJECT_ID}")
for i in "${!FLAVOR_IDS[@]}"; do
    IDX=$((i + 1))
    CODE="${FLAVOR_IDS[$i]}"
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

# ── 调用 BSS 询价 API（直接数组展开传参）────────────────────────────────────────
RESULT=$(hcloud BSS ListOnDemandResourceRatings "${ARGS[@]}" 2>/dev/null) || true

if [ -z "${RESULT:-}" ]; then
    echo -e "${RED}[!] BSS 询价失败，请检查参数或网络连接。${NC}"
    exit 1
fi

# ── 将 flavor IDs 转为 JSON 传给 Python ───────────────────────────────────────
FLAVOR_JSON=$(printf '%s\n' "${FLAVOR_IDS[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))")

# ── 解析并格式化输出 ──────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ModelArts Notebook 按需询价结果 (region: ${TARGET_REGION})${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""

echo "${RESULT}" | FLAVOR_IDS_JSON="${FLAVOR_JSON}" python3 -c "
import sys, json, os, re

flavor_ids = json.loads(os.environ['FLAVOR_IDS_JSON'])

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
print(f'  {\"#\":<4} {\"规格 (flavor_id)\":<35} {\"按需价格\":>12} {\"折扣\":>10}')
print(f'  {\"----\":<4} {\"-----------------------------------\":<35} {\"------------\":>12} {\"----------\":>10}')

for r in results:
    idx = int(r.get('id', 0))
    code = flavor_ids[idx - 1] if idx - 1 < len(flavor_ids) else f'unknown_{idx}'
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
print(f'  说明: 以上为单实例价格，实际费用 = 单价 x 运行时长(小时)')
"

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
