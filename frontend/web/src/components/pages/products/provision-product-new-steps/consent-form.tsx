import { FC, useState } from 'react';
import { Box, Checkbox } from '@cloudscape-design/components';
import { UserPrompt } from '../../shared/user-prompt';

type Props = {
  cancelConfirmVisible: boolean,
  setCancelConfirmVisible: (visible: boolean) => void,
  handleCancelConfirm: () => void,
  i18nStrings: {
    cancelPromptHeader: string,
    cancelPromptText1: string,
    cancelPromptText2: string,
    cancelPromptText3: string,
    cancelPromptCancelText: string,
    cancelPromptConfirmText: string,
    submitButton: string,
    consentFormHeader: string,
    consentFormDescription: string[],
    consentFormUsePoliciesHeader: string,
    consentFormUsePolicies: string[],
    consentFormResponsibilitiesHeader: string,
    consentFormResponsibilities1: string[],
    consentFormResponsibilities2: string[],
    consentFormRisksHeader: string,
    consentFormRisks1: string[],
    consentFormRisks2: string[],
    consentFormRisks3: string[],
    consentFormAcknowledgement: string[],
    consentFormCheckboxLabel: string,
  },
};

export const ConsentForm: FC<Props> = ({
  cancelConfirmVisible,
  setCancelConfirmVisible,
  handleCancelConfirm,
  i18nStrings,
}) => {

  const [isChecked, setIsChecked] = useState(false); // State to track checkbox state

  const handleCheckboxChange = () => {
    setIsChecked(!isChecked);
  };

  function createModalText() {
    return <>
      <Box variant="p">
        <dl>{i18nStrings.consentFormDescription}</dl>
        <p><strong>{i18nStrings.consentFormUsePoliciesHeader}</strong></p>
        <ul>
          <li>{i18nStrings.consentFormUsePolicies[0]}</li>
          <li>{i18nStrings.consentFormUsePolicies[1]}</li>
          <li>{i18nStrings.consentFormUsePolicies[2]}</li>
          <li>{i18nStrings.consentFormUsePolicies[3]}</li>
        </ul>
        <p><strong>{i18nStrings.consentFormResponsibilitiesHeader}</strong></p>
        <ul>
          <li>{i18nStrings.consentFormResponsibilities1}</li>
          <li>{i18nStrings.consentFormResponsibilities2}</li>
        </ul>
        <p><strong>{i18nStrings.consentFormRisksHeader}</strong></p>
        <ul>
          <li>{i18nStrings.consentFormRisks1}</li>
          <li>{i18nStrings.consentFormRisks2}</li>
          <li>{i18nStrings.consentFormRisks3}</li>
        </ul>
        <dl>{i18nStrings.consentFormAcknowledgement}</dl>
      </Box>
      <Checkbox checked={isChecked} onChange={handleCheckboxChange}>
        {i18nStrings.consentFormCheckboxLabel}
      </Checkbox>
    </>;
  }

  return (
    <UserPrompt
      onConfirm={handleCancelConfirm}
      onCancel={() => setCancelConfirmVisible(false)}
      headerText={i18nStrings.consentFormHeader}
      content={createModalText()}
      cancelText={i18nStrings.cancelPromptCancelText}
      confirmText={i18nStrings.submitButton}
      confirmButtonLoading={false}
      confirmButtonDisabled={!isChecked}
      visible={cancelConfirmVisible}
    />

  );
};