from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_delete_recipe(mock_moto_calls, get_ec2_image_builder_recipe_srv):
    # ARRANGE & ACT
    get_ec2_image_builder_recipe_srv.delete(recipe_version_arn=GlobalVariables.TEST_IMAGE_RECIPE_ARN.value)

    # ASSERT
    delete_component_kwargs = {
        "imageRecipeArn": GlobalVariables.TEST_IMAGE_RECIPE_ARN.value,
    }
    mock_moto_calls["DeleteImageRecipe"].assert_called_once_with(**delete_component_kwargs)


def test_should_create_recipe(mock_moto_calls, get_ec2_image_builder_recipe_srv):
    # ARRANGE &  ACT
    response = get_ec2_image_builder_recipe_srv.create(
        name=GlobalVariables.TEST_RECIPE_NAME.value,
        description=GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
        version=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        component_arns=[
            (
                f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
                f"{GlobalVariables.AWS_ACCOUNT_ID.value}:component/"
                f"{GlobalVariables.TEST_COMPONENT_ID.value}/"
                f"/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}/1"
            )
        ],
        parent_image=GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
        volume_size=int(GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value),
    )

    # ASSERT
    create_recipe_kwargs = {
        "blockDeviceMappings": [
            {
                "deviceName": "/dev/sda1",
                "ebs": {
                    "encrypted": True,
                    "kmsKeyId": f"arn:aws:kms:{GlobalVariables.TEST_REGION.value}:{GlobalVariables.AWS_ACCOUNT_ID.value}:alias/{GlobalVariables.TEST_IMAGE_KEY_NAME.value}",
                    "volumeSize": int(GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value),
                },
            }
        ],
        "components": [
            {
                "componentArn": (
                    f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
                    f"{GlobalVariables.AWS_ACCOUNT_ID.value}:component/"
                    f"{GlobalVariables.TEST_COMPONENT_ID.value}/"
                    f"/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}/1"
                )
            }
        ],
        "description": GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
        "name": GlobalVariables.TEST_RECIPE_NAME.value,
        "parentImage": GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
        "semanticVersion": GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
    }
    mock_moto_calls["CreateImageRecipe"].assert_called_once_with(**create_recipe_kwargs)
    assert response == GlobalVariables.TEST_IMAGE_RECIPE_ARN.value


def test_should_get_a_recipe(mock_moto_calls, get_ec2_image_builder_recipe_srv):
    # ARRANGE & ACT
    response = get_ec2_image_builder_recipe_srv.get_build_arn(name="test-recipe", version="1.0.0")

    # ASSERT
    get_recipe_kwargs = {"filters": [{"name": "name", "values": ["test-recipe"]}]}
    mock_moto_calls["ListImageRecipes"].assert_called_once_with(**get_recipe_kwargs)
    assert response == GlobalVariables.TEST_IMAGE_RECIPE_ARN.value
