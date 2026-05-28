#!/bin/bash
set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
echo "          JiuwenSwarm Deployment Script"
echo "============================================================="

export DEBIAN_FRONTEND=noninteractive

# Create configuration directories
log_info "Creating configuration directories..."
mkdir -p /root/.jiuwenswarm/config
mkdir -p /root/.jiuwenswarm/logs
mkdir -p /root/.jiuwenswarm/data
mkdir -p /root/.jiuwenswarm/cache

# Create configuration files
log_info "Creating configuration files..."
cat > /root/.jiuwenswarm/config/config.yaml << 'CONFIGEOF'
channels:
  xiaoyi:
    enabled: false
    ak: ""
    sk: ""
    api_id: ""
    agent_id: ""
  
  feishu:
    enabled: false
    app_id: ""
    app_secret: ""
  
  dingtalk:
    enabled: false
    client_id: ""
    client_secret: ""
    allow_from: ""

database:
  type: sqlite
  path: /root/.jiuwenswarm/data/jiuwenswarm.db

cache:
  type: memory
  size: 1000

security:
  session_secret: "change-this-to-a-random-string"
  cors_origins: "*"
  rate_limit: 100
CONFIGEOF

cat > /root/.jiuwenswarm/config/.env << 'ENVEOL'
API_BASE=https://api.openai.com/v1
API_KEY=your-api-key-here
MODEL_NAME=gpt-4
MODEL_PROVIDER=openai

JIUWENSWARM_HOST=0.0.0.0
JIUWENSWARM_PORT=5173
JIUWENSWARM_LOG_LEVEL=INFO
ENVEOL

chmod 600 /root/.jiuwenswarm/config/config.yaml
chmod 600 /root/.jiuwenswarm/config/.env


log_info "Installing Python 3.11"
# 1. Install PPA tools
sudo apt update
sudo apt install -y software-properties-common

# 2. Add deadsnakes PPA (provides multiple Python versions)
sudo add-apt-repository ppa:deadsnakes/ppa -y

# 3. Update sources
sudo apt update

# 4. Install Python 3.11 + venv + dev
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 5. Verify installation
python3.11 --version


log_info "Creating Python virtual environment..."
python3.11 -m venv /opt/jiuwenswarm-env

source /opt/jiuwenswarm-env/bin/activate

log_info "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel -q -i https://mirrors.aliyun.com/pypi/simple/

log_info "Installing JiuwenSwarm (using domestic mirror)..."
pip install jiuwenswarm -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir

# Initialize JiuwenSwarm
log_info "Starting JiuwenSwarm initialization..."

# Use expect or printf to send all responses sequentially
# First try expect, use printf if unavailable
if command -v expect &> /dev/null; then
    log_info "Using expect to auto-answer interactive prompts..."
    expect << 'EOF'
set timeout 60
spawn jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml
expect {
    "Do you want to continue? (yes/no):" {
        send "yes\r"
        exp_continue
    }
    "Please enter option (1, 2, zh, en) or no to cancel:" {
        send "1\r"
        exp_continue
    }
    "Enter option (1, 2, zh, en) or no to cancel:" {
        send "zh\r"
        exp_continue
    }
    eof {
        catch wait result
        exit [lindex $result 3]
    }
    timeout {
        puts "Initialization timeout"
        exit 1
    }
}
EOF
    init_result=$?
else
    log_info "Using printf to auto-answer interactive prompts..."
    # Use printf to send all responses with sufficient delay
    {
        echo "yes"
        sleep 2
        echo "1"
        sleep 2
    } | jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml
    init_result=$?
fi

if [[ $init_result -eq 0 ]]; then
    log_success "JiuwenSwarm initialization completed"
else
    log_error "JiuwenSwarm initialization failed (exit code: $init_result)"
    log_info "Attempting alternative initialization method..."
    
    # Alternative: Use --yes and --lang parameters
    if jiuwenswarm-init --help 2>&1 | grep -q "--yes"; then
        log_info "Trying --yes and --lang parameters..."
        jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml --yes --lang zh
        if [[ $? -eq 0 ]]; then
            log_success "JiuwenSwarm initialization completed (alternative method)"
            init_result=0
        else
            log_error "Alternative method also failed, please run initialization manually"
        fi
    else
        log_error "Cannot complete initialization automatically, please execute manually: jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml"
        exit 1
    fi
fi

log_info "Creating systemd service..."
cat > /etc/systemd/system/jiuwenswarm.service << 'SERVICE_EOF'
[Unit]
Description=JiuwenSwarm Service
Description=Multi-Agent Collaboration Platform
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/jiuwenswarm-env
EnvironmentFile=/root/.jiuwenswarm/config/.env
ExecStart=/opt/jiuwenswarm-env/bin/jiuwenswarm-start
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jiuwenswarm

[Install]
WantedBy=multi-user.target
SERVICE_EOF

log_info "Enabling and starting service..."
systemctl daemon-reload
systemctl enable jiuwenswarm
systemctl start jiuwenswarm

log_info "Waiting for service to start..."
sleep 15

log_info "Checking port listening..."
if netstat -tln | grep -q ':5173'; then
    log_success "Port 5173 is listening"
else
    log_error "Port 5173 is not listening"
    journalctl -u jiuwenswarm --no-pager | tail -20
    exit 1
fi

log_info "Checking service health status..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/health | grep -q "200"; then
    log_success "Service health check passed"
else
    log_error "Service health check failed"
    journalctl -u jiuwenswarm --no-pager | tail -20
    exit 1
fi

log_success "JiuwenSwarm service started successfully!"
log_info "Web access address: http://$(hostname -I | awk '{print $1}'):5173"

echo "============================================================="
echo "          Deployment Complete"
echo "============================================================="
