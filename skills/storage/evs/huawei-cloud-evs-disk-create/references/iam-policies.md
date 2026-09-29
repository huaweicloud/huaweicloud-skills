# IAM Permission Policies - Huawei Cloud EVS Disk Create

IAM permission policies required for this skill.

## Required Permissions Overview

| Operation | IAM Action | Description |
|-----------|-----------|-------------|
| Create EVS volume | `evs:volumes:create` | Create cloud disk |
| List EVS volumes | `evs:volumes:list` | List disks to verify creation |
| View EVS volume details | `evs:volumes:get` | Query disk details |
| List availability zones | `evs:AvailabilityZones:list` | Query availability zones |

---

## Minimum Required Policy (JSON)

### New IAM (v5 API - Identity Policy Authorization)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "evs:volumes:create",
        "evs:volumes:list",
        "evs:volumes:get",
        "evs:AvailabilityZones:list"
      ],
      "Resource": [
        "EVS:*:*:volume:*"
      ]
    }
  ]
}
```

---

## System Policies

Use Huawei Cloud pre-built system policies for simplified authorization:

| System Policy | Included Permissions | Use Case |
|--------------|---------------------|----------|
| `EVS FullAccess` | All EVS permissions | ✅ Recommended for this skill |
| `EVS ReadOnlyAccess` | EVS read-only permissions | View disks only, cannot create |

**Recommended combination:** `EVS FullAccess`

---

## Policy Best Practices

1. **Least privilege principle**: Grant only the minimum required permissions; prefer the custom policy above over `EVS FullAccess`
2. **Write confirmation**: Creating disks is a write operation that incurs cost; verify parameters with the user before executing `CreateVolume`
3. **Quota awareness**: Check account's EVS disk quantity quota and total capacity quota before batch creation
4. **Regular review**: Periodically review IAM policies to ensure no excess permissions

---

## References

- [EVS IAM Authorization](https://support.huaweicloud.com/perms-cfg-evs/evs_01_0023.html)
- [Creating IAM Custom Policies](https://support.huaweicloud.com/usermanual-iam/iam_01_0605.html)