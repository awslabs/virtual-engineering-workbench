import { FC } from 'react';
import { Box, SpaceBetween, Button, Modal } from '@cloudscape-design/components';
import { i18n } from './retire-version.translations';


type Props = {
  versionName: string,
  isOpen: boolean,
  onClose: () => void,
  onConfirm: () => void,
  isLoading: boolean,
};


export const RetireVersionModal: FC<Props> = ({
  versionName,
  isOpen,
  onClose,
  onConfirm,
  isLoading
}) => {
  return (
    <Modal
      size='medium'
      visible={isOpen}
      onDismiss={onClose}
      header={i18n.modalHeader}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="s">
            <Button variant="link" onClick={onClose}>{i18n.modalButtonCancel}</Button>
            <Button
              variant="primary"
              onClick={onConfirm}
              loading={isLoading}
            >
              {i18n.modalButtonConfirm}
            </Button>
          </SpaceBetween>
        </Box>
      }
      data-test='retire-version-modal'
    >
      <p>{i18n.modalDescriptionTop} <strong>{versionName}</strong></p>
      <p>{i18n.modalDescriptionMiddle}</p>
      <p>{i18n.modalDescriptionBottom}</p>
    </Modal>
  );
};