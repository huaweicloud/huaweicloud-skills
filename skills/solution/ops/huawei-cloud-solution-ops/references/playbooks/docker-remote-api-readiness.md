# Docker Remote API Readiness Playbook

## 目标

在 ECS 上安装 Docker、按需开放 Remote API，并用协议调用验证 Docker daemon 和镜像拉取/容器运行。

## 适用场景

- 用户要求安装 Docker
- 用户明确要求开放 Docker TCP 2375
- 当前环境没有稳定 SSH，但可以访问公网端口

## 安全边界

Docker TCP 2375 是未加密管理端口，只有用户明确要求时才开放。最终输出必须提醒这是高风险端口。

## Bash cloud-init 模板

```bash
#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

mkdir -p /etc/docker /etc/systemd/system/docker.service.d /var/lib/huawei-cloud-solution-ops
exec > >(tee -a /var/log/huawei-cloud-solution-ops-docker-init.log) 2>&1

for i in 1 2 3; do
  apt-get update -y && break
  sleep $((i * 10))
done

apt-get install -y docker.io curl

cat >/etc/docker/daemon.json <<'JSON'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ]
}
JSON

cat >/etc/systemd/system/docker.service.d/override.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://0.0.0.0:2375
EOF

systemctl daemon-reload
systemctl enable docker
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
