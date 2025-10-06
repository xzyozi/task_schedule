import importlib
import json
import base64
import sys
import traceback

def _resolve_func(path):
    """Resolves a function from a string path."""
    if ':' not in path:
        raise ValueError("Invalid function path format. Expected 'module.path:function_name'")
    module_path, func_name = path.rsplit(':', 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)

def main():
    """
    Wrapper to execute a Python function with serialized arguments.
    Expects two command-line arguments:
    1. The target function path (e.g., 'my.module:my_func').
    2. A Base64 encoded JSON string of a dictionary with 'args' and 'kwargs' keys.
    """
    if len(sys.argv) != 3:
        print("Usage: python_job_wrapper.py <function_path> <base64_json_payload>", file=sys.stderr)
        sys.exit(1)

    target_func_path = sys.argv[1]
    payload_b64 = sys.argv[2]

    try:
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        args = payload.get('args', [])
        kwargs = payload.get('kwargs', {})
        
        target_func = _resolve_func(target_func_path)
        
        result = target_func(*args, **kwargs)
        
        if result is not None:
            print(result)
        
        sys.exit(0)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
