# Troubleshooting Guide - MaaS Model Invocation

This document provides troubleshooting guidance for common issues when invoking MaaS models.

## 1. Authentication Issues

### 1.1 API Key Invalid or Not Working

**Symptoms**: HTTP 401 error, "Invalid API Key" message

**Possible Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| API Key just created, not yet effective | Wait a few minutes (typically 2-5 minutes) for the API Key to become effective |
| API Key copied incorrectly | Verify the API Key has no extra spaces or missing characters |
| API Key used in wrong region | API Keys are region-specific. Create a new API Key in the target region (西南-贵阳一) |
| API Key has been deleted | Create a new API Key |
| Authorization header format incorrect | Ensure header format is: `Authorization: Bearer <MAAS_API_KEY>` (note the space after "Bearer") |

### 1.2 API Key Creation Issues

**Problem**: Cannot create API Key

**Solutions**:
- Check if you have reached the 30 API Key limit per account. Delete unused keys first.
- Verify you have API Key operation permissions (see IAM policies for sub-user configuration)
- Check if "Strict Authorization Mode" is enabled and you're a sub-user without permissions

### 1.3 API Key Lost

**Problem**: API Key is lost and cannot be retrieved

**Solution**: API Key cannot be recovered once lost. Create a new API Key. **Important**: The API Key will only be displayed once after creation. Please copy and save it promptly.

## 2. Model Service Issues

### 2.1 Preset Service Not Activated

**Symptoms**: "Service not found" or "Model service not available" error

**Solution**:
1. Log in to MaaS console
2. Navigate to "Model Inference > Online Inference > Preset Services"
3. Find the target model service and click "Activate Service"
4. Check "I have read and agree to the above description and the MaaS Service Statement" and click "One-click Activate"

**Note**: First-time use requires activating the preset service before calling the API.

### 2.2 Model Parameter Incorrect

**Symptoms**: HTTP 404 error, "Model not found" message

**Solution**: Verify the `model` parameter value matches exactly. Common mistakes:
- Using display name instead of model parameter (e.g., `DeepSeek-V3.2` instead of `deepseek-v3.2`)
- Using incorrect version suffix (e.g., `deepseek-v3.1` instead of `deepseek-v3.1-terminus`)

Refer to the model list in SKILL.md for correct `model` parameter values.

### 2.3 Service Frozen or Disabled

**Symptoms**: "Service frozen" or "Payment status expired"

**Solutions**:
- **Frozen status**: Account may be in arrears. Recharge your account to unfreeze.
- **Expired status**: Resource was deleted due to account arrears beyond retention period. Re-activate the preset service.

## 3. Request Issues

### 3.1 Rate Limiting (Too Many Requests)

**Symptoms**: HTTP 429 error, error code `ModelArts.81101`

**Solutions**:
- Implement exponential backoff retry mechanism
- Reduce request frequency (send requests evenly, avoid burst)
- Check model's default rate limits (TPM and RPM)
- Consider creating a custom access point with higher rate limits

**Default Rate Limits by Model**:

| Model | TPM | RPM |
|-------|-----|-----|
| DeepSeek-V4-Pro | 30,000 | 3 |
| DeepSeek-V4-Flash | 30,000 | 3 |
| DeepSeek-V3.2 | 500,000 | 700 |
| DeepSeek-V3.1 / V3 / R1 | 500,000 | 1,500 |
| Qwen3 series | 500,000 | 1,500 |
| Kimi-K2.6 | 100,000 | 10 |
| Kimi-K2 | 500,000 | 1,500 |
| LongCat-Flash-Chat | 5,000,000 | 1,000 |
| GLM-5 / GLM-5.1 | 500,000 | 30 |

### 3.2 Request Body Too Large

**Symptoms**: HTTP 413 error, "Request entity too large"

**Solutions**:
- For image upload: Ensure Base64-encoded image is < 10MB
- For image generation (Qwen-Image): Request body must be ≤ 8MB
- For image editing (Qwen-Image-Edit 20250913): Request body must be ≤ 20MB
- For image editing (Qwen-Image-Edit 20251028): Request body must be ≤ 30MB

### 3.3 Context Length Exceeded

**Symptoms**: Error message about exceeding maximum context length

**Solutions**:
- Reduce the input message length
- Use a model with larger context window (e.g., DeepSeek-V4-Pro with 1M context)
- Truncate conversation history for multi-turn conversations
- Set `max_tokens` to limit output length

### 3.4 Output Truncated

**Symptoms**: Model output is incomplete or cut off

**Solutions**:
- Increase `max_tokens` parameter
- Use prefix continuation to continue from where output was truncated
- For Function Call: ensure `max_tokens` is large enough to not truncate `tool_calls`

## 4. Feature-Specific Issues

### 4.1 Deep Thinking Issues

**Problem**: Deep thinking not working or unexpected behavior

**Solutions**:
- Verify the model supports deep thinking (check model capabilities)
- For toggle-support models, ensure `"thinking": {"type": "enabled"}` is set
- For DeepSeek-V3.1: Deep thinking is incompatible with Function Call - don't use both simultaneously
- For DeepSeek-V3.1: Deep thinking doesn't support prefix continuation
- In multi-turn conversations, don't include `reasoning_content` as input - only keep `role` and `content`

**Problem**: Deep thinking output is too long

**Solutions**:
- Some models support truncating the thinking chain
- Consider disabling deep thinking for simpler tasks

### 4.2 Function Call Issues

**Problem**: Model returns multiple function calls when only one was expected

**Solution**: This is due to ambiguous prompt or vague tool definition. Optimize the prompt and tool definition following best practices.

**Problem**: Cannot parse `tool_calls` after setting `max_tokens`

**Solution**: `max_tokens` may be too small, truncating the `tool_calls` output. Increase `max_tokens`.

**Problem**: Special label tokens in output when System Prompt sets output format

**Solution**: The System Prompt format may not follow the model's required format. Optimize the prompt.

### 4.3 Image Understanding Issues

**Problem**: Image not recognized correctly

**Solutions**:
- Ensure Base64 encoding is correct and MIME type matches image format
- Check image size is within limits (Base64 < 10MB)
- For text-heavy images with small fonts, the model may not accurately recognize text due to token compression
- For multi-image + text input, place text after images for better results

**Problem**: Image format not supported

**Solution**: Supported formats are: JPEG, PNG, GIF, WEBP. Convert the image to a supported format first.

### 4.4 Video Generation Issues

**Problem**: Video generation task not completing

**Solutions**:
- Video generation is asynchronous and takes time. Wait and query again.
- Task data is only retained for 24 hours. Save results promptly.
- Check task status through the query API.

**Problem**: Video generation task failed

**Solutions**:
- Verify input parameters (prompt, size, fps, duration)
- Check if the model is activated
- Ensure API Key has appropriate permissions

## 5. Network and Connection Issues

### 5.1 Connection Timeout

**Solutions**:
- Increase connection timeout in your HTTP client
- Check network connectivity to `api.modelarts-maas.com`
- Use retry mechanism with exponential backoff

### 5.2 SSL Certificate Issues

**Solutions**:
- Ensure your environment has the correct CA certificate bundle installed
- For Python with `requests`: Set `verify='/path/to/ca-bundle.crt'` if using a custom CA
- For production: Properly configure SSL certificates

## 6. Permission Issues

### 6.1 MaaS Console Access Restricted

**Symptoms**: "Access Restricted" dialog in MaaS console

**Solutions**:
- Sub-user: Contact administrator to configure missing permissions
- Follow the steps in `references/iam-policies.md` to add missing permissions
- Check if ModelArts delegation authorization is completed

### 6.2 Missing Dependency Service Authorization

**Symptoms**: Prompt at top of MaaS console about missing dependency service authorization

**Solutions**:
- Main user: Click the link to navigate to authorization page
- Sub-user: Contact administrator

## 7. Development Tool Integration Issues

### 7.1 OpenClaw Issues

**Problem**: "Gateway service disabled" after running `openclaw gateway restart`

**Solution**: Manually start the gateway service: `openclaw gateway`

### 7.2 Cursor Issues

**Problem**: Cannot verify API connectivity in Cursor

**Solutions**:
- Only check the MaaS model (uncheck other models)
- Ensure Base URL is correct (remove `/chat/completions` suffix)
- Verify API Key is correct and effective

### 7.3 API Key Not Effective Immediately

**Problem**: API Key doesn't work right after creation

**Solution**: MaaS API Key takes a few minutes to become effective after creation. Wait and try again.

## 8. Error Code Reference

| Error Code | HTTP Status | Description | Solution |
|------------|-------------|-------------|----------|
| ModelArts.81101 | 429 | Too Many Requests | Reduce request frequency, implement retry |
| - | 401 | Authentication failed | Check API Key |
| - | 403 | Permission denied | Check IAM permissions |
| - | 404 | Model not found | Check model parameter |
| - | 413 | Request too large | Reduce request body size |
| - | 429 | Rate limit exceeded | Wait and retry |
| - | 500 | Internal server error | Retry later |
| - | 503 | Service unavailable | Retry later, check service status |
