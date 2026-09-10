# IAM Policies - MRS Redis Meta Check

## Basic Diagnosis (Read-only)

| API Action         | Permission             | Purpose                               |
|--------------------|------------------------|---------------------------------------|
| mrs:clusters:get   | View cluster details   | Get cluster basic information         |
| mrs:clusters:list  | List clusters          | Confirm cluster exists                |
| mrs:host:list      | List hosts             | Get host list                         |

## Minimum Permission Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mrs:clusters:get",
        "mrs:clusters:list",
        "mrs:host:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Failure Handling

1. When any command fails due to permission errors, read this document
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Common Permission Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 403 | Insufficient permissions | Check if the IAM user has the above permissions |
| 401 | Authentication failed | Check AK/SK configuration or IAM Token validity |
| 50201 | Autopilot backend unavailable | Retry later or contact operations staff |
| RDS.9999 | Autopilot backend error | Retry later or contact operations staff |
