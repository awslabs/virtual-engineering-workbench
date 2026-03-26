import assertpy

from app.provisioning.domain.read_models import version


def test_add_version_should_store_version(
    mock_table_name, mock_dynamodb, mock_logger, get_sample_version, mock_ddb_repo
):
    # ARRANGE
    v = get_sample_version(
        parameters=[
            version.VersionParameter(
                parameterKey="test", parameterMetadata=version.ParameterMetadata(label="test-label")
            )
        ],
    )

    # ACT
    with mock_ddb_repo:
        mock_ddb_repo.get_repository(version.VersionPrimaryKey, version.Version).add(v)
        mock_ddb_repo.commit()

    # ASSERT
    with mock_ddb_repo:
        ent = mock_ddb_repo.get_repository(version.VersionPrimaryKey, version.Version).get(
            version.VersionPrimaryKey(
                productId="prod-1",
                versionId="vers-1",
                awsAccountId="001234567890",
            )
        )
    assertpy.assert_that(ent).is_equal_to(v)
