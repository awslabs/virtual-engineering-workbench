from aws_lambda_powertools.utilities.data_classes.common import DictWrapper


class ScheduledJobEvent(DictWrapper):
    @property
    def job_name(self) -> str:
        """Type of the event sent from the step function"""
        return self["jobName"]

    @property
    def parameters(self) -> dict | None:
        return self.get("parameters", None)
