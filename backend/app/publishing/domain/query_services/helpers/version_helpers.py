from datetime import datetime

from app.publishing.domain.model import version, version_summary

VERSION_STAGE_SORT_ORDER = {
    version.VersionStage.DEV: 1,
    version.VersionStage.QA: 2,
    version.VersionStage.PROD: 3,
}


def get_summary(distributions: list[version.Version]) -> version_summary.VersionSummary | None:
    if not distributions:
        return None

    first_distribution = next(d for d in distributions)
    latest_update_date = max((datetime.fromisoformat(d.lastUpdateDate) for d in distributions))
    stages = {(VERSION_STAGE_SORT_ORDER.get(d.stage, 0), d.stage) for d in distributions}
    status = calculate_version_summary_status(distributions)

    summary = version_summary.VersionSummary(
        versionId=first_distribution.versionId,
        name=first_distribution.versionName,
        description=first_distribution.versionDescription,
        versionType=first_distribution.versionType,
        stages=[s for i, s in sorted(list(stages))],
        status=status,
        recommendedVersion=first_distribution.isRecommendedVersion,
        lastUpdate=latest_update_date.isoformat(),
        restoredFromVersionName=first_distribution.restoredFromVersionName,
        originalAmiId=first_distribution.originalAmiId if first_distribution.originalAmiId else None,
        lastUpdatedBy=first_distribution.lastUpdatedBy,
    )

    return summary


def calculate_version_summary_status(distributions: list[version.Version]) -> version_summary.VersionSummaryStatus:
    """
    This function calculates a status for version summary using the statuses of distributions following the logic:
    - Failed -> If at least one of the distributions is in failed status.
    - Created -> If all distributions are in created status.
    - Retired -> If all distributions are in retired status.
    - Processing -> For any other interim status.
    """
    created_count = 0
    retired_count = 0
    for vers in distributions:
        # Return Failed if there is any failed distribution
        if vers.status == version.VersionStatus.Failed:
            return version_summary.VersionSummaryStatus.Failed
        elif vers.status == version.VersionStatus.Created:
            created_count += 1
        elif vers.status == version.VersionStatus.Retired:
            retired_count += 1

    if created_count == len(distributions):
        # Return Created if all Created
        return version_summary.VersionSummaryStatus.Created
    elif retired_count == len(distributions):
        # Return Retired if all Retired
        return version_summary.VersionSummaryStatus.Retired

    # Return Processing for anything else
    return version_summary.VersionSummaryStatus.Processing
