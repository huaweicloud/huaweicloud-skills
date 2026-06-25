English | [中文](README_zh.md)

# DWS Autopilot MCP Server

## Table of Contents
- [1. Introduction](#1-introduction)
- [2. Features](#2-features)
  - [2.1 Tools](#21-tools)
  - [2.2 Authentication](#22-authentication)
  - [2.3 Config Encryption](#23-config-encryption)
- [3. Installation & Configuration](#3-installation--configuration)
  - [3.1 Prerequisites](#31-prerequisites)
  - [3.2 Installation](#32-installation)
  - [3.3 Configuration](#33-configuration)
  - [3.4 Config Management CLI](#34-config-management-cli)
  - [3.5 Client Configuration](#35-client-configuration)
- [4. Getting Started](#4-getting-started)

## 1. Introduction
MCP (Model Context Protocol) is an open protocol standard proposed by Anthropic in November 2024, aiming to solve the fragmentation problem of interaction between large language models and external systems (such as databases, APIs). By standardizing the interface, it allows LLMs to dynamically understand tool functions and perform tasks, reducing integration costs.
Setting up the DWS Autopilot MCP Server allows users to leverage LLM capabilities to query DWS cluster monitoring metrics and host information through natural language, enabling intelligent operations.

## 2. Features

### 2.1 Tools
DWS Autopilot MCP Server provides the following tools:

1. **dws_autopilot_get_hosts**
   Query DWS cluster host information with filtering by hostname/IP, pagination, and sorting support

2. **dws_autopilot_get_metric**
   Query DWS cluster metric data, supporting cpu_usage, mem_usage, disk_usage_avg, tcp_resend_rate, disk_io, net_io, etc.

### 2.2 Authentication
AK/SK authentication mode is supported. The MCP Server uses the configured AK/SK to sign API requests for authentication.

### 2.3 Config Encryption
Sensitive fields (AK, SK) support AES-256-GCM encrypted storage:
- Auto-detects plaintext and encrypts on MCP Server startup
- Machine fingerprint-based key protection, bound to the current machine environment
- Master key dual protection: crypter (stored in yaml) + cryptComponent (stored in crypt.json)

## 3. Installation & Configuration

### 3.1 Prerequisites
+ Python 3.10 or above
+ pip package manager

### 3.2 Installation
```bash
# Clone the repository
git clone https://github.com/huaweicloud/dws_ai_native/tree/dws_autopilot_mcp_server/hwcloud_dws_mcp_mag
cd hwcloud_dws_mcp_mag

# Install dependencies
pip install .
```

### 3.3 Configuration
The configuration file is located at `conf/dws_config.yaml`. Fill in the configuration before first use:

```yaml
region_id: "cn-north-7"
ak: "your_access_key"
sk: "your_secret_key"
project_id: "your_project_id"
```

**Parameter Reference:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `region_id` | Huawei Cloud region ID, used to auto-generate API endpoints | `cn-north-7` |
| `ak` | Huawei Cloud Access Key ID (enter plaintext, auto-encrypted on startup) | - |
| `sk` | Huawei Cloud Secret Access Key (enter plaintext, auto-encrypted on startup) | - |
| `project_id` | Huawei Cloud project ID | - |

> `region_id` automatically generates `DMS_MONITORING_BASE_URL` (`https://dws.{region_id}.myhuaweicloud.com`), no manual configuration needed.

> You can also specify the config file path via the `DWS_MCP_CONFIG` environment variable.

### 3.4 Config Management CLI
After installation, the `dws-mcp-config` CLI tool is available. Run commands from the project root directory (`dws_autopilot_mcp/`):

#### init - Initialize or Update Configuration
The `init` command sets configuration parameters:

```bash
python -m dws_autopilot_mcp.config_cli init --region_id cn-north-7 --ak your_ak --sk your_sk --project_id your_project_id
```

> The `init` command supports partial updates — only specified parameters are updated, unspecified ones remain unchanged. For example, to update only the AK: `python -m dws_autopilot_mcp.config_cli init --ak new_ak`.
>
> After updating configuration, restart the MCP Server to auto-encrypt sensitive fields (AK, SK).

#### Other Commands

```bash
# Manually trigger encryption (auto-executed on MCP Server startup as well)
python -m dws_autopilot_mcp.config_cli encrypt

# Show config status (secrets are masked as ******)
python -m dws_autopilot_mcp.config_cli show

# Reset config to empty template (clear all parameters and remove crypt.json)
python -m dws_autopilot_mcp.config_cli reset
```

> The `encrypt`, `show`, and `reset` commands require no additional parameters and are independent of the authentication mode.

### 3.5 Client Configuration
Using OpenClaw as an example, add the following to MCP Servers configuration:

```json
{
  "dws_autopilot_mcp": {
    "type": "local",
    "command": [
      "/path/to/python.exe",
      "-m",
      "dws_autopilot_mcp.server"
    ],
    "environment": {
      "PYTHONPATH": "/path/to/dws_autopilot_mcp/src"
    }
  }
}
```

> Replace `/path/to/python.exe` with your local Python executable path, and `/path/to/dws_autopilot_mcp/src` with the absolute path to this project's `src` directory.

## 4. Getting Started
After completing the configuration, you can interact with your DWS cluster using natural language, for example:
- "Query XXXX cluster host information"
- "Show XXXX cluster CPU usage for the last hour"
