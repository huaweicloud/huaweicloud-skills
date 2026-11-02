## 华为云场景知识

以下为华为云云服务的场景化知识，在分析资源的安全配置时，需要考虑以下信息：

**云服务资源类型对应关系**

| provider | type              | 中文名         | 说明                      |
|:---------|:------------------|:------------|:------------------------|
| cts      | trackers          | 云审计服务追踪器    | 提供对各种云资源操作记录的收集、存储和查询功能 |
| config   | trackers          | 配置审计服务资源记录器 | 提供资源配置的持续审计能力           |
| config   | policyAssignments | 合规规则        | 定义合规检查逻辑                |
| config   | conformancePacks  | 合规规则包       | 批量合规规则模板                |
| vpc      | vpcs              | 虚拟私有云       | -                       |
| vpc      | subnets           | 子网          | -                       |
| vpc      | securityGroups    | 安全组         | 实例级有状态访问控制              |
| vpc      | ports             | 网络接口（端口）    | -                       |
| vpc      | publicips         | 弹性公网IP      | -                       |
| vpc      | firewalls         | 网络ACL       | 子网级无状态访问控制              |
| iam      | users             | IAM用户       | AK信息仅允许在此字段出现           |
| iam      | groups            | 用户组         | -                       |
| iam      | policies          | 身份策略        | -                       |
| iam      | agencies          | 委托          | -                       |
| obs      | buckets           | 对象存储桶       | -                       |

**Region映射**

| 区域        | regionCode     |
|:----------|:---------------|
| 华北-北京一    | cn-north-1     |
| 华北-北京二    | cn-north-2     |
| 华北-北京三    | cn-north-3     |
| 华北-北京四    | cn-north-4     |
| 华北-乌兰察布一  | cn-north-9     |
| 华东一       | cn-east-4      |
| 华东-上海一    | cn-east-3      |
| 华东-上海二    | cn-east-2      |
| 华东-青岛     | cn-east-5      |
| 华南-广州     | cn-south-1     |
| 华南-深圳     | cn-south-2     |
| 西南-贵阳一    | cn-southwest-2 |
| 中国-香港     | ap-southeast-1 |
| 亚太-曼谷     | ap-southeast-2 |
| 亚太-新加坡    | ap-southeast-3 |
| 亚太-雅加达    | ap-southeast-4 |
| 亚太-马尼拉    | ap-southeast-5 |
| 中东-利雅得    | me-east-1      |
| 土耳其-伊斯坦布尔 | tr-west-1      |
| 非洲-开罗     | af-north-1     |
| 非洲-约翰内斯堡  | af-south-1     |
| 拉美-墨西哥城一  | na-mexico-1    |
| 拉美-墨西哥城二  | la-north-2     |
| 拉美-圣地亚哥   | la-south-2     |
| 拉美-圣保罗一   | sa-brazil-1    |

## 各服务安全知识索引

- [VPC 安全知识](./service/vpc.md)
- [IAM 安全知识](./service/iam.md)
- [OBS 安全知识](./service/obs.md)
- [Config 核心概念](./service/config.md)

