# ROS bag to LeRobot manifest

Use the bundled `bag2manifest` implementation to inspect a representative local bag and produce a ROS Manifest 2.0 `manifest.yaml` for a later conversion step. This workflow prepares configuration; it does not write a LeRobot dataset or submit a CloudRobo processing task. The bundled implementation is based on [`bag2manifest`](https://github.com/rebornczs/bag2manifest) revision `0926db6`, with local ROS Manifest 2.0 updates synchronized to the independent repository, under its MIT license (`scripts/bag2manifest/LICENSE`).

## Choose a mode

### Terminal conversation

Use this when the user wants to work in chat, inspect a bag, or generate a manifest without opening a browser. Install `scripts/bag2manifest/requirements-core.txt` in an isolated Python environment. Ask for a local bag path only if absent, then run:

```bash
python scripts/bag2manifest/generate_manifest.py <bag-path> --output <output-dir>
```

The command writes `summary.md`, `profile.json`, `choices.json`, `manifest.yaml`, and `issues.json`. Read `summary.md` first: it lists topic counts and frequencies, image metadata, state/action dimensions and sample ranges, timestamps, suggestions, and issues. Use the JSON files when more detail is needed. Present a compact summary, then ask for choices the recording cannot establish, especially ambiguous action topics (`E021`), task description, camera selection, and disputed state fields. Update `choices.json` and rerun with `--choices <output-dir>/choices.json`; pass `--confirm-action` only after the suggested action topic has been reviewed. Exit code 2 means the manifest is still a draft with unresolved errors. `issues.json` retains raw scan findings in `source` even after a user resolves them; use `unresolved_errors` and the exit code to judge the final draft. Deliver the manifest path and remaining warnings after validation passes.

Use `--msg-dir <definitions-dir>` for custom db3 messages, `--repo-id <org/name>` and `--task-text <text>` when known, and `--max-seconds N` for a quick first inspection. Recheck a final mapping against a representative full bag before a batch.

### Local Web workbench

Use this when the user asks for the page, browser preview, or visual mapping. Install `scripts/bag2manifest/requirements.txt` in an isolated Python environment, then start the bundled Gradio server from this skill directory:

```bash
python scripts/bag2manifest/start_web.py --port 7860
```

Keep the process running and give the user `http://127.0.0.1:7860`. The launcher binds to loopback and adds localhost to proxy bypass settings for Gradio's startup check. The workbench accepts a bag directory, `.mcap`, `.db3`, split `.db3` files, or `.zip`. Guide the user through camera thumbnails, state curves, action versus state overlays, and the output page's editable YAML validation. Use a different port if 7860 is occupied. Bind to another network interface only if the user requests remote access.

## Mapping and review

1. Read `profile.json` for topic types, frequencies, image samples, numeric field stats, suggestions, and source issues. Use the suggested mapping as a starting point, then confirm it against the robot's actual recording setup.
2. Confirm enabled cameras, names, image orientation and encoding, and fixed dimensions. Depth cameras are disabled by default. Use a consistent even `resize` where needed.
3. Preserve the order and meaning of the state vector. Constant joints from a sample remain present by default because removing them can change dimensions across bags. For `JointState`, select joints by name.
4. Confirm action source and strategy: `stored` or `next_state`. Multiple plausible action topics (`E021`) need an explicit choice. A `next_state` fallback is a suggestion, not evidence that it matches the robot's command stream. Gripper actions are never appended automatically: explicitly configure an expr or a per-field next_state with a flattened state_index and role=gripper.
5. Check time alignment (`W041`, `W043`), fps, task text or task topic, and any custom message definitions. A `.db3` with custom types needs matching `.msg` or `.idl` definitions via `--msg-dir`; MCAP commonly carries its own schema.
6. Review all entries in `issues.json`. Resolve error entries before handing the manifest to a conversion workflow. Treat warnings as checks against the actual recording, especially constant channels, action/state dimension differences, missing task text, and partial sampling. Test the manifest on a small episode before a full batch.

`choices.json` contains the editable defaults. Override top-level keys such as `cameras`, `state`, `action_strategy`, `action`, `fps`, `stamp_source`, `task_mode`, and `task_text`; arrays replace the whole default array. `state` and `action` choices may be scalar field paths (UI shorthand), Manifest 2.0 locator objects, per-field next_state actions, or derived expressions with `expr`, ordered `inputs` (`f0`, `f1`, …), optional `name`, and optional `normalize`. Use the visual workbench when the mapping needs image or curve inspection.

The bundled reader opens local data without sending it to an external service. In Web mode, the browser transfers selected files to the local Gradio server. The resulting `profile.json` can contain image thumbnails, field samples, and task text from the bag; handle it with the same access restrictions as the source recording.

For a concrete terminal dialogue and the corresponding Web handoff, see [Conversation example](bag2manifest-conversation-example.md).

## ROS 2.0 contract and source ownership

Read [ROS Manifest 2.0](ros-manifest-2.0.md) before generating or editing configuration. The export uses locator objects, embedded ordered JointState names, source.time/source.segment, and the new output keys. Preserve raw gripper scale unless the user requests an expr normalization; default interpolation depends on segment and role. For batch data, explicitly verify source.bag_glob (`--bag-glob` may override the sample-based guess).

The runnable local Web application is `scripts/bag2manifest/bag2manifest/webapp.py`. The independent `rebornczs/bag2manifest` repository is the implementation source; synchronize shared modules, CLI wrappers, tests and dependencies with this vendored copy when changing its contract. Keep skill orchestration and dialogue in references. `cloudrobo-samples` contains no tracked bag2manifest implementation and needs no source copy; examples there can reference the tool and this skill. Never assume the independent checkout exists on another user's machine.

## Unified Web workflow

State, action and extra features share one editor: select a dimension on the left; select its source and edit on the right; save changes in place. Add starts a new dimension. Search and topic filtering use one field picker; formulas reuse it for ordered inputs. Move/delete/undo stay above the dimension list. Curves remain visible below the editor and default to all current form dimensions, updating on add/delete/edit. Row selection is for editing and does not filter curves. Optional curve filters retain dimension identity through reorder; clicking legend items can hide traces. Plot normalization affects display only; formula normalization writes configuration only when enabled.

Action supports original fields, formulas and a next-state dimension. State references retain the selected dimension's identity through reorder; deletion marks the reference invalid and blocks export until restored or reselected. Advanced field controls expose role, interpolation and default. Output name and fixed normalization interval can be edited in place.

Output order: dataset information → task source with conditional text/topic input and samples → FPS/message timestamp source/tolerance → batch glob and per_bag/min_frames → advanced file splitting/codec/curation → final summary, validation and download. per_bag and hold are explanatory text, not single-option radio controls. Form changes invalidate previous downloads. YAML edits require revalidation and do not update form controls.

Do not invent a master topic or synchronization policy: the provided ROS specification does not define the target frame timeline, start/end bounds, auto timestamp fallback hierarchy, log_time versus rosbag_time distinction, interpolation/tolerance coupling, first-frame hold/default precedence, DB3 split-file episode grouping, or external task overrides in topic mode. Identify these as unresolved converter behavior and request the converter code or specification when a task depends on them. Curves are sampled previews, not converter synchronization results.

## Conversation decision preferences

If the user requests automatic operation, inspect the bag, let the model select mapping under the ROS rules, generate and validate, and deliver decisions/assumptions without asking at every step. The command's automatic inference is rules-based; the model's choices go through choices.json. A missing decoder or unusable required data still blocks a valid final export. If the user requests interactive operation, ask about the specified choices or material ambiguity. Existing user authorization persists; avoid repeating decisions already supplied. Do not represent the Web as having an embedded LLM: it runs deterministic inference and human editing.
