## IAM 安全知识

**AK/SK安全配置**

华为云的Access Key（AK）为20位随机字符串（例如HPUAAJJAC9GJZDIQCTHN），Secret Key（SK）为40位随机字符串。在资源配置中，仅允许在iam.users字段中包含AK信息，严禁在任何资源配置中明文存储或传递SK。若检测到SK存在于配置中，则判定为敏感信息泄露风险，需立即整改。

