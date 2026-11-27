import { Box, HelpPanel, Wizard } from '@cloudscape-design/components';
import { FC } from 'react';
import {
  ImportImageRequest,
  ImportImageResponse,
  DiscoverMarketplaceSubscriptionsResponse,
  ListImportableAmisResponse,
} from '../../../../services/API/proserve-wb-packaging-api';
import { AwsPublishedAmiAPI } from '../../../../services/API/aws-published-ami-api';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18n } from './import-image-wizard.translations';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from
  '../../../layout/workbench-app-layout/workbench-app-layout';
import { useImportImageWizard } from './import-image-wizard.logic';
import { ImportImageStepSource } from './import-image-step-source';
import { ImportImageStepAmi } from './import-image-step-ami';
import { ImportImageStepAwsPublished } from './import-image-step-aws-published';
import { ImportImageStepDetails } from './import-image-step-details';
import { ImportImageStepPlatform } from './import-image-step-platform';
import { ImportImageStepSoftware } from './import-image-step-software';
import { ImportImageStepReview } from './import-image-step-review';
import { CancelPrompt } from '../..';

interface ServiceAPI {
  importImage: (
    projectId: string, body: ImportImageRequest,
  ) => Promise<ImportImageResponse>,
  discoverMarketplaceSubscriptions: (
    projectId: string,
  ) => Promise<DiscoverMarketplaceSubscriptionsResponse>,
  listImportableAmis: (
    projectId: string,
  ) => Promise<ListImportableAmisResponse>,
}

interface ImportImageWizardProps {
  serviceApi: ServiceAPI,
  awsPublishedApi?: AwsPublishedAmiAPI,
}

export const ImportImageWizard: FC<ImportImageWizardProps> = (
  { serviceApi, awsPublishedApi },
) => {
  const logic = useImportImageWizard({ serviceApi, awsPublishedApi });

  // The step-2 title and content both depend on the source.
  const step2Title = {
    EXISTING_AMI: i18n.step2TitleAmi,
    MARKETPLACE_PRODUCT: i18n.step2TitleSubscription,
    AWS_PUBLISHED_AMI: i18n.step2TitleAwsPublished,
  }[logic.imageSource];

  const steps = [
    {
      title: i18n.step1Title,
      content: <ImportImageStepSource
        imageSource={logic.imageSource}
        setImageSource={logic.setImageSource}
        awsPublishedAvailable={!!logic.awsListingId}
      />,
    },
    {
      title: step2Title,
      content: logic.imageSource === 'AWS_PUBLISHED_AMI'
        ? <ImportImageStepAwsPublished
          resolution={logic.awsResolution}
          resolveError={logic.awsResolveError}
          isResolving={logic.loadingAwsResolution}
          candidates={logic.awsCandidates}
          selectedCandidate={logic.selectedAwsCandidate}
          onSelectCandidate={logic.handleAwsCandidateSelection}
        />
        : <ImportImageStepAmi
          imageSource={logic.imageSource}
          importableAmis={logic.importableAmis}
          loadingAmis={logic.loadingAmis}
          selectedAmi={logic.selectedAmi}
          setSelectedAmi={logic.setSelectedAmi}
          subscriptions={logic.subscriptions}
          loadingSubscriptions={logic.loadingSubscriptions}
          selectedSubscription={logic.selectedSubscription}
          handleSubscriptionSelection={logic.handleSubscriptionSelection}
          handoffStatus={logic.handoffStatus}
        />,
    },
    {
      title: i18n.step3Title,
      content: <ImportImageStepDetails
        imageName={logic.imageName}
        setImageName={logic.setImageName}
        imageDescription={logic.imageDescription}
        setImageDescription={logic.setImageDescription}
      />,
    },
    {
      title: i18n.step4Title,
      content: <ImportImageStepPlatform
        platform={logic.platform}
        setPlatform={logic.setPlatform}
        osVersion={logic.osVersion}
        setOsVersion={logic.setOsVersion}
      />,
    },
    {
      title: i18n.step5Title,
      content: <ImportImageStepSoftware
        componentVersionDetails={logic.componentVersionDetails}
        setComponentVersionDetails={logic.setComponentVersionDetails}
        updateComponentDetail={logic.updateComponentDetail}
      />,
    },
    {
      title: i18n.step6Title,
      content: <ImportImageStepReview
        imageSource={logic.imageSource}
        amiId={logic.selectedAmiId}
        selectedSubscription={logic.selectedSubscription}
        imageName={logic.imageName}
        platform={logic.platform}
        osVersion={logic.osVersion}
        componentVersionDetails={logic.componentVersionDetails}
        setActiveStepIndex={logic.setActiveStepIndex}
      />,
    },
  ];

  const breadcrumbItems: BreadcrumbItem[] = [
    { path: i18n.step1Title, href: '#' },
  ];

  return (
    <div data-test="import-image-wizard">
      <CancelPrompt
        cancelConfirmVisible={logic.cancelConfirmVisible}
        setCancelConfirmVisible={logic.setCancelConfirmVisible}
        handleCancelConfirm={() => logic.navigateTo(RouteNames.Images)}
        i18nStrings={{
          cancelPromptHeader: i18n.cancelPromptHeader,
          cancelPromptText1: i18n.cancelPromptText1,
          cancelPromptText2: i18n.cancelPromptText2,
          cancelPromptText3: i18n.cancelPromptText3,
          cancelPromptCancelText: i18n.cancelPromptCancelText,
          cancelPromptConfirmText: i18n.cancelPromptConfirmText,
        }}
      />
      <WorkbenchAppLayout
        breadcrumbItems={breadcrumbItems}
        contentType="default"
        tools={
          <HelpPanel header={<h2>{i18n.imageSourceHeader}</h2>}>
            <Box variant="p">
              {i18n.sourceExistingAmiDescription}
            </Box>
          </HelpPanel>
        }
        content={
          <Wizard
            steps={steps}
            activeStepIndex={logic.activeStepIndex}
            onNavigate={({ detail }) => {
              if (detail.requestedStepIndex > logic.activeStepIndex
                && !logic.canProceedFromStep(logic.activeStepIndex)) {
                return;
              }
              logic.setActiveStepIndex(detail.requestedStepIndex);
            }}
            onSubmit={logic.handleSubmit}
            onCancel={() => logic.setCancelConfirmVisible(true)}
            isLoadingNextStep={logic.submitting}
            i18nStrings={{
              stepNumberLabel: i18n.stepNumberLabel,
              collapsedStepsLabel: i18n.collapsedStepsLabel,
              cancelButton: i18n.cancelButton,
              previousButton: i18n.previousButton,
              nextButton: i18n.nextButton,
              submitButton: i18n.submitButton,
            }}
          />
        }
      />
    </div>
  );
};
