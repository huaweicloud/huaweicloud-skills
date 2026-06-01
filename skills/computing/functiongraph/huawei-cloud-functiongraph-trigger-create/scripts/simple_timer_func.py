def handler(event, context):
    import json
    from datetime import datetime
    
    result = {
        "message": "Timer triggered successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "event": event
    }
    
    print(json.dumps(result, ensure_ascii=False))
    return result