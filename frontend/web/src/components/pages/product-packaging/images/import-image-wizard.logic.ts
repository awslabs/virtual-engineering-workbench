import { useEffect, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import {
  ComponentVersionDetailInput as ComponentVersionDetail,
  DiscoveredMarketplaceSubscription as MarketplaceSubscription,
  MarketplaceMetadataInput as MarketplaceMetadata,
  ImportImageRequest,
  ImportImageResponse,
  ImportableAmi,
  DiscoverMarketplaceSubscriptionsResponse,
  ListImportableAmisResponse,
} from '../../../../services/API/proserve-wb-packaging-api';
import { useImportImage } from
  '../../../../hooks/packaging/import-image.logic';
import { useDiscoverMarketplaceSubscriptions } from
  '../../../../hooks/packaging/discover-marketplace-subscriptions.logic';
import { useNavigationPaths } from
  '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from
  '../../../layout/navigation/navigation.static';
import { useNotifications } from '../../../layout';
import { i18n } from './import-image-wizard.translations';

const INITIAL_STEP_INDEX = 0;
const INITIAL_COMPONENT_VERSION: ComponentVersionDetail = {
  softwareVendor: '',
  softwareName: '',
  softwareVersion: '',
};

const STEP_AMI = 1;
const STEP_DETAILS = 2;
const STEP_PLATFORM = 3;
const STEP_SOFTWARE = 4;

export type ImageSource = 'EXISTING_AMI' | 'MARKETPLACE_PRODUCT';

interface ServiceAPI {
  importImage: (projectId: string, body: ImportImageRequest) => Promise<ImportImageResponse>,
  discoverMarketplaceSubscriptions: (
    projectId: string,
  ) => Promise<DiscoverMarketplaceSubscriptionsResponse>,
  listImportableAmis: (
    projectId: string,
  ) => Promise<ListImportableAmisResponse>,
}

interface ImportImageWizardLogicProps {
  serviceApi: ServiceAPI,
}

const buildMarketplaceMetadata = (
  subscription: MarketplaceSubscription,
): MarketplaceMetadata => ({
  productCode: subscription.productCode || '',
  subscriptionOwnership: subscription.subscriptionOwnership || '',
  regionalAmiIds: subscription.regionalAmiIds || {},
  licenseConfigurationArn: subscription.licenseConfigurationArn,
  homeRegion: subscription.homeRegion,
});

export const useImportImageWizard = (
  { serviceApi }: ImportImageWizardLogicProps,
) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const projectId = selectedProject?.projectId;
  const { navigateTo } = useNavigationPaths();
  const { showSuccessNotification, showErrorNotification } = useNotifications();

  const { importImage, isLoading: submitting } = useImportImage({
    serviceApi, projectId: projectId || '',
  });

  const [activeStepIndex, setActiveStepIndex] = useState(INITIAL_STEP_INDEX);
  const [imageSource, setImageSource] = useState<ImageSource>('EXISTING_AMI');

  const {
    subscriptions,
    isLoading: loadingSubscriptions,
  } = useDiscoverMarketplaceSubscriptions({
    serviceApi, enabled: imageSource === 'MARKETPLACE_PRODUCT',
  });

  const [amiId, setAmiId] = useState('');
  const [selectedAmi, setSelectedAmi] = useState<ImportableAmi | null>(null);
  const [importableAmis, setImportableAmis] = useState<ImportableAmi[]>([]);
  const [loadingAmis, setLoadingAmis] = useState(false);

  useEffect(() => {
    if (imageSource === 'EXISTING_AMI' && projectId) {
      setLoadingAmis(true);
      serviceApi.listImportableAmis(projectId)
        .then(res => setImportableAmis(res.amis || []))
        .catch(() => setImportableAmis([]))
        .finally(() => setLoadingAmis(false));
    }
  }, [imageSource, projectId]);
  const [imageName, setImageName] = useState('');
  const [imageDescription, setImageDescription] = useState('');
  const [platform, setPlatform] = useState('');
  const [osVersion, setOsVersion] = useState('');
  const [componentVersionDetails, setComponentVersionDetails] = useState<
    ComponentVersionDetail[]
  >([{ ...INITIAL_COMPONENT_VERSION }]);
  const [selectedSubscription, setSelectedSubscription] = useState<
    MarketplaceSubscription | null
  >(null);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);

  const buildRequestBody = (): ImportImageRequest => ({
    imageSource,
    amiId: imageSource === 'MARKETPLACE_PRODUCT'
      ? selectedSubscription?.hubRegionAmiId || ''
      : selectedAmi?.amiId || amiId,
    imageName,
    imageDescription: imageDescription || undefined,
    platform,
    osVersion,
    componentVersionDetails: componentVersionDetails.filter(
      c => c.softwareName && c.softwareVersion,
    ),
    ...imageSource === 'MARKETPLACE_PRODUCT'
      && selectedSubscription && {
      marketplaceMetadata: buildMarketplaceMetadata(
        selectedSubscription,
      ),
    },
  });

  const handleSubmit = async () => {
    if (!projectId) { return; }
    try {
      const result = await importImage(buildRequestBody());
      showSuccessNotification({
        header: i18n.importSuccess(result.imageId || ''),
        content: '',
      });
      navigateTo(RouteNames.Images);
    } catch (e: unknown) {
      const msg = e instanceof Error
        ? e.message : i18n.importFailed;
      showErrorNotification({
        header: i18n.importFailed, content: msg,
      });
    }
  };

  const handleSubscriptionSelection = (item: MarketplaceSubscription) => {
    if (item && !item.alreadyImported) {
      setSelectedSubscription(item);
      setImageName(item.productName || '');
    }
  };

  const updateComponentDetail = (
    index: number,
    field: keyof ComponentVersionDetail,
    value: string,
  ) => {
    const updated = [...componentVersionDetails];
    updated[index] = { ...updated[index], [field]: value };
    setComponentVersionDetails(updated);
  };

  const canProceedFromStep = (stepIndex: number): boolean => {
    switch (stepIndex) {
      case STEP_AMI:
        return imageSource === 'EXISTING_AMI'
          ? !!selectedAmi : !!selectedSubscription;
      case STEP_DETAILS:
        return !!imageName.trim();
      case STEP_PLATFORM:
        return platform !== '' && osVersion.trim() !== '';
      case STEP_SOFTWARE:
        return componentVersionDetails.some(
          c => c.softwareName.trim() && c.softwareVersion.trim(),
        );
      default:
        return true;
    }
  };

  return {
    activeStepIndex,
    setActiveStepIndex,
    imageSource,
    setImageSource,
    amiId,
    setAmiId,
    selectedAmi,
    setSelectedAmi,
    importableAmis,
    loadingAmis,
    imageName,
    setImageName,
    imageDescription,
    setImageDescription,
    platform,
    setPlatform,
    osVersion,
    setOsVersion,
    componentVersionDetails,
    setComponentVersionDetails,
    selectedSubscription,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    subscriptions,
    loadingSubscriptions,
    submitting,
    handleSubmit,
    handleSubscriptionSelection,
    updateComponentDetail,
    canProceedFromStep,
    navigateTo,
  };
};
