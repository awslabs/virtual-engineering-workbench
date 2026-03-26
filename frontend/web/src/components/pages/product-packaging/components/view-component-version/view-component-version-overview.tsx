import { ColumnLayout, Container, Header, Link, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { ComponentVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { i18n } from './view-component-version.translations';
import { CopyText, UserDate } from '../../../shared';
import { ComponentVersionStatus } from '../shared/component-version-status';

export const ViewComponentVersionOverview = ({
  componentVersion,
  componentVersionLoading,
}: { componentVersion?: ComponentVersion, componentVersionLoading: boolean }) => {

  if (componentVersionLoading) { return <Spinner />; }
  if (!componentVersion) { return <></>; }

  return (
    <Container header={<Header>{i18n.detailsHeader}</Header>} data-test="component-details">
      <SpaceBetween size="l">
        <ColumnLayout columns={3} variant="text-grid">
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsComponentId} data-test="component-id">
              <CopyText
                copyButtonLabel={i18n.detailsComponentId}
                copyText={componentVersion.componentId}
                successText={i18n.componentIdIdCopySuccess}
                errorText={i18n.componentIdIdCopyError}
              />
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsVersionId} data-test="version-id">
              <CopyText
                copyButtonLabel={i18n.detailsVersionId}
                copyText={componentVersion.componentVersionId}
                successText={i18n.versionIdCopySuccess}
                errorText={i18n.versionIdCopyError}
              />
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsStatus} data-test="status">
              <ComponentVersionStatus status={componentVersion.status} />
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsSoftwareVendor} data-test="software-vendor">
              {componentVersion.softwareVendor}
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsSoftwareVersion} data-test="software-version">
              {componentVersion.softwareVersion}
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsLicenseDashboard} data-test="license-dashboard">
              <Link
                external
                href={componentVersion.licenseDashboard}>
                {componentVersion.licenseDashboard}
              </Link>
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsAuthor} data-test="created-by">
              {componentVersion.createdBy}
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsLastContributor} data-test="last-updated-by">
              {componentVersion.lastUpdatedBy}
            </ValueWithLabel>
          </SpaceBetween>
          <SpaceBetween size="l">
            <ValueWithLabel label={i18n.detailsLastUpdate} data-test="last-update-date">
              <UserDate date={componentVersion.lastUpdateDate} />
            </ValueWithLabel>
          </SpaceBetween>
        </ColumnLayout>
        <ValueWithLabel label={i18n.detailsNotes} data-test="notes">
          {componentVersion.notes}
        </ValueWithLabel>
      </SpaceBetween>
    </Container>
  );
};