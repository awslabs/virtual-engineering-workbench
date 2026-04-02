from typing import Literal

from pydantic import BaseModel, Field


class MetricProducerJob(BaseModel):
    job_name: Literal["MetricProducerJob"] = Field("MetricProducerJob", alias="jobName")
