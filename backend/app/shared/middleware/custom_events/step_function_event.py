from aws_lambda_powertools.utilities.data_classes.common import DictWrapper


class StepFunctionEvent(DictWrapper):
    @property
    def event_type(self) -> str:
        """Type of the event sent from the step function"""
        return self["eventType"]
