import functools
import inspect

from pydantic import BaseModel


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
            sig = inspect.signature(func)
            func_params = sig.parameters

            # This handles the case where parameters are passed in a 'params' dictionary
            # by our job_executor.
            if "params" in kwargs:
                # Case 1: The function expects a single argument that is a Pydantic model.
                if len(func_params) == 1:
                    param_name, param_obj = list(func_params.items())[0]
                    param_type = param_obj.annotation

                    if inspect.isclass(param_type) and issubclass(param_type, BaseModel):
                        try:
                            # Instantiate the Pydantic model with the provided dict.
                            model_instance = param_type(**kwargs["params"])
                            # Call the function with the single model instance.
                            return func(**{param_name: model_instance})
                        except Exception as e:
                            raise TypeError(
                                f"Failed to create Pydantic model '{param_type.__name__}' from parameters: {e}"
                            ) from e

                # Case 2: The function expects regular keyword arguments. Unpack the dict.
                return func(**kwargs["params"])

            # Fallback for direct calls (not from workflow executor)
            return func(*args, **kwargs)

        # Attach metadata to the function object for discovery
        wrapper._task_meta = {"enabled": enabled, "name": name, "description": description}
        return wrapper

    return decorator
