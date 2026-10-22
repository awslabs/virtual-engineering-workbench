// a workbench's failure on its card and details page (texts: workbench-failure.logic.ts).
import { Alert, Box, ExpandableSection, SpaceBetween } from '@cloudscape-design/components';
import { ProvisionedProduct } from '../../../services/API/proserve-wb-provisioning-api';
import { failureText, useCanSeeRawFailureReason } from './workbench-failure.logic';

interface WorkbenchFailureProps {
  provisionedProduct?: ProvisionedProduct,
}

export function WorkbenchFailureAlert({ provisionedProduct }: WorkbenchFailureProps) {
  const showRawReason = useCanSeeRawFailureReason();
  const failure = provisionedProduct?.failure;
  if (!provisionedProduct || !failure) {
    return null;
  }
  const text = failureText(failure, provisionedProduct.provisionedProductId, provisionedProduct.region);
  return (
    <Alert
      type={failure.operation === 'START' ? 'warning' : 'error'}
      header={text.header}
      data-test="workbench-failure"
    >
      <SpaceBetween size="xs">
        <Box variant="p">{text.content}</Box>
        {showRawReason && provisionedProduct.statusReason &&
          <ExpandableSection headerText="AWS reason (admins)" variant="footer">
            <Box variant="code">{provisionedProduct.statusReason}</Box>
          </ExpandableSection>
        }
      </SpaceBetween>
    </Alert>
  );
}

// One line on the workbench card.
export function WorkbenchFailureSummary({ provisionedProduct }: WorkbenchFailureProps) {
  const failure = provisionedProduct?.failure;
  if (!provisionedProduct || !failure) {
    return null;
  }
  const text = failureText(failure, provisionedProduct.provisionedProductId, provisionedProduct.region);
  return (
    <Box
      color={failure.operation === 'START' ? 'text-status-warning' : 'text-status-error'}
      fontSize="body-s"
      data-test={`wb-failure-${provisionedProduct.provisionedProductId}`}
    >
      {text.header}
    </Box>
  );
}
