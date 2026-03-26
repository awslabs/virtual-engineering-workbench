from typing import Optional

from pydantic import BaseModel, Field


class TaskContext(BaseModel):
    aws_request_id: str = Field(..., title="AwsRequestId")
    function_name: str = Field(..., title="FunctionName")
    function_version: Optional[str] = Field(None, title="FunctionVersion")
    log_group_name: Optional[str] = Field(None, title="LogGroupName")
    log_stream_name: Optional[str] = Field(None, title="LogStreamName")
    invoked_function_arn: str = Field(..., title="InvokedFunctionArn")
    memory_limit_in_mb: int = Field(..., title="MemoryLimitInMb")
