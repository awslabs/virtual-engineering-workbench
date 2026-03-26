# -*- coding: utf-8 -*-
from typing import Optional

import constructs
from aws_cdk import aws_cloudwatch
from aws_cdk.aws_cloudwatch import (  # GraphWidget,; LogQueryWidget,; TextWidget,
    ComparisonOperator,
    IMetric,
    TreatMissingData,
)


class L3Alarm(constructs.Construct):
    """
    CDK Construct to create Cloudwatch Alarms
    """

    def __init__(
        self,
        scope: constructs.Construct,
        construct_id: str,
        alarm_name: str,
        alarm_description: str,
        metric: Optional[IMetric],
        threshold: Optional[int],
        evaluation_periods: Optional[int],
        datapoints_to_alarm: Optional[int],
    ) -> None:
        """
        Implements AWS Cloudwatch Alarm.

        Parameters
        ----------
        scope : Construct
            Scope within which this construct is defined
        id : str
            Identifier of the construct
        name : str
            Name of the cloudwatch alarm
        description : str
            Description of the cloudwatch alarm
        metric : cloudwatch IMetric
        Evaluation Periods : int
            Is the number of the most recent periods, or data points, to evaluate when determining alarm state
        Period : int
            Is the length of time to evaluate the metric or expression to create each individual data point for an alarm. It is expressed in seconds
        datapoints : int
            Is the number of data points within the Evaluation Periods that must be breaching to cause the alarm to go to the ALARM state

        """
        super().__init__(scope, construct_id)

        self._alarm = aws_cloudwatch.Alarm(
            self,
            "L3Alarm",
            alarm_name=alarm_name,
            alarm_description=alarm_description or None,
            actions_enabled=True,
            metric=metric,
            threshold=threshold,
            datapoints_to_alarm=datapoints_to_alarm,
            evaluation_periods=evaluation_periods,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )

    @property
    def alarm(self):
        """
        Return: The Cloudwatch Alarm
        """
        return self._alarm

    @property
    def alarm_arn(self):
        """
        Return: The Cloudwatch Alarm arn
        """
        return self._alarm.alarm_arn
