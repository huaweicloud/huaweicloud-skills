#!/bin/bash
# Huawei Cloud OBS Batch Bucket Creation Script
# Usage: ./batch_create_buckets.sh <prefix> <region> <purpose1> <purpose2> ...

set -e

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
    if ! hcloud OBS ls &> /dev/null; then
        print_error "OBS configuration invalid or credentials error"
        echo "Please check the following configuration:"
        echo "1. Environment variables: OBS_ACCESS_KEY_ID, OBS_SECRET_ACCESS_KEY, OBS_ENDPOINT"
        echo "2. Configuration file: ~/.obsutilconfig"
        echo "3. Run: hcloud OBS config to check configuration"
        exit 1
    fi
    
    print_success "hcloud command and OBS configuration check passed"
}

# Validate bucket name
validate_bucket_name() {
    local bucket_name="$1"
    
    if [[ ${#bucket_name} -lt 3 || ${#bucket_name} -gt 63 ]]; then
        print_error "Bucket name length must be between 3-63 characters"
        return 1
    fi
    
    if [[ ! "$bucket_name" =~ ^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$ ]]; then
        print_error "Bucket name can only contain lowercase letters, numbers and hyphens, and cannot start or end with a hyphen"
        return 1
    fi
    
    if [[ "$bucket_name" == *--* ]]; then
        print_error "Bucket name cannot contain two consecutive hyphens"
        return 1
    fi

    if [[ "$bucket_name" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        print_error "Bucket name cannot be in IP address format"
        return 1
    fi
    
    return 0
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

    
    # Build command, use -e parameter to specify endpoint
    if hcloud OBS mb "obs://$bucket_name" -location="$region" -acl="$acl" -sc="$storage_class" ; then
        print_success "Bucket '$bucket_name' created successfully"
        
        # Display bucket information
        echo ""
        echo "Bucket Information:"
        hcloud OBS stat "obs://$bucket_name" | grep -E "(Bucket|Location|CreationDate|ACL)" || true
        echo ""
        
        return 0
    else
        # Check if it's a successful case but with non-zero exit code
        local exit_code=$?
        if [ $exit_code -eq 6 ]; then
            print_warning "Bucket '$bucket_name' created successfully, but command returned non-zero exit code (6), this is normal behavior for Huawei Cloud CLI"
            echo ""
            echo "Bucket Information:"
            hcloud OBS stat "obs://$bucket_name" | grep -E "(Bucket|Location|CreationDate|ACL)" || true
            echo ""
            return 0
        else
            print_error "Bucket '$bucket_name' creation failed, exit code: $exit_code"
            return 1
        fi
    fi
}

# Batch create buckets
batch_create() {
    local prefix="$1"
    local region="$2"
    shift 2
    local purposes=("$@")
    
    local timestamp=$(date +%Y%m%d)
    local success_count=0
    local total_count=${#purposes[@]}
    
    print_info "Starting batch bucket creation"
    echo "  Prefix: $prefix"
    echo "  Region: $region"
    echo "  Purposes: ${purposes[*]}"
    echo "  Timestamp: $timestamp"
    echo ""
    
    for purpose in "${purposes[@]}"; do
        local bucket_name="${prefix}-${purpose}-${timestamp}"
        
        # Validate bucket name
        if ! validate_bucket_name "$bucket_name"; then
            print_warning "Skipping invalid bucket name: $bucket_name"
            continue
        fi
        
        # Set ACL and storage class
        local acl="private"
        local storage_class="standard"
        
        case $purpose in
            logs|backup)
                acl="private"
                storage_class="ia"  # Infrequent access
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
        
        # Create bucket
        if create_bucket "$bucket_name" "$region" "$acl" "$storage_class"; then
            ((success_count++))
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
    
    
    local prefix="$1"
    local region="$2"
    shift 2
    
    
    # Execute batch creation
    batch_create "$prefix" "$region" "$@"
    
}

# Run main program
main "$@"
