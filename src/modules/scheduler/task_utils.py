import functools

def task(enabled=True, name=None, description=None):
    """
    A decorator to mark a function as a discoverable task for the scheduler UI.

    Args:
        enabled (bool): Whether the task should be visible in the UI. Defaults to True.
        name (str, optional): The display name for the task in the UI. 
                              If not provided, the function name is used.
        description (str, optional): A short description for the task shown in the UI. 
                                     If not provided, the function's docstring is used.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Attach metadata to the function object for discovery
        wrapper._task_meta = {
            'enabled': enabled,
            'name': name,
            'description': description
        }
        return wrapper
    return decorator
