import hashlib


def test_should_accept_pending_resource_share_invitations(
    lambda_context, payload, mocked_accept_resource_share_invitation_request
):
    # ARRANGE

    from infra.constructs.ssm.handler import handler

    payload = payload(resource_type="Create")

    # ACT
    handler.handler(payload, lambda_context)

    # ASSERT
    mocked_accept_resource_share_invitation_request.assert_called_once_with(
        resourceShareInvitationArn="invitation-arn",
        clientToken=hashlib.sha256("invitation-arn".encode("utf-8")).hexdigest()[:64],
    )


def test_should_ignore_accepted_resource_share_invitations(
    lambda_context,
    payload,
    mocked_accept_resource_share_invitation_request,
    mocked_get_resource_share_invitations_response,
):
    # ARRANGE

    from infra.constructs.ssm.handler import handler

    payload = payload(resource_type="Create")
    mocked_get_resource_share_invitations_response["resourceShareInvitations"][0]["status"] = "ACCEPTED"

    # ACT
    handler.handler(payload, lambda_context)

    # ASSERT
    mocked_accept_resource_share_invitation_request.assert_not_called()
