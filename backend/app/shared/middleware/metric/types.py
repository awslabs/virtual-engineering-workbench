from typing import NamedTuple

from aws_lambda_powertools.metrics import MetricUnit


class MetricDimensionNames:
    ByAPI = "ByAPI"
    AsyncEventHandler = "AsyncEventHandler"
    Test = "Test"


class MetricDefinition(NamedTuple):
    name: str
    unit: MetricUnit


class StandardMetrics:
    """Standard metric definitions"""

    Success = MetricDefinition("Success", MetricUnit.Count)
    """ Number of successful calls """

    InvalidData = MetricDefinition("InvalidData", MetricUnit.Count)
    """ Number of calls with invocation errors (with invalid data passed in) """

    Failure = MetricDefinition("Failure", MetricUnit.Count)
    """ Number of failed calls (with exception raised) """

    TotalCount = MetricDefinition("TotalCount", MetricUnit.Count)
    """ Total number of calls """

    SecretFetchError = MetricDefinition("SecretFetchError", MetricUnit.Count)
    """ Number of failed secret manager fetch calls (with exception raised) """

    Duration = MetricDefinition("Duration", MetricUnit.Milliseconds)
    """ Latency or duration of the call in milliseconds """
