from pydantic import ConfigDict

from app.provisioning.domain.value_objects import (
    network_value_object,
    preferred_maintenance_windows_value_object,
    region_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class UpdateUserProfileCommand(command_bus.Command):
    user_id: user_id_value_object.UserIdValueObject
    preferred_region: region_value_object.RegionValueObject
    preferred_network: network_value_object.NetworkValueObject
    preferred_maintenance_windows: (
        preferred_maintenance_windows_value_object.PreferredPreferredMaintenanceWindowsValueObject
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)
