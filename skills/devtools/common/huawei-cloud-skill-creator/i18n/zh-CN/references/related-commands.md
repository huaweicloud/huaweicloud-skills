# 相关命令速查 - huawei-cloud-skill-creator-skill

> 当需要快速查找 Skill 创建相关命令时读取此文件。

## hcloud CLI 通用命令

使用 CLI help 标志探索服务和操作（如 `--help`）。

```bash
# 示例：列出 ECS 实例
hcloud ECS ListServers --cli-region={region}
```

## 常用服务速查

| 服务 | 常用操作 | 说明 |
|------|----------|------|
| ECS | ListServers, ShowServer, CreateServers, DeleteServers | 弹性云服务器 |
| VPC | ListVpcs, ShowVpc, CreateVpc, DeleteVpc | 虚拟私有云 |
| OBS | ListBuckets, CreateBucket, DeleteBucket | 对象存储 |
| RDS | ListInstances, ShowInstance, CreateInstance | 关系型数据库 |
| IAM | ListUsers, ShowUser, CreatePolicy | 身份认证 |
| CCE | ListClusters, ShowCluster, CreateCluster | 云容器引擎 |
| CES | ListMetrics, ShowMetricData, ListAlarms | 云监控 |
| ELB | ListLoadBalancers, ShowLoadBalancer | 弹性负载均衡 |
| EVS | ListVolumes, ShowVolume, CreateVolume | 弹性云硬盘 |

## Skill 验证命令

```bash
# 验证 Skill 结构
bash scripts/validate-skill.sh {skill-path}

# 检查 SKILL.md 格式
head -1 {skill-path}/SKILL.md  # 应为 ---

# 检查 references 完整性
ls {skill-path}/references/
```

## 文件操作命令

```bash
# 创建 Skill 目录结构
mkdir -p {domain}/{skill-name}/{references,scripts,templates,demo}

# 从模板生成 SKILL.md
cp templates/SKILL.md.template {domain}/{skill-name}/SKILL.md
```
