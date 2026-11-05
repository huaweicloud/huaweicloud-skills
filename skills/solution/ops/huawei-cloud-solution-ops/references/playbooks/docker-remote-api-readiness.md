# Docker Remote API Readiness Playbook

## 目标

在 ECS 上安装 Docker、按需开放 Remote API，并用协议调用验证 Docker daemon 和镜像拉取/容器运行。

## 适用场景

- 用户要求安装 Docker
- 用户明确要求开放 Docker TCP 2375
- 当前环境没有稳定 SSH，但可以访问公网端口

## 安全边界

Docker TCP 2375 是未加密管理端口，只有用户明确要求时才开放。最终输出必须提醒这是高风险端口。默认只允许 Unix socket；需要 TCP 时必须以 `DOCKER_TCP_BIND` 显式指定具体内网地址（拒绝 `0.0.0.0` 通配），并以 `DOCKER_TCP_SOURCE_CIDR` 声明允许的源网段做防火墙白名单。禁止把未加密的控制平面做成开机自启的持久化 systemd 服务。

## Bash cloud-init 模板

```bash
#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

mkdir -p /etc/docker /var/lib/huawei-cloud-solution-ops /var/log/huawei-cloud-solution-ops
exec > >(tee -a /var/log/huawei-cloud-solution-ops/docker-init.log) 2>&1

for i in 1 2 3; do
  apt-get update -y && break
  sleep $((i * 10))
done

apt-get install -y docker.io

# 默认只启用 Unix socket 的 Docker 控制平面；TCP 监听必须显式授权。
# DOCKER_TCP_BIND 必须是非 0.0.0.0 的授权内网地址，DOCKER_TCP_SOURCE_CIDR 是允许访问的源网段。
DOCKER_TCP_BIND="${DOCKER_TCP_BIND:-}"
DOCKER_TCP_SOURCE_CIDR="${DOCKER_TCP_SOURCE_CIDR:-}"
if [[ -n "${DOCKER_TCP_BIND}" ]]; then
  if [[ "${DOCKER_TCP_BIND}" == "0.0.0.0" || -z "${DOCKER_TCP_SOURCE_CIDR}" ]]; then
    echo "Docker TCP bind 必须显式指定授权内网地址并提供源网段白名单；拒绝 0.0.0.0 通配监听。" >&2
    exit 2
  fi
fi

if [[ -n "${DOCKER_TCP_BIND}" ]]; then
  cat >/etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ],
  "hosts": [
    "unix:///var/run/docker.sock",
    "tcp://${DOCKER_TCP_BIND}:2375"
  ]
}
EOF
else
  cat >/etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ],
  "hosts": ["unix:///var/run/docker.sock"]
}
EOF
fi

# 来源网段白名单：仅允许声明的 CIDR 访问 TCP 管理端口（云安全组亦需同规则收口）。
if command -v iptables >/dev/null 2>&1 && [[ -n "${DOCKER_TCP_SOURCE_CIDR}" ]]; then
  iptables -C INPUT -p tcp --dport 2375 -s "${DOCKER_TCP_SOURCE_CIDR}" -j ACCEPT 2>/dev/null \
    || iptables -I INPUT -p tcp --dport 2375 -s "${DOCKER_TCP_SOURCE_CIDR}" -j ACCEPT
  iptables -C INPUT -p tcp --dport 2375 -j DROP 2>/dev/null \
    || iptables -A INPUT -p tcp --dport 2375 -j DROP
fi

systemctl restart docker

for i in 1 2 3 4 5 6; do
  curl -fsS --max-time 5 http://127.0.0.1:2375/version && break
  sleep 5
done

docker info >/var/lib/huawei-cloud-solution-ops/docker-info.txt

cat >/var/lib/huawei-cloud-solution-ops/readiness.json <<'JSON'
{"service":"docker","status":"ready","port":2375}
JSON
```

> 说明：不写入任何影响开机自启的持久化 systemd 服务来固化未加密 TCP 监听。`docker` 服务保持系统默认启动策略；如果用户确认需长期暴露 Docker TCP，必须改为 Docker TLS 客户端证书方案，且仅绑定内网授权地址并配合安全组/防火墙白名单，而不是以 `0.0.0.0:2375` 持久开机自启。

## 验收顺序

1. ECS 是 `ACTIVE`。
2. EIP 已绑定。
3. 安全组开放用户要求的 Docker 端口和业务端口。
4. 协议验证：

```bash
curl --max-time 15 http://<EIP>:2375/version
curl --max-time 15 http://<EIP>:2375/info
```

5. 需要运行容器时，优先使用 Docker Remote API 创建、启动、取日志；镜像源不可达时换用当前网络可达镜像源。

## 失败分类

- `/version` 超时：优先排查安全组、EIP、防火墙、daemon 是否监听。
- `/version` 成功但 `docker run` 失败：区分镜像源不可达和 Docker daemon 异常。
- 没有 SSH 或远程命令能力时，不要声称已经执行了 `docker info`；只能报告协议探测事实。
