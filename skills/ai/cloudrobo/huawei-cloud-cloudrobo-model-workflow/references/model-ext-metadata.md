# model_ext_metadata Construction Guide

> `model_feature_mapping` must be explicitly passed via `--model-ext-metadata` when creating an inference service. The platform does not read `model_feature_mapping` from the asset version. Not passing this parameter causes the inference service to immediately FAIL.

## Step 3.2a: Select r2c Template

Select the corresponding r2c template based on robot type. The template provides the structure for `model_feature_mapping`, including `input_features` (state, camera, task), `output_features` (action), and `stop_condition` (fixed, no modification needed).

### so101 Real-Robot r2c Template (Single-Arm 6-DOF)

```json
{
    "model_feature_mapping": {
        "input_features": {
            "observation.state": {
                "shape": [6],
                "dtype": "float32",
                "values": [
                    "observation.joint_states.position@{joint_1}",
                    "observation.joint_states.position@{joint_2}",
                    "observation.joint_states.position@{joint_3}",
                    "observation.joint_states.position@{joint_4}",
                    "observation.joint_states.position@{joint_5}",
                    "observation.joint_states.position@{joint_6}"
                ]
            },
            "observation.images.third": {
                "dtype": "float32",
                "value": "observations.images.color.front"
            },
            "observation.images.wrist": {
                "dtype": "float32",
                "value": "observations.images.color.wrist"
            },
            "task": {
                "type": "PROMPT"
            }
        },
        "output_features": {
            "action": {
                "chunk_size": 100,
                "shape": [6],
                "values": [
                    "actions.joint_states.position@{joint_1}",
                    "actions.joint_states.position@{joint_2}",
                    "actions.joint_states.position@{joint_3}",
                    "actions.joint_states.position@{joint_4}",
                    "actions.joint_states.position@{joint_5}",
                    "actions.joint_states.position@{joint_6}"
                ]
            }
        }
    },
    "stop_condition": {
        "max_iter_num": 60,
        "max_run_time": 5
    }
}
```

### JAKA Real-Robot r2c Template

```json
{
    "model_feature_mapping": {
        "input_features": {
            "observation.state": {
                "shape": [7],
                "dtype": "float32",
                "values": [
                    "observation.joint_states.position@{joint_1}",
                    "observation.joint_states.position@{joint_2}",
                    "observation.joint_states.position@{joint_3}",
                    "observation.joint_states.position@{joint_4}",
                    "observation.joint_states.position@{joint_5}",
                    "observation.joint_states.position@{joint_6}",
                    "observation.joint_states.position@{gripper_1}"
                ]
            },
            "observation.images.top": {
                "dtype": "uint8",
                "value": "observations.images.color.top"
            },
            "observation.images.wrist": {
                "dtype": "uint8",
                "value": "observations.images.color.wrist"
            },
            "task": {
                "type": "PROMPT"
            }
        },
        "output_features": {
            "action": {
                "chunk_size": 50,
                "shape": [7],
                "values": [
                    "actions.joint_states.position@{joint_1}",
                    "actions.joint_states.position@{joint_2}",
                    "actions.joint_states.position@{joint_3}",
                    "actions.joint_states.position@{joint_4}",
                    "actions.joint_states.position@{joint_5}",
                    "actions.joint_states.position@{joint_6}",
                    "actions.joint_states.position@{gripper_1}"
                ]
            }
        }
    },
    "stop_condition": {
        "max_iter_num": 60,
        "max_run_time": 5
    }
}
```

> **Critical: `chunk_size` must match training hyperparameter `model.action-horizon`**:
> - OpenPI model default `model.action-horizon=50`, so `chunk_size=50`
> - If `model.action-horizon` was modified during training, `chunk_size` must be updated accordingly
> - Mismatch causes inference service deployment failure or runtime errors

## Step 3.2b: Read Dataset meta/info.json

Read the training dataset's `meta/info.json`, from the `features` field get:
- `observation.state` shape (joint count) and joint name list
- `action` or `actions` shape (action dimension) and joint name list
- Camera key names (used for non-OpenPI models)

## Step 3.2c: Dynamically Construct model_feature_mapping

Using the r2c template as base, dynamically modify `input_features` and `output_features` based on dataset meta/info.json:

1. **`observation.state`**: Update `shape` array and `values` list based on dataset info's shape and joint names
2. **`action`**: Update `shape` array and `values` list based on dataset info's shape and joint names
3. **`chunk_size`**: Must match training hyperparameter `model.action-horizon` (OpenPI default 50)
4. **Camera keys** (non-OpenPI models): Update camera entry keys in input_features based on dataset info's camera key names
5. **Other fields unchanged**: `value` (robot camera topic), `task`, `stop_condition` keep template values. Note `dtype` keeps template value `uint8` (do not change to `float32`)

## Step 3.2d: OpenPI Model Camera Special Handling

> **Applicable condition**: Execute when the base model is OpenPI series (`Physical-Intelligence_PI0-Base`, `Physical-Intelligence_PI05-Base`). Skip for other models (e.g., LeRobot series).

OpenPI models require fixed 3-camera input in `input_features`, with fixed keys:
- `observation.images.front`
- `observation.images.wrist_left`
- `observation.images.wrist_right`

so101 and JAKA have only 2 cameras. Processing method:
1. Assign the r2c template's 1st camera `value` to `observation.images.front`
2. Assign the r2c template's 2nd camera `value` to `observation.images.wrist_left`
3. Copy `observation.images.wrist_left`'s `value` to `observation.images.wrist_right`

**Example**: so101 + OpenPI model

r2c template cameras (original):
```json
"observation.images.third": {"dtype": "uint8", "value": "observations.images.color.front"},
"observation.images.wrist": {"dtype": "uint8", "value": "observations.images.color.wrist"}
```

After OpenPI conversion:
```json
"observation.images.front": {"dtype": "uint8", "value": "observations.images.color.front"},
"observation.images.wrist_left": {"dtype": "uint8", "value": "observations.images.color.wrist"},
"observation.images.wrist_right": {"dtype": "uint8", "value": "observations.images.color.wrist"}
```

## Final model_ext_metadata Format

Combine `model_feature_mapping` and `stop_condition` into a JSON string (**do not** include `model_type` field):

```json
{"model_feature_mapping":{"input_features":{...},"output_features":{...}},"stop_condition":{"max_iter_num":60,"max_run_time":5}}
```

> **Critical: Do not include `model_type` field**. Successfully deployed inference services do not include this field. Including `model_type` may cause deployment failure.
>
> **Note**: `--model-ext-metadata` value is a raw JSON string. The CLI does not parse it as a dict but passes it directly as a string to the API (API field `model_ext_metadata` type is `string`).
>
> If PowerShell parsing fails, write JSON to a file and use Python subprocess to call the CLI.
