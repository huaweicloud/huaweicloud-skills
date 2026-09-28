# Region Mapping

The `region` column in the Excel template is filled with Chinese region names (e.g. "华东-上海一"), while `hcloud --cli-region`
requires a region code (e.g. `cn-east-3`). This skill's config module (`resolve_region` in `scripts/capacity/config.py`)
performs the conversion. Rules are as follows:

## Supported Chinese name ↔ code (common)

| Chinese region | Aliases | Code |
|---|---|---|
| 华北-北京一 | 北京一 | cn-north-1 |
| 华北-北京四 | 北京四 | cn-north-4 |
| 华北-乌兰察布一 | 乌兰察布 | cn-north-9 |
| 华东-上海一 | 上海一 / 华东一 | cn-east-3 |
| 华东-上海二 | 上海二 / 华东二 | cn-east-2 |
| 华东-青岛 | 青岛 | cn-east-4 |
| 华南-广州 | 广州 | cn-south-1 |
| 华南-深圳 | 深圳 | cn-south-4 |
| 西南-贵阳一 | 贵阳 | cn-southwest-2 |
| 中国-香港 | 香港 | ap-southeast-1 |
| 亚太-新加坡 | 新加坡 | ap-southeast-3 |
| 亚太-曼谷 | 曼谷 | ap-southeast-2 |
| 亚太-雅加达 | 雅加达 | ap-southeast-4 |
| 非洲-约翰内斯堡 | 约翰内斯堡 | af-south-1 |
| 拉美-墨西哥城一 | 墨西哥 | la-north-2 |
| 拉美-圣保罗一 | 圣保罗 | sa-brazil-1 |

## Matching rules

1. Already a region code (shaped like `cn-*`, `ap-*`, etc.) → passed through directly.
2. Exact match on Chinese full name / alias.
3. Contains-match (a cell with remarks, e.g. "华东-上海一(主)" also resolves).
4. Nothing found → returns an error; the model asks the user to confirm the correct region code.

## Notes

- The template sample's "华东二" resolves by alias to `cn-east-2`.
- Monitoring data for mainland China regions (cn-*) splits day windows by UTC+8; overseas regions use UTC.
- If hcloud reports a region unavailable, first check whether the CES endpoint of that region is DNS-resolved to an intranet IP;
  see `troubleshooting-dns.md`.