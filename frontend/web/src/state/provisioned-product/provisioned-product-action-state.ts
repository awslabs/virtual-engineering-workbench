import { atomFamily } from 'recoil';

export enum ProvisionedProductActionState {
  None,
  InitiatingStart,
  InitiatingStop,
}

export const provisionedProductActionState = atomFamily<ProvisionedProductActionState, string>({
  key: 'provisioned-product-ation-state',
  default: ProvisionedProductActionState.None,
});
