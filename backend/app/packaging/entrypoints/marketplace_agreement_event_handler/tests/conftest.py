from enum import Enum
from unittest import mock

import boto3
import moto
import pytest
from attr import dataclass


class GlobalVariables(Enum):
    TEST_TABLE_NAME = "TEST"
    TEST_REGION = "us-east-1"
    TEST_AGREEMENT_ID = "agmt-9xyz8wmklp67rt32nb1qv45ds"
    TEST_OFFER_ID = "offer-abcdef123456"
    TEST_PRODUCT_ID = "prod-abc123xyz456"
    TEST_ACCEPTOR_ACCOUNT = "987654321098"
    TEST_PROPOSER_ACCOUNT = "123456789012"
    TEST_REQUEST_ID = "7f3e2d1c-a9b8-4f5e-6d7c-1234567890ab"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "MarketplaceAgreementEventHandler")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture(autouse=True)
def mock_sts(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("sts", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:us-east-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


def _base_event(detail_type: str, detail: dict) -> dict:
    """Wrap ``detail`` in an EventBridge envelope matching AWS's
    ``aws.agreement-marketplace`` shape.

    The account IDs here are the ones AWS would populate on the outer
    envelope for a buyer-side event.
    """
    return {
        "version": "0",
        "id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
        "detail-type": detail_type,
        "source": "aws.agreement-marketplace",
        "account": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value,
        "time": "2024-08-30T21:36:03Z",
        "region": "us-east-1",
        "resources": [f"arn:aws:aws-marketplace::aws:agreement:{GlobalVariables.TEST_AGREEMENT_ID.value}"],
        "detail": detail,
    }


@pytest.fixture
def created_new_event():
    """``Purchase Agreement Created - Acceptor`` — ``NEW`` intent.

    First-time creation carries no ``product`` block and no
    ``previousAgreementId``.
    """

    def _make():
        return _base_event(
            "Purchase Agreement Created - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "intent": "NEW",
                    "status": "ACTIVE",
                    "acceptanceTime": "2024-06-26T21:36:03Z",
                    "startTime": "2024-08-30T21:36:03Z",
                    "endTime": "2025-05-30T21:36:03Z",
                },
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {"accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value},
                "offer": {"id": GlobalVariables.TEST_OFFER_ID.value},
            },
        )

    return _make


@pytest.fixture
def created_renew_event():
    """``Purchase Agreement Created - Acceptor`` — ``RENEW`` intent.

    Auto-renewal includes ``previousAgreementId``, a ``product`` block,
    and human-readable ``proposer.name`` / ``offer.name``.
    """

    def _make():
        return _base_event(
            "Purchase Agreement Created - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": "agmt-newrenewalagreementid",
                    "intent": "RENEW",
                    "status": "ACTIVE",
                    "startTime": "2025-05-30T21:36:03Z",
                    "endTime": "2026-05-30T21:36:03Z",
                    "previousAgreementId": GlobalVariables.TEST_AGREEMENT_ID.value,
                },
                "product": {"id": GlobalVariables.TEST_PRODUCT_ID.value, "title": "Example Product Title"},
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {
                    "name": "Example Seller Name",
                    "accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value,
                },
                "offer": {"id": GlobalVariables.TEST_OFFER_ID.value, "name": "Example Offer Name"},
            },
        )

    return _make


@pytest.fixture
def amended_event():
    """``Purchase Agreement Amended - Acceptor`` — buyer opt-out example."""

    def _make():
        return _base_event(
            "Purchase Agreement Amended - Acceptor",
            {
                "requestId": "3d4c9f9b-b809-4f5e-9fac-a9ae98b05cbb",
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "intent": "AMEND",
                    "status": "ACTIVE",
                    "acceptanceTime": "2024-06-26T21:36:03Z",
                    "startTime": "2024-08-30T21:36:03Z",
                    "endTime": "2025-05-30T21:36:03Z",
                    "autoRenewalEnabled": True,
                },
                "renewalSummary": {
                    "lockoutStartTime": "2025-05-20T21:36:03Z",
                    "disabledBy": "ACCEPTOR",
                },
                "product": {"id": GlobalVariables.TEST_PRODUCT_ID.value, "title": "Example Product Title"},
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {"accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value},
                "offer": {"id": GlobalVariables.TEST_OFFER_ID.value, "name": "Example Offer Name"},
            },
        )

    return _make


@pytest.fixture
def ended_event():
    """``Purchase Agreement Ended - Acceptor`` — ``CANCELLED`` reason."""

    def _make(status: str = "CANCELLED"):
        return _base_event(
            "Purchase Agreement Ended - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "status": status,
                },
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {"accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value},
                "offer": {"id": GlobalVariables.TEST_OFFER_ID.value},
            },
        )

    return _make


@pytest.fixture
def ending_event():
    """``Purchase Agreement Ending - Acceptor`` — 180-day bucket."""

    def _make(days: int = 180):
        return _base_event(
            "Purchase Agreement Ending - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "startTime": "2024-08-30T21:36:03Z",
                    "endTime": "2025-05-30T21:36:03Z",
                    "daysBeforeEndTime": days,
                    "autoRenewalEnabled": True,
                    "status": "ACTIVE",
                },
                "renewalSummary": {
                    "lockoutStartTime": "2025-05-20T21:36:03Z",
                    "disabledBy": "ACCEPTOR",
                },
                "product": {"id": GlobalVariables.TEST_PRODUCT_ID.value, "title": "Example Product Title"},
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {
                    "name": "Example Seller Name",
                    "accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value,
                },
                "offer": {"id": GlobalVariables.TEST_OFFER_ID.value, "name": "Example Offer Name"},
            },
        )

    return _make


@pytest.fixture
def renewal_terms_finalized_event():
    """``Purchase Agreement Renewal Terms Finalized - Acceptor``."""

    def _make():
        return _base_event(
            "Purchase Agreement Renewal Terms Finalized - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "startTime": "2024-08-30T21:36:03Z",
                    "endTime": "2025-05-30T21:36:03Z",
                },
                "renewalSummary": {
                    "tcv": "105000.00",
                    "currency": "USD",
                    "termsFinalizedTime": "2025-05-15T21:36:03Z",
                    "lockoutReached": False,
                    "lockoutStartTime": "2025-05-20T21:36:03Z",
                },
                "product": {"id": GlobalVariables.TEST_PRODUCT_ID.value, "title": "Example Product Title"},
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {
                    "name": "Example Seller Name",
                    "accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value,
                },
            },
        )

    return _make


@pytest.fixture
def renewal_upcoming_event():
    """``Purchase Agreement Renewal Upcoming - Acceptor``."""

    def _make():
        return _base_event(
            "Purchase Agreement Renewal Upcoming - Acceptor",
            {
                "requestId": GlobalVariables.TEST_REQUEST_ID.value,
                "catalog": "AWSMarketplace",
                "agreement": {
                    "id": GlobalVariables.TEST_AGREEMENT_ID.value,
                    "startTime": "2024-08-30T21:36:03Z",
                    "endTime": "2025-05-30T21:36:03Z",
                },
                "renewalSummary": {
                    "lockoutReached": True,
                    "tcv": "105000.00",
                    "currency": "USD",
                },
                "product": {"id": GlobalVariables.TEST_PRODUCT_ID.value, "title": "Example Product Title"},
                "acceptor": {"accountId": GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value},
                "proposer": {
                    "name": "Example Seller Name",
                    "accountId": GlobalVariables.TEST_PROPOSER_ACCOUNT.value,
                },
            },
        )

    return _make


@pytest.fixture
def mocked_command_bus():
    """Autospec of the command bus so tests can assert dispatched commands
    without going through the real handlers/message bus."""
    from app.shared.adapters.message_bus import command_bus

    return mock.create_autospec(spec=command_bus.CommandBus)


@pytest.fixture(autouse=True)
def ami_agreement_gate(aws_credentials, mock_sts):
    """Admit every agreement as AMI-only by default.

    The handler gates all six event types on
    ``dependencies.agreement_svc.is_ami_agreement``, which calls
    ``DescribeAgreement``. moto does not implement the
    ``marketplace-agreement`` service, so without this the existing
    dispatch tests would exercise a live AWS call. Tests that care about
    the gate override the return value or side effect.

    Depends on ``aws_credentials`` and ``mock_sts`` so that importing the
    handler here cannot beat them: the handler builds its Powertools
    ``Metrics`` and its boto session at module import, and both need the
    environment those two fixtures install.
    """
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    svc = mock.MagicMock()
    svc.is_ami_agreement.return_value = True
    original = handler.dependencies.agreement_svc
    handler.dependencies.agreement_svc = svc
    yield svc
    handler.dependencies.agreement_svc = original
