import {
  ComponentVersionEntry,
  MandatoryComponentsList,
} from '../../../../../services/API/proserve-wb-packaging-api';
import { useState, useEffect } from 'react';
import { WizardProps, SelectProps } from '@cloudscape-design/components';
import { PACKAGING_OS_VERSIONS, PACKAGING_SUPPORTED_ARCHITECTURES } from '../..';

const EMPTY_ARRAY_LENGTH = 0;
const MIN_COMPONENT_VERSION_ENTRIES = 1;

// eslint-disable-next-line complexity
export const useMandatoryComponentsListWizard = ({
  mandatoryComponentsList = {} as MandatoryComponentsList
}: {
  mandatoryComponentsList?: MandatoryComponentsList,
}) => {
  const isUpdate = !!mandatoryComponentsList.mandatoryComponentsListPlatform;
  const STEP_1_INDEX = 1;
  // eslint-disable-next-line @typescript-eslint/no-magic-numbers
  const STEP_2_INDEX = isUpdate ? 1 : 2;
  // eslint-disable-next-line @typescript-eslint/no-magic-numbers
  const STEP_3_INDEX = isUpdate ? 2 : 3;
  // eslint-disable-next-line @typescript-eslint/no-magic-numbers
  const STEP_4_INDEX = isUpdate ? 3 : 4;
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);

  // Separate state for prepended and appended components
  const [prependedComponentVersionEntries, setPrependedComponentVersionEntries]
    = useState<ComponentVersionEntry[]>(
      (mandatoryComponentsList?.prependedComponentsVersions || [])
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .map(({ position, ...rest }) => rest)
    );
  const [appendedComponentVersionEntries, setAppendedComponentVersionEntries]
    = useState<ComponentVersionEntry[]>(
      (mandatoryComponentsList?.appendedComponentsVersions || [])
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .map(({ position, ...rest }) => rest)
    );

  const [mandatoryComponentsListPlatform, setMandatoryComponentsListPlatform]
    = useState<string>(mandatoryComponentsList?.mandatoryComponentsListPlatform);
  const [
    mandatoryComponentsListOsVersion,
    setMandatoryComponentsListOsVersion,
  ] = useState<SelectProps.Option>({
    value: mandatoryComponentsList.mandatoryComponentsListOsVersion,
  });
  const [mandatoryComponentsListArchitecture, setMandatoryComponentsListArchitecture] =
    useState<SelectProps.Option>({
      value: mandatoryComponentsList.mandatoryComponentsListArchitecture,
    });
  const availableRecipeSupportedOsVersions = PACKAGING_OS_VERSIONS[mandatoryComponentsListPlatform] || [];
  const availableRecipeSupportedArchitectures =
    PACKAGING_SUPPORTED_ARCHITECTURES[mandatoryComponentsListPlatform] || [];
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isPrependedComponentsValid, setIsPrependedComponentsValid] = useState(true);
  const [isAppendedComponentsValid, setIsAppendedComponentsValid] = useState(true);
  const [hasDuplicateComponents, setHasDuplicateComponents] = useState(false);

  useEffect(() => {
    if (mandatoryComponentsList?.mandatoryComponentsListPlatform) {
      setMandatoryComponentsListPlatform(mandatoryComponentsList.mandatoryComponentsListPlatform);
      setMandatoryComponentsListArchitecture({
        value: mandatoryComponentsList.mandatoryComponentsListArchitecture
      });
      setMandatoryComponentsListOsVersion({
        value: mandatoryComponentsList.mandatoryComponentsListOsVersion,
      });

      // Remove position field so components render as editable in the wizard
      const prependedWithoutPosition = (mandatoryComponentsList.prependedComponentsVersions || [])
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .map(({ position, ...rest }) => rest);
      const appendedWithoutPosition = (mandatoryComponentsList.appendedComponentsVersions || [])
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        .map(({ position, ...rest }) => rest);

      setPrependedComponentVersionEntries(prependedWithoutPosition);
      setAppendedComponentVersionEntries(appendedWithoutPosition);
    }
  }, [mandatoryComponentsList]);

  function isPlatformValid() {
    return mandatoryComponentsListPlatform !== undefined;
  }

  function isSupportedArchitectureValid() {
    return mandatoryComponentsListArchitecture !== undefined;
  }

  function isSupportedOsVersionValid() {
    return mandatoryComponentsListOsVersion !== undefined;
  }

  function isStep1Valid() {
    return isPlatformValid() && isSupportedArchitectureValid() && isSupportedOsVersionValid();
  }

  function validateComponentVersionEntries(items: ComponentVersionEntry[]) {
    for (const item of items) {
      if (!item.componentId || !item.componentVersionId) {
        return false;
      }
    }
    return true;
  }

  function checkForDuplicates() {
    const prependedIds = new Set(prependedComponentVersionEntries.map(c => c.componentId));
    const appendedIds = new Set(appendedComponentVersionEntries.map(c => c.componentId));

    for (const id of prependedIds) {
      if (appendedIds.has(id)) {
        setHasDuplicateComponents(true);
        return true;
      }
    }
    setHasDuplicateComponents(false);
    return false;
  }

  function isStep2Valid() {
    const isValid = validateComponentVersionEntries(prependedComponentVersionEntries);
    setIsPrependedComponentsValid(isValid);
    return isValid;
  }

  function isStep3Valid() {
    const isValid = validateComponentVersionEntries(appendedComponentVersionEntries);
    setIsAppendedComponentsValid(isValid);
    const hasDupes = checkForDuplicates();
    return isValid && !hasDupes;
  }

  function isStep4Valid() {
    const EMPTY_ARRAY_LENGTH = 0;
    // At least one component must be specified
    const hasComponents = prependedComponentVersionEntries.length > EMPTY_ARRAY_LENGTH ||
                         appendedComponentVersionEntries.length > EMPTY_ARRAY_LENGTH;
    return hasComponents && !checkForDuplicates();
  }

  // eslint-disable-next-line complexity
  function isStepValid(index: number) {
    if (!isUpdate && index === STEP_1_INDEX) {
      return isStep1Valid();
    }

    if (index === STEP_2_INDEX) {
      return isStep2Valid();
    }

    if (index === STEP_3_INDEX) {
      return isStep3Valid();
    }

    if (index === STEP_4_INDEX) {
      return isStep4Valid();
    }

    return true;
  }

  function requiresValidation(reason: string) {
    return reason === 'next';
  }

  function handleOnNavigate(detail: WizardProps.NavigateDetail) {
    if (requiresValidation(detail.reason) && !isStepValid(detail.requestedStepIndex)) {
      setIsSubmitted(true);
      return;
    }
    setIsSubmitted(false);
    setActiveStepIndex(detail.requestedStepIndex);
  }

  return {
    activeStepIndex,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    setActiveStepIndex,
    mandatoryComponentsListPlatform,
    setMandatoryComponentsListPlatform,
    mandatoryComponentsListOsVersion,
    setMandatoryComponentsListOsVersion,
    mandatoryComponentsListArchitecture,
    setMandatoryComponentsListArchitecture,
    availableRecipeSupportedArchitectures,
    availableRecipeSupportedOsVersions,
    isSupportedArchitectureValid,
    isSupportedOsVersionValid,
    isPlatformValid,
    isSubmitted,
    prependedComponentVersionEntries,
    setPrependedComponentVersionEntries,
    appendedComponentVersionEntries,
    setAppendedComponentVersionEntries,
    isPrependedComponentsValid,
    isAppendedComponentsValid,
    hasDuplicateComponents,
    minComponentVersionEntries: MIN_COMPONENT_VERSION_ENTRIES,
    isUpdate,
    step1Index: STEP_1_INDEX,
    step2Index: STEP_2_INDEX,
    step3Index: STEP_3_INDEX,
    step4Index: STEP_4_INDEX,
  };
};