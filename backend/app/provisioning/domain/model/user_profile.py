from pydantic import Field

from app.provisioning.domain.model.maintenance_window import MaintenanceWindow
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class UserProfilePrimaryKey(unit_of_work.PrimaryKey):
    userId: str = Field(..., title="UserId")


class UserProfile(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    preferredRegion: str = Field(..., title="PreferredRegion")
    preferredNetwork: str | None = Field(None, title="PreferredNetwork")
    preferredMaintenanceWindows: list[MaintenanceWindow] | None = Field(None, title="PreferredMaintenanceWindows")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    preferredAvailabilityZone: str | None = Field(None, title="PreferredAvailabilityZone")
