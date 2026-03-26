from pydantic import Field

from app.publishing.domain.read_models import component_version_detail
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class AmiPrimaryKey(unit_of_work.PrimaryKey):
    amiId: str = Field(..., title="AmiId")


class Ami(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    amiId: str = Field(..., title="AmiId")
    amiName: str = Field(..., title="AmiName")
    amiDescription: str | None = Field(None, title="AmiDescription")
    componentVersionDetails: list[component_version_detail.ComponentVersionDetail] | None = Field(
        None, title="ComponentVersionDetails"
    )
    osVersion: str | None = Field(None, title="OsVersion")
    platform: str | None = Field(None, title="Platform")
    architecture: str | None = Field(None, title="Architecture")
    integrations: list[str] = Field([], title="integrations")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
