#!/bin/bash
# ============================================================
#  CCE AZ Power Outage Chaos Experiment — Environment Check
# ============================================================

echo "=============================================="
echo "  CCE AZ Power Outage Chaos Experiment — Environment Check"
echo "=============================================="

PASS=0
WARN=0
FAIL=0

# Helper: check if a kubectl binary actually works (not a truncated/corrupt file)
kubectl_works() {
    local bin="$1"
    [ -x "$bin" ] || return 1
    "$bin" version --client &>/dev/null
}

# Helper: remove broken kubectl binary that may shadow package-manager install
remove_broken_kubectl() {
    local broken_paths="/usr/local/bin/kubectl /root/bin/kubectl"
    for p in $broken_paths; do
        if [ -e "$p" ] && ! kubectl_works "$p"; then
            echo "  [!] Removing broken kubectl at $p ..."
            rm -f "$p" 2>/dev/null || true
        fi
    done
}

# Helper: install kubectl
# Priority: 1) CDN binary download (default v1.28.0, override with KUBECTL_VERSION)
#           2) dnf/yum kubernetes-client package (last resort, may be older)
install_kubectl() {
    # Clean up any broken/truncated binary from a previous failed download.
    # A corrupt /usr/local/bin/kubectl shadows /usr/bin/kubectl from dnf and
    # causes "Text file busy" or "too large section header offset" errors.
    remove_broken_kubectl

    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)  arch="amd64" ;;
        aarch64) arch="arm64" ;;
        *) echo "  [✗] Unsupported architecture: $arch"; return 1 ;;
    esac

    # Default kubectl version. Override with KUBECTL_VERSION to match the cluster.
    local version="${KUBECTL_VERSION:-v1.28.0}"

    # --- Strategy 1: CDN binary download (preferred) ---
    # Downloads the exact version that matches the CCE cluster, avoiding the
    # outdated distro package (e.g. v1.20 on openEuler 22.03) which falls far
    # outside kubectl's supported +/-1 minor version skew.
    local install_dir
    if [ -w /usr/local/bin ] 2>/dev/null; then
        install_dir="/usr/local/bin"
    else
        install_dir="/root/bin"
        mkdir -p "$install_dir"
    fi

    local mirrors=(
        "https://dl.k8s.io/release/${version}/bin/linux/${arch}/kubectl"
        "https://mirrors.aliyun.com/kubernetes-release/release/${version}/bin/linux/${arch}/kubectl"
        "https://mirrors.huaweicloud.com/kubernetes-release/release/${version}/bin/linux/${arch}/kubectl"
    )

    local tmpfile
    tmpfile=$(mktemp /tmp/kubectl_download.XXXXXX) || return 1

    local downloaded=false
    for url in "${mirrors[@]}"; do
        echo "  Downloading kubectl ${version} for linux/${arch} from $url ..."
        if curl -fsSL --max-time 120 "$url" -o "$tmpfile" 2>/dev/null; then
            downloaded=true
            break
        fi
        echo "  [!] Download from $url failed, trying next mirror ..."
    done

    if [ "$downloaded" = false ]; then
        echo "  [!] Failed to download kubectl ${version} from all mirrors, falling back to package manager ..."
        rm -f "$tmpfile"
    else
        # Wait briefly to ensure file handle is fully released
        sleep 1

        # Move to target and set permissions
        if ! mv "$tmpfile" "${install_dir}/kubectl" 2>/dev/null; then
            rm -f "$tmpfile"
        else
            chmod 755 "${install_dir}/kubectl" 2>/dev/null || python3 -c "import os; os.chmod('${install_dir}/kubectl', 0o755)"

            # Verify the binary works
            if kubectl_works "${install_dir}/kubectl"; then
                echo "  [✓] kubectl installed from CDN: $(${install_dir}/kubectl version --client 2>/dev/null | head -1)"
                # Add to PATH if not already there
                case ":$PATH:" in
                    *":${install_dir}:"*) ;;
                    *) export PATH="${install_dir}:$PATH" ;;
                esac
                return 0
            else
                echo "  [✗] kubectl binary downloaded but failed to execute"
                rm -f "${install_dir}/kubectl"
            fi
        fi
    fi

    # --- Strategy 2: dnf/yum kubernetes-client package (fallback) ---
    # May install an older version (e.g. v1.20 on openEuler). Works when the
    # CDN is unreachable; check the resulting version against the cluster.
    if command -v dnf &>/dev/null || command -v yum &>/dev/null; then
        local pm
        pm=$(command -v dnf 2>/dev/null || command -v yum 2>/dev/null)
        echo "  [!] Falling back to $pm install -y kubernetes-client ..."
        if timeout 300 $pm install -y kubernetes-client || timeout 300 $pm reinstall -y kubernetes-client; then
            if kubectl_works /usr/bin/kubectl; then
                echo "  [✓] kubectl installed via $pm: $(/usr/bin/kubectl version --client 2>/dev/null | head -1)"
                echo "  [⚠] Package version may be older than the cluster. Prefer CDN install with KUBECTL_VERSION matching the cluster K8s version."
                return 0
            fi
        fi
        echo "  [✗] $pm install failed or kubectl still not working"
    fi
    return 1
}

# [1/6] Python3
echo "[1/6] Checking Python3 ..."
if command -v python3 &>/dev/null; then
    echo "  [✓] Python3 found: $(python3 --version)"
    PASS=$((PASS + 1))
else
    echo "  [✗] Python3 not found"
    FAIL=$((FAIL + 1))
fi

# [2/6] hcloud CLI
echo "[2/6] Checking hcloud CLI ..."
if command -v hcloud &>/dev/null; then
    echo "  [✓] hcloud CLI found"
    PASS=$((PASS + 1))
else
    echo "  [✗] hcloud CLI not found"
    FAIL=$((FAIL + 1))
fi

# [3/6] kubectl (auto-install if missing)
echo "[3/6] Checking kubectl ..."
if command -v kubectl &>/dev/null && kubectl_works "$(command -v kubectl)"; then
    echo "  [✓] kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null | head -1)"
    PASS=$((PASS + 1))
else
    echo "  [!] kubectl not found or broken. Attempting auto-install ..."
    if install_kubectl; then
        PASS=$((PASS + 1))
    else
        echo "  [!] kubectl auto-install failed. CCE node/pod discovery will be unavailable."
        echo "      Manual install options:"
        echo "        dnf install -y kubernetes-client    (openEuler, preferred)"
        echo "        curl -fsSL 'https://dl.k8s.io/release/v1.28.0/bin/linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')/kubectl' -o /tmp/kubectl && sleep 1 && mv /tmp/kubectl /usr/local/bin/kubectl && chmod 755 /usr/local/bin/kubectl"
        WARN=$((WARN + 1))
    fi
fi

# [4/6] Credentials
echo "[4/6] Checking credentials ..."
if [ -n "$HW_ACCESS_KEY" ]; then
    echo "  [✓] HW_ACCESS_KEY is set"
    PASS=$((PASS + 1))
else
    echo "  [✗] HW_ACCESS_KEY is not set"
    FAIL=$((FAIL + 1))
fi

if [ -n "$HW_SECRET_KEY" ]; then
    echo "  [✓] HW_SECRET_KEY is set"
    PASS=$((PASS + 1))
else
    echo "  [✗] HW_SECRET_KEY is not set"
    FAIL=$((FAIL + 1))
fi

# [5/6] Region
echo "[5/6] Checking region ..."
if [ -n "$HW_REGION_NAME" ]; then
    echo "  [✓] HW_REGION_NAME is set: $HW_REGION_NAME"
    PASS=$((PASS + 1))
else
    echo "  [!] HW_REGION_NAME not set. Ask the user which region to use — do NOT silently default."
    WARN=$((WARN + 1))
fi

# [6/6] Optional tools
echo "[6/6] Checking optional tools ..."
if command -v jq &>/dev/null; then
    echo "  [✓] jq found (for JSON processing)"
    PASS=$((PASS + 1))
else
    echo "  [!] jq not found (optional, for JSON processing)"
    WARN=$((WARN + 1))
fi

echo ""
echo "=============================================="
echo "  Summary: $PASS passed, $WARN warnings, $FAIL failed"
echo "=============================================="

if [ $FAIL -gt 0 ]; then
    echo "  Environment check FAILED."
    exit 1
else
    echo "  Environment check PASSED."
    exit 0
fi
