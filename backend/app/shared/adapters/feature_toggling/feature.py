from typing import List, Optional

from pydantic import Field

from app.shared.adapters.feature_toggling import frontend_feature


class Feature(frontend_feature.FrontendFeature):
    userOverrides: Optional[List[str]] = Field(..., title="UserOverrides")
