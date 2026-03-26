import { rcompare } from 'semver';
import { PRODUCT_VERSION_RELEASE_TYPE_MAP } from '../../products.translations';
import { useState, useEffect } from 'react';
import { WizardProps } from '@cloudscape-design/components';
import { isNullOrEmpty } from '../../../../../utils/form-validation-helper';
import useSwr from 'swr';
import { useNotifications } from '../../../../layout';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './product-version-wizard.translations';
import {
  Ami,
  GetAmisResponse,
  GetLatestMajorVersionsResponse,
  GetLatestTemplateResponse,
  ValidateProductVersionRequest,
  VersionSummary,
} from '../../../../../services/API/proserve-wb-publishing-api';
import { publishingAPI } from '../../../../../services';

const PRODUCT_VERSION_DESCRIPTION_REGEX = /^[A-Za-z0-9_ -]{0,100}$/u;
const STEP_1_INDEX = 1;
const STEP_2_INDEX = 2;

type ServiceAPI = {
  getAmis: (projectId: string) => Promise<GetAmisResponse>,
  getLatestTemplate: (projectId: string, productId: string, versionId?: string) =>
  Promise<GetLatestTemplateResponse>,
  validateProductVersion: (
    projectId: string,
    productId: string,
    validateComponentVersionRequest: ValidateProductVersionRequest
  ) => Promise<object>,
  getLatestMajorVersions: (
    projectId: string, productId: string
  ) => Promise<GetLatestMajorVersionsResponse>,
};


export const useProductVersionWizard = ({
  projectId,
  productId,
  productVersion,
  serviceApi,
  activeStepIndex,
  setActiveStepIndex
}: {
  projectId: string,
  productId: string,
  productVersion: VersionSummary,
  serviceApi: ServiceAPI,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => any,
  // eslint-disable-next-line complexity
}) => {
  const versionReleaseTypes = Object.keys(PRODUCT_VERSION_RELEASE_TYPE_MAP);

  const { showErrorNotification } = useNotifications();
  const isUpdate = !!productVersion && !!productVersion.versionId;
  const [versionReleaseType, setVersionReleaseType] = useState(versionReleaseTypes[1]);
  const [isVersionReleaseTypeValid, setIsVersionReleaseTypeValid] = useState(true);
  const [isAmiSelectValid, setIsAmiSelectValid] = useState(true);
  const [yamlDefinition, setYamlDefinition] = useState('');
  const [originalYamlDefinition, setOriginalYamlDefinition] = useState('');
  const [isYamlDefinitionValidationInProgress, setIsYamlDefinitionValidationInProgress] = useState(false);
  const [isYamlDefinitionValid, setIsYamlDefinitionValid] = useState(true);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);
  const [productVersionDescription, setProductVersionDescription] =
    useState<string>(productVersion.description ?? '');
  const [selectedAmi, setSelectedAmi] = useState<Ami>({} as Ami);
  const [selectedBaseMajorVersion, setSelectedBaseMajorVersion] = useState<VersionSummary>();

  // Helper function for version ID
  const getVersionId = () : string | undefined => {
    if (isUpdate) {
      return productVersion.versionId;
    } else if (versionReleaseType !== versionReleaseTypes[0]) {
      return selectedBaseMajorVersion?.versionId;
    }
    return undefined;
  };

  // Helper function for AMI ID
  const getTargetAmiId = () : string | undefined => {
    if (isUpdate) {
      return productVersion.originalAmiId;
    }
    return selectedBaseMajorVersion?.originalAmiId;

  };

  const { data: amiData, isLoading: isAmiDataLoading } = useSwr(
    ['products/product/ami', projectId],
    async ([, projectId]) => {
      return publishingAPI.getAmis(projectId);
    },
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchAmisError,
          content: err.message
        });
      }
    }
  );


  const { data: templateData, isLoading: isTemplateDataLoading } = useSwr(
    ['products/product/template', projectId, productId, getVersionId()],
    async ([,projectId, productId, versionId]) => {
      return publishingAPI.getLatestTemplate(projectId, productId, versionId);
    },
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchTemplateError,
          content: err.message
        });
      }
    }
  );

  const { data: productData } = useSwr(
    ['products/product', projectId, productId],
    async ([, projectId, productId]) => {
      return publishingAPI.getProduct(projectId, productId);
    },
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchProductError ?? 'Failed to fetch product',
          content: err.message
        });
      }
    }
  );

  const { data: latestMajorVersionsData, isLoading: isLatestMajorVersionsLoading } = useSwr(
    ['products/product/latest-major-versions', projectId, productId],
    async ([,projectId, productId]) => {
      return publishingAPI.getLatestMajorVersions(projectId, productId);
    },
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchLatestMajorVersionsError,
          content: err.message
        });
      }
    });

  function isProductVersionDescriptionValid(desc: string): boolean {
    return PRODUCT_VERSION_DESCRIPTION_REGEX.test(desc.trim());
  }

  function isAmiIdValid(desc: string): boolean {
    return !isNullOrEmpty(desc);
  }

  function isStep1Valid() {
    setIsVersionReleaseTypeValid(isUpdate || !isNullOrEmpty(versionReleaseType));
    setIsAmiSelectValid(!isNullOrEmpty(selectedAmi.amiId));
    return (
      isProductVersionDescriptionValid(productVersionDescription) &&
      isAmiIdValid(selectedAmi.amiId)
    );
  }

  function isStep2Valid() {
    if (!!yamlDefinition && isYamlDefinitionValid) {
      setIsYamlDefinitionValidationInProgress(true);
      setIsYamlDefinitionValid(false);

      const validateProductVersionRequest: ValidateProductVersionRequest = {
        versionTemplateDefinition: yamlDefinition,
      };

      serviceApi.
        validateProductVersion(projectId, productId, validateProductVersionRequest)
        .then(() => {
          setIsYamlDefinitionValid(true);
          setActiveStepIndex(STEP_2_INDEX);
        })
        .catch(async (e) => {
          showErrorNotification({
            header: i18n.validateVersionFailMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => {
          setIsYamlDefinitionValidationInProgress(false);
        });
    }
    return false;
  }

  function isStepValid(index: number) {
    if (index === STEP_1_INDEX) {
      return isStep1Valid();
    }

    if (index === STEP_2_INDEX) {
      return isStep2Valid();
    }
    return true;
  }

  function requiresValidation(reason: string) {
    return reason === 'next';
  }

  function handleOnNavigate(detail: WizardProps.NavigateDetail) {
    if (requiresValidation(detail.reason) && !isStepValid(detail.requestedStepIndex)) {
      return;
    }
    setActiveStepIndex(detail.requestedStepIndex);
  }


  useEffect(() => {
    if (!amiData?.amis) { return; }

    const defaultAmi = {} as Ami;
    const originalAmiId = getTargetAmiId() || '';
    const previousVersionAmi = amiData.amis.find(ami => ami.amiId === originalAmiId);

    setSelectedAmi(previousVersionAmi || defaultAmi);
  }, [amiData]);

  useEffect(() => {
    const template = templateData?.template || '';
    setYamlDefinition(template);
    if (!originalYamlDefinition && template) {
      setOriginalYamlDefinition(template);
    }
  }, [templateData]);

  useEffect(() => {
    const versions = productData?.product.versions;
    if (!versions?.length) { return; }

    const nonRetired = [...versions.filter(v => v.status === 'RELEASED' || v.status === 'RETIRED')]
      .sort((a, b) => rcompare(a.name, b.name));

    if (isUpdate) {
      const current = nonRetired.find(v => v.versionId === productVersion.versionId);
      setSelectedBaseMajorVersion(current ?? nonRetired[0]);
    } else {
      setSelectedBaseMajorVersion(nonRetired[0]);
    }
  }, [productData]);

  function returnAmiBasedOnId(amiId: string) {
    const correctAmi = amiData?.amis?.find(ami => ami.amiId === amiId);
    return correctAmi;
  }

  useEffect(() => {
    if (!selectedBaseMajorVersion) {
      return;
    }
    const targetAmiId = getTargetAmiId();

    setSelectedAmi(returnAmiBasedOnId(targetAmiId ?? '') ?? {} as Ami);
  }, [selectedBaseMajorVersion, versionReleaseType]);

  useEffect(() => {
    const versions = productData?.product.versions;
    if (!versions?.length || versionReleaseType !== versionReleaseTypes[0]) { return; }
    const sorted = [...versions.filter(
      v => v.status === 'RELEASED' || v.status === 'RETIRED'
    )].sort((a, b) => rcompare(a.name, b.name));
    setSelectedBaseMajorVersion(sorted[0]);
  }, [versionReleaseType]);

  const fetchVersionYaml = async (versionId: string): Promise<string> => {
    const response = await serviceApi.getLatestTemplate(projectId, productId, versionId);
    return response.template || '';
  };

  const nonRetiredVersions = [...
  productData?.product.versions?.filter(
    v => v.status === 'RELEASED' || v.status === 'RETIRED'
  ) ?? []
  ].sort((a, b) => rcompare(a.name, b.name));

  return {
    isUpdate,
    activeStepIndex,
    productVersionDescription,
    setProductVersionDescription,
    isProductVersionDescriptionValid,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    isVersionReleaseTypeValid,
    isAmiSelectValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    setActiveStepIndex,
    yamlDefinition,
    setYamlDefinition,
    originalYamlDefinition,
    isYamlDefinitionValidationInProgress,
    isYamlDefinitionValid,
    setIsYamlDefinitionValid,
    amis: amiData?.amis,
    amisLoading: isAmiDataLoading,
    yamlDefinitionLoading: isTemplateDataLoading,
    selectedAmi,
    setSelectedAmi,
    baseMajorVersions: latestMajorVersionsData?.versions,
    isBaseMajorVersionsLoading: isLatestMajorVersionsLoading,
    selectedBaseMajorVersion,
    setSelectedBaseMajorVersion,
    releasedVersions: nonRetiredVersions,
    fetchVersionYaml,
  };
};