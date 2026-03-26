import time

import boto3
import pytest
from mypy_boto3_stepfunctions import client

STATE_MACHINE_ARN = "arn:aws:states:us-east-1:123456789012:stateMachine:AmiSharingStateMachine"
SFN_CLIENT: client.SFNClient = boto3.client(
    "stepfunctions", region_name="us-east-1", endpoint_url="http://localhost:8083"
)
MAX_RETRIES = 10


@pytest.fixture()
def start_execution():
    def _start_execution(test_name: str, test_event: str) -> str:
        result = SFN_CLIENT.start_execution(stateMachineArn=f"{STATE_MACHINE_ARN}#{test_name}", input=test_event)
        return result["executionArn"]

    return _start_execution


@pytest.fixture()
def wait_for_execution():
    def _wait_for_execution(execution_arn: str):
        status = "RUNNING"
        retries = 0
        output = None
        while status == "RUNNING" and retries < MAX_RETRIES:
            # Exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s, 3.2s, 6.4s (max)
            backoff = min(0.2 * (2**retries), 6.4)
            time.sleep(backoff)
            result = SFN_CLIENT.describe_execution(executionArn=execution_arn)
            status = result["status"]
            output = result.get("output")
            retries += 1
        history = SFN_CLIENT.get_execution_history(executionArn=execution_arn)
        return status, output, history

    return _wait_for_execution


@pytest.fixture()
def mocked_test_event():
    def _mocked_test_event(product_type: str = "WORKBENCH"):
        test_event = {
            "version": "0",
            "id": "a0fd2d09-02c3-1696-1cee-406e4cc14c86",
            "detail-type": "ProductVersionCreationStarted",
            "source": "proserve.workbench.publishing.dev",
            "account": "201223934255",
            "time": "2023-08-01T14:18:48Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventName": "ProductVersionCreationStarted",
                "productId": "prod-dt3ycosm",
                "versionId": "vers-1vbc9box",
                "awsAccountId": "105249321508",
                "productType": product_type,
            },
        }
        return str(test_event).replace("'", '"')

    return _mocked_test_event
