# IAM Policies for ModelArts Notebook Management

> Least-privilege IAM policies for all 31 notebook management operations.

## Policy: ModelArts Notebook Full Management

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:notebook:create",
        "modelarts:notebook:list",
        "modelarts:notebook:get",
        "modelarts:notebook:update",
        "modelarts:notebook:delete",
        "modelarts:notebook:start",
        "modelarts:notebook:stop",
        "modelarts:notebook:getLease",
        "modelarts:notebook:renewLease",
        "modelarts:notebook:listTags",
        "modelarts:notebook:createTag",
        "modelarts:notebook:deleteTag",
        "modelarts:notebook:createImage",
        "modelarts:image:list",
        "modelarts:image:register",
        "modelarts:image:get",
        "modelarts:image:delete",
        "modelarts:image:sync",
        "modelarts:imageGroup:list",
        "modelarts:imageGroup:delete",
        "modelarts:imageGroup:update",
        "modelarts:notebook:listFlavors",
        "modelarts:notebook:listSwitchableFlavors",
        "modelarts:cluster:list",
        "modelarts:cluster:get",
        "modelarts:feature:list",
        "modelarts:notebook:listStorage",
        "modelarts:notebook:attachStorage",
        "modelarts:notebook:getStorage",
        "modelarts:notebook:detachStorage"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy: ModelArts Notebook Read-Only

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:notebook:list",
        "modelarts:notebook:get",
        "modelarts:notebook:getLease",
        "modelarts:notebook:listTags",
        "modelarts:image:list",
        "modelarts:image:get",
        "modelarts:imageGroup:list",
        "modelarts:notebook:listFlavors",
        "modelarts:notebook:listSwitchableFlavors",
        "modelarts:cluster:list",
        "modelarts:cluster:get",
        "modelarts:feature:list",
        "modelarts:notebook:listStorage",
        "modelarts:notebook:getStorage"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Use **Full Management** policy for complete notebook lifecycle management
- Use **Read-Only** policy for query-only scenarios (monitoring, inspection)
- Additional `SWR` permissions may be required for image creation and registration operations
- Additional `OBS`/`SFS` permissions may be required for dynamic storage operations
