import assertpy
import pytest
from assertpy import assert_that

from app.publishing.domain.query_services import shared_amis_domain_query_service
from app.publishing.entrypoints.ami_sharing.model import step_function_model
from app.publishing.entrypoints.ami_sharing.model.step_function_model import SucceedAmiSharingResponse


def test_handle_decide_action(mock_dependencies, lambda_context):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.DecideActionRequest(
        productId="prod-123", versionId="vers-123", awsAccountId="123456789012", productType="WORKBENCH"
    )

    # ACT
    result = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_equal_to(
        step_function_model.DecideActionResponse(
            decision=shared_amis_domain_query_service.ShareAmiDecision.Done,
            originalAmiId="ami-12345",
            copiedAmiId="ami-54321",
            region="eu-west-3",
        ).dict(by_alias=True)
    )


def test_handle_decide_action_for_container_product(mock_dependencies, lambda_context, shared_amis_domain_qry_svc):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    shared_amis_domain_qry_svc.make_share_ami_decision.return_value = (
        shared_amis_domain_query_service.ShareAmiDecision.NOT_REQUIRED,
        "eu-west-3",
        "",
        "",
    )
    shared_amis_domain_qry_svc.verify_copy.return_value = True

    handler.dependencies = mock_dependencies
    request = step_function_model.DecideActionRequest(
        productId="prod-123", versionId="vers-123", awsAccountId="123456789012", productType="CONTAINER"
    )

    # ACT
    result = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result).is_equal_to(
        step_function_model.DecideActionResponse(
            decision=shared_amis_domain_query_service.ShareAmiDecision.NOT_REQUIRED,
            originalAmiId="",
            copiedAmiId="",
            region="eu-west-3",
        ).dict(by_alias=True)
    )


def test_handle_copy_ami(mock_dependencies, lambda_context):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.CopyAmiRequest(originalAmiId="ami-12345", region="eu-west-3")

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.CopyAmiResponse(copiedAmiId="ami-54321").dict(by_alias=True)
    )


def test_handle_share_ami(mock_dependencies, lambda_context):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.ShareAmiRequest(
        originalAmiId="ami-12345", copiedAmiId="ami-54321", region="eu-west-3", awsAccountId="123456789012"
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(step_function_model.ShareAmiResponse().dict(by_alias=True))


def test_handle_verify_copy(mock_dependencies, lambda_context):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies

    request = step_function_model.VerifyCopyRequest(region="eu-west-3", copiedAmiId="copy-12345")

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(
        step_function_model.VerifyCopyResponse(isCopyVerified=True).dict(by_alias=True)
    )


@pytest.mark.parametrize(
    "copied_ami_id, product_type, should_raise_error",
    [
        (None, "CONTAINER", False),
        ("", "CONTAINER", False),
        ("ami-67890xyz", "WORKBENCH", False),
        ("ami-67890xyz", "VIRTUAL_TARGET", False),
        ("", "WORKBENCH", True),
        ("", "VIRTUAL_TARGET", True),
        (None, "WORKBENCH", True),
        (None, "VIRTUAL_TARGET", True),
    ],
)
def test_handle_succeed_ami_sharing_handle_various_inputs(
    mock_dependencies, lambda_context, copied_ami_id, product_type, should_raise_error
):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.SucceedAmiSharingRequest(
        productId="prod-12345abc",
        versionId="vers-12345abc",
        awsAccountId="123456789012",
        copiedAmiId=copied_ami_id,
        previousEventName="ProductVersionCreationStarted",
        productType=product_type,
    )

    # ACT & ASSERT
    if should_raise_error:
        with pytest.raises(ValueError, match="copiedAmiId must be provided unless productType is 'Container'"):
            handler.handler(request.dict(by_alias=True), lambda_context)
    else:
        response = handler.handler(request.dict(by_alias=True), lambda_context)
        assert_that(response).is_not_none()
        assert_that(response).is_equal_to(SucceedAmiSharingResponse().dict(by_alias=True))


def test_handle_fail_ami_sharing(mock_dependencies, lambda_context):
    # ARRANGE
    from app.publishing.entrypoints.ami_sharing import handler

    handler.dependencies = mock_dependencies
    request = step_function_model.FailAmiSharingRequest(
        productId="prod-12345abc", versionId="vers-12345abc", awsAccountId="123456789012"
    )

    # ACT
    response = handler.handler(request.dict(by_alias=True), lambda_context)

    # ASSERT
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response).is_equal_to(step_function_model.FailAmiSharingResponse().dict(by_alias=True))
