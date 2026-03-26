import logging

METADATA_KEY_CFN_INTERFACE = "AWS::CloudFormation::Interface"
METADATA_KEY_PARAM_LABELS = "ParameterLabels"
METADATA_KEY_PARAM_VALUES = "ParameterAllowedValueLabels"  # deprecated param metadata for backwards compatibility
METADATA_KEY_PARAM_META = "ParameterMetadata"  # preferred metadata key
METADATA_KEY_PARAM_OPTION_LABELS = "OptionLabels"
METADATA_KEY_PARAM_OPTION_WARNINGS = "OptionWarnings"


class ProductVersionParameterMetadata:
    """
    Class handles product input parameter metadata handling.
    """

    def __init__(
        self, logger: logging.Logger, interface_meta_dict: dict, legacy_param_labels_dict: dict, param_meta_dict: dict
    ):
        self._logger = logger
        self._interface_meta_dict = interface_meta_dict
        self._legacy_param_labels_dict = legacy_param_labels_dict
        self._param_meta_dict = param_meta_dict

    def get_user_friendly_name(self, parameter_key: str) -> str | None:
        """Returns a user friendly parameter name."""

        return self._interface_meta_dict.get(parameter_key, {}).get("default", None)

    def get_parameter_warnings(self, parameter_key: str) -> dict:
        """Returns a dictionary of warnings to display when parameter is set to a particular value."""

        try:
            return {
                key: value
                for (key, value) in self._param_meta_dict.get(parameter_key, {})
                .get(METADATA_KEY_PARAM_OPTION_WARNINGS, {})
                .items()
            }
        except:
            self._logger.exception(f"Unable to fetch parameter option warnings for {parameter_key}")

        return {}

    def get_parameter_option_labels(self, parameter_key: str) -> dict:
        """Returns user friendly dropdown value names"""

        option_labels: dict[str, str] = {}

        param_meta = self._param_meta_dict.get(parameter_key, {}).get(
            METADATA_KEY_PARAM_OPTION_LABELS, {}
        ) or self._legacy_param_labels_dict.get(parameter_key, {})

        try:
            option_labels = {key: value for (key, value) in param_meta.items()}
        except:
            self._logger.exception(f"Unable to fetch parameter option labels for {parameter_key}")

        return option_labels

    def has_parameter_metadata(self, parameter_key: str) -> bool:
        available_meta = {
            *self._interface_meta_dict.keys(),
            *self._legacy_param_labels_dict.keys(),
            *self._param_meta_dict.keys(),
        }
        return parameter_key in available_meta


def from_cloud_formation_metadata_dict(logger: logging.Logger, metadata: dict) -> ProductVersionParameterMetadata:
    """
    Parses the parameter metadata dict as described in the ADR.
    """

    return ProductVersionParameterMetadata(
        logger=logger,
        interface_meta_dict=metadata.get(METADATA_KEY_CFN_INTERFACE, {}).get(METADATA_KEY_PARAM_LABELS, {}),
        legacy_param_labels_dict=metadata.get(METADATA_KEY_PARAM_VALUES, {}),
        param_meta_dict=metadata.get(METADATA_KEY_PARAM_META, {}),
    )
