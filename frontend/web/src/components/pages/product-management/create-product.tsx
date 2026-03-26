import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  HelpPanel,
  Input,
  Select,
  SpaceBetween,
  Spinner
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-product.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { useCreateProduct } from './create-product.logic';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { Technology } from '../../../services/API/proserve-wb-projects-api';
import { PRODUCT_TYPE_MAP } from './products.translations';

export const CreateProduct = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <div>No program selected</div>;
  }
  const {
    technologies,
    isLoadingTechnologies,
    productName,
    setProductName,
    productDescription,
    setProductDescription,
    technology,
    setTechnology,
    saveProduct,
    isSaving,
    productTypes,
    productType,
    setProductType,
    isProductNameValid,
    isProductDescriptionValid,
    isProductTechnologyValid,
    isProductTypeValid,
    isSubmitted
  } = useCreateProduct({ projectId: selectedProject.projectId });

  const { navigateTo, getPathFor } = useNavigationPaths();

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Products) },
          { path: i18n.breadcrumbLevel2, href: '#' }
        ]}
        content={renderContent()}
        customHeader={renderHeader()}
        tools={renderTools()}
      />
    </>
  );

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
    >{i18n.infoHeader}</Header>;
  }

  function renderContent() {
    return <>
      <SpaceBetween size='l'>
        <Container header={
          <Header variant='h2'>
            {i18n.productDetailsHeaderLabel}
          </Header>
        }>
          {!!isLoadingTechnologies && <Spinner size='big' />}
          {!isLoadingTechnologies && renderInputForm()}
        </Container>
        {renderButtons()}
      </SpaceBetween>
    </>;
  }

  function renderButtons() {
    return <>
      <Box float='right'>
        <SpaceBetween direction='horizontal' size='xs' alignItems='end'>
          <Button
            data-test='create-product-cancel-button'
            onClick={() => {
              navigateTo(RouteNames.Products);
            }}>
            {i18n.cancelButtonText}
          </Button>
          <Button
            onClick={saveProduct}
            data-test='create-product-create-button'
            variant='primary'
            loading={isSaving}
          >
            {i18n.createButtonText}
          </Button>
        </SpaceBetween>
      </Box>
    </>;
  }

  function displayConstraintText(message: string, isValid: boolean) {
    return (!isSubmitted || isSubmitted && isValid) && message;
  }

  function displayErrorMessage(message: string, isValid: boolean) {
    return isSubmitted && !isValid && message;
  }

  // eslint-disable-next-line complexity
  function renderInputForm() {
    return <>
      <Form data-test='create-product-form'>
        <SpaceBetween direction='vertical' size='l'>
          <FormField
            label={i18n.productNameLabel}
            constraintText={displayConstraintText(i18n.productNameValidationMessage, isProductNameValid())}
            errorText={displayErrorMessage(i18n.productNameValidationMessage, isProductNameValid())}
            data-test='create-product-name-field'>
            <Input value={productName}
              onChange={({ detail: { value } }) => setProductName(value)}
              invalid={isSubmitted && !isProductNameValid()}
              placeholder={i18n.productNamePlaceholder} />
          </FormField>
          <FormField label={i18n.productDescLabel}
            constraintText={displayConstraintText(
              i18n.productDescriptionValidationMessage,
              isProductDescriptionValid()
            )}
            errorText={displayErrorMessage(
              i18n.productDescriptionValidationMessage,
              isProductDescriptionValid()
            )}
            data-test='create-product-description-field'>
            <Input value={productDescription}
              invalid={isSubmitted && !isProductDescriptionValid()}
              onChange={({ detail: { value } }) => setProductDescription(value)}
              placeholder={i18n.productDescPlaceholder} />
          </FormField>
          <FormField label={i18n.technologyLabel}
            data-test='create-product-technology-field'
            errorText={displayErrorMessage(i18n.technologyPlaceholder, isProductTechnologyValid())}>
            <Select
              selectedOption={technology ? getTechnologyOption(technology) : null}
              onChange={({ detail }) => setTechnology({
                name: detail.selectedOption.label ?? '',
                id: detail.selectedOption.value ?? ''
              })}
              invalid={isSubmitted && technology === undefined}
              options={technologies.map(getTechnologyOption)}
              statusType={isLoadingTechnologies ? 'loading' : 'finished'}
              placeholder={i18n.technologyPlaceholder}
            />
          </FormField>
          <FormField
            label={i18n.productTypeLabel}
            errorText={displayErrorMessage(i18n.productTypePlaceholder, isProductTypeValid())}
            data-test='create-product-type-field' >
            <Select
              selectedOption={productType ? getProductTypeOption(productType) : null}
              onChange={({ detail }) => setProductType(detail.selectedOption.value ?? '')}
              invalid={isSubmitted && productType === undefined}
              options={productTypes.map(getProductTypeOption)}
              placeholder={i18n.productTypePlaceholder}
            />
          </FormField>
        </SpaceBetween>
      </Form>
    </>;
  }

  function getTechnologyOption(t: Technology) {
    return {
      label: t.name, value: t.id
    };
  }

  function getProductTypeOption(prodType: string) {
    return {
      label: PRODUCT_TYPE_MAP[prodType],
      value: prodType
    };
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box>
            <p>{i18n.infoPanelMessage3}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b><br />{i18n.infoPanelPoint2Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
