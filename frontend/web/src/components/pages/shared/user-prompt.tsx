import React from 'react';
import { Box, Button, SpaceBetween } from '@cloudscape-design/components';
import Modal from '@cloudscape-design/components/modal';

const userPrompt = ({
  onConfirm,
  onCancel,
  headerText,
  content,
  cancelText,
  confirmText,
  confirmButtonLoading,
  confirmButtonDisabled,
  confirmButtonHidden,
  visible,
  'data-test': dataTest,
  size = 'medium'
}: {
  onConfirm: () => void,
  onCancel: () => void,
  headerText: string,
  content: React.ReactNode,
  cancelText: string,
  confirmText: string,
  confirmButtonLoading: boolean,
  confirmButtonDisabled?: boolean,
  confirmButtonHidden?: boolean,
  visible: boolean,
  'data-test'?: string, // eslint-disable-line @typescript-eslint/naming-convention
  size?: 'small' | 'medium' | 'large' | 'max',
}) => {
  return (
    <Modal
      onDismiss={onCancel}
      visible={visible}
      closeAriaLabel="Close modal"
      size={size}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button
              data-test="modal-cancel-button"
              onClick={onCancel}
              variant="link">{cancelText}</Button>
            {!confirmButtonHidden && <Button
              data-test="modal-confirm-button"
              onClick={onConfirm}
              variant="primary"
              loading={confirmButtonLoading}
              disabled={confirmButtonDisabled}
            >
              {confirmText}
            </Button>}
          </SpaceBetween>
        </Box>
      }
      header={headerText}
      data-test={dataTest}
    >
      {content}
    </Modal>
  );

};

export { userPrompt as UserPrompt };