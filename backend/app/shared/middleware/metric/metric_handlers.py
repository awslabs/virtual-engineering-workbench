import base64
import functools
import hmac
import json
import time
from typing import Callable, Dict, Optional

from aws_lambda_powertools.metrics import Metrics

from app.shared.api import secrets_manager_api
from app.shared.middleware.metric.types import StandardMetrics


def _get_data(args, kwargs):
    op = None
    user_name = None
    path = None
    if "event" in kwargs:
        op = kwargs.get("event").get("requestContext", {}).get("operationName", None)
        user_name = kwargs.get("event").get("requestContext", {}).get("authorizer", {}).get("userName", None)
        path = kwargs.get("event").get("requestContext", {}).get("path", None)
    elif args:
        op = args[0].get("requestContext", {}).get("operationName", None)
        user_name = args[0].get("requestContext", {}).get("authorizer", {}).get("userName", None)
        path = args[0].get("requestContext", {}).get("path", None)

    return op, user_name, path


def _add_metric_dimensions(metric_dimensions: Dict[str, str], metrics: Metrics, op):
    for name, value in metric_dimensions.items():
        metrics.add_dimension(name, value)

    if op:
        metrics.add_dimension("operationName", op)


def report_invocation_metrics(  # noqa: C901
    dimensions: Optional[Dict[str, str]] = None,
    service: Optional[str] = None,
    namespace: Optional[str] = None,
    enable_audit: Optional[bool] = False,
    region_name: Optional[str] = "us-east-1",
    secret_name: Optional[str] = None,
):
    """
    Handler/decorator that can be wrapped around backend functions to handle metric reporting.
    Following are the rules:
    * On successful call to the function:
        - The following metrics are published:
            *.Success(1)
            *.TotalCount(1)
            *.Duration(duration of the function call in milliseconds)
        - Returns original value returned from the wrapped function
    * On all other exceptions:
        - The following metrics are published:
            *.Failure(1)
            *.TotalCount(1)
            *.Duration(duration of the function call in milliseconds)
        - Re-raises the exception
    :param Optional[Dict[str, str]] dimensions: Metric dimensions as a
        Dict[<dimension_name>: <dimension_value>] that should be assigned to the published metrics.
    :param Optional[str] service: Metric service name e.g Products/Projects/Authorizer. If None, the default value
        defined in POWERTOOLS_SERVICE_NAME env. variable will be used, Defaults to None.
    :param Optional[str] namespace: Metric namespace. If None, the default value
        defined in POWERTOOLS_METRICS_NAMESPACE env. variable is used e.g VirtualEngineeringWorkbench. Defaults to None.
    """
    metric_dimensions = dimensions or {}
    metrics = Metrics(service, namespace)
    if enable_audit:
        try:
            secrets_manager = secrets_manager_api.SecretsManagerAPI(region=region_name, session=None)
            key_val = secrets_manager.get_secret_value(secret_id=secret_name)
        except Exception:
            metrics.add_metric(StandardMetrics.SecretFetchError.name, StandardMetrics.SecretFetchError.unit, 1)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = _get_data(args, kwargs)
            op, user_name, path = data

            _add_metric_dimensions(metric_dimensions, metrics, op)
            # _add_metric_metadata(user_name, enable_audit, key_val, metrics, path)
            if user_name and enable_audit:
                hmac_user_name = hmac.new(key=key_val.encode(), msg=user_name.encode(), digestmod="sha1")
                decoded_user_name = base64.b64encode(hmac_user_name.digest()).decode()
                metrics.add_metadata(key="userName", value=decoded_user_name)

            if path:
                metrics.add_metadata(key="path", value=path)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                metrics.add_metric(StandardMetrics.Success.name, StandardMetrics.Success.unit, 1)
                return result
            except Exception:
                metrics.add_metric(StandardMetrics.Failure.name, StandardMetrics.Failure.unit, 1)
                raise
            finally:
                metrics.add_metric(StandardMetrics.TotalCount.name, StandardMetrics.TotalCount.unit, 1)
                duration_ms = (time.perf_counter() - start_time) * 1000
                metrics.add_metric(StandardMetrics.Duration.name, StandardMetrics.Duration.unit, duration_ms)
                metric_obj = metrics.serialize_metric_set()
                metrics.clear_metrics()
                print(json.dumps(metric_obj))

        return wrapper

    return decorator
