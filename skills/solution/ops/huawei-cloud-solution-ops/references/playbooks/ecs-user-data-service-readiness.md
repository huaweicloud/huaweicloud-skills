# ECS User Data Service Readiness Playbook

## 目标

通过幂等 cloud-init/user_data 在 ECS 首次启动时完成软件安装、服务启动和可探测的 readiness 标记。

## 适用场景

- 创建 ECS 并要求安装 Nginx、Docker、WordPress 或其他常驻服务
- 当前环境没有稳定远程命令执行能力
- 需要在公网或 ELB 后端做 HTTP/TCP 协议验收

## 通用 cloud-init 原则

- 使用 `#!/bin/bash` 或合法 `#cloud-config`，不要混用格式。
- 脚本必须幂等：重复执行不应破坏已有配置。
- 写文件前先 `mkdir -p` 父目录。
- 安装软件前设置非交互模式和必要的重试。
- 最后写入 readiness 文件，例如 `/var/lib/huawei-cloud-solution-ops/readiness.json`。
- 对外服务必须 `enable` 并 `restart`。

## Bash 模板

适合放入 ECS `user_data` 后再按 API 要求 base64 编码：

```bash
#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

mkdir -p /var/lib/huawei-cloud-solution-ops
exec > >(tee -a /var/log/huawei-cloud-solution-ops-init.log) 2>&1

apt_get_update() {
  for i in 1 2 3; do
    apt-get update -y && return 0
    sleep $((i * 10))
  done
  return 1
}

apt_get_update
apt-get install -y nginx curl

cat >/var/www/html/index.html <<'HTML'
huawei-cloud-solution-ops web ready
HTML

systemctl enable nginx
systemctl restart nginx

curl -fsS --max-time 10 http://127.0.0.1/ >/tmp/huawei-cloud-solution-ops-http-check.txt

cat >/var/lib/huawei-cloud-solution-ops/readiness.json <<'JSON'
{"service":"nginx","status":"ready","port":80}
JSON
```

## 验收顺序

1. ECS 状态是 `ACTIVE`。
2. 安全组开放目标端口。
3. EIP 或 ELB 绑定正确。
4. 用公网协议探测验证：

```bash
curl -I --max-time 15 http://<EIP-or-ELB>/
curl --max-time 15 http://<EIP-or-ELB>/
```

## 失败分类

- ECS `ACTIVE` 但端口超时：优先查安全组、EIP/ELB 绑定和服务是否监听。
- cloud-init 可能未完成：等待短时间后重试协议探测；不要无限等待。
- 仓库不可达：改用当前区域可达镜像源或发行版仓库；仍不可达时输出外部网络阻塞证据。
