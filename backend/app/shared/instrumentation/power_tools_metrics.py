from aws_lambda_powertools import metrics, single_metric

from app.shared.instrumentation import metrics as metrics_int


class PowerToolsMetrics(metrics_int.Metrics):
    def publish_counter(self, metric_name: str, metric_type: metrics_int.MetricType, count: int = 1) -> None:
        with single_metric(name=metric_name, unit=metrics.MetricUnit.Count, value=count) as metric:
            metric.add_dimension(name="type", value=metric_type)
