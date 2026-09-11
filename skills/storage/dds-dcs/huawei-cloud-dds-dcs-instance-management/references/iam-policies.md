# IAM Policies for DDS and DCS

> Least-privilege IAM policy examples for Huawei Cloud DDS and DCS operations.

## DDS Read-only (Query) Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dds:instance:list",
                "dds:instance:get",
                "dds:backup:list",
                "dds:configuration:list",
                "dds:flavor:list",
                "dds:storageType:list"
            ],
            "Resource": [
                "dds:*:*:instance:*",
                "dds:*:*:backup:*",
                "dds:*:*:configuration:*",
                "dds:*:*:flavor:*",
                "dds:*:*:storageType:*"
            ]
        }
    ]
}
```

## DDS Full Management Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dds:instance:create",
                "dds:instance:delete",
                "dds:instance:list",
                "dds:instance:get",
                "dds:instance:addNode",
                "dds:instance:resize",
                "dds:instance:restart",
                "dds:backup:create",
                "dds:backup:delete",
                "dds:backup:list",
                "dds:configuration:list",
                "dds:flavor:list",
                "dds:storageType:list"
            ],
            "Resource": [
                "dds:*:*:instance:*",
                "dds:*:*:backup:*",
                "dds:*:*:configuration:*",
                "dds:*:*:flavor:*",
                "dds:*:*:storageType:*"
            ]
        }
    ]
}
```

## DCS Read-only (Query) Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dcs:instance:list",
                "dcs:instance:get",
                "dcs:instance:getNodes",
                "dcs:template:list",
                "dcs:template:get",
                "dcs:whitelist:get",
                "dcs:acl:list"
            ],
            "Resource": [
                "dcs:*:*:instance:*",
                "dcs:*:*:template:*",
                "dcs:*:*:whitelist:*",
                "dcs:*:*:acl:*"
            ]
        }
    ]
}
```

## DCS Full Management Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dcs:instance:create",
                "dcs:instance:delete",
                "dcs:instance:restart",
                "dcs:instance:list",
                "dcs:instance:get",
                "dcs:instance:getNodes",
                "dcs:template:create",
                "dcs:template:list",
                "dcs:template:get",
                "dcs:template:delete",
                "dcs:whitelist:get",
                "dcs:acl:list"
            ],
            "Resource": [
                "dcs:*:*:instance:*",
                "dcs:*:*:template:*",
                "dcs:*:*:whitelist:*",
                "dcs:*:*:acl:*"
            ]
        }
    ]
}
```

## Combined DDS + DCS Admin Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dds:*:*",
                "dcs:*:*"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```