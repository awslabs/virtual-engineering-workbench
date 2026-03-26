import {
  Container,
  Form,
  FormField,
  Header,
  Input,
  RadioGroup,
  SpaceBetween,
  Select,
  Spinner,
  SelectProps
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './product-version-wizard.translations';
import { PRODUCT_VERSION_RELEASE_TYPE_MAP } from '../../products.translations';
import {
  Ami,
  VersionSummary,
} from '../../../../../services/API/proserve-wb-publishing-api';
import { isNullOrEmpty } from '../../../../../utils/form-validation-helper';

const ZERO = 0;
const ONE = 1;
export interface ProductVersionWizardStep1Props {
  isUpdate: boolean,
  productVersionDescription: string,
  setProductVersionDescription: (description: string) => void,
  isProductVersionDescriptionValid: boolean,
  versionReleaseTypes: string[],
  versionReleaseType: string,
  setVersionReleaseType: (versionReleaseType: string) => void,
  isVersionReleaseTypeValid: boolean,
  isAmiSelectValid: boolean,
  amis: Ami[],
  selectedAmi: Ami,
  setSelectedAmi: (ami: Ami) => void,
  isAmisLoading: boolean,
  baseMajorVersions: VersionSummary[],
  isBaseMajorVersionsLoading: boolean,
  selectedBaseMajorVersion: VersionSummary,
  setSelectedBaseMajorVersion: (version: VersionSummary) => void,
}

export const ProductVersionWizardStep1: FC<ProductVersionWizardStep1Props> = ({
  isUpdate,
  productVersionDescription,
  setProductVersionDescription,
  isProductVersionDescriptionValid,
  isAmiSelectValid,
  versionReleaseTypes,
  versionReleaseType,
  setVersionReleaseType,
  isVersionReleaseTypeValid,
  amis,
  selectedAmi,
  setSelectedAmi,
  isAmisLoading,
  baseMajorVersions,
  isBaseMajorVersionsLoading,
  selectedBaseMajorVersion,
  setSelectedBaseMajorVersion,
}) => {

  function getReleaseTypeOption(prodType: string) {
    return {
      label: PRODUCT_VERSION_RELEASE_TYPE_MAP[prodType],
      value: prodType
    };
  }

  function getAmiOption(inputAmi: Ami) {
    return {
      label: inputAmi?.amiId,
      value: inputAmi?.amiId,
      description: inputAmi?.amiDescription,
      tags: [inputAmi?.amiName],
    };
  }

  function getBaseMajorVersionOption(inputVersionSummary: VersionSummary) {
    return {
      label: inputVersionSummary?.name.split('.')[0] + '.x.x',
      value: inputVersionSummary?.versionId,
      description: 'Latest version: ' + inputVersionSummary?.name
    };
  }

  function getReleaseTypeError() {
    return !isVersionReleaseTypeValid && isNullOrEmpty(versionReleaseType) ?
      i18n.step1InputReleaseTypeError : '';
  }

  function getAmiIdError() {
    return !isAmiSelectValid && isNullOrEmpty(selectedAmi.amiId) ?
      i18n.step1InputAmiIdError : '';
  }

  function returnAmiBasedOnId(amiId: string) {
    const correctAmi = amis?.find(ami => ami.amiId === amiId);
    return correctAmi;
  }

  function renderDescription() {
    return <FormField label={i18n.productDescLabel}
      errorText={!isProductVersionDescriptionValid && i18n.productVersionDescriptionValidationMessage}>
      <Input value={productVersionDescription}
        onChange={({ detail: { value } }) => setProductVersionDescription(value)}
        placeholder={i18n.productDescPlaceholder} />
    </FormField>;
  }

  function renderAmi() {
    return <FormField label={i18n.amiIdLabel} errorText={getAmiIdError()}>
      <Select
        selectedOption={selectedAmi.amiId ? getAmiOption(selectedAmi) : null}
        onChange={({ detail }) =>
          setSelectedAmi(returnAmiBasedOnId(detail.selectedOption.value ?? '') ?? {} as Ami)}
        options={amis?.map(getAmiOption)}
        placeholder={i18n.amiIdPlaceholder}
        filteringType="auto"
        empty={i18n.emptyAmiIdPlaceholder}
        statusType={isAmisLoading || isBaseMajorVersionsLoading ? 'loading' : 'finished'}
        invalid={!isAmiSelectValid}
        data-test='ami-id-select'
      />
    </FormField>;
  }

  const renderAmiImage = () => {
    if (isAmisLoading) {
      return <Spinner size="normal" />;
    }
    return renderAmi();
  };

  function renderReleaseType() {
    return <FormField
      label={i18n.releaseTypeHeader}
      errorText={getReleaseTypeError()}
    >
      <RadioGroup
        onChange={({ detail }) => setVersionReleaseType(detail.value)}
        value={versionReleaseType}
        items={versionReleaseTypes.map(getReleaseTypeOption)}
        data-test="release-type-radio-group"
      />
    </FormField>;
  }

  function changeBaseMajorVersion(selectedOption: SelectProps.Option) {
    setSelectedBaseMajorVersion(
      baseMajorVersions.find(v => v.versionId === selectedOption.value) as VersionSummary
    );
  }

  function renderBaseMajorVersion() {
    return <FormField
      label={i18n.step1BaseMajorVersionLabel}
      description={<label>{i18n.step1BaseMajorVersionLabelDescription1}<br />
        {i18n.step1BaseMajorVersionLabelDescription2}</label>}
    >
      <Select
        options={baseMajorVersions.length > ZERO ? baseMajorVersions.map(getBaseMajorVersionOption) : []}
        selectedOption={selectedBaseMajorVersion !== undefined ?
          getBaseMajorVersionOption(selectedBaseMajorVersion) : null}
        onChange={({ detail }) => changeBaseMajorVersion(detail.selectedOption)}
        placeholder={i18n.step1BaseMajorVersionSelectPlaceholder}
        filteringType="auto"
        empty={i18n.step1BaseMajorVersionSelectEmptyPlaceholder}
        statusType={isBaseMajorVersionsLoading ? 'loading' : 'finished'}
        disabled={baseMajorVersions.length <= ONE}
        data-test='base-version-select'
      />
    </FormField>;
  }

  function isReleaseTypeRendered() {
    return !isUpdate && baseMajorVersions.length > ZERO;
  }

  function isBaseMajorVersionRendered() {
    return !isUpdate &&
    versionReleaseType !== versionReleaseTypes[0] &&
    baseMajorVersions.length > ZERO;
  }

  return <Container
    header={<Header variant="h2">
      {i18n.step1Header}
    </Header>}
  >
    <Form>
      <SpaceBetween direction='vertical' size='l'>
        {renderDescription()}
        {isReleaseTypeRendered() && renderReleaseType()}
        {isBaseMajorVersionRendered() && renderBaseMajorVersion()}
        {renderAmiImage()}
      </SpaceBetween>
    </Form>
  </Container>;
};
