import { i18n } from '.';
import {
  ProvisionedProduct,
} from '../../../../services/API/proserve-wb-provisioning-api/index.ts';

export type ProvisionedProductLoginTranslations = typeof i18n;

export interface ProvisionedProductLoginProps {
  loginPromptVisible: boolean,
  setLoginPromptVisible: (state: boolean) => void,
  provisionedProduct: ProvisionedProduct,
  i18n: ProvisionedProductLoginTranslations,
  headlessLogin?: boolean,
}
