import json
import os


def set_json_dict(file_path, data=None, set_attrs=None):
    if data is not None and not isinstance(data, dict):
        print(f"Error: data must be a dict")
        return False
    
    if set_attrs is not None and not isinstance(set_attrs, dict):
        print(f"Error: set_attrs must be a dict")
        return False
    
    if data is None and set_attrs is None:
        return os.path.exists(file_path)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    result = json.loads(content)
                else:
                    result = {}
        except (json.JSONDecodeError, Exception):
            result = {}
    else:
        result = {}
    
    if data is not None:
        result = data
    elif set_attrs is not None:
        if not isinstance(result, dict):
            result = {}
        result.update(set_attrs)
    
    return write_data_to_json(result, file_path, overwrite=True)


def write_data_to_json(data, file_path, overwrite=True):
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        file_exists = os.path.exists(file_path)
        
        if file_exists and not overwrite:
            print(f"File exists and overwrite=False: {file_path}")
            return False
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        
        operation = "overwrite" if file_exists else "create"
        print(f"Data {operation}: {file_path}")
        return True
        
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"File write error: {e}")
        return False
    except (TypeError, ValueError) as e:
        print(f"Data serialization error: {e}")
        return False
    except Exception as e:
        print(f"Unknown error: {e}")
        return False