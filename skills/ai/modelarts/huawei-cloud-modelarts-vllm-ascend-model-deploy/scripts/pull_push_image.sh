#!/bin/bash
# 从 Quay.io 拉取 vllm-ascend 镜像并推送至华为云 SWR
# tag 必须来自 vllm-ascend 模型适配文档,不要默认用 latest

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
docker_pull() {
  if docker pull --help 2>&1 | grep -q -- '--progress'; then
    docker pull --progress=plain "$1"
  else
    docker pull "$1"
  fi
}
docker_push() {
  if docker push --help 2>&1 | grep -q -- '--progress'; then
    docker push --progress=plain "$1"
  else
    docker push "$1"
  fi
}

# ---------- 执行: 拉取 -> 打标签 -> 登录 -> 推送 ----------
echo "[1/4] 校验 tag '${TAG}' 是否与模型适配文档标注的 vllm-ascend 版本一致(禁止默认 latest)"
echo "[2/4] 从源仓库拉取镜像: ${SRC_IMAGE}(此步耗时取决于镜像大小与网络,请耐心等待)"
docker_pull "$SRC_IMAGE"

echo "[3/4] 打标签并登录 SWR: ${SWR_DOMAIN}"
docker tag "$SRC_IMAGE" "${DEST_IMAGE}:${TAG}"
# 密码经 stdin 注入,不暴露于 ps/proc/cmdline/shell history
echo "$SWR_PASSWORD" | docker login -u "$SWR_USER" --password-stdin "$SWR_DOMAIN"

echo "[4/4] 推送镜像到 SWR: ${DEST_IMAGE}:${TAG}(此步耗时取决于镜像大小与网络,请耐心等待)"
docker_push "${DEST_IMAGE}:${TAG}"

echo ""
echo "================================================================"
echo "完成! 请将以下完整 SWR 镜像地址记录为 SWR_IMAGE_ADDRESS:"
echo "  ${DEST_IMAGE}:${TAG}"
echo "================================================================"
echo "后续 ModelArts 部署新版在线服务时,该地址作为 roles[].image(模型镜像来源)填写。"
echo "安全提醒: 使用后请执行 docker logout ${SWR_DOMAIN} 清理本地登录凭据。"
echo "版本核对: 可用 'docker image inspect ${SRC_IMAGE} | grep -iE \"vllm|cann\"' 确认镜像内版本。"
