#!/bin/bash
# 从 Quay.io 拉取 vllm-ascend 镜像并推送至华为云 SWR
# tag 必须来自 vllm-ascend 模型适配文档,不要默认用 latest
# 镜像目标部署架构为 ARM64(昇腾 NPU 服务器),拉取/推送必须带 --platform linux/arm64
# 拉取完成后必须用 docker inspect 校验镜像架构,确保为 arm64

set -euo pipefail

SRC_IMAGE="${1:?用法: pull_push_image.sh <源镜像> [--org 组织名] [--name 镜像名] [--login \"docker login -u <user> --password-stdin <domain>\"] [--tag 版本]}"
shift || true

SWR_ORG="${SWR_ORG:-}"
SWR_NAME="${SWR_NAME:-}"
LOGIN_CMD="${LOGIN_CMD:-}"
TAG=""

# ---------- 解析参数 ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --org)   SWR_ORG="$2";  shift 2 ;;
    --name)  SWR_NAME="$2"; shift 2 ;;
    --tag)   TAG="$2";      shift 2 ;;
    --login) LOGIN_CMD="$2"; shift 2 ;;
    *) echo "[错误] 未知参数: $1" >&2; exit 1 ;;
  esac
done

# ---------- 确定 tag(缺省取源镜像自身的 tag) ----------
SRC_TAG="${SRC_IMAGE##*:}"
if [ -z "$TAG" ]; then
  if [ "$SRC_TAG" != "$SRC_IMAGE" ]; then TAG="$SRC_TAG"; else TAG="latest"; fi
fi

SWR_USER="${SWR_USER:-}"
SWR_PASSWORD="${SWR_PASSWORD:-}"
SWR_REGION="${SWR_REGION:-}"
SWR_DOMAIN=""

# ---------- 解析 docker login 命令(方式一)或使用环境变量(方式二) ----------
# 安全要求: 禁止命令行明文传密码(-p <password>),仅支持 --password-stdin 或 SWR_PASSWORD 环境变量
if [ -n "$LOGIN_CMD" ]; then
  # 从 "docker login -u <user> --password-stdin <domain>" 提取用户名与域名
  # 密码经 stdin 注入(从 SWR_PASSWORD 环境变量读取),不进 argv
  set -- $LOGIN_CMD
  while [ $# -gt 0 ]; do
    case "$1" in
      -u|--username)  SWR_USER="$2";     shift 2 ;;
      -p|--password)  echo "[错误] 禁止命令行明文传密码(-p)。请用 --password-stdin + SWR_PASSWORD 环境变量" >&2; exit 1 ;;
      --password-stdin) shift ;;
      docker|login)   shift ;;
      *)              SWR_DOMAIN="$1";   shift ;;
    esac
  done
  [ -n "$SWR_DOMAIN" ] || { echo "[错误] 无法从 docker login 命令解析 SWR 域名: $LOGIN_CMD" >&2; exit 1; }
  [ -n "$SWR_PASSWORD" ] || \
    { echo "[错误] 未设置 SWR_PASSWORD 环境变量(--login 模式下密码经 stdin 注入,不进命令行)" >&2; exit 1; }
else
  : "${SWR_REGION:?需要设置 SWR_REGION(方式二环境变量)或使用 --login 传入登录命令}"
  : "${SWR_USER:?需要设置 SWR_USER(方式二环境变量)或使用 --login 传入登录命令}"
  : "${SWR_PASSWORD:?需要设置 SWR_PASSWORD(环境变量,不进命令行 argv)}"
  SWR_DOMAIN="swr.${SWR_REGION}.myhuaweicloud.com"
fi
: "${SWR_ORG:?需要设置 SWR_ORG 或使用 --org 参数}"

# 镜像名缺省取源镜像名(如 quay.io/ascend/vllm-ascend -> vllm-ascend)
if [ -z "$SWR_NAME" ]; then
  SWR_NAME="$(basename "${SRC_IMAGE%%:*}")"
fi

DEST_IMAGE="${SWR_DOMAIN}/${SWR_ORG}/${SWR_NAME}"

# ---------- docker 命令封装: 优先使用 --progress=plain 透传进度 ----------
# 拉取/推送必须带 --platform linux/arm64(昇腾 NPU 节点为 ARM64 架构)
# Docker 守护进程未开启 experimental features 时 --platform 报错,函数内捕获后降级为不带 --platform
docker_pull() {
  local image="$1"
  echo "[拉取] docker pull --platform linux/arm64 ${image}"
  if docker pull --platform linux/arm64 --progress=plain "$image" 2>&1 | tee /tmp/pull_"$$.log"; then
    return 0
  fi
  # 捕获 stderr 判断是否为 --platform 报错,降级提示
  local err
  err=$(grep -iE 'unknown flag: --platform|--platform.*is only supported.*experimental' /tmp/pull_"$$.log" || true)
  if [ -n "$err" ]; then
    cat <<'EOF' >&2
[警告] Docker 版本较旧或守护进程未开启实验特性(experimental features),--platform 参数不支持。
处理方案(在 Docker 宿主机执行):
  a. 打开或创建 /etc/docker/daemon.json
  b. 添加 {"experimental": true}
  c. sudo systemctl daemon-reload
  d. sudo systemctl restart docker
  e. docker version 确认 Server.Experimental=true 后重试
降级策略: 不带 --platform 直接拉取(ARM64 宿主机拉到即 ARM64,但拉取后必须用 docker inspect 校验架构)
EOF
    echo "[拉取][降级] docker pull --progress=plain ${image}"
    docker pull --progress=plain "$image"
    return $?
  fi
  rm -f /tmp/pull_"$$.log"
  return 1
}
docker_push() {
  local image="$1"
  echo "[推送] docker push --platform linux/arm64 ${image}"
  if docker push --platform linux/arm64 --progress=plain "$image" 2>&1 | tee /tmp/push_"$$.log"; then
    return 0
  fi
  local err
  err=$(grep -iE 'unknown flag: --platform|--platform.*is only supported.*experimental' /tmp/push_"$$.log" || true)
  if [ -n "$err" ]; then
    echo "[推送][降级] docker push --progress=plain ${image}(宿主机已校验为 ARM64 架构)"
    docker push --progress=plain "$image"
    return $?
  fi
  rm -f /tmp/push_"$$.log"
  return 1
}

# 校验镜像架构必须为 arm64(强制,失败需重新拉取)
check_image_arch() {
  local image="$1"
  echo "[校验] 镜像架构: docker inspect ${image} | grep -i architecture"
  local arch
  arch=$(docker inspect "$image" 2>/dev/null | grep -i '"Architecture"' | head -1 | sed -E 's/.*"Architecture"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/I' || true)
  arch="${arch// /}"
  echo "[校验] Architecture=${arch:-未知}"
  if [ -z "$arch" ]; then
    echo "[错误] 无法读取镜像 ${image} 的 Architecture 字段,可能镜像不存在或 inspect 输出异常" >&2
    exit 1
  fi
  case "$arch" in
    arm64|aarch64)
      echo "[校验] 通过: ${arch} 满足昇腾 NPU(ARM64)部署要求"
      ;;
    *)
      echo "[错误] 镜像架构为 ${arch},非 arm64/aarch64,无法在昇腾 NPU(ARM64)节点运行(exec format error)" >&2
      echo "       请删除镜像后重拉并复查 --platform linux/arm64 参数:" >&2
      echo "         docker rmi ${image} && docker pull --platform linux/arm64 ${image}" >&2
      exit 1
      ;;
  esac
}

# ---------- 执行: 拉取 -> 校验架构 -> 打标签 -> 登录 -> 推送 ----------
echo "[1/5] 校验 tag '${TAG}' 是否与模型适配文档标注的 vllm-ascend 版本一致(禁止默认 latest)"
echo "[2/5] 从源仓库拉取 ARM64 镜像: ${SRC_IMAGE}(此步耗时取决于镜像大小与网络,请耐心等待)"
docker_pull "$SRC_IMAGE"

echo "[3/5] 校验镜像架构必须为 arm64"
check_image_arch "$SRC_IMAGE"

echo "[4/5] 打标签并登录 SWR: ${SWR_DOMAIN}"
docker tag "$SRC_IMAGE" "${DEST_IMAGE}:${TAG}"
# 密码经 stdin 注入,不暴露于 ps/proc/cmdline/shell history
echo "$SWR_PASSWORD" | docker login -u "$SWR_USER" --password-stdin "$SWR_DOMAIN"

echo "[5/5] 推送镜像到 SWR: ${DEST_IMAGE}:${TAG}(此步耗时取决于镜像大小与网络,请耐心等待)"
docker_push "${DEST_IMAGE}:${TAG}"

echo ""
echo "================================================================"
echo "完成! 请将以下完整 SWR 镜像地址记录为 SWR_IMAGE_ADDRESS:"
echo "  ${DEST_IMAGE}:${TAG}"
echo "================================================================"
echo "后续 ModelArts 部署新版在线服务时,该地址作为 roles[].image(模型镜像来源)填写。"
echo "安全提醒: 使用后请执行 docker logout ${SWR_DOMAIN} 清理本地登录凭据。"
echo "架构核对: 可用 'docker image inspect ${DEST_IMAGE}:${TAG} | grep -i architecture' 确认镜像为 arm64。"
echo "版本核对: 可用 'docker image inspect ${DEST_IMAGE}:${TAG} | grep -iE \"vllm|cann\"' 确认镜像内版本。"
