#!/bin/bash
# Huawei Cloud OBS Batch Bucket Creation Script
# Usage:
#   Mode 1 (auto-naming, default):
#     ./batch_create_buckets.sh <prefix> <region> <purpose1> <purpose2> ...
#   Mode 2 (custom bucket names):
#     ./batch_create_buckets.sh --names "bucket-a,bucket-b" --region <region>
#
# Note: `set -e` is intentionally NOT used. The Huawei Cloud KooCLI returns exit
# code 6 even for some successful bucket operations (documented normal behavior),
# so a bare `set -e` would abort the whole batch on the first bucket. Each command
# therefore checks its exit code explicitly: 0 and 6 are treated as success, and a
# genuinely failed bucket is skipped while the remaining buckets still get created.

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if hcloud command is available
check_hcloud() {
    if ! command -v hcloud &> /dev/null; then
        print_error "hcloud command not found, please install Huawei Cloud KooCLI first"
        echo "Installation Guide: https://support.huaweicloud.com/cli-koocli/koocli_01_0001.html"
        exit 1
    fi

    # Check OBS configuration
    hcloud OBS ls &> /dev/null
    local rc=$?
    if [ $rc -ne 0 ] && [ $rc -ne 6 ]; then
        print_error "OBS configuration invalid or credentials error (exit code: $rc)"
        echo "Please check the following configuration:"
        echo "1. Environment variables: OBS_ACCESS_KEY_ID, OBS_SECRET_ACCESS_KEY, OBS_ENDPOINT"
        echo "2. Configuration file: ~/.obsutilconfig"
        echo "3. Run: hcloud OBS config to check configuration"
        exit 1
    fi

    print_success "hcloud command and OBS configuration check passed"
}

# Validate bucket name (per OBS naming specification)
validate_bucket_name() {
    local bucket_name="$1"

    if [[ ${#bucket_name} -lt 3 || ${#bucket_name} -gt 63 ]]; then
        print_error "Bucket name length must be between 3-63 characters"
        return 1
    fi

    if [[ ! "$bucket_name" =~ ^[a-z0-9][a-z0-9.\-]*[a-z0-9]$ ]]; then
        print_error "Bucket name can only contain lowercase letters, numbers, hyphens and dots, and cannot start or end with a hyphen or dot"
        return 1
    fi

    if [[ "$bucket_name" == *".."* ]]; then
        print_error "Bucket name cannot contain two consecutive dots"
        return 1
    fi

    if [[ "$bucket_name" == *"-."* || "$bucket_name" == *".-"* ]]; then
        print_error "Bucket name cannot contain adjacent hyphen and dot"
        return 1
    fi

    if [[ "$bucket_name" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        print_error "Bucket name cannot be in IP address format"
        return 1
    fi

    return 0
}

# Validate region code
validate_region() {
    local region="$1"
    local valid_regions="cn-north-1 cn-north-4 cn-north-9 cn-north-5 cn-east-2 cn-east-3 cn-east-4 cn-east-5 cn-south-1 cn-south-2 cn-south-4 cn-south-5 cn-south-21 cn-southwest-2 cn-southeast-1 ap-southeast-1 ap-southeast-2 ap-southeast-3 ap-southeast-4 ap-southeast-5 ap-southeast-6 ap-southeast-7 ap-northeast-1 af-south-1 la-south-2 na-mexico-1 sa-brazil-1 eu-west-101 eu-west-0"

    if [[ -z "$region" ]]; then
        print_error "Region is required. Use --region <region> or <region> as positional argument."
        return 1
    fi

    for r in $valid_regions; do
        if [ "$r" == "$region" ]; then
            return 0
        fi
    done

    print_error "Invalid region: $region"
    echo "Valid regions: $valid_regions"
    return 1
}

# Create single bucket
create_bucket() {
    local bucket_name="$1"
    local region="$2"
    local acl="${3:-private}"
    local storage_class="${4:-standard}"

    print_info "Creating bucket: $bucket_name"
    echo "  Region: $region"
    echo "  Access Permission: $acl"
    echo "  Storage Class: $storage_class"

    hcloud OBS mb "obs://$bucket_name" -location="$region" -acl="$acl" -sc="$storage_class"
    local exit_code=$?

    # Exit code 6 from Huawei Cloud CLI is documented normal behavior, treat as success
    if [ $exit_code -eq 0 ] || [ $exit_code -eq 6 ]; then
        print_success "Bucket '$bucket_name' created successfully"

        # Display bucket information
        echo ""
        echo "Bucket Information:"
        hcloud OBS stat "obs://$bucket_name" | grep -E "(Bucket|Location|CreationDate|ACL)" || true
        echo ""

        return 0
    else
        print_error "Bucket '$bucket_name' creation failed, exit code: $exit_code"
        return 1
    fi
}

# Create a single bucket for a given purpose (auto-naming mode)
create_bucket_for_purpose() {
    local prefix="$1"
    local region="$2"
    local purpose="$3"

    local bucket_name="${prefix}-${purpose}-$(date +%Y%m%d)"

    # Validate bucket name
    if ! validate_bucket_name "$bucket_name"; then
        print_warning "Skipping invalid bucket name: $bucket_name"
        return 1
    fi

    # Set ACL and storage class
    local acl="private"
    local storage_class="standard"

    case $purpose in
        logs|backup)
            acl="private"
            storage_class="warm"  # Infrequent access
            ;;
        website|assets)
            acl="public-read"
            storage_class="standard"
            ;;
        data|temp)
            acl="private"
            storage_class="standard"
            ;;
    esac

    if create_bucket "$bucket_name" "$region" "$acl" "$storage_class"; then
        return 0
    fi
    return 1
}

# Batch create buckets with auto-generated names (prefix-purpose-timestamp)
batch_create() {
    local prefix="$1"
    local region="$2"
    shift 2
    local purposes=("$@")

    local timestamp=$(date +%Y%m%d)
    local success_count=0
    local total_count=${#purposes[@]}

    print_info "Starting batch bucket creation (auto-naming mode)"
    echo "  Prefix: $prefix"
    echo "  Region: $region"
    echo "  Purposes: ${purposes[*]}"
    echo "  Timestamp: $timestamp"
    echo ""

    for purpose in "${purposes[@]}"; do
        if create_bucket_for_purpose "$prefix" "$region" "$purpose"; then
            success_count=$((success_count + 1))
        fi

        echo "----------------------------------------"
    done

    # Summary results
    echo ""
    echo "Batch creation completed!"
    echo "  Successful: $success_count/$total_count"
    echo "  Failed: $((total_count - success_count))"

    if [ $success_count -eq $total_count ]; then
        print_success "All buckets created successfully!"
    elif [ $success_count -gt 0 ]; then
        print_warning "Some buckets created successfully"
    else
        print_error "All bucket creations failed"
        exit 1
    fi
}

# Batch create buckets with explicit user-supplied names
batch_create_named() {
    local names_csv="$1"
    local region="$2"

    IFS=',' read -r -a bucket_names <<< "$names_csv"
    local success_count=0
    local total_count=${#bucket_names[@]}

    print_info "Starting batch bucket creation (custom names mode)"
    echo "  Region: $region"
    echo "  Buckets: ${bucket_names[*]}"
    echo ""

    if [ $total_count -eq 0 ]; then
        print_error "No bucket names provided, use --names \"bucket-a,bucket-b\""
        exit 1
    fi

    for bucket_name in "${bucket_names[@]}"; do
        bucket_name=$(echo "$bucket_name" | xargs)

        if ! validate_bucket_name "$bucket_name"; then
            print_warning "Skipping invalid bucket name: $bucket_name"
            echo "----------------------------------------"
            continue
        fi

        if create_bucket "$bucket_name" "$region" "private" "standard"; then
            success_count=$((success_count + 1))
        fi

        echo "----------------------------------------"
    done

    # Summary results
    echo ""
    echo "Batch creation completed!"
    echo "  Successful: $success_count/$total_count"
    echo "  Failed: $((total_count - success_count))"

    if [ $success_count -eq $total_count ]; then
        print_success "All buckets created successfully!"
    elif [ $success_count -gt 0 ]; then
        print_warning "Some buckets created successfully"
    else
        print_error "All bucket creations failed"
        exit 1
    fi
}

# Main program
main() {
    echo "Huawei Cloud OBS Batch Bucket Creation Tool"
    echo "========================================"

    # Check dependencies
    check_hcloud

    local mode="auto"
    local names=""
    local region=""
    local prefix=""
    local positional=()

    while [ $# -gt 0 ]; do
        case "$1" in
            --names)
                mode="named"
                names="$2"
                shift 2
                ;;
            --region)
                region="$2"
                shift 2
                ;;
            -*)
                print_error "Unknown option: $1"
                echo "Usage:"
                echo "  Mode auto:  ./batch_create_buckets.sh <prefix> <region> [purpose1] [purpose2] ..."
                echo "  Mode named: ./batch_create_buckets.sh --names \"bucket-a,bucket-b\" --region <region>"
                exit 1
                ;;
            *)
                positional+=("$1")
                shift
                ;;
        esac
    done

    if [ "$mode" == "named" ]; then
        if [[ -z "$region" ]]; then
            print_error "Missing --region, e.g. --region cn-north-4"
            exit 1
        fi
        if ! validate_region "$region"; then
            exit 1
        fi
        batch_create_named "$names" "$region"
    else
        if [ ${#positional[@]} -lt 2 ]; then
            print_error "Usage: ./batch_create_buckets.sh <prefix> <region> [purpose1] [purpose2] ..."
            exit 1
        fi
        prefix="${positional[0]}"
        region="${positional[1]}"
        purposes=("${positional[@]:2}")
        if [ ${#purposes[@]} -eq 0 ]; then
            print_error "At least one purpose is required, e.g. ./batch_create_buckets.sh demo cn-north-4 logs"
            exit 1
        fi
        if ! validate_region "$region"; then
            exit 1
        fi
        batch_create "$prefix" "$region" "${purposes[@]}"
    fi
}

# Run main program
main "$@"
