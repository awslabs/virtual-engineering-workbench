import { useEffect, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { useSearchParams } from 'react-router-dom';
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
import { useResolveAwsPublishedAmi, AwsPublishedAmiServiceAPI } from
  '../../../../hooks/packaging/resolve-aws-published-ami.logic';
import { useNavigationPaths } from
  '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from
  '../../../layout/navigation/navigation.static';
import { useNotifications } from '../../../layout';
import { i18n } from './import-image-wizard.translations';
import {
  MARKETPLACE_SOURCE_PARAM,
  MARKETPLACE_SOURCE_VALUE,
  findHandoffSubscription,
  parseMarketplaceImportHandoff,
} from './marketplace-import-handoff';
import { parseAwsPublishedImportHandoff } from './aws-published-import-handoff';
import {
  AwsPublishedAmiCandidate,
  ResolveAwsPublishedAmiResponse,
  pickableCandidates,
  platformFromDetails,
} from '../../../../services/API/aws-published-ami-api';

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

/** `imageName` is bounded by the import request schema. */
const MAX_IMAGE_NAME = 100;
const NAME_START = 0;

export type ImageSource = 'EXISTING_AMI' | 'MARKETPLACE_PRODUCT' | 'AWS_PUBLISHED_AMI';

/**
 * Progress of preselecting the subscription named in a purchase hand-off.
 * - `none`: the URL carried no valid hand-off.
 * - `pending`: waiting for the subscriptions list.
 * - `selected`: the matching subscription was preselected.
 * - `alreadyImported`: the matching subscription is imported and up to date,
 *   so it cannot be selected.
 * - `unavailable`: the list arrived without a single match, typically because
 *   the new subscription is not listed yet. The list is not re-fetched; the
 *   user has to reload the page.
 */
export type HandoffStatus = 'none' | 'pending' | 'selected' | 'alreadyImported' | 'unavailable';

interface ServiceAPI {
  importImage: (projectId: string, body: ImportImageRequest) => Promise<ImportImageResponse>,
  discoverMarketplaceSubscriptions: (
    projectId: string,
  ) => Promise<DiscoverMarketplaceSubscriptionsResponse>,
  listImportableAmis: (
    projectId: string,
  ) => Promise<ListImportableAmisResponse>,
}

/**
 * The AWS-published client. Optional so the many callers and tests that never
 * reach this source need not supply it; the step reports the source as
 * unavailable when it is missing.
 */
type AwsPublishedAPI = AwsPublishedAmiServiceAPI;

interface ImportImageWizardLogicProps {
  serviceApi: ServiceAPI,
  awsPublishedApi?: AwsPublishedAPI,
}

/** A subscription can be picked unless it is imported and up to date. */
const isSelectableSubscription = (item: MarketplaceSubscription): boolean =>
  !item.alreadyImported || item.newerVersionAvailable === true;

/** The source a deep link selects, defaulting to a cold start. */
const initialSourceFor = (
  searchParams: URLSearchParams,
  awsListingId: string | null,
): ImageSource => {
  if (awsListingId) { return 'AWS_PUBLISHED_AMI'; }
  if (searchParams.get(MARKETPLACE_SOURCE_PARAM) === MARKETPLACE_SOURCE_VALUE) {
    return 'MARKETPLACE_PRODUCT';
  }
  return 'EXISTING_AMI';
};

/**
 * The message for the AWS-published step, or `null` when there is nothing to
 * report. A missing client is reported as an unavailable source rather than a
 * failed lookup, because nothing was attempted.
 */
const awsPublishedErrorMessage = ({
  imageSource,
  listingId,
  hasClient,
  failure,
}: {
  imageSource: ImageSource,
  listingId: string | null,
  hasClient: boolean,
  failure: Error | null,
}): string | null => {
  if (imageSource !== 'AWS_PUBLISHED_AMI' || !listingId) { return null; }
  if (!hasClient) { return i18n.awsPublishedUnavailable; }
  return failure?.message || null;
};

export const buildMarketplaceMetadata = (
  subscription: MarketplaceSubscription,
): MarketplaceMetadata => ({
  productCode: subscription.productCode || '',
});

/**
 * Preselect the subscription named in a purchase hand-off, once, as soon as
 * the subscriptions list is in. Adjusts state during render rather than in an
 * effect, so there is no frame showing the picker with nothing selected. Runs
 * at most once because it moves the status out of `pending`.
 */
const useHandoffPreselection = ({
  searchParams,
  subscriptions,
  ready,
  select,
}: {
  searchParams: URLSearchParams,
  subscriptions: MarketplaceSubscription[],
  ready: boolean,
  select: (item: MarketplaceSubscription) => void,
}) => {
  const [handoff] = useState(() => parseMarketplaceImportHandoff(searchParams));
  const [handoffStatus, setHandoffStatus] = useState<HandoffStatus>(
    handoff ? 'pending' : 'none',
  );
  if (handoff && handoffStatus === 'pending' && ready) {
    const match = findHandoffSubscription(subscriptions, handoff);
    if (!match) {
      setHandoffStatus('unavailable');
    } else if (isSelectableSubscription(match)) {
      select(match);
      setHandoffStatus('selected');
    } else {
      setHandoffStatus('alreadyImported');
    }
  }
  return handoffStatus;
};

export const useImportImageWizard = (
  { serviceApi, awsPublishedApi }: ImportImageWizardLogicProps,
) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const projectId = selectedProject?.projectId;
  const { navigateTo } = useNavigationPaths();
  const { showSuccessNotification, showErrorNotification } = useNotifications();

  // Deep-link: after a Marketplace purchase the procurement wizard links here
  // with ?source=marketplace, so the wizard skips the source tile and opens on
  // the subscription picker. The link may also carry the purchased product's
  // Marketplace product id (see marketplace-import-handoff.ts); the matching
  // subscription is preselected once the subscriptions list has loaded.
  //
  // ?source=aws-published&listingId=<id> comes instead from a listing AWS
  // sells itself. Those products have no subscription, so they never appear in
  // the picker; the AMI is resolved from the listing (see
  // aws-published-import-handoff.ts). Without a well-formed listing id there
  // is nothing to resolve, so the source is not offered at all.
  const [searchParams] = useSearchParams();
  const [awsPublishedHandoff] = useState(
    () => parseAwsPublishedImportHandoff(searchParams),
  );
  const awsListingId = awsPublishedHandoff?.listingId ?? null;

  const initialSource: ImageSource = initialSourceFor(searchParams, awsListingId);
  // Both deep links land on the picker step; only a cold start shows the
  // source tiles.
  const initialStepIndex = initialSource === 'EXISTING_AMI'
    ? INITIAL_STEP_INDEX
    : STEP_AMI;

  const { importImage, isLoading: submitting } = useImportImage({
    serviceApi, projectId: projectId || '',
  });

  const [activeStepIndex, setActiveStepIndex] = useState(initialStepIndex);
  const [imageSource, setImageSource] = useState<ImageSource>(initialSource);

  const {
    subscriptions,
    isLoading: loadingSubscriptions,
    isLoaded: subscriptionsLoaded,
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
  const [selectedAwsCandidate, setSelectedAwsCandidate] = useState<
    AwsPublishedAmiCandidate | null
  >(null);

  /**
   * Take an AMI the backend offered for this listing. Ignores one that is
   * already imported into the project, so neither the user nor the automatic
   * preselection can queue a duplicate import.
   *
   * Fills in the name and platform the import needs, which the user can still
   * change on the later steps. An unambiguous product is named after the
   * product; when the user had to choose between architectures, the AMI name
   * is what distinguishes their choice.
   */
  const selectAwsCandidate = (
    item: AwsPublishedAmiCandidate | null | undefined,
    resolution: ResolveAwsPublishedAmiResponse | null,
  ) => {
    if (!item) { return; }
    if ((resolution?.alreadyImportedAmiIds || []).includes(item.amiId)) { return; }
    setSelectedAwsCandidate(item);
    const name = resolution?.resolved ? resolution.productName : item.amiName;
    setImageName(name.slice(NAME_START, MAX_IMAGE_NAME));
    setPlatform(platformFromDetails(item.platformDetails));
  };

  const {
    resolution: awsResolution,
    isLoading: loadingAwsResolution,
    error: awsResolveFailure,
  } = useResolveAwsPublishedAmi({
    serviceApi: awsPublishedApi,
    listingId: awsListingId,
    enabled: imageSource === 'AWS_PUBLISHED_AMI',
  });

  // A missing client is reported as an unavailable source rather than a
  // failed lookup: nothing was attempted.
  const awsResolveError = awsPublishedErrorMessage({
    imageSource,
    listingId: awsListingId,
    hasClient: !!awsPublishedApi,
    failure: awsResolveFailure,
  });

  /**
   * Preselect the resolved AMI once, as soon as the lookup is in. Adjusts
   * state during render rather than in an effect, like the purchase hand-off
   * above, so there is no frame showing the step with nothing selected.
   * Only an unambiguous product is preselected; when several AMIs are offered
   * they differ by architecture, so guessing would import the wrong image.
   */
  const [awsPreselectDone, setAwsPreselectDone] = useState(false);
  if (awsResolution && !awsPreselectDone) {
    setAwsPreselectDone(true);
    if (awsResolution.resolved) {
      selectAwsCandidate(awsResolution.resolved, awsResolution);
    }
  }

  const handleAwsCandidateSelection = (
    item: AwsPublishedAmiCandidate | null | undefined,
  ) => selectAwsCandidate(item, awsResolution);

  const selectedAmiId = (): string => {
    if (imageSource === 'MARKETPLACE_PRODUCT') {
      return selectedSubscription?.hubRegionAmiId || '';
    }
    if (imageSource === 'AWS_PUBLISHED_AMI') {
      return selectedAwsCandidate?.amiId || '';
    }
    return selectedAmi?.amiId || amiId;
  };

  const buildRequestBody = (): ImportImageRequest => ({
    imageSource,
    amiId: selectedAmiId(),
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

  /**
   * The AWS-published import body.
   *
   * `marketplaceMetadata.listingId` is mandatory for this source: the backend
   * resolves the listing again and accepts `amiId` only if that resolution
   * offers it. `productCode` is required by the request schema but derived
   * server-side from the AMI, so it is sent empty.
   */
  const buildAwsPublishedRequestBody = (
    listingId: string,
  ): ImportImageRequest => ({
    imageSource: 'AWS_PUBLISHED_AMI',
    amiId: selectedAwsCandidate?.amiId || '',
    imageName,
    imageDescription: imageDescription || undefined,
    platform,
    osVersion,
    componentVersionDetails: componentVersionDetails.filter(
      c => c.softwareName && c.softwareVersion,
    ),
    marketplaceMetadata: {
      listingId,
      productCode: '',
    },
  });

  /**
   * The body to submit. Every source, this one included, goes through
   * `serviceApi.importImage`; the generated serialiser carries
   * `marketplaceMetadata.listingId` now, so no second import path is needed.
   *
   * The AWS-published source is guarded first, because neither case can
   * produce an import the backend would accept: without a client nothing was
   * ever resolved, and without a listing id there is no AMI to import.
   */
  const buildSubmitBody = (): ImportImageRequest => {
    if (imageSource !== 'AWS_PUBLISHED_AMI') { return buildRequestBody(); }
    if (!awsPublishedApi) { throw new Error(i18n.awsPublishedUnavailable); }
    if (!awsListingId) { throw new Error(i18n.awsPublishedResolveFailed); }
    return buildAwsPublishedRequestBody(awsListingId);
  };

  const handleSubmit = async () => {
    if (!projectId) { return; }
    try {
      const result = await importImage(buildSubmitBody());
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
    // Accept a subscription selection when either:
    //   - the product has not been imported yet (fresh subscribe), or
    //   - it's been imported but a newer AMI version is available (update flow).
    // The backend already surfaces `latestAmiId` as `hubRegionAmiId` in
    // the update case, so no extra client-side munging is needed here.
    if (item && isSelectableSubscription(item)) {
      setSelectedSubscription(item);
      setImageName(item.productName || '');
    }
  };

  const handoffStatus = useHandoffPreselection({
    searchParams,
    subscriptions,
    ready: subscriptionsLoaded && !loadingSubscriptions,
    select: handleSubscriptionSelection,
  });

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
        if (imageSource === 'EXISTING_AMI') { return !!selectedAmi; }
        if (imageSource === 'AWS_PUBLISHED_AMI') { return !!selectedAwsCandidate; }
        return !!selectedSubscription;
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
    handoffStatus,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    subscriptions,
    loadingSubscriptions,
    submitting,
    handleSubmit,
    handleSubscriptionSelection,
    awsListingId,
    awsResolution,
    awsResolveError,
    loadingAwsResolution,
    awsCandidates: pickableCandidates(awsResolution),
    selectedAwsCandidate,
    handleAwsCandidateSelection,
    selectedAmiId: selectedAmiId(),
    updateComponentDetail,
    canProceedFromStep,
    navigateTo,
  };
};
