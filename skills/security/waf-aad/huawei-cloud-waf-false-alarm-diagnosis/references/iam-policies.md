# IAM Policies for WAF False Alarm Diagnosis

This skill is **read-only**. Grant only query permissions. Apply the policy to the agent's IAM user/agency on the target project(s).

## Minimum Read-Only Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:host:list",
        "waf:host:get",
        "waf:compositeHost:list",
        "waf:compositeHost:get",
        "waf:policy:list",
        "waf:policy:get",
        "waf:securityEvents:list",
        "waf:securityEvents:get",
        "waf:rule:list",
        "waf:rule:get",
        "waf:ignoreRule:list",
        "waf:whiteblackipRule:list",
        "waf:geoipRule:list",
        "waf:customRule:list",
        "waf:punishmentRule:list",
        "waf:anticrawlerRule:list",
        "waf:ccRule:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> Note: Action names follow the WAF service's IAM policy grant format. If the exact action string differs in your region/console, use the equivalent read-only actions for: host list/get, policy list/get, event list/get, and rule list across whitelist/geoip/custom/punishment/anticrawler/CC. Deny any `create/update/delete` action at the top to protect production safety:

```json
{
  "Effect": "Deny",
  "Action": [
    "waf:*:create",
    "waf:*:update",
    "waf:*:delete"
  ],
  "Resource": ["*"]
}
```

## What This Skill Does NOT Need

- No write actions (`Create*`, `Update*`, `Delete*`) — the skill only outputs commands for the user to run.
- No billing / cost permissions.
- No organization (RMS) permissions.