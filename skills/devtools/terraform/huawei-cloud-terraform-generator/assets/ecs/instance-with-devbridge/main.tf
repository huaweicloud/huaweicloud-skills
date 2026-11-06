# DevBridge SSH Tunnel Auto-Setup ECS Template
#
# Mode: B1 (FunctionGraph proxy) — the ONLY supported mode.
#   Zero credentials in user_data; requires FunctionGraph + IAM agency permissions.
#   The previous Fallback mode (DevBridge API Key directly in user_data) has been REMOVED
#   by security mandate. If B1 preconditions are not met, do NOT auto-install; direct the
#   user to the one-click install guide: https://gitcode.com/anruostyle/devbridge-ssh-setup/blob/main/安装指导.md
#
# Architecture:
#   Sandbox (before apply) -> create/reuse a DevBridge API Key via DevStage API (user-level AK/SK)
#   Terraform apply        -> writes that key into the FunctionGraph function's user_data (EXISTING_API_KEY)
#   ECS (at boot)          -> metadata service (agency STS) -> invoke FunctionGraph -> receive the pre-created key
#
# Security:
#   user_data contains NO credentials; function user_data contains ONLY the revocable
#   DevBridge API Key (no AK/SK). No AK/SK in any Terraform artifact.
#   Zero inbound security group rules, SSH/RDP via DevBridge tunnel only.
#
# Cost: 0 for FunctionGraph (free tier: 1M invocations/month)
#
# After creation, connect via: devbridge connect <tunnel-id> -> ssh root@localhost

# ================================================================
# Data Sources
# ================================================================
data "huaweicloud_availability_zones" "test" {
  region = var.region_name
}

data "huaweicloud_compute_flavors" "test" {
  availability_zone = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
  performance_type  = var.instance_flavor_performance_type
  cpu_core_count    = var.instance_flavor_cpu_core_count
  memory_size       = var.instance_flavor_memory_size
}

data "huaweicloud_images_image" "test" {
  name_regex   = var.instance_image_name != "" ? var.instance_image_name : null
  image_id     = var.instance_image_id != "" ? var.instance_image_id : null
  visibility   = var.instance_image_id != "" ? null : "public"
  architecture = var.instance_image_id != "" ? null : "x86"
  most_recent  = true
}

data "huaweicloud_identity_projects" "current" {
  name = var.region_name
}

# ================================================================
# Random suffix: unique per deployment, avoids resource-name
# collisions (FunctionGraph function, IAM role, IAM agency) when the
# template is reused multiple times in the same account.
# ================================================================
resource "random_id" "suffix" {
  byte_length = 4
}

# ================================================================
# FunctionGraph Function: DevBridge API Key Creator
# ================================================================
# NOTE: FunctionGraph inline mode expects base64 of the Python file directly,
# NOT base64 of a zip file. Using filebase64() on the .py file directly.
resource "huaweicloud_fgs_function" "key_creator" {
  name          = local.function_name
  app           = "default"
  runtime       = "Python3.9"
  handler       = "index.handler"
  code_type     = "inline"
  func_code     = filebase64("${path.module}/function_code.py")
  code_filename = "index.py"
  timeout       = 30
  memory_size   = 128

  # user_data: JSON string passed to function, accessible via context.getUserData(key)
  # Only the pre-created DevBridge API Key is passed (NO AK/SK) — the key is created
  # in the sandbox before apply, not by this function (see ecs-devbridge-option.md Step 0).
  user_data = jsonencode({
    EXISTING_API_KEY = var.devbridge_api_key != null ? var.devbridge_api_key : ""
  })
}

# ================================================================
# IAM: Custom role for ECS to invoke the FunctionGraph function
# ================================================================
resource "huaweicloud_identity_role" "invoke_function" {
  count       = var.use_custom_role ? 1 : 0
  name        = "InvokeDevbridgeFn-${local.suffix}"
  description = "Allow ECS to invoke the DevBridge key creator FunctionGraph function"
  type        = "AX"

  policy = jsonencode({
    Version = "1.1"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["functiongraph:invokeFunction"]
        Resource = ["*"]
      }
    ]
  })
}

# ================================================================
# IAM Agency: ECS uses this to get STS credentials from metadata service
# ================================================================
resource "huaweicloud_identity_agency" "ecs_devbridge" {
  name                   = "ecs-devbridge-fg-${local.suffix}"
  description            = "Allow ECS to invoke FunctionGraph for DevBridge API Key creation"
  delegated_service_name = var.agency_delegated_service_name

  project_role {
    project = var.region_name
    roles   = var.use_custom_role ? [huaweicloud_identity_role.invoke_function[0].name] : [var.predefined_role_name]
  }
}

# ================================================================
# OS type detection and user_data generation
# ================================================================
locals {
  suffix      = random_id.suffix.hex
  is_windows  = can(regex("(?i)windows", data.huaweicloud_images_image.test.os))
  tunnel_port = local.is_windows ? 3389 : 22

  function_name = "devbridge-key-creator-${local.suffix}"
  function_urn  = "urn:fss:${var.region_name}:${data.huaweicloud_identity_projects.current.projects[0].id}:function:default:${local.function_name}:latest"

  # --- Linux user_data ---
  linux_user_data = <<-EOT
#!/bin/bash
# === DevBridge SSH Tunnel Auto-Setup (Linux, B1: FunctionGraph proxy) ===
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required" >&2; exit 1
fi

export FG_REGION="${var.region_name}"
export FG_PROJECT_ID="${data.huaweicloud_identity_projects.current.projects[0].id}"
export FG_FUNCTION_URN="${local.function_urn}"

export HW_API_KEY=$(python3 << 'PYEOF'
import hashlib, hmac, datetime, json, urllib.request, urllib.parse, sys, os, time

region = os.environ['FG_REGION']
project_id = os.environ['FG_PROJECT_ID']
function_urn = os.environ['FG_FUNCTION_URN']

host = f'functiongraph.{region}.myhuaweicloud.com'
method = 'POST'
path = f'/v2/{project_id}/fgs/functions/{function_urn}/invocations'
# URL-encode path + add trailing slash for signing (matches server canonical)
encoded_path = urllib.parse.quote(path + '/', safe='/')

body = b'{}'


def fetch_sts():
    meta = json.loads(urllib.request.urlopen(
        'http://169.254.169.254/openstack/latest/securitykey', timeout=10
    ).read())
    return meta['credential']


def invoke_fg(cred):
    sts_ak = cred['access']
    sts_sk = cred['secret']
    sts_token = cred['securitytoken']

    t = datetime.datetime.utcnow()
    sdk_date = t.strftime('%Y%m%dT%H%M%SZ')
    hashed_payload = hashlib.sha256(body).hexdigest()
    canonical_headers = 'content-type:application/json\n' + 'host:' + host + '\n' + 'x-sdk-date:' + sdk_date + '\n' + 'x-security-token:' + sts_token + '\n'
    signed_headers = 'content-type;host;x-sdk-date;x-security-token'
    canonical_request = method + '\n' + encoded_path + '\n' + '' + '\n' + canonical_headers + '\n' + signed_headers + '\n' + hashed_payload
    hashed_canonical = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    string_to_sign = 'SDK-HMAC-SHA256' + '\n' + sdk_date + '\n' + hashed_canonical
    signature = hmac.new(sts_sk.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    auth = 'SDK-HMAC-SHA256 Access=' + sts_ak + ', SignedHeaders=' + signed_headers + ', Signature=' + signature

    url = 'https://' + host + path
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Authorization': auth,
        'X-Sdk-Date': sdk_date,
        'Content-Type': 'application/json',
        'X-Security-Token': sts_token,
    })
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


# Retry STS fetch: the IAM agency STS credentials may not be ready immediately
# after the ECS boots (observed failure ~2min after boot). Retry with backoff.
cred = None
for attempt in range(3):
    try:
        cred = fetch_sts()
        break
    except Exception as e:
        if attempt == 2:
            print(f'ERROR: Failed to get STS from metadata service after 3 attempts: {e}', file=sys.stderr)
            sys.exit(1)
        time.sleep(10)

# Retry FunctionGraph invocation: transient network errors should not abort the
# whole DevBridge setup. Retry with backoff.
for attempt in range(3):
    try:
        resp = invoke_fg(cred)
        if isinstance(resp, dict) and 'api_key' in resp:
            print(resp['api_key'])
            break
        elif isinstance(resp, dict) and 'error' in resp:
            print(f'ERROR: Function returned error: {resp["error"]}', file=sys.stderr)
            sys.exit(1)
        else:
            print(f'ERROR: Unexpected response: {resp}', file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        if attempt == 2:
            print(f'ERROR: Failed to invoke function after 3 attempts: {e}', file=sys.stderr)
            sys.exit(1)
        time.sleep(5)
PYEOF
)

export HOME="$${HOME:-/root}"
DEVBRIDGE_SETUP_URL="https://raw.gitcode.com/anruostyle/devbridge-ssh-setup/raw/3fba517b905d0c16851c90af0787af08a35fc668/setup-devbridge-ssh.sh"
DEVBRIDGE_SETUP_SHA256="d969e41f47e84a1e7e666712432a7cc46bd8d66a493f757f6e72d77b67c48896"
curl -fsSL --http1.1 "$DEVBRIDGE_SETUP_URL" -o /tmp/setup-devbridge-ssh.sh
echo "$DEVBRIDGE_SETUP_SHA256  /tmp/setup-devbridge-ssh.sh" | sha256sum -c - >/dev/null 2>&1 || { echo "devbridge setup script SHA256 mismatch" >&2; exit 1; }
bash /tmp/setup-devbridge-ssh.sh
rm -f /tmp/setup-devbridge-ssh.sh

history -c 2>/dev/null || true
rm -f /root/.bash_history 2>/dev/null || true
unset HW_API_KEY FG_REGION FG_PROJECT_ID FG_FUNCTION_URN
EOT


  # --- Windows user_data ---
  windows_user_data = <<-EOT
#ps1_sysnative
# === DevBridge RDP Tunnel Auto-Setup (Windows, B1: FunctionGraph proxy) ===
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$fgRegion = "${var.region_name}"
$fgProjectId = "${data.huaweicloud_identity_projects.current.projects[0].id}"
$fgFunctionUrn = "${local.function_urn}"
$apiKey = $null

# --- Method 1: Try hcloud CLI (CodeArts image likely has it) ---
$hcloud = $null
foreach ($cmd in @("hcloud", "C:\Program Files\CodeArts\cli\bin\hcloud.exe", "C:\huaweicloud-cli\hcloud.exe")) {
    try { & $cmd --version 2>&1 | Out-Null; $hcloud = $cmd; break } catch {}
}

if ($hcloud) {
    Write-Output "Using hcloud: $hcloud"
    try {
        $resp = & $hcloud FunctionGraph InvokeFunction --cli-region=$fgRegion --project_id=$fgProjectId --function_urn=$fgFunctionUrn --'{}'="" 2>&1
        $json = $resp | ConvertFrom-Json
        if ($json.api_key) { $apiKey = $json.api_key }
    } catch { Write-Output "hcloud invoke failed: $_" }
}

# --- Method 2: Try Python (if hcloud not found or failed) ---
if (-not $apiKey) {
    Write-Output "Trying Python approach..."
    $python = $null
    foreach ($cmd in @("python", "python3", "C:\Python311\python.exe", "C:\Python39\python.exe", "C:\Python38\python.exe")) {
        try { $ver = & $cmd --version 2>&1; if ($ver -match "Python 3") { $python = $cmd; break } } catch {}
    }
    
    if (-not $python) {
        Write-Output "Python not found, downloading embedded Python 3.11..."
        $pyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        $pyZip = "$env:TEMP\py-embed.zip"
        $pyDir = "$env:TEMP\py-embed"
        try {
            Invoke-WebRequest -Uri $pyUrl -OutFile $pyZip -UseBasicParsing -TimeoutSec 60
            if (Test-Path $pyDir) { Remove-Item $pyDir -Recurse -Force }
            Expand-Archive -Path $pyZip -DestinationPath $pyDir -Force
            $pthFile = Get-ChildItem "$pyDir\*._pth" | Select-Object -First 1
            if ($pthFile) {
                $pthContent = Get-Content $pthFile.FullName
                $pthContent = $pthContent -replace "^#import site", "import site"
                Set-Content $pthFile.FullName $pthContent
            }
            $python = "$pyDir\python.exe"
        } catch { Write-Output "Python download failed: $_" }
    }
    
    if ($python) {
        Write-Output "Using Python: $python"
        $env:FG_REGION = $fgRegion
        $env:FG_PROJECT_ID = $fgProjectId
        $env:FG_FUNCTION_URN = $fgFunctionUrn
        $pyB64 = "aW1wb3J0IGhhc2hsaWIsIGhtYWMsIGRhdGV0aW1lLCBqc29uLCB1cmxsaWIucmVxdWVzdCwgdXJsbGliLnBhcnNlLCBzeXMsIG9zLCB0aW1lCgpyZWdpb24gPSBvcy5lbnZpcm9uWydGR19SRUdJT04nXQpwcm9qZWN0X2lkID0gb3MuZW52aXJvblsnRkdfUFJPSkVDVF9JRCddCmZ1bmN0aW9uX3VybiA9IG9zLmVudmlyb25bJ0ZHX0ZVTkNUSU9OX1VSTiddCgpob3N0ID0gZidmdW5jdGlvbmdyYXBoLntyZWdpb259Lm15aHVhd2VpY2xvdWQuY29tJwptZXRob2QgPSAnUE9TVCcKcGF0aCA9IGYnL3YyL3twcm9qZWN0X2lkfS9mZ3MvZnVuY3Rpb25zL3tmdW5jdGlvbl91cm59L2ludm9jYXRpb25zJwojIFVSTC1lbmNvZGUgcGF0aCArIGFkZCB0cmFpbGluZyBzbGFzaCBmb3Igc2lnbmluZyAobWF0Y2hlcyBzZXJ2ZXIgY2Fub25pY2FsKQplbmNvZGVkX3BhdGggPSB1cmxsaWIucGFyc2UucXVvdGUocGF0aCArICcvJywgc2FmZT0nLycpCgpib2R5ID0gYid7fScKCgpkZWYgZmV0Y2hfc3RzKCk6CiAgICBtZXRhID0ganNvbi5sb2Fkcyh1cmxsaWIucmVxdWVzdC51cmxvcGVuKAogICAgICAgICdodHRwOi8vMTY5LjI1NC4xNjkuMjU0L29wZW5zdGFjay9sYXRlc3Qvc2VjdXJpdHlrZXknLCB0aW1lb3V0PTEwCiAgICApLnJlYWQoKSkKICAgIHJldHVybiBtZXRhWydjcmVkZW50aWFsJ10KCgpkZWYgaW52b2tlX2ZnKGNyZWQpOgogICAgc3RzX2FrID0gY3JlZFsnYWNjZXNzJ10KICAgIHN0c19zayA9IGNyZWRbJ3NlY3JldCddCiAgICBzdHNfdG9rZW4gPSBjcmVkWydzZWN1cml0eXRva2VuJ10KCiAgICB0ID0gZGF0ZXRpbWUuZGF0ZXRpbWUudXRjbm93KCkKICAgIHNka19kYXRlID0gdC5zdHJmdGltZSgnJVklbSVkVCVIJU0lU1onKQogICAgaGFzaGVkX3BheWxvYWQgPSBoYXNobGliLnNoYTI1Nihib2R5KS5oZXhkaWdlc3QoKQogICAgY2Fub25pY2FsX2hlYWRlcnMgPSAnY29udGVudC10eXBlOmFwcGxpY2F0aW9uL2pzb25cbicgKyAnaG9zdDonICsgaG9zdCArICdcbicgKyAneC1zZGstZGF0ZTonICsgc2RrX2RhdGUgKyAnXG4nICsgJ3gtc2VjdXJpdHktdG9rZW46JyArIHN0c190b2tlbiArICdcbicKICAgIHNpZ25lZF9oZWFkZXJzID0gJ2NvbnRlbnQtdHlwZTtob3N0O3gtc2RrLWRhdGU7eC1zZWN1cml0eS10b2tlbicKICAgIGNhbm9uaWNhbF9yZXF1ZXN0ID0gbWV0aG9kICsgJ1xuJyArIGVuY29kZWRfcGF0aCArICdcbicgKyAnJyArICdcbicgKyBjYW5vbmljYWxfaGVhZGVycyArICdcbicgKyBzaWduZWRfaGVhZGVycyArICdcbicgKyBoYXNoZWRfcGF5bG9hZAogICAgaGFzaGVkX2Nhbm9uaWNhbCA9IGhhc2hsaWIuc2hhMjU2KGNhbm9uaWNhbF9yZXF1ZXN0LmVuY29kZSgndXRmLTgnKSkuaGV4ZGlnZXN0KCkKICAgIHN0cmluZ190b19zaWduID0gJ1NESy1ITUFDLVNIQTI1NicgKyAnXG4nICsgc2RrX2RhdGUgKyAnXG4nICsgaGFzaGVkX2Nhbm9uaWNhbAogICAgc2lnbmF0dXJlID0gaG1hYy5uZXcoc3RzX3NrLmVuY29kZSgndXRmLTgnKSwgc3RyaW5nX3RvX3NpZ24uZW5jb2RlKCd1dGYtOCcpLCBoYXNobGliLnNoYTI1NikuaGV4ZGlnZXN0KCkKICAgIGF1dGggPSAnU0RLLUhNQUMtU0hBMjU2IEFjY2Vzcz0nICsgc3RzX2FrICsgJywgU2lnbmVkSGVhZGVycz0nICsgc2lnbmVkX2hlYWRlcnMgKyAnLCBTaWduYXR1cmU9JyArIHNpZ25hdHVyZQoKICAgIHVybCA9ICdodHRwczovLycgKyBob3N0ICsgcGF0aAogICAgcmVxID0gdXJsbGliLnJlcXVlc3QuUmVxdWVzdCh1cmwsIGRhdGE9Ym9keSwgbWV0aG9kPSdQT1NUJywgaGVhZGVycz17CiAgICAgICAgJ0F1dGhvcml6YXRpb24nOiBhdXRoLAogICAgICAgICdYLVNkay1EYXRlJzogc2RrX2RhdGUsCiAgICAgICAgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJywKICAgICAgICAnWC1TZWN1cml0eS1Ub2tlbic6IHN0c190b2tlbiwKICAgIH0pCiAgICByZXR1cm4ganNvbi5sb2Fkcyh1cmxsaWIucmVxdWVzdC51cmxvcGVuKHJlcSwgdGltZW91dD0zMCkucmVhZCgpKQoKCiMgUmV0cnkgU1RTIGZldGNoOiB0aGUgSUFNIGFnZW5jeSBTVFMgY3JlZGVudGlhbHMgbWF5IG5vdCBiZSByZWFkeSBpbW1lZGlhdGVseQojIGFmdGVyIHRoZSBFQ1MgYm9vdHMgKG9ic2VydmVkIGZhaWx1cmUgfjJtaW4gYWZ0ZXIgYm9vdCkuIFJldHJ5IHdpdGggYmFja29mZi4KY3JlZCA9IE5vbmUKZm9yIGF0dGVtcHQgaW4gcmFuZ2UoMyk6CiAgICB0cnk6CiAgICAgICAgY3JlZCA9IGZldGNoX3N0cygpCiAgICAgICAgYnJlYWsKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBpZiBhdHRlbXB0ID09IDI6CiAgICAgICAgICAgIHByaW50KGYnRVJST1I6IEZhaWxlZCB0byBnZXQgU1RTIGZyb20gbWV0YWRhdGEgc2VydmljZSBhZnRlciAzIGF0dGVtcHRzOiB7ZX0nLCBmaWxlPXN5cy5zdGRlcnIpCiAgICAgICAgICAgIHN5cy5leGl0KDEpCiAgICAgICAgdGltZS5zbGVlcCgxMCkKCiMgUmV0cnkgRnVuY3Rpb25HcmFwaCBpbnZvY2F0aW9uOiB0cmFuc2llbnQgbmV0d29yayBlcnJvcnMgc2hvdWxkIG5vdCBhYm9ydCB0aGUKIyB3aG9sZSBEZXZCcmlkZ2Ugc2V0dXAuIFJldHJ5IHdpdGggYmFja29mZi4KZm9yIGF0dGVtcHQgaW4gcmFuZ2UoMyk6CiAgICB0cnk6CiAgICAgICAgcmVzcCA9IGludm9rZV9mZyhjcmVkKQogICAgICAgIGlmIGlzaW5zdGFuY2UocmVzcCwgZGljdCkgYW5kICdhcGlfa2V5JyBpbiByZXNwOgogICAgICAgICAgICBwcmludChyZXNwWydhcGlfa2V5J10pCiAgICAgICAgICAgIGJyZWFrCiAgICAgICAgZWxpZiBpc2luc3RhbmNlKHJlc3AsIGRpY3QpIGFuZCAnZXJyb3InIGluIHJlc3A6CiAgICAgICAgICAgIHByaW50KGYnRVJST1I6IEZ1bmN0aW9uIHJldHVybmVkIGVycm9yOiB7cmVzcFsiZXJyb3IiXX0nLCBmaWxlPXN5cy5zdGRlcnIpCiAgICAgICAgICAgIHN5cy5leGl0KDEpCiAgICAgICAgZWxzZToKICAgICAgICAgICAgcHJpbnQoZidFUlJPUjogVW5leHBlY3RlZCByZXNwb25zZToge3Jlc3B9JywgZmlsZT1zeXMuc3RkZXJyKQogICAgICAgICAgICBzeXMuZXhpdCgxKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIGlmIGF0dGVtcHQgPT0gMjoKICAgICAgICAgICAgcHJpbnQoZidFUlJPUjogRmFpbGVkIHRvIGludm9rZSBmdW5jdGlvbiBhZnRlciAzIGF0dGVtcHRzOiB7ZX0nLCBmaWxlPXN5cy5zdGRlcnIpCiAgICAgICAgICAgIHN5cy5leGl0KDEpCiAgICAgICAgdGltZS5zbGVlcCg1KQ=="
        $pyBytes = [System.Convert]::FromBase64String($pyB64)
        $pyScript = [System.Text.Encoding]::UTF8.GetString($pyBytes)
        $pyFile = "$env:TEMP\fg_invoke.py"
        [System.IO.File]::WriteAllText($pyFile, $pyScript, [System.Text.Encoding]::UTF8)
        try {
            $result = & $python $pyFile 2>$null
            if ($result -match "^devbridge_") { $apiKey = $result }
        } catch { Write-Output "Python invoke failed: $_" }
        Remove-Item $pyFile -Force -ErrorAction SilentlyContinue
    }
}

# --- Check result ---
if ($apiKey -match "^devbridge_") {
    $env:HW_API_KEY = $apiKey
    Write-Output "DevBridge API Key obtained"
} else {
    Write-Output "ERROR: Failed to get API Key via B1, all methods failed"
    exit 1
}

# --- Run DevBridge Windows setup ---
$scriptUrl = "https://raw.gitcode.com/anruostyle/devbridge-ssh-setup/raw/3fba517b905d0c16851c90af0787af08a35fc668/setup-devbridge-ssh-windows.txt"
$scriptPath = "$env:TEMP\setup-devbridge-ssh-windows.ps1"
$scriptContent = (Invoke-WebRequest -Uri $scriptUrl -UseBasicParsing).Content
$scriptSha256 = "f3ebde48fc11c1032f82496e8e0985e690004f6c02c5ad28021fc457dc4891ef"
$hash = [System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($scriptContent))).Replace("-","").ToLower()
if ($hash -ne $scriptSha256) { Write-Output "devbridge setup script SHA256 mismatch"; exit 1 }
$scriptContent = $scriptContent -replace "`r?`n", "`r`n"
$scriptContent = $scriptContent -replace 'Read-Host \| Out-Null', 'Write-Output ""'
[System.IO.File]::WriteAllText($scriptPath, $scriptContent, [System.Text.Encoding]::UTF8)
& $scriptPath
Remove-Item -Path $scriptPath -Force -ErrorAction SilentlyContinue
$env:HW_API_KEY = $null
$env:FG_REGION = $null
$env:FG_PROJECT_ID = $null
$env:FG_FUNCTION_URN = $null
Clear-History -ErrorAction SilentlyContinue
EOT

}

# --- Network ---
resource "huaweicloud_vpc" "test" {
  name = var.vpc_name
  cidr = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "test" {
  vpc_id     = huaweicloud_vpc.test.id
  name       = var.subnet_name
  cidr       = var.subnet_cidr == "" ? cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0) : var.subnet_cidr
  gateway_ip = var.subnet_gateway_ip == "" ? cidrhost(cidrsubnet(huaweicloud_vpc.test.cidr, 8, 0), 1) : var.subnet_gateway_ip
}

# --- Security Group: ZERO inbound rules, restricted egress ---
resource "huaweicloud_networking_secgroup" "test" {
  name                 = var.security_group_name
  delete_default_rules = true
}

resource "huaweicloud_networking_secgroup_rule" "egress_tcp443" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "egress_tcp80" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "egress_udp53" {
  security_group_id = huaweicloud_networking_secgroup.test.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = 53
  port_range_max    = 53
  remote_ip_prefix  = "0.0.0.0/0"
}

# --- Key Pair ---
resource "huaweicloud_kps_keypair" "test" {
  name       = var.keypair_name
  public_key = var.keypair_public_key
}

# --- EIP for outbound access ---
resource "huaweicloud_vpc_eip" "test" {
  publicip {
    type = var.eip_type
  }
  bandwidth {
    name        = var.bandwidth_name
    size        = var.bandwidth_size
    share_type  = var.bandwidth_share_type
    charge_mode = var.bandwidth_charge_mode
  }
}

# --- ECS Instance ---
resource "huaweicloud_compute_instance" "test" {
  name               = var.instance_name
  image_id           = data.huaweicloud_images_image.test.image_id
  flavor_id          = var.instance_flavor_id == "" ? try(data.huaweicloud_compute_flavors.test.flavors[0].id, "") : var.instance_flavor_id
  security_group_ids = [huaweicloud_networking_secgroup.test.id]
  availability_zone  = var.availability_zone == "" ? try(data.huaweicloud_availability_zones.test.names[0], null) : var.availability_zone
  key_pair           = huaweicloud_kps_keypair.test.name
  admin_pass         = local.is_windows ? var.admin_pass : null

  # IAM agency: ECS gets STS from metadata service to invoke FunctionGraph
  agency_name = huaweicloud_identity_agency.ecs_devbridge.name

  network {
    uuid = huaweicloud_vpc_subnet.test.id
  }

  user_data = local.is_windows ? local.windows_user_data : local.linux_user_data

  lifecycle {
    ignore_changes = [image_id, flavor_id, availability_zone]
  }
}

# --- Associate EIP to ECS ---
resource "huaweicloud_compute_eip_associate" "test" {
  instance_id = huaweicloud_compute_instance.test.id
  public_ip   = huaweicloud_vpc_eip.test.address
}
