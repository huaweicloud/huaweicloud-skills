# Task: Auth Management

## Overview

SWR authentication provides docker login credentials for pushing and pulling images. This task covers obtaining both temporary (12-hour) and long-term (1-year) login credentials.

## Operations Catalog

| Operation              | Method | Description              | Key Parameters                    |
| ---------------------- | ------ | ------------------------ | --------------------------------- |
| `CreateAuthorizationToken` | POST | 获取临时登录指令         | `--projectname`                   |
| `CreateSecret`         | POST   | 获取长期登录指令         | `--projectname`                   |

## Workflows

### W1: Get Temporary Login Token (12-hour validity)

```bash
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4
```

**Optional Parameter**:
- `--projectname`: Project name, defaults to region name (e.g., `cn-north-1`)

**Response Structure** (verified against actual API - Docker auth config format):

```json
{
  "auths": {
    "swr.cn-north-4.myhuaweicloud.com": {
      "auth": "base64-encoded-auth-token"
    }
  }
}
```

- `auths`: Docker config auth object, registry host as key
- `auth`: Base64-encoded `username:password` string

**Constructing Docker Login Command**:

The `auth` field is a base64-encoded string containing `username:password`. Decode it to get the credentials:

```bash
# Decode the auth field to get username and password
# echo <auth_value> | base64 -d  →  username:password
# Then login with decoded credentials:
docker login -u <decoded_username> -p <decoded_password> swr.cn-north-4.myhuaweicloud.com
```

**Use Cases**:
- Temporary docker push/pull access
- Development environment login
- Short-lived CI/CD pipeline credentials

**Token Lifetime**: 12 hours from generation

### W2: Get Long-term Login Secret (1-year validity)

```bash
hcloud SWR CreateSecret --cli-region=cn-north-4
```

**Optional Parameter**:
- `--projectname`: Project name

**Response Structure**: Same Docker auth config format as temporary token (`auths` object with base64 `auth` field)

**Use Cases**:
- CI/CD pipeline persistent credentials
- Automation scripts that run over extended periods
- Kubernetes cluster image pull secrets

**Token Lifetime**: 1 year from generation

**Recommendation**: For Kubernetes deployments, store the long-term secret as a Kubernetes Secret:

```bash
# Create Kubernetes secret for SWR registry
kubectl create secret docker-registry swr-secret \
  --docker-server=swr.cn-north-4.myhuaweicloud.com \
  --docker-username=cn-north-4_<user_name> \
  --docker-password=<secret_from_CreateSecret>
```

### W3: Multi-Region Login

For working with multiple SWR regions, generate credentials for each region:

```bash
# Login for cn-north-4
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# Login for cn-east-3
hcloud SWR CreateAuthorizationToken --cli-region=cn-east-3

# Login for ap-southeast-1
hcloud SWR CreateAuthorizationToken --cli-region=ap-southeast-1
```

**Note**: Each region has its own SWR registry endpoint:
- cn-north-4: `swr.cn-north-4.myhuaweicloud.com`
- cn-east-3: `swr.cn-east-3.myhuaweicloud.com`
- ap-southeast-1: `swr.ap-southeast-1.myhuaweicloud.com`

## Common Scenarios

### S1: CI/CD Pipeline Setup

Configure automated image push/pull for CI/CD:

```bash
# 1. Get long-term credentials
hcloud SWR CreateSecret --cli-region=cn-north-4

# 2. Store credentials in CI/CD environment variables
# (Do NOT print credentials - store them securely)

# 3. Use in pipeline script
docker login -u ${SWR_USERNAME} -p ${SWR_PASSWORD} swr.cn-north-4.myhuaweicloud.com
docker push swr.cn-north-4.myhuaweicloud.com/${NAMESPACE}/${REPO}:${TAG}
```

### S2: Kubernetes Deployment Setup

Configure Kubernetes to pull images from SWR:

```bash
# 1. Get long-term credentials
hcloud SWR CreateSecret --cli-region=cn-north-4

# 2. Create Kubernetes docker-registry secret
kubectl create secret docker-registry swr-regcred \
  --docker-server=swr.cn-north-4.myhuaweicloud.com \
  --docker-username=<username> \
  --docker-password=<password> \
  --namespace=<k8s-namespace>

# 3. Reference in pod/deployment spec
# imagePullSecrets:
#   - name: swr-regcred
```

### S3: Manual Image Push/Pull

```bash
# 1. Get temporary token
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4

# 2. Login to SWR registry
docker login -u cn-north-4_<user> -p <token> swr.cn-north-4.myhuaweicloud.com

# 3. Tag and push image
docker tag my-app:latest swr.cn-north-4.myhuaweicloud.com/group-dev/my-app:latest
docker push swr.cn-north-4.myhuaweicloud.com/group-dev/my-app:latest

# 4. Pull image
docker pull swr.cn-north-4.myhuaweicloud.com/group-dev/my-app:v1.0
```

## Security Notes

- 🚫 Never store login credentials in code repositories
- 🚫 Never display full credentials in logs or conversation
- ✅ Use environment variables or secret management tools
- ✅ Rotate long-term credentials periodically
- ✅ Use temporary tokens for development, long-term for production automation