#!/bin/bash
# Validate Terraform configuration
# Usage: ./scripts/validate_terraform.sh <project_dir>
#
# Runs: terraform fmt → validate → plan
# Does NOT run terraform apply.

PROJECT_DIR="${1:-.}"
TFRC_FILE="${2:-.tfrc}"

cd "$PROJECT_DIR" || exit 1

# Set up Huawei Cloud mirror
export TF_CLI_CONFIG_FILE="$(pwd)/$TFRC_FILE"

echo "=== Step 1: terraform fmt ==="
terraform fmt -recursive
if [ $? -ne 0 ]; then
  echo "FAIL: terraform fmt"
  exit 1
fi
echo "OK"

echo ""
echo "=== Step 2: terraform init ==="
terraform init -upgrade 2>&1 | tail -5
if [ $? -ne 0 ]; then
  echo "FAIL: terraform init"
  exit 1
fi

echo ""
echo "=== Step 3: terraform validate ==="
terraform validate
if [ $? -ne 0 ]; then
  echo "FAIL: terraform validate"
  exit 1
fi

echo ""
echo "=== Step 4: terraform plan ==="
terraform plan -no-color 2>&1 | tail -20

echo ""
echo "=== Validation complete ==="
echo "Review the plan above. Do NOT run terraform apply without user confirmation."
