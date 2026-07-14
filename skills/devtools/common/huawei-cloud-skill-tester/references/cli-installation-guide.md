# CLI Installation Guide

> Installation and initialization steps for hcloud CLI and npx skills.

## hcloud CLI Installation

```bash
# Install via npm
npm install -g @huaweicloud/hcloud

# Verify installation
hcloud --version
```

## hcloud CLI Authentication Configuration

```bash
# Configure via environment variables (recommended)
export HUAWEI_ACCESS_KEY=${your_ak}
export HUAWEI_SECRET_KEY=${your_sk}

# Or configure via CLI
hcloud configure set --access-key=${HUAWEI_ACCESS_KEY} --secret-key=${HUAWEI_SECRET_KEY}

# Set default region
hcloud configure set --region=cn-north-4

# Verify configuration
hcloud configure list
```

## npx skills Installation

```bash
# npx comes with Node.js, ensure Node.js >= 16
node --version

# Install a Skill
npx skills add <repo-url> --skill <skill-name>

# List installed Skills
npx skills list

# Remove a Skill
npx skills remove <skill-name>
```

## Prerequisite Verification

```bash
# One-command verification of all prerequisites
hcloud --version && hcloud configure list && node --version
```
