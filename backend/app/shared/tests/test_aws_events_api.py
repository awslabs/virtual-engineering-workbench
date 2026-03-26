import json

import assertpy
import boto3
import moto
import pytest

from app.shared.api import aws_events_api


@pytest.fixture(autouse=True)
def mock_events_client():
    with moto.mock_aws():
        yield boto3.client("events", "eu-central-1")


def test_put_events_should_publish_to_event_bridge(mock_events_client):
    # ARRANGE
    events_api = aws_events_api.AWSEventsApi(client=mock_events_client)

    # ACT
    response = events_api.put_event(
        source="manual:onboarding",
        detail=json.dumps({"test": "test"}),
        resources=["onboardingSource"],
        detail_type="myDetailType",
    )

    # ASSERT
    assertpy.assert_that(response.failed_entry_count).is_equal_to(0)
    assertpy.assert_that(response.entries).is_length(1)
