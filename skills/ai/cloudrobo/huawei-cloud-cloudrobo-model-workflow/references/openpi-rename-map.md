# OpenPI Model data.rename_map Construction

> **Applicable condition**: Execute this step when the base model is `Physical-Intelligence_PI0-Base` or `Physical-Intelligence_PI05-Base`. Skip for other models (e.g., LeRobot series).

OpenPI models require the dataset's view key, state key, and action key to align with the model's expected fixed keys. If the dataset's keys do not match OpenPI's default keys, use the `data.rename_map` parameter to map them.

## OpenPI Expected Fixed Keys

| Type | OpenPI Expected Key | Description |
|------|-------------------|-------------|
| View 1 | `observation.images.front` | Front camera |
| View 2 | `observation.images.wrist_left` | Left wrist camera |
| View 3 | `observation.images.wrist_right` | Right wrist camera |
| State | `observation.state` | Robot state |
| Action | `actions` | Action sequence (note the trailing s) |

## Construction Steps

### 1. Read Dataset meta/info.json

Read the dataset's `meta/info.json`, find the `features` field, and extract the user's actual keys:
- User's view keys (all keys under `observation.images.*`)
- User's state key (typically `observation.state`)
- User's action key (may be `action` or `actions`)

### 2. Map Views by Order

Map the user's view keys to OpenPI's 3 standard view keys in order of appearance:
- User's 1st view → `observation.images.front`
- User's 2nd view → `observation.images.wrist_left`
- User's 3rd view → `observation.images.wrist_right`
- If user has only 2 views, map only the first 2 standard keys, drop the 3rd
- If user has only 1 view, map only `observation.images.front`

### 3. Map State and Action

- State: user's state key → `observation.state`
- Action: user's action key → `actions` (note the trailing s)

### 4. Construct JSON and Wrap in Single Quotes

- `rename_map` keys are the user's actual keys, values are OpenPI's standard keys
- Use compact JSON format (no spaces): `json.dumps(rename_map, separators=(',', ':'))`
- **Must wrap the entire JSON string in single quotes `'`**, otherwise the server-side validation will reject it (`"` characters are not in the allowed regex pattern)

## Construction Examples

```python
import json

# Example 1: User dataset keys match OpenPI defaults, but action key is "action" (no s)
rename_map = {
    "observation.images.front": "observation.images.front",
    "observation.images.wrist_left": "observation.images.wrist_left",
    "observation.images.wrist_right": "observation.images.wrist_right",
    "observation.state": "observation.state",
    "action": "actions"  # User's "action" maps to OpenPI's "actions"
}
# Compact JSON + single-quote wrap
value = "'" + json.dumps(rename_map, separators=(',', ':')) + "'"
# Result: '{"observation.images.front":"observation.images.front",...,"action":"actions"}'

# Example 2: User dataset has different view keys, and only 2 views
rename_map = {
    "observation.images.external": "observation.images.front",
    "observation.images.wrist": "observation.images.wrist_left",
    "observation.state": "observation.state",
    "actions": "actions"  # User's key is already "actions", direct mapping
}
value = "'" + json.dumps(rename_map, separators=(',', ':')) + "'"

# Example 3: User has 3 custom view keys, action and state keys also differ
rename_map = {
    "observation.images.image1": "observation.images.front",
    "observation.images.image2": "observation.images.wrist_left",
    "observation.images.image3": "observation.images.wrist_right",
    "state": "observation.state",
    "action": "actions"
}
value = "'" + json.dumps(rename_map, separators=(',', ':')) + "'"
```

## Format in parameters

```json
{"key": "data.rename_map", "value": "'{\"observation.images.front\":\"observation.images.front\",\"observation.images.wrist_left\":\"observation.images.wrist_left\",\"observation.images.wrist_right\":\"observation.images.wrist_right\",\"observation.state\":\"observation.state\",\"action\":\"actions\"}'"}
```

## Key Format Requirements

- The `value` must start and end with single quote `'`, with compact JSON (no spaces) in between
- Double quotes `"` in JSON keys and values must not be omitted
- If `data.rename_map` parameter is omitted (`required: false`), the algorithm uses the default value, which already includes self-mapping for all 5 standard keys

## data.rename_map Mapping Rules

| Rule | Description |
|------|-------------|
| View order | User's 1st/2nd/3rd view → `front`/`wrist_left`/`wrist_right` |
| Fewer than 3 views | Keep only items mapped to `front`/`wrist_left`, drop extras |
| State | User's state key → `observation.state` (must include) |
| Action | User's action key → `actions` (note trailing s, must include) |
| Format | value = `'` + compact JSON (`separators=(',',':')`) + `'` |
| Optional | `required: false`; when omitted, algorithm uses default (all 5 standard keys self-mapped) |

## OpenPI PI05 FFT Default Hyperparameters

| Key | Default | Description |
|-----|---------|-------------|
| `batch_size` | `32` | Batch size |
| `num_train_steps` | `100000` | Training steps |
| `save_interval` | `10000` | Save frequency |
| `model.action-horizon` | `50` | Action sequence length |
| `data.rename_map` | `'{"observation.images.front":"observation.images.front",...,"action":"actions"}'` | Field mapping |
| `model.dtype` | `bfloat16` | Precision (`bfloat16`/`float32`) |
| `lr_schedule.peak_lr` | `5e-05` | Peak learning rate |
| `lr_schedule.decay_lr` | `5e-05` | Decay learning rate |
| `lr_schedule.warmup_steps` | `1000` | Warmup steps |
| `lr_schedule.decay_steps` | `30000` | Decay steps |

> LeRobot PI05 does not need rename_map — natively accepts LeRobot v3 format.
> **`save_interval` must be ≤ `num_train_steps`**, otherwise no model file is generated at training end.
