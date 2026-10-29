// why a workbench failed to launch or start, in plain words (components: workbench-failure.tsx).
// The hub classifies the raw AWS reason into a stable code (failure.code); admins also see the raw reason.
import { useEffect, useRef } from 'react';
import { useRecoilValue } from 'recoil';
import {
  ProvisionedProduct,
  WorkbenchFailure,
} from '../../../services/API/proserve-wb-provisioning-api';
import { ProjectRoles, selectedProjectState } from '../../../state';
import { useNotifications } from '../../layout';
const TRANSITIONAL_STATUSES: ReadonlySet<string> = new Set([
  'STARTING', 'PROVISIONING', 'STOPPING', 'SHUTTING_DOWN',
  'DEPROVISIONING', 'UPDATING', 'CONFIGURATION_IN_PROGRESS',
]);

function isTransitional(status?: string): boolean {
  return status !== undefined && TRANSITIONAL_STATUSES.has(status.toUpperCase());
}

export interface FailureText {
  header: string,
  content: string,
}

const OPERATION_VERBS: Record<string, string> = {
  LAUNCH: 'launched',
  START: 'started',
  UPDATE: 'updated',
  REMOVE: 'removed',
};

const ADMIN_ROLES: readonly string[] = [ProjectRoles.Admin, ProjectRoles.ProgramOwner];

function instanceFamily(instanceType?: string): string {
  return instanceType?.split('.')[0] ?? 'this';
}

function nextStep(failure: WorkbenchFailure): string {
  if (failure.operation === 'LAUNCH') {
    return 'Remove this workbench and launch it again.';
  }
  if (failure.operation === 'START') {
    return 'Start it again.';
  }
  return '';
}

export function failureText(failure: WorkbenchFailure, reference: string, region?: string): FailureText {
  const where = region ? `in ${region}` : 'in this region';
  const verb = OPERATION_VERBS[failure.operation ?? ''] ?? 'set up';
  const instanceType = failure.instanceType ?? 'this instance type';
  const contact = `Contact the platform team with the reference ${reference}.`;
  switch (failure.code) {
    case 'CAPACITY':
      return {
        header: `AWS has no free capacity for ${instanceType} right now`,
        content: [
          `The workbench couldn't be ${verb}: AWS had no free ${instanceType} ${where} at that moment.`,
          'Nothing is wrong with the workbench or VEW, and it can\'t be known in advance.',
          failure.gpu
            ? `GPU capacity ${where} is often tight; it usually comes back within hours.`
            : '',
          `Try again later, or choose another size. ${nextStep(failure)}`,
        ].filter(Boolean).join(' '),
      };
    case 'QUOTA':
      return {
        header: `The program's AWS quota for ${instanceFamily(failure.instanceType)} instances is used up`,
        content: `The workbench couldn't be ${verb}: the program's AWS account can't run more of these `
          + 'instances. Stop another workbench of this kind, or ask your program admin to raise the quota.',
      };
    case 'UNSUPPORTED_IN_AZ':
      return {
        header: `${instanceType} isn't available where this workbench runs`,
        content: `The workbench couldn't be ${verb}: AWS doesn't offer ${instanceType} in this workbench's `
          + `availability zone. Choose another size. ${nextStep(failure)}`,
      };
    case 'PERMISSIONS':
      return {
        header: `VEW wasn't allowed to finish: the workbench couldn't be ${verb}`,
        content: `An AWS permission blocked it. ${contact}`,
      };
    case 'TEMPLATE':
      return {
        header: `The workbench's product couldn't be ${verb}`,
        content: `The product version failed while VEW set it up. ${contact}`,
      };
    default:
      return {
        header: `The workbench couldn't be ${verb}`,
        content: `VEW didn't recognise the reason. ${contact}`,
      };
  }
}

export function useCanSeeRawFailureReason(): boolean {
  const roles = useRecoilValue(selectedProjectState).roles ?? [];
  return roles.some((role) => ADMIN_ROLES.includes(role));
}

// A launch or start that fails while the page is open: tell the user at once, not only on the card.
export function useWorkbenchFailureNotifications(products: readonly (ProvisionedProduct | undefined)[]) {
  const { showErrorNotification } = useNotifications();
  const previousStatuses = useRef(new Map<string, string>());

  useEffect(() => {
    for (const product of products) {
      if (!product) {
        continue;
      }
      const previous = previousStatuses.current.get(product.provisionedProductId);
      const settled = previous !== undefined && isTransitional(previous) && !isTransitional(product.status);
      if (settled && product.failure) {
        const text = failureText(product.failure, product.provisionedProductId, product.region);
        showErrorNotification({ header: `${product.productName}: ${text.header}`, content: text.content });
      }
      previousStatuses.current.set(product.provisionedProductId, product.status);
    }
  }, [products, showErrorNotification]);
}
