from pydantic import BaseModel, Field


class MetricProducerJob(BaseModel):
    job_name: str = Field("MetricProducerJob", alias="jobName", const=True)
