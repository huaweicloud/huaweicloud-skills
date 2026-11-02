## OBS 安全知识

**公共访问阻止（BPA）四参数**

| 参数 | JSON键 | 说明 |
|:-----|:-------|:-----|
| block_public_acls | BlockPublicAcls | 阻止设置公共ACL。设为true时，上传对象或修改ACL指定为公共访问将返回403 |
| block_public_policy | BlockPublicPolicy | 阻止设置允许公共访问的桶策略。设为true时，此类桶策略将配置失败 |
| ignore_public_acls | IgnorePublicAcls | 忽略现有公共ACL。设为true时，桶或对象的公共ACL变为无效 |
| restrict_public_buckets | RestrictPublicBuckets | 限制现有公共桶策略。设为true时，仅云服务和桶拥有者账号可访问 |

> 安全建议：将四个参数全部设置为true，可完全阻止OBS桶的公共访问。

