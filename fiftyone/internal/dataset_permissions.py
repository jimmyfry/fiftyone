"""
FiftyOne Teams dataset permissions utilities.

| Copyright 2017-2023, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import enum
import inspect
from functools import wraps

import fiftyone.internal.context_vars as fo_context_vars
from fiftyone.internal.util import get_api_url
from fiftyone.internal.requests import make_sync_request


_API_URL = get_api_url()

_DATASET_USER_PERMISSION_QUERY = """
query DatasetUserPermissionQuery($dataset: String!, $userId: String!) {
  dataset(identifier: $dataset) {
    user(id: $userId) {
      activePermission
    }
  }
}
"""


class DatasetPermission(enum.Enum):
    """Enum for possible dataset permission levels"""

    NO_ACCESS = 0
    VIEW = 1
    TAG = 2
    EDIT = 3
    MANAGE = 4


class ReadOnlyObjectException(ValueError):
    """Exception for mutating a read-only object."""

    def __init__(self, class_name):
        message = f"Cannot edit a read-only {class_name} object"
        super().__init__(message)


class DatasetPermissionException(PermissionError):
    """Exception for using an impermissible action on a dataset."""

    def __init__(self, class_name, dataset_permission):
        if dataset_permission is None:
            message = f"User does not have access to this {class_name} object."
        else:
            message = (
                f"User does not have {dataset_permission.name} permission "
                f"on this {class_name} object necessary to perform this action."
            )
        super().__init__(message)


def _access_nested_element(root, nested_attrs):
    node = root
    # Traverse nested attributes if any, get()ing or getattr()ing along the way.
    for attr in nested_attrs:
        if node is None:
            break
        elif isinstance(node, dict):
            node = node.get(attr, None)
        else:
            node = getattr(node, attr, None)
    return node


def get_dataset_permissions_for_current_user(dataset):
    """Get active permission to the dataset for the user in context_vars, if any."""
    user_id = fo_context_vars.running_user_id.get()
    if not user_id:
        return None

    result = make_sync_request(
        f"{_API_URL}/graphql/v1",
        None,  # FIFTYONE_API_KEY will be used if token is None
        _DATASET_USER_PERMISSION_QUERY,
        variables={"dataset": dataset, "userId": user_id},
    )

    result = _access_nested_element(
        result, ("data", "dataset", "user", "activePermission")
    )

    if not result or result == "NO_ACCESS":
        raise DatasetPermissionException("Dataset", None)

    return DatasetPermission[result]


def _get_argument_by_param_name(func, param_name, *args, **kwargs):
    # Resolve function arguments
    bound_args = inspect.signature(func).bind(*args, **kwargs)
    bound_args.apply_defaults()

    # Support "." notation to get nested fields
    chunks = param_name.split(".")
    param_name = chunks[0]
    nested_attrs = chunks[1:]

    if param_name in bound_args.arguments:
        arg = bound_args.arguments[param_name]
    elif param_name in kwargs:
        arg = kwargs[param_name]
    else:
        raise RuntimeError(
            f"Param '{param_name}' is not in signature"
            f" of function '{func.__name__}'"
        )

    # Traverse nested attributes if any, get()ing or getattr()ing along the way.
    arg = _access_nested_element(arg, nested_attrs)

    return arg


def _mutates_data(
    maybe_func=None,
    *,
    condition_param=None,
    data_obj_param="self",
    permission_required=DatasetPermission.EDIT,
    enforce_readonly=True,
):
    """Private decorator that applies mutation checks on the function.
    Including readonly and permission checking.
    """

    def check_readonly_decorator(func):
        @wraps(func)
        def check_readonly_wrapper(*args, **kwargs):
            try:
                data_object = _get_argument_by_param_name(
                    func, data_obj_param, *args, **kwargs
                )
            except TypeError:
                # If we get a TypeError here that means the arguments are
                #   invalid so we can just run the function which will throw
                #   the TypeError itself, thus leaving ourselves out of the
                #   stack trace.
                pass

            else:
                deny_exception = None
                if (
                    enforce_readonly
                    and hasattr(data_object, "_readonly")
                    and bool(data_object._readonly)
                ):
                    deny_exception = ReadOnlyObjectException(
                        type(data_object).__name__
                    )
                elif (
                    hasattr(data_object, "_permission")
                    and data_object._permission is not None
                    and data_object._permission.value
                    < permission_required.value
                ):
                    deny_exception = DatasetPermissionException(
                        type(data_object).__name__, permission_required
                    )
                if deny_exception:
                    if condition_param is None or bool(
                        _get_argument_by_param_name(
                            func, condition_param, *args, **kwargs
                        )
                    ):
                        raise deny_exception

            return func(*args, **kwargs)

        return check_readonly_wrapper

    return (
        check_readonly_decorator(maybe_func)
        if maybe_func
        else check_readonly_decorator
    )


def requires_can_tag(
    maybe_func=None, *, condition_param=None, data_obj_param="self"
):
    """Decorator to notate a dataset function requires TAG permission"""
    return _mutates_data(
        maybe_func=maybe_func,
        condition_param=condition_param,
        data_obj_param=data_obj_param,
        permission_required=DatasetPermission.TAG,
    )


def requires_can_edit(
    maybe_func=None,
    *,
    condition_param=None,
    data_obj_param="self",
    enforce_readonly=True,
):
    """Decorator to notate a dataset function requires EDIT permission"""
    return _mutates_data(
        maybe_func=maybe_func,
        condition_param=condition_param,
        data_obj_param=data_obj_param,
        permission_required=DatasetPermission.EDIT,
        enforce_readonly=enforce_readonly,
    )


def requires_can_manage(
    maybe_func=None, *, condition_param=None, data_obj_param="self"
):
    """Decorator to notate a dataset function requires MANAGE permission"""
    return _mutates_data(
        maybe_func=maybe_func,
        condition_param=condition_param,
        data_obj_param=data_obj_param,
        permission_required=DatasetPermission.MANAGE,
    )