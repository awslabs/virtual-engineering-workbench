from decimal import Decimal

import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException


def test_should_create_agreement_request(mock_moto_calls, get_marketplace_procurement_srv):
    # ARRANGE — requestedTerms list for the usage-based flow.
    requested_terms = [
        {"id": "term-usage-1"},
        {"id": "term-legal-1"},
    ]

    # ACT
    quote = get_marketplace_procurement_srv.create_agreement_request(
        client_token="token-abc",
        agreement_proposal_identifier="at-proposalabc123",
        requested_terms=requested_terms,
    )

    # ASSERT
    mock_moto_calls["CreateAgreementRequest"].assert_called_once_with(
        clientToken="token-abc",
        intent="NEW",
        agreementProposalIdentifier="at-proposalabc123",
        requestedTerms=requested_terms,
    )
    assertpy.assert_that(quote.agreementRequestId).is_equal_to("ar-1234567890abc")
    assertpy.assert_that(quote.chargeSummary).is_not_none()
    assertpy.assert_that(quote.chargeSummary.newAgreementValue).is_equal_to(Decimal("42.00"))
    assertpy.assert_that(quote.chargeSummary.newAgreementValueAfterTax).is_equal_to(Decimal("46.20"))
    assertpy.assert_that(quote.chargeSummary.currencyCode).is_equal_to("USD")


def test_should_pass_configurable_upfront_term_configuration(mock_moto_calls, get_marketplace_procurement_srv):
    """Guards the AWS-documented shape for annual upfront pricing:
    ``requestedTerms`` entries can carry a ``configuration`` payload that
    must be forwarded verbatim to the AWS API."""
    # ARRANGE
    requested_terms = [
        {
            "id": "term-annual-1",
            "configuration": {
                "configurableUpfrontPricingTermConfiguration": {
                    "selectorValue": "P365D",
                    "dimensions": [{"dimensionKey": "Users", "dimensionValue": 100}],
                }
            },
        }
    ]

    # ACT
    get_marketplace_procurement_srv.create_agreement_request(
        client_token="token-def",
        agreement_proposal_identifier="at-def456",
        requested_terms=requested_terms,
    )

    # ASSERT — the configuration payload must be forwarded verbatim.
    _, called_kwargs = mock_moto_calls["CreateAgreementRequest"].call_args
    assertpy.assert_that(called_kwargs["requestedTerms"]).is_equal_to(requested_terms)
    assertpy.assert_that(called_kwargs["intent"]).is_equal_to("NEW")


def test_should_return_quote_without_charge_summary_when_response_omits_it(
    mock_moto_calls, get_marketplace_procurement_srv
):
    # ARRANGE
    mock_moto_calls["CreateAgreementRequest"].return_value = {"agreementRequestId": "ar-nocharge"}

    # ACT
    quote = get_marketplace_procurement_srv.create_agreement_request(
        client_token="token-xyz",
        agreement_proposal_identifier="at-xyz",
        requested_terms=[{"id": "term-1"}],
    )

    # ASSERT
    assertpy.assert_that(quote.agreementRequestId).is_equal_to("ar-nocharge")
    assertpy.assert_that(quote.chargeSummary).is_none()


def test_should_parse_charge_summary_when_only_new_agreement_value_present(
    mock_moto_calls, get_marketplace_procurement_srv
):
    """Pure usage-based pricing returns newAgreementValue=0 and omits
    newAgreementValueAfterTax; the adapter must not choke on the missing
    field."""
    # ARRANGE
    mock_moto_calls["CreateAgreementRequest"].return_value = {
        "agreementRequestId": "ar-usage-only",
        "chargeSummary": {"currencyCode": "USD", "newAgreementValue": "0"},
    }

    # ACT
    quote = get_marketplace_procurement_srv.create_agreement_request(
        client_token="t", agreement_proposal_identifier="at-p", requested_terms=[{"id": "term-1"}]
    )

    # ASSERT
    assertpy.assert_that(quote.chargeSummary.newAgreementValue).is_equal_to(Decimal("0"))
    assertpy.assert_that(quote.chargeSummary.newAgreementValueAfterTax).is_none()
    assertpy.assert_that(quote.chargeSummary.currencyCode).is_equal_to("USD")


def test_should_raise_request_rejected_when_create_agreement_request_is_invalid(
    mock_moto_calls, get_marketplace_procurement_srv
):
    from app.packaging.domain.exceptions.marketplace_request_rejected_exception import (
        MarketplaceRequestRejectedException,
    )

    # ARRANGE
    mock_moto_calls["CreateAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "invalid term"}},
        operation_name="CreateAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceRequestRejectedException, match="invalid term"):
        get_marketplace_procurement_srv.create_agreement_request(
            client_token="token", agreement_proposal_identifier="at-p", requested_terms=[]
        )


def test_should_raise_adapter_exception_when_create_agreement_request_is_denied(
    mock_moto_calls, get_marketplace_procurement_srv
):
    # ARRANGE
    mock_moto_calls["CreateAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "AccessDeniedException", "Message": "nope"}},
        operation_name="CreateAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_procurement_srv.create_agreement_request(
            client_token="token", agreement_proposal_identifier="at-p", requested_terms=[]
        )


def test_should_accept_agreement_request(mock_moto_calls, get_marketplace_procurement_srv):
    # ACT
    accepted = get_marketplace_procurement_srv.accept_agreement_request("ar-1234567890abc")

    # ASSERT
    mock_moto_calls["AcceptAgreementRequest"].assert_called_once_with(agreementRequestId="ar-1234567890abc")
    assertpy.assert_that(accepted.agreementId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_AGREEMENT_ID.value)


def test_should_raise_adapter_exception_when_accept_agreement_request_fails(
    mock_moto_calls, get_marketplace_procurement_srv
):
    # ARRANGE
    mock_moto_calls["AcceptAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "expired"}},
        operation_name="AcceptAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_procurement_srv.accept_agreement_request("ar-gone")


def test_accept_should_raise_a_conflict_exception_with_the_resource_aws_names(
    mock_moto_calls, get_marketplace_procurement_srv
):
    """AWS AcceptAgreementRequest raises ConflictException when the request
    is no longer acceptable, including when it was already accepted. The
    adapter raises the domain's conflict type with AWS's resourceType and
    resourceId so the command handler can check whether the acceptance
    already happened."""
    # ARRANGE
    mock_moto_calls["AcceptAgreementRequest"].side_effect = ClientError(
        error_response={
            "Error": {"Code": "ConflictException", "Message": "already accepted"},
            "resourceType": "Agreement",
            "resourceId": "agmt-existing",
        },
        operation_name="AcceptAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException) as exc_info:
        get_marketplace_procurement_srv.accept_agreement_request("ar-already")
    assertpy.assert_that(exc_info.value.resource_type).is_equal_to("Agreement")
    assertpy.assert_that(exc_info.value.resource_id).is_equal_to("agmt-existing")


def test_conflict_exception_is_not_an_adapter_exception(mock_moto_calls, get_marketplace_procurement_srv):
    """Calibration: the two failure kinds stay distinguishable."""
    # ARRANGE
    mock_moto_calls["AcceptAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "already accepted"}},
        operation_name="AcceptAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException) as exc_info:
        get_marketplace_procurement_srv.accept_agreement_request("ar-already")
    assertpy.assert_that(isinstance(exc_info.value, adapter_exception.AdapterException)).is_false()
    assertpy.assert_that(exc_info.value.resource_type).is_none()
    assertpy.assert_that(exc_info.value.resource_id).is_none()


def test_should_cancel_agreement(mock_moto_calls, get_marketplace_procurement_srv):
    # ACT
    get_marketplace_procurement_srv.cancel_agreement(GlobalVariables.TEST_MARKETPLACE_AGREEMENT_ID.value)

    # ASSERT
    mock_moto_calls["CancelAgreement"].assert_called_once_with(
        agreementId=GlobalVariables.TEST_MARKETPLACE_AGREEMENT_ID.value
    )


def test_should_raise_adapter_exception_when_cancel_agreement_fails(mock_moto_calls, get_marketplace_procurement_srv):
    # ARRANGE
    mock_moto_calls["CancelAgreement"].side_effect = ClientError(
        error_response={"Error": {"Code": "AccessDeniedException", "Message": "nope"}},
        operation_name="CancelAgreement",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_procurement_srv.cancel_agreement("agmt-bad")


def test_cancel_should_raise_a_conflict_exception(mock_moto_calls, get_marketplace_procurement_srv):
    """AWS CancelAgreement raises ConflictException when the agreement
    cannot be cancelled in its current state, including when it is already
    cancelled. The adapter raises the domain's conflict type so the command
    handler can check the agreement's status."""
    # ARRANGE
    mock_moto_calls["CancelAgreement"].side_effect = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "already cancelled"}},
        operation_name="CancelAgreement",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException):
        get_marketplace_procurement_srv.cancel_agreement("agmt-already")


def test_create_should_raise_a_conflict_exception_when_a_token_is_reused_with_other_terms(
    mock_moto_calls, get_marketplace_procurement_srv
):
    # ARRANGE
    mock_moto_calls["CreateAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "token reused"}},
        operation_name="CreateAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException):
        get_marketplace_procurement_srv.create_agreement_request(
            client_token="token-abc", agreement_proposal_identifier="at-proposal", requested_terms=[{"id": "t"}]
        )


def test_cancel_should_report_an_unsupported_cancellation_as_a_domain_error(
    mock_moto_calls, get_marketplace_procurement_srv
):
    """AWS answers CancelAgreement for an agreement that was accepted a
    moment ago with ValidationException "This action is not supported." Left
    as an adapter error that surfaced as an HTTP 500 with no reason; as a
    domain error the buyer gets a 400 that says what to do instead."""
    # ARRANGE
    mock_moto_calls["CancelAgreement"].side_effect = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "This action is not supported."}},
        operation_name="CancelAgreement",
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as raised:
        get_marketplace_procurement_srv.cancel_agreement("agmt-free")

    # ASSERT
    assertpy.assert_that(str(raised.value)).contains("agmt-free").contains("This action is not supported.")
    assertpy.assert_that(str(raised.value)).contains("Try again in a few minutes").contains("AWS Marketplace console")


def test_accept_should_report_a_rejected_request_as_a_domain_error(mock_moto_calls, get_marketplace_procurement_srv):
    # ARRANGE
    mock_moto_calls["AcceptAgreementRequest"].side_effect = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "The agreement request has expired."}},
        operation_name="AcceptAgreementRequest",
    )

    # ACT / ASSERT
    with pytest.raises(domain_exception.DomainException, match="The agreement request has expired."):
        get_marketplace_procurement_srv.accept_agreement_request("ar-expired")
