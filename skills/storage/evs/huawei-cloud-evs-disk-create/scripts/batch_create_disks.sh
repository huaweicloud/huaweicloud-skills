#!/bin/bash
# Huawei Cloud EVS Batch Disk Creation Script
# Usage: ./batch_create_disks.sh --prefix <prefix> --region <region> --az <az> --count <count> [--volume-type <type>] [--size <size>] [--snapshot-id <id>] [--yes]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

usage() {
    cat <<EOF
Usage: $0 --prefix <prefix> --region <region> --az <az> --count <count> [options]

Required arguments:
  --prefix <prefix>     Disk name prefix
  --region <region>     Region code (e.g., cn-north-4)
  --az <az>             Availability zone (e.g., cn-north-4a)
  --count <count>       Number of disks to create

Optional arguments:
  --volume-type <type>  Disk type (default: GPSSD)
  --size <size>         Disk size in GB (default: 40)
  --snapshot-id <id>    Snapshot ID to create disks from
  --yes                 Skip the confirmation prompt
  -h, --help            Show this help message
EOF
}

check_hcloud() {
    if ! command -v hcloud &> /dev/null; then
        print_error "hcloud command not found, please install Huawei Cloud KooCLI first"
        echo "Installation Guide: https://support.huaweicloud.com/cli-koocli/koocli_01_0001.html"
        exit 1
    fi

    if ! hcloud configure list &> /dev/null; then
        print_error "Huawei Cloud CLI credentials not configured"
        echo "Please run: hcloud configure init"
        exit 1
    fi

    print_success "hcloud command and credentials check passed"
}

validate_disk_name() {
    local disk_name="$1"

    if [[ ${#disk_name} -lt 1 || ${#disk_name} -gt 64 ]]; then
        print_error "Disk name length must be between 1-64 characters"
        return 1
    fi

    return 0
}

create_disk() {
    local disk_name="$1"
    local region="$2"
    local az="$3"
    local volume_type="$4"
    local size="$5"
    local snapshot_id="$6"

    local cmd=(
        hcloud EVS CreateVolume
        --cli-region="$region"
        --volume.availability_zone="$az"
        --volume.size="$size"
        --volume.volume_type="$volume_type"
        --volume.name="$disk_name"
    )

    if [[ -n "$snapshot_id" ]]; then
        cmd+=(--volume.snapshot_id="$snapshot_id")
    fi

    print_info "Creating disk: $disk_name"
    echo "  Region: $region"
    echo "  Availability Zone: $az"
    echo "  Volume Type: $volume_type"
    echo "  Size: ${size} GB"

    if "${cmd[@]}"; then
        print_success "Disk '$disk_name' created successfully"
        return 0
    else
        local exit_code=$?
        print_error "Disk '$disk_name' creation failed, exit code: $exit_code"
        return 1
    fi
}

parse_args() {
    PREFIX=""
    REGION=""
    AZ=""
    COUNT=""
    VOLUME_TYPE="GPSSD"
    SIZE="40"
    SNAPSHOT_ID=""
    AUTO_YES=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prefix)
                PREFIX="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --az)
                AZ="$2"
                shift 2
                ;;
            --count)
                COUNT="$2"
                shift 2
                ;;
            --volume-type)
                VOLUME_TYPE="$2"
                shift 2
                ;;
            --size)
                SIZE="$2"
                shift 2
                ;;
            --snapshot-id)
                SNAPSHOT_ID="$2"
                shift 2
                ;;
            --yes)
                AUTO_YES=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done
}

batch_create() {
    local timestamp=$(date +%Y%m%d%H%M%S)
    local success_count=0

    print_info "Starting batch disk creation"
    echo "  Prefix: $PREFIX"
    echo "  Region: $REGION"
    echo "  Availability Zone: $AZ"
    echo "  Count: $COUNT"
    echo "  Volume Type: $VOLUME_TYPE"
    echo "  Size: ${SIZE} GB"
    echo ""

    for i in $(seq 1 "$COUNT"); do
        local disk_name="${PREFIX}-${timestamp}-${i}"

        if ! validate_disk_name "$disk_name"; then
            print_warning "Skipping invalid disk name: $disk_name"
            continue
        fi

        if create_disk "$disk_name" "$REGION" "$AZ" "$VOLUME_TYPE" "$SIZE" "$SNAPSHOT_ID"; then
            ((success_count++))
        fi

        echo "----------------------------------------"
    done

    echo ""
    echo "Batch creation completed!"
    echo "  Successful: $success_count/$COUNT"
    echo "  Failed: $((COUNT - success_count))"

    if [ $success_count -eq $COUNT ]; then
        print_success "All disks created successfully!"
    elif [ $success_count -gt 0 ]; then
        print_warning "Some disks created successfully"
    else
        print_error "All disk creations failed"
        exit 1
    fi
}

main() {
    echo "Huawei Cloud EVS Batch Disk Creation Tool"
    echo "========================================"

    parse_args "$@"

    if [[ -z "$PREFIX" || -z "$REGION" || -z "$AZ" || -z "$COUNT" ]]; then
        print_error "Missing required arguments"
        usage
        exit 1
    fi

    if [[ ! "$COUNT" =~ ^[0-9]+$ ]]; then
        print_error "Count must be a positive integer"
        exit 1
    fi

    check_hcloud

    echo "  Please confirm the disk creation parameters above."
    if [[ "$AUTO_YES" -ne 1 ]]; then
        read -r -p "Are you sure you want to create $COUNT disk(s)? [y/N]: " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            print_info "Operation cancelled by user"
            exit 0
        fi
    fi

    batch_create
}

main "$@"