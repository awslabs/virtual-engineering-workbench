import { OutputParameter } from '../../state';
import {
  Feature,
  FeatureToggleItem,
  WorkbenchFeatureToggleItem,
} from './feature-toggle.state';
import { useCallback, useMemo } from 'react';
import { ProvisionedProduct } from '../../services/API/proserve-wb-provisioning-api';
import { useNotifications } from '../layout';

export const FEATURE_TOGGLE_WORKBENCH = 'FeatureToggles';

export function getWorkbenchFeatureToggles(workbenchOutputParams: OutputParameter[]): FeatureToggleItem[] {
  return workbenchOutputParams
    .filter(p => p.outputKey === FEATURE_TOGGLE_WORKBENCH)
    .flatMap(p => JSON.parse(p.outputValue) as WorkbenchFeatureToggleItem[])
    .filter(uf => {
      return Object.values<string>(Feature).includes(uf.feature);
    })
    .map(wf => {
      return {
        enabled: wf.enabled,
        feature: Feature[wf.feature as keyof typeof Feature],
        version: '1.0.0',
      } as FeatureToggleItem;
    });
}

type ReturnType = {
  isFeatureEnabled: (projectId: Feature) => boolean,
};

export function useWorkbenchFeatureToggles(provisionedProduct: ProvisionedProduct): ReturnType {

  const { showErrorNotification } = useNotifications();

  const activeFeatureToggles = useMemo(() => {
    try {
      return getWorkbenchFeatureToggles(provisionedProduct.outputs || []);
    } catch (e) {
      showErrorNotification({
        header: 'Failed to load product feature toggles',
        content: `${e}`,
      });
      return [];
    }
  }, [provisionedProduct]);


  const isFeatureEnabled = useCallback((feature: Feature): boolean => {
    return activeFeatureToggles.find(x => x.feature === feature && x.enabled) !== undefined;
  }, [activeFeatureToggles]);

  return { isFeatureEnabled };
}