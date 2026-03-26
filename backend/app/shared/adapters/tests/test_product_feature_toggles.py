import assertpy
import pytest

from app.shared.adapters.feature_toggling import product_feature_toggles


@pytest.fixture
def sample_outputs():
    return [
        product_feature_toggles.Output(
            outputKey="FeatureToggles",
            outputValue='[{"feature": "DCVConnectionOptions", "enabled": true}, {"feature": "WorkbenchWorkingDirectoryEnabled", "enabled": false}]',
            description="Test description",
        ),
        product_feature_toggles.Output(outputKey="OtherKey", outputValue="some value", description="Other description"),
    ]


@pytest.fixture
def empty_feature_toggles():
    return [
        product_feature_toggles.Output(outputKey="OtherKey", outputValue="some value", description="Other description")
    ]


def test_initialize_with_valid_feature_toggles(sample_outputs):
    # ARRANGE
    toggles = product_feature_toggles.ProductFeatureToggles(sample_outputs)

    # ACT
    is_dcv_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.DCVConnectionOptions)
    is_working_dir_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.WorkbenchWorkingDirectoryEnabled)

    # ASSERT
    assertpy.assert_that(is_dcv_enabled).is_true()
    assertpy.assert_that(is_working_dir_enabled).is_false()


def test_initialize_with_no_feature_toggles(empty_feature_toggles):
    # ARRANGE
    toggles = product_feature_toggles.ProductFeatureToggles(empty_feature_toggles)

    # ACT
    is_dcv_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.DCVConnectionOptions)
    is_working_dir_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.WorkbenchWorkingDirectoryEnabled)

    # ASSERT
    assertpy.assert_that(is_dcv_enabled).is_false()
    assertpy.assert_that(is_working_dir_enabled).is_false()


def test_initialize_with_empty_outputs():
    # ARRANGE
    toggles = product_feature_toggles.ProductFeatureToggles([])

    # ACT
    is_dcv_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.DCVConnectionOptions)

    # ASSERT
    assertpy.assert_that(is_dcv_enabled).is_false()


def test_check_non_existent_feature(sample_outputs):
    # ARRANGE
    toggles = product_feature_toggles.ProductFeatureToggles(sample_outputs)

    # ACT
    is_auto_stop_protection_enabled = toggles.is_enabled(product_feature_toggles.ProductFeature.AutoStopProtection)

    # ASSERT
    assertpy.assert_that(is_auto_stop_protection_enabled).is_false()


def test_invalid_json_feature_toggles():
    # ARRANGE
    invalid_outputs = [
        product_feature_toggles.Output(
            outputKey="FeatureToggles", outputValue="invalid json", description="Test description"
        )
    ]

    # ACT & ASSERT
    assertpy.assert_that(product_feature_toggles.ProductFeatureToggles).raises(Exception).when_called_with(
        invalid_outputs
    )
