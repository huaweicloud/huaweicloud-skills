#!/usr/bin/env python3
"""
Phase 3: COC Remote Installation of JiuwenSwarm Service Dependencies on Flexus L Instance

This script remotely installs the basic dependency environment required for JiuwenSwarm service 
on Flexus L instances using Huawei Cloud COC service.

Main installations include: Python 3.11+, Node.js 18.x, Git, and basic system tools.

Note: This script only installs the basic dependency environment, not the JiuwenSwarm service itself.
Service deployment will be completed in deploy_service.py.
"""

import os
import sys
import json
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Import utility modules
sys.path.insert(0, str(Path(__file__).parent))
try:
    from utils import (
        get_huaweicloud_credentials,
        get_coc_client,
        submit_and_monitor_script,
        coc_query_execution,
        coc_create_script,
        coc_execute_script,
        print_header,
        print_success,
        print_error,
        print_warning,
        print_info,
        load_json_file,
        save_json_file
    )
except ImportError as e:
    log.error(f"Failed to import utility module: {e}")
    log.error("Please ensure utils.py exists")
    sys.exit(1)

# Configuration parameters
EXECUTION_TIMEOUT = 1799  # 30-minute timeout (Huawei Cloud COC API limit: must be less than 1800 seconds)
MAX_RETRIES = 3

def check_job_status(execute_uuid):
    """Check COC job status - based on Huawei Cloud COC GetScriptJobInfo API response format"""
    print_header("Checking COC Job Status")
    print_info(f"Job UUID: {execute_uuid}")
    
    print_info("Querying job status...")
    
    # Use the new coc_query_execution function
    result = coc_query_execution(execute_uuid)
    
    if not result.get("ok"):
        error_info = result.get("error", {})
        print_error(f"Query failed: {error_info.get('message', 'Unknown error')}")
        print_error(f"Error code: {error_info.get('code', 'UNKNOWN')}")
        return None
    
    job_info = result.get("result", {})
    
    # Check if job_info is empty or has no status information
    if not job_info:
        print_warning("API call successful, but no job data was retrieved")
        print_info("Possible reasons:")
        print_info("  - Job UUID does not exist")
        print_info("  - Job has not started execution yet")
        print_info("  - API response data format has changed")
        return None
    
    status = job_info.get('status', 'UNKNOWN')
    
    # Update status mapping based on Huawei Cloud COC API documentation
    # Job statuses: READY (preparing), PROCESSING (running), ABNORMAL (abnormal), CANCELED (canceled), FINISHED (completed)
    STATUS_MAP = {
        'READY': 'Preparing',
        'PROCESSING': 'Running',
        'FINISHED': 'Completed',
        'ABNORMAL': 'Abnormal',
        'CANCELED': 'Canceled'
    }
    status_display = STATUS_MAP.get(status, status)
    
    print_info("="*60)
    print_info(f"Execution UUID: {execute_uuid}")
    print_info(f"Script Name: {job_info.get('script_name', 'N/A')}")
    print_info(f"Execute User: {job_info.get('execute_user', 'N/A')}")
    print_info(f"Status: {status} ({status_display})")
    
    # Display execution time
    if job_info.get('execute_costs'):
        execute_costs_ms = job_info.get('execute_costs', 0)
        execute_costs_seconds = job_info.get('execute_costs_seconds', execute_costs_ms / 1000 if execute_costs_ms else 0)
        print_info(f"Execution Time: {execute_costs_ms}ms ({execute_costs_seconds:.2f} seconds)")
    
    # Display creator
    if job_info.get('creator'):
        print_info(f"Creator: {job_info['creator']}")
    
    # Display statistics
    total_count = job_info.get('total_count', 0)
    success_count = job_info.get('success_count', 0)
    fail_count = job_info.get('fail_count', 0)
    processing_count = job_info.get('processing_count', 0)
    
    if total_count > 0:
        print_info(f"Execution Statistics:")
        print_info(f"  Total: {total_count} instances")
        print_info(f"  Success: {success_count}")
        print_info(f"  Failed: {fail_count}")
        print_info(f"  Processing: {processing_count}")
        
        # Calculate success rate
        success_rate = (success_count / total_count) * 100
        print_info(f"  Success Rate: {success_rate:.1f}%")
    
    # Display time information
    if job_info.get('create_time'):
        print_info(f"Create Time: {job_info['create_time']}")
    if job_info.get('finish_time'):
        print_info(f"Finish Time: {job_info['finish_time']}")
        # Calculate duration
        try:
            if job_info.get('execute_costs_seconds'):
                duration_seconds = job_info.get('execute_costs_seconds', 0)
                if duration_seconds > 0:
                    print_info(f"Duration: {duration_seconds:.0f} seconds ({duration_seconds/60:.1f} minutes)")
        except Exception:
            pass
    
    # Display properties information
    if job_info.get('script_uuid'):
        print_info(f"Script UUID: {job_info['script_uuid']}")
    if job_info.get('script_source'):
        print_info(f"Script Source: {job_info['script_source']}")
    if job_info.get('current_execute_batch_index'):
        print_info(f"Current Batch: {job_info['current_execute_batch_index']}")
    
    # Display execution parameters
    if job_info.get('timeout'):
        print_info(f"Timeout Setting: {job_info['timeout']} seconds")
    if job_info.get('success_rate'):
        print_info(f"Success Rate Requirement: {job_info['success_rate']}%")
    if job_info.get('resourceful') is not None:
        print_info(f"Resource Aware: {'Yes' if job_info['resourceful'] else 'No'}")
    
    # Display error information
    if job_info.get('error'):
        print_error(f"Error Message: {job_info['error']}")
    
    # Display detailed error information (if any)
    if job_info.get('error_details'):
        print_error("Detailed Error Information:")
        for detail in job_info['error_details']:
            print_error(f"  - {detail}")
    
    print_info("="*60)
    
    # Display script output (if any)
    if job_info.get('output'):
        output = job_info['output']
        print_info("\nScript Output:")
        print(output[:2000] if len(output) > 2000 else output)
        if len(output) > 2000:
            print_info(f"... (output truncated, total {len(output)} characters)")
    
    # Display instance-level details (if any)
    if job_info.get('instance_details'):
        print_info("\nInstance Execution Details:")
        for idx, instance in enumerate(job_info['instance_details'], 1):
            instance_id = instance.get('instance_id', 'N/A')
            instance_status = instance.get('status', 'UNKNOWN')
            instance_output = instance.get('output', '')
            instance_error = instance.get('error', '')
            
            print_info(f"Instance {idx}: {instance_id}")
            print_info(f"  Status: {instance_status}")
            if instance_error:
                print_error(f"  Error: {instance_error}")
            if instance_output and len(instance_output) > 0:
                print_info(f"  Output: {instance_output[:100]}...")
    
    # According to Huawei Cloud COC API, when status becomes ABNORMAL, CANCELED, or FINISHED, script execution ends
    # Return status classification
    if status in ['FINISHED']:
        print_success("Job executed successfully!")
        return job_info
    elif status in ['ABNORMAL', 'CANCELED']:
        print_error("Job execution ended!")
        return job_info
    elif status in ['READY', 'PROCESSING']:
        print_warning("Job is still running...")
        return job_info
    else:
        print_warning(f"Unknown job status: {status}")
        return job_info

def query_instance_by_ip(public_ip):
    """Query Flexus L instance information by public IP"""
    try:
        from huaweicloudsdkcore.auth.credentials import GlobalCredentials, BasicCredentials
        from huaweicloudsdkrms.v1 import RmsClient
        from huaweicloudsdkrms.v1.region.rms_region import RmsRegion
        from huaweicloudsdkrms.v1 import model
    except ImportError:
        log.error("huaweicloudsdkrms module not installed. Please run: pip install huaweicloudsdkrms")
        return None

    # Get credentials
    AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    
    # RMS requires GlobalCredentials
    if SECURITY_TOKEN:
        credentials = GlobalCredentials(AK, SK).with_security_token(SECURITY_TOKEN)
    else:
        credentials = GlobalCredentials(AK, SK)
    client = RmsClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(RmsRegion.value_of(REGION)) \
        .build()

    request = model.ListAllResourcesRequest()
    request.region_id = REGION
    request.type = "hcss.l-instance"  # Flexus L instance type
    request.limit = 200

    try:
        response = client.list_all_resources(request)
        resources = response.resources if hasattr(response, 'resources') else []

        for r in resources:
            name = getattr(r, 'name', '') or getattr(r, 'resource_name', '')
            instance_id = getattr(r, 'id', '') or getattr(r, 'resource_id', '')
            props = getattr(r, 'properties', None)

            ip = None
            ecs_instance_id = None

            if props:
                resources_list = props.get('resources', [])
                for res in resources_list:
                    if isinstance(res, dict):
                        attrs = res.get('resource_attributes', [])
                        for attr in attrs:
                            if isinstance(attr, dict):
                                key = attr.get('key')
                                value = attr.get('value')
                                if key == 'public_ip_address':
                                    ip = value
                                if key == 'associate_instance_id':
                                    ecs_instance_id = value

            if ip == public_ip:
                return {
                    'instance_name': name,
                    'instance_id': instance_id,
                    'ecs_instance_id': ecs_instance_id,
                    'public_ip': ip,
                    'region': REGION,
                    'status': props.get('status') if props else 'UNKNOWN',
                    'instance_type': 'Flexus L Instance'
                }
    except Exception as e:
        log.error(f"Failed to query Flexus L instance information: {e}")
    
    return None

def load_instance_info():
    """Load Flexus L instance information from file"""
    info_file = Path(__file__).parent / "new_instance_info.json"
    if info_file.exists():
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure instance type information is included
                if 'instance_type' not in data:
                    data['instance_type'] = 'Flexus L Instance'
                return data
        except Exception as e:
            log.error(f"Failed to read instance information file: {e}")
    return None

def get_dependencies_script():
    """Get dependency installation script content - specifically for JiuwenSwarm basic dependency installation on Flexus L instances"""
    return '''#!/bin/bash
set -euo pipefail

# Color output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

echo "============================================================="
echo "          JiuwenSwarm Basic Dependency Installation Script (Flexus L Instance)"
echo "============================================================="

export DEBIAN_FRONTEND=noninteractive

# ====================================================
# 1. System Environment Check
# ====================================================
check_system_environment() {
    log_info "Checking system environment..."
    
    # Check operating system
    if [[ ! -f /etc/os-release ]]; then
        log_error "Unable to determine operating system"
        return 1
    fi
    
    # Read OS information
    source /etc/os-release
    
    log_info "Operating System: $NAME $VERSION"
    log_info "Architecture: $(uname -m)"
    log_info "Kernel Version: $(uname -r)"
    
    # Check if Ubuntu
    if [[ "$ID" != "ubuntu" ]]; then
        log_warning "Current system is not Ubuntu, may not be compatible"
    fi
    
    # Check memory
    local total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $total_mem -lt 2048 ]]; then
        log_warning "Insufficient system memory (current: ${total_mem}MB, recommended: 4096MB)"
    else
        log_info "System Memory: ${total_mem}MB"
    fi
    
    # Check disk space
    local free_disk=$(df -h / | awk 'NR==2 {print $4}')
    log_info "Root Partition Free Space: $free_disk"
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    log_info "CPU Cores: $cpu_cores"
    
    # Check disk usage
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ $disk_usage -gt 80 ]]; then
        log_warning "High disk usage (${disk_usage}%), recommend cleaning up space"
    fi
    
    # Check network connectivity
    if ping -c 1 -W 2 pypi.org &> /dev/null; then
        log_success "Internet connection normal (pypi.org reachable)"
    else
        log_warning "Internet connection may have issues, may affect dependency downloads"
    fi
    
    if ping -c 1 -W 2 github.com &> /dev/null; then
        log_success "GitHub connection normal"
    else
        log_warning "GitHub connection may have issues"
    fi
    
    log_success "System environment check completed"
}

# ====================================================
# 2. Dependency Package Installation
# ====================================================
install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    # Preprocessing: Check and fix system Python environment
    if ! python3 -c "import apt_pkg" 2>/dev/null; then
        log_warning "Detected apt_pkg module issue, attempting auto-fix..."
        # Find system original python3 path
        SYSTEM_PYTHON=$(ls -la /usr/bin/python3 | awk '{print $11}')
        if [ -n "$SYSTEM_PYTHON" ] && [ "$SYSTEM_PYTHON" != "/usr/bin/python3" ]; then
            log_info "Found system Python path: $SYSTEM_PYTHON"
            # Temporarily restore system python3 for apt operations
            cp /usr/bin/python3 /usr/bin/python3.tmp 2>/dev/null || true
            ln -sf "$SYSTEM_PYTHON" /usr/bin/python3
            log_success "Temporarily restored system Python for apt tools"
        else
            log_warning "Unable to auto-fix, continuing..."
        fi
    fi
    
    # Update package list
    log_info "Updating package list..."
    apt-get update -qq
    
    # Install basic tools
    log_info "Installing system basic tools..."
    apt-get install -y -qq \\
        curl \\
        wget \\
        git \\
        vim \\
        htop \\
        net-tools \\
        tree \\
        unzip \\
        zip \\
        jq \\
        software-properties-common \\
        build-essential \\
        libssl-dev \\
        libffi-dev \\
        ca-certificates \\
        gnupg \\
        lsb-release \\
        pkg-config
    
    # Check and install Python 3.11+
    log_info "Checking Python version..."
    local python_version=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    local python_major=$(echo "$python_version" | cut -d. -f1)
    local python_minor=$(echo "$python_version" | cut -d. -f2)
    
    if [[ "$python_major" -lt 3 ]] || [[ "$python_major" -eq 3 && "$python_minor" -lt 11 ]]; then
        log_info "Current Python version: $python_version, need to install Python 3.11+"
        
        # Check OS version
        source /etc/os-release
        
        if [[ "$ID" == "ubuntu" ]]; then
            log_info "Detected Ubuntu system, installing Python 3.11..."
            
            # Add deadsnakes PPA (for Ubuntu 20.04+)
            apt-get install -y software-properties-common
            add-apt-repository -y ppa:deadsnakes/ppa
            apt-get update -qq
            
            # Install Python 3.11 and related packages
            apt-get install -y -qq \\
                python3.11 \\
                python3.11-venv \\
                python3.11-dev \\
                python3.11-distutils \\
                python3-pip
            
            # Set Python 3.11 as default python3
            update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            update-alternatives --set python3 /usr/bin/python3.11
            
            # Ensure pip points to correct Python version
            python3.11 -m pip install --upgrade pip --break-system-packages
            log_success "Python 3.11 installation completed"
        else
            log_warning "Non-Ubuntu system, please ensure Python 3.11+ is installed"
            log_warning "Current Python version: $python_version"
            log_warning "JiuwenSwarm requires Python 3.11+, please install manually"
        fi
    else
        log_info "Python version meets requirements: $python_version"
        
        # Install Python development packages
        apt-get install -y -qq \\
            python3-pip \\
            python3-venv \\
            python3-dev \\
            python3-setuptools
    fi
    
    # Check and install Node.js 18.x
    log_info "Checking Node.js version..."
    if command -v node &> /dev/null; then
        local node_version=$(node --version 2>&1)
        local node_major=$(echo "$node_version" | cut -d'.' -f1 | tr -d 'v')
        if [[ "$node_major" -ge 18 ]]; then
            log_success "Node.js version meets requirements: $node_version"
        else
            log_info "Node.js version too old ($node_version), upgrading to 18.x..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y -qq nodejs
            log_success "Node.js upgraded to 18.x completed"
        fi
    else
        log_info "Installing Node.js 18.x..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y -qq nodejs
        log_success "Node.js 18.x installation completed"
    fi
    
    # Check npm
    if command -v npm &> /dev/null; then
        local npm_version=$(npm --version 2>&1)
        log_success "npm installed: $npm_version"
    else
        log_info "npm installed with Node.js"
    fi
    
    log_success "System dependencies installation completed"
}

# ====================================================
# 3. Python Environment Configuration
# ====================================================
setup_python_environment() {
    log_info "Configuring Python environment..."
    
    # Create virtual environment directory
    local venv_dir="/opt/jiuwenswarm-env"
    
    if [[ -d "$venv_dir" ]]; then
        log_warning "Virtual environment already exists, will recreate"
        rm -rf "$venv_dir"
    fi
    
    # Create virtual environment - use python3.11 to ensure correct version
    log_info "Creating Python virtual environment..."
    python3.11 -m venv "$venv_dir"
    
    # Activate virtual environment
    source "$venv_dir/bin/activate"
    
    # Upgrade pip, setuptools and wheel
    log_info "Upgrading pip, setuptools and wheel..."
    pip install --upgrade pip setuptools wheel -q
    
    # Create configuration directories
    log_info "Creating configuration directories..."
    mkdir -p "$venv_dir"/{config,logs,data,cache}
    chmod 755 "$venv_dir"/{config,logs,data,cache}
    
    # Set environment variables
    log_info "Setting environment variables..."
    cat > /etc/profile.d/jiuwenswarm.sh << 'EOF'
export JIUWENSWARM_HOME="/opt/jiuwenswarm-env"
export PATH="$PATH:/usr/local/bin"
export PYTHONPATH="${PYTHONPATH:-}:$JIUWENSWARM_HOME"
EOF
    
    # Set file permissions
    chmod 644 /etc/profile.d/jiuwenswarm.sh
    
    log_success "Python environment configuration completed"
}

# ====================================================
# Main Execution Flow
# ====================================================
main() {
    # 1. System environment check
    if ! check_system_environment; then
        log_error "System environment check failed"
        exit 1
    fi
    
    # 2. Dependency package installation
    if ! install_system_dependencies; then
        log_error "System dependency installation failed"
        exit 1
    fi
    
    # 3. Python environment configuration
    if ! setup_python_environment; then
        log_error "Python environment configuration failed"
        exit 1
    fi
    
    # Verify installation
    log_info "Verifying installation..."
    echo "  - Python version: $(python3 --version 2>&1)"
    echo "  - Python3.11 version: $(python3.11 --version 2>&1)"
    echo "  - pip version: $(pip3 --version 2>&1 | head -1)"
    echo "  - Node.js version: $(node --version 2>&1)"
    echo "  - npm version: $(npm --version 2>&1)"
    echo "  - Git version: $(git --version 2>&1)"
    
    echo "============================================================="
    log_success "JiuwenSwarm basic dependency environment installation completed"
    log_info "Installed core dependencies:"
    echo "  - Python 3.11+"
    echo "  - Node.js 18.x"
    echo "  - Git"
    echo "  - pip, npm package managers"
    echo "  - System basic tools (curl, wget, vim, etc.)"
    log_info "System ready for JiuwenSwarm service deployment"
    echo "============================================================="
}

# Execute main function
main "$@"
'''

def install_dependencies(instance_info):
    """Install JiuwenSwarm service dependency environment on Flexus L instance"""
    print_header("Phase 3: COC Remote Installation of JiuwenSwarm Basic Dependencies")
    print_info("Target: Flexus L Instance")
    print_info("Description: Only install basic dependencies (Python 3.11+, Node.js 18.x, Git, etc.)")
    
    # Get credentials
    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
        print_info(f"Using Region: {REGION}")
        print_info(f"AK: {AK[:4]}...{AK[-4:]}")
        if SECURITY_TOKEN:
            print_info(f"[INFO] Using temporary security credentials (STS token)")
    except ValueError as e:
        print_error(f"Failed to get credentials: {e}")
        return None
    
    print_info("Flexus L Instance Information:")
    print(f"  - Instance Name: {instance_info.get('instance_name', 'N/A')}")
    print(f"  - Instance Type: {instance_info.get('instance_type', 'Flexus L Instance')}")
    print(f"  - Instance ID: {instance_info['instance_id']}")
    print(f"  - ECS Instance ID: {instance_info['ecs_instance_id']}")
    print(f"  - Public IP: {instance_info['public_ip']}")
    print(f"  - Region: {instance_info.get('region', REGION)}")
    print(f"  - Status: {instance_info.get('status', 'UNKNOWN')}")
    
    print_info(f"Timeout Setting: {EXECUTION_TIMEOUT}s ({EXECUTION_TIMEOUT/60:.0f} minutes)")
    print_info(f"Max Retries: {MAX_RETRIES}")

    try:
        client = get_coc_client()
        print_success("COC client created successfully")
    except Exception as e:
        print_error(f"Failed to create COC client: {e}")
        return None

    # Prepare target instance information
    target_instances = [{
        "resource_id": instance_info['instance_id'],  # Use Flexus L instance resource ID, not ECS instance ID
        "region_id": instance_info.get('region', REGION),
        "provider": "HCSS",
        "type": "L-INSTANCE"
    }]

    # Get dependency installation script
    deps_script = get_dependencies_script()
    
    # Generate script name
    script_name = f"jiuwenswarm-deps-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    description = f"JiuwenSwarm basic dependency installation on {instance_info.get('instance_name', instance_info['instance_id'])} (Flexus L Instance)"
    
    print_info(f"Starting dependency installation script: {script_name}")
    print_info(f"Target Instance: {instance_info['public_ip']} ({instance_info['instance_id']})")
    print_info(f"Instance Type: {instance_info.get('instance_type', 'Flexus L Instance')}")
    print_info("Installation Content:")
    print("  - Python 3.11+")
    print("  - Node.js 18.x")
    print("  - Git")
    print("  - System basic tools (curl, wget, vim, etc.)")
    print("  - pip, npm package managers")
    
    # Use new coc_create_script and coc_execute_script functions (refer to OpenClaw implementation)
    try:
        # 1. Create script
        print_info(f"Creating COC script: {script_name}")
        create_result = coc_create_script(
            name=script_name,
            script_type="SHELL",
            content=deps_script,
            description=description,
            risk_level="LOW",
            version="1.0.0"
        )
        
        if not create_result.get("ok"):
            error_info = create_result.get("error", {})
            print_error(f"Script creation failed: {error_info.get('message', 'Unknown error')}")
            return None
        
        script_uuid = create_result.get("result", {}).get("script_uuid")
        if not script_uuid:
            print_error("Script created successfully but script UUID not retrieved")
            return None
        
        print_success(f"Script created successfully: {script_uuid}")
        
        # 2. Execute script (don't wait automatically, poll status manually)
        print_info(f"Starting script execution...")
        execute_result = coc_execute_script(
            script_uuid=script_uuid,
            execute_user="root",
            timeout=EXECUTION_TIMEOUT,
            success_rate=100.0,
            target_instances=target_instances,
            rotation_strategy="CONTINUE",
            wait_for_complete=False  # Don't wait automatically, check status manually
        )
        
        # Check if job submission was successful - status code 200 or 202 indicates successful submission
        status_code = execute_result.get("status_code", 200)
        if execute_result.get("ok") and status_code in [200, 202]:
            execute_uuid = execute_result.get("result", {}).get("execute_uuid")
            print_info(f"Job submitted successfully, response status code: {status_code}, execution UUID: {execute_uuid}")
            
            # Poll to check script execution status
            print_info("Starting to poll script execution status...")
            start_time = time.time()
            last_status = None
            
            while time.time() - start_time < EXECUTION_TIMEOUT:
                job_result = coc_query_execution(execute_uuid)
                if job_result.get("ok"):
                    job_info = job_result.get("result", {})
                    status = job_info.get("status", "UNKNOWN")
                    
                    if status != last_status:
                        last_status = status
                        print_info(f"Current Status: {status}")
                    
                    # According to GetScriptJobInfo API, FINISHED, CANCELED, ABNORMAL indicate execution completion
                    if status == "FINISHED":
                        print_success("Flexus L instance basic dependency environment installation successful!")
                        result_data = job_info
                        # Display execution results
                        print_info(f"Execution Result: Total {result_data.get('total_count', 1)} instances, Success {result_data.get('success_count', 0)}, Failed {result_data.get('fail_count', 0)}")
                        print_info(f"Execution UUID: {result_data.get('execute_uuid', 'N/A')}")
                        print_info(f"Status: {result_data.get('status', 'UNKNOWN')}")
                        
                        if result_data.get('create_time'):
                            print_info(f"Create Time: {result_data['create_time']}")
                        if result_data.get('finish_time'):
                            print_info(f"Finish Time: {result_data['finish_time']}")
                        
                        # Display script output
                        script_output = ""
                        
                        # First try to get from script_content field (new field)
                        if result_data.get('script_content'):
                            script_output = result_data['script_content']
                            print_info("Getting script content from script_content field in API response")
                        # Second try to get from output field (standard API response field)
                        elif result_data.get('output'):
                            script_output = result_data['output']
                            print_info("Getting script execution output from output field in API response")
                        # Then check output in instance_details
                        elif result_data.get('instance_details'):
                            for instance in result_data['instance_details']:
                                if isinstance(instance, dict) and instance.get('output'):
                                    script_output = instance['output']
                                    print_info("Getting script execution output from instance_details[].output in API response")
                                    break
                        
                        if script_output:
                            print_info("\nScript Output:")
                            print(script_output[:2000] if len(script_output) > 2000 else script_output)
                        
                        return result_data
                    elif status in ["CANCELED", "ABNORMAL"]:
                        print_error(f"Script execution failed, status: {status}")
                        error_msg = job_info.get("error", "Unknown error")
                        print_error(f"Error Message: {error_msg}")
                        return None
                
                time.sleep(5)
            else:
                print_error("Script execution timeout")
                return None
        else:
            error_info = execute_result.get("error", {})
            print_error(f"Script execution failed: {error_info.get('message', 'Unknown error')}")
            
            # Display error details
            result_data = execute_result.get("result", {})
            if result_data:
                print_error(f"Execution UUID: {result_data.get('execute_uuid', 'N/A')}")
                print_error(f"Status: {result_data.get('status', 'UNKNOWN')}")
                if result_data.get('error'):
                    print_error(f"Error Message: {result_data['error']}")
                if result_data.get('output'):
                    output = result_data['output']
                    print_info("\nScript Output:")
                    print(output[:2000] if len(output) > 2000 else output)
            
            return None
            
    except Exception as e:
        print_error(f"Script execution failed: {e}")
        print_error("Possible reason: COC service cannot recognize instance resource ID")
        print_error(f"Please check if instance ID: {instance_info['instance_id']} is correct")
        return None

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='COC Remote Installation of JiuwenSwarm Basic Dependencies on Flexus L Instance',
        epilog='Note: This script only installs basic dependency environment, not the JiuwenSwarm service itself.'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Top-level arguments (for backward compatibility)
    parser.add_argument('--instance-id', type=str, help='Flexus L instance RMS resource ID')
    parser.add_argument('--ecs-instance-id', type=str, help='ECS instance ID corresponding to Flexus L instance')
    parser.add_argument('--ip', type=str, help='Public IP address of Flexus L instance')
    parser.add_argument('--no-wait', action='store_true', help='Submit without waiting for execution result')
    parser.add_argument('--timeout', type=int, default=EXECUTION_TIMEOUT, help=f'Execution timeout in seconds (default: {EXECUTION_TIMEOUT})')
    parser.add_argument('--max-retries', type=int, default=MAX_RETRIES, help=f'Max retry attempts (default: {MAX_RETRIES})')
    
    # install command (default)
    install_parser = subparsers.add_parser('install', help='Install dependency environment')
    install_parser.add_argument('--instance-id', type=str, help='Flexus L instance RMS resource ID')
    install_parser.add_argument('--ecs-instance-id', type=str, help='ECS instance ID corresponding to Flexus L instance')
    install_parser.add_argument('--ip', type=str, help='Public IP address of Flexus L instance')
    install_parser.add_argument('--no-wait', action='store_true', help='Submit without waiting for execution result')
    install_parser.add_argument('--timeout', type=int, default=EXECUTION_TIMEOUT, help=f'Execution timeout in seconds (default: {EXECUTION_TIMEOUT})')
    install_parser.add_argument('--max-retries', type=int, default=MAX_RETRIES, help=f'Max retry attempts (default: {MAX_RETRIES})')
    
    # status command
    status_parser = subparsers.add_parser('status', help='Check job status')
    status_parser.add_argument('--execute-uuid', type=str, required=True, help='Job execution UUID')
    
    return parser.parse_args()

def main():
    """Main function - Remotely install JiuwenSwarm basic dependencies on Flexus L instance via COC"""
    args = parse_args()
    
    # Update configuration parameters
    global EXECUTION_TIMEOUT, MAX_RETRIES
    if hasattr(args, 'timeout') and args.timeout:
        EXECUTION_TIMEOUT = args.timeout
    if hasattr(args, 'max_retries') and args.max_retries:
        MAX_RETRIES = args.max_retries

    # Execute different operations based on command
    if args.command == 'status':
        # Check job status
        check_job_status(args.execute_uuid)
        return
    elif args.command == 'install':
        # Use install subcommand arguments
        pass
    elif args.command is None:
        # No subcommand specified, check for top-level arguments (backward compatibility)
        # If any top-level arguments (--ip, --instance-id, etc.), execute installation
        if args.ip or args.instance_id:
            pass  # Execute installation
        else:
            # No arguments, show help
            print_header("Flexus L Instance - JiuwenSwarm Basic Dependency Installation")
            print_info("Available Commands:")
            print("  install   - Install dependency environment")
            print("  status    - Check job status")
            print("\nUsage Examples:")
            print("  python install_deps.py install --ip X.X.X.X")
            print("  python install_deps.py status --execute-uuid SCTxxx")
            print("  python install_deps.py --ip X.X.X.X  (legacy format, backward compatible)")
            return
    else:
        print_error(f"Unknown command: {args.command}")
        sys.exit(1)

    print_header("Flexus L Instance - JiuwenSwarm Basic Dependency Installation")
    print_info("Description: This script remotely installs via Huawei Cloud COC service")
    print_info("             the basic dependency environment required for JiuwenSwarm service.")
    print_info("             Main installations: Python 3.11+, Node.js 18.x, Git, system tools, etc.")
    print("="*60)

    # Check environment variables
    try:
        AK, SK, REGION, SECURITY_TOKEN = get_huaweicloud_credentials()
    except ValueError as e:
        print_error(str(e))
        print("\nSet command:")
        print("  Windows: set HUAWEICLOUD_SDK_AK=your_ak && set HUAWEICLOUD_SDK_SK=your_sk && set HUAWEICLOUD_REGION=cn-north-4")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_AK=your_ak && export HUAWEICLOUD_SDK_SK=your_sk && export HUAWEICLOUD_REGION=cn-north-4")
        print("\nFor temporary security credentials (STS token), also set:")
        print("  Windows: set HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        print("  Linux/Mac: export HUAWEICLOUD_SDK_SECURITY_TOKEN=your_token")
        sys.exit(1)

    # Get instance information
    instance_info = None
    if args.instance_id and args.ip:
        instance_info = {
            'instance_id': args.instance_id,
            'ecs_instance_id': args.ecs_instance_id,
            'public_ip': args.ip,
            'region': REGION,
            'instance_type': 'Flexus L Instance'
        }
    elif args.ip:
        print_info(f"Querying Flexus L instance information by public IP: {args.ip}")
        instance_info = query_instance_by_ip(args.ip)
        if not instance_info:
            print_error("Unable to find Flexus L instance with specified IP")
            print_error("Please confirm the instance type is Flexus L")
            sys.exit(1)
    else:
        instance_info = load_instance_info()
        if not instance_info:
            print_error("Unable to get Flexus L instance information")
            print_info("Please specify one of the following parameters:")
            print("  1. --instance-id and --ip (specify instance info manually)")
            print("  2. --ip (query instance info automatically)")
            print("  3. Ensure new_instance_info.json file exists")
            sys.exit(1)

    # Ensure necessary fields exist
    if 'ecs_instance_id' not in instance_info:
        print_error("Instance information missing ecs_instance_id field")
        print_error("Please ensure you provide the ECS instance ID of the Flexus L instance")
        sys.exit(1)

    # Install dependencies
    result = install_dependencies(instance_info)
    print(f" result: {result}")
    if result:
        # Save execution result
        result_file = Path(__file__).parent / "deps_install_result.json"
        result_data = {
            'execute_uuid': result.get('execute_uuid', ''),
            'instance_id': instance_info['instance_id'],
            'ecs_instance_id': instance_info['ecs_instance_id'],
            'public_ip': instance_info['public_ip'],
            'instance_type': instance_info.get('instance_type', 'Flexus L Instance'),
            'region': instance_info.get('region', REGION),
            'instance_name': instance_info.get('instance_name', ''),
            'status': result.get('status', ''),
            'start_time': result.get('start_time', ''),
            'end_time': result.get('end_time', ''),
            'total_count': result.get('total_count', 0),
            'success_count': result.get('success_count', 0),
            'fail_count': result.get('fail_count', 0),
            'timestamp': datetime.now().isoformat(),
            'phase': 'phase3_dependencies',
            'description': 'Flexus L instance JiuwenSwarm basic dependency installation',
            'script_version': 'v3.0-simplified'
        }
        
        try:
            save_json_file(result_file, result_data)
            print_info(f"Execution result saved to: {result_file}")
        except Exception as e:
            print_error(f"Failed to save execution result: {e}")

        print_success("Flexus L instance basic dependency installation task completed!")
        print_info(f"Execution UUID: {result.get('execute_uuid', 'N/A')}")
        print_info(f"Instance: {instance_info['public_ip']} ({instance_info['instance_id']})")
        print_info(f"Instance Type: {instance_info.get('instance_type', 'Flexus L Instance')}")
        print_info("Installed core dependencies:")
        print("  - Python 3.11+")
        print("  - Node.js 18.x")
        print("  - Git")
        print("  - pip, npm package managers")
        print("  - System basic tools")
        
        if not args.no_wait:
            print("\nNext step: Run deploy_service.py for JiuwenSwarm service deployment")
        else:
            print("\n[Note] --no-wait parameter used, script submitted but not waiting for completion")
            print("       Run python install_deps.py status --execute-uuid " + result.get('execute_uuid', '') + " to check job status")
        print("\nNote: This phase only installs basic dependencies. Service deployment will be done in the next phase")
    else:
        print_error("Dependency installation task failed")
        sys.exit(1)

if __name__ == "__main__":
    main()