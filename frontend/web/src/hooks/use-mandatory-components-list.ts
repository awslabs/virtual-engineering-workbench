import { useState, useCallback } from 'react';
import { ComponentVersionEntry } from '../services/API/proserve-wb-packaging-api';

export interface MandatoryComponentsListState {
  prependedComponents: ComponentVersionEntry[],
  appendedComponents: ComponentVersionEntry[],
}

export interface UseMandatoryComponentsListReturn {
  prependedComponents: ComponentVersionEntry[],
  appendedComponents: ComponentVersionEntry[],
  addPrependedComponent: (component: ComponentVersionEntry) => void,
  addAppendedComponent: (component: ComponentVersionEntry) => void,
  removePrependedComponent: (componentId: string) => void,
  removeAppendedComponent: (componentId: string) => void,
  setPrependedComponents: (components: ComponentVersionEntry[]) => void,
  setAppendedComponents: (components: ComponentVersionEntry[]) => void,
  validateNoDuplicates: () => boolean,
  hasDuplicateComponents: boolean,
}

export const useMandatoryComponentsList = (
  initialPrependedComponents: ComponentVersionEntry[] = [],
  initialAppendedComponents: ComponentVersionEntry[] = []
): UseMandatoryComponentsListReturn => {
  const [prependedComponents, setPrependedComponents] = useState<ComponentVersionEntry[]>(
    initialPrependedComponents
  );
  const [appendedComponents, setAppendedComponents] = useState<ComponentVersionEntry[]>(
    initialAppendedComponents
  );
  const [hasDuplicateComponents, setHasDuplicateComponents] = useState(false);

  const validateNoDuplicates = useCallback((): boolean => {
    const prependedIds = new Set(prependedComponents.map(c => c.componentId));
    const appendedIds = new Set(appendedComponents.map(c => c.componentId));

    for (const id of prependedIds) {
      if (appendedIds.has(id)) {
        setHasDuplicateComponents(true);
        return false;
      }
    }

    setHasDuplicateComponents(false);
    return true;
  }, [prependedComponents, appendedComponents]);

  const addPrependedComponent = useCallback((component: ComponentVersionEntry) => {
    setPrependedComponents(prev => {
      const exists = prev.some(c => c.componentId === component.componentId);
      if (exists) {
        return prev;
      }
      return [...prev, component];
    });
  }, []);

  const addAppendedComponent = useCallback((component: ComponentVersionEntry) => {
    setAppendedComponents(prev => {
      const exists = prev.some(c => c.componentId === component.componentId);
      if (exists) {
        return prev;
      }
      return [...prev, component];
    });
  }, []);

  const removePrependedComponent = useCallback((componentId: string) => {
    setPrependedComponents(prev => prev.filter(c => c.componentId !== componentId));
  }, []);

  const removeAppendedComponent = useCallback((componentId: string) => {
    setAppendedComponents(prev => prev.filter(c => c.componentId !== componentId));
  }, []);

  return {
    prependedComponents,
    appendedComponents,
    addPrependedComponent,
    addAppendedComponent,
    removePrependedComponent,
    removeAppendedComponent,
    setPrependedComponents,
    setAppendedComponents,
    validateNoDuplicates,
    hasDuplicateComponents,
  };
};
