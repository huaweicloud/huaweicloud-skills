"""
FunctionGraph function: Return a pre-created DevBridge API Key to the ECS.

Architecture (B1):
  Sandbox (before apply) -> ensure a DevBridge API Key exists (reuse, or create it
  via DevStage API using the sandbox's user-level AK/SK)
  Terraform apply -> writes that key into this function's user_data as EXISTING_API_KEY
  ECS (at boot) -> metadata service (get agency STS) -> invoke this function -> receive the key

  The function holds NO AK/SK. Creating the key happens in the sandbox (where user-level
  AK/SK is available and DevStage accepts it), NOT inside this function. The function only
  forwards the pre-created key.

Security:
  - Function user_data contains ONLY a DevBridge API Key (revocable, tunnel-only scope),
    never AK/SK
  - tfstate therefore contains no AK/SK (only the revocable DevBridge API Key)
  - The ECS only receives the resulting DevBridge API Key, never AK/SK
  - IAM agency restricts who can invoke this function
"""
import json


def handler(event, context):
    """Return the pre-created DevBridge API Key to the ECS.

    The key was created in the sandbox before apply and passed in as EXISTING_API_KEY.
    This function does not (and cannot) create a key itself — it only forwards.

    Returns:
        dict: {"api_key": "..."} on success, {"error": "..."} otherwise.
    """
    existing_key = ''
    try:
        existing_key = context.getUserData('EXISTING_API_KEY') or ''
    except Exception:
        existing_key = ''

    if existing_key and existing_key not in ('null', ''):
        return {"api_key": existing_key}

    return {
        "error": (
            "No DevBridge API Key provided. The key must be pre-created in the sandbox "
            "before apply — see ecs-devbridge-option.md Step 0."
        )
    }
