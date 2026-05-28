# JiuwenSwarm Configuration

# Server Configuration
server:
  host: 0.0.0.0
  port: 5173

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(levelname)s - %(message)s"

# Message Channel Configuration
channels:
  xiaoyi:
    enabled: false
    ak: ""
    sk: ""
    agent_id: ""
  
  feishu:
    enabled: false
    app_id: ""
    app_secret: ""
  
  dingtalk:
    enabled: false
    client_id: ""
    client_secret: ""
    allow_from: "*"

# Model Configuration (read from .env file)
model:
  api_base: ${API_BASE}
  api_key: ${API_KEY}
  model_name: ${MODEL_NAME}
  model_provider: ${MODEL_PROVIDER}

# Database Configuration
database:
  type: sqlite
  path: ./data/jiuwenswarm.db

# Security Configuration
security:
  allowed_origins:
    - "*"
  cors_enabled: true
