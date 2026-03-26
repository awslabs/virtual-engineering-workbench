import { FC } from 'react';
import { Box } from '@cloudscape-design/components';
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
  },
};

export const CancelPrompt: FC<Props> = ({
  cancelConfirmVisible,
  setCancelConfirmVisible,
  handleCancelConfirm,
  i18nStrings,
}) => {

  function createModalText() {
    return <>
      <Box variant="p">{i18nStrings.cancelPromptText1}</Box>
      <Box variant="p">{i18nStrings.cancelPromptText2}</Box>
      <Box variant="p">{i18nStrings.cancelPromptText3}</Box>
    </>;
  }

  return (
    <UserPrompt
      onConfirm={handleCancelConfirm}
      onCancel={() => setCancelConfirmVisible(false)}
      headerText={i18nStrings.cancelPromptHeader}
      content={createModalText()}
      cancelText={i18nStrings.cancelPromptCancelText}
      confirmText={i18nStrings.cancelPromptConfirmText}
      confirmButtonLoading={false}
      visible={cancelConfirmVisible}
      data-test="cancel-product-version-prompt"
    />
  );
};