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

init_result=1

# Method 1: First try direct run (non-interactive mode)
# jiuwenswarm-init detects non-tty input and auto-enters non-interactive mode
log_info "Method 1: Trying direct run (non-interactive mode)..."
jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml < /dev/null
init_result=$?

if [[ $init_result -eq 0 ]]; then
    log_success "JiuwenSwarm initialization completed (non-interactive mode)"
else
    log_info "Method 1 failed, trying interactive methods..."
    
    # Method 2: Use expect for interactive prompts
    if command -v expect &> /dev/null; then
        log_info "Method 2: Using expect to auto-answer interactive prompts..."
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
    fi
    
    # Method 3: Use printf with proper handling for broken pipe
    if [[ $init_result -ne 0 ]]; then
        log_info "Method 3: Using printf with pipe..."
        {
            printf "yes\n1\n"
        } | jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml 2>&1 | tail -100
        init_result=${PIPESTATUS[1]}
    fi
    
    # Method 4: Try with --yes and --lang parameters if available
    if [[ $init_result -ne 0 ]]; then
        if jiuwenswarm-init --help 2>&1 | grep -q "--yes"; then
            log_info "Method 4: Trying --yes and --lang parameters..."
            jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml --yes --lang zh
            init_result=$?
            if [[ $init_result -eq 0 ]]; then
                log_success "JiuwenSwarm initialization completed (--yes method)"
            fi
        fi
    fi
fi

if [[ $init_result -ne 0 ]]; then
    log_error "All initialization methods failed"
    log_error "Please execute manually: jiuwenswarm-init --config /root/.jiuwenswarm/config/config.yaml"
    exit 1
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
