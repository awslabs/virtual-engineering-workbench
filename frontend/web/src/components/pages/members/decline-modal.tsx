import { FC, useState } from 'react';
import { Box, SpaceBetween, Button, Modal, Textarea } from '@cloudscape-design/components';
import { i18n } from './members.translations';

type Props = {
  isOpen: boolean,
  onClose: () => void,
  onSubmit: (reason: string) => void,
  isLoading: boolean,
};


export const DeclineModal: FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}) => {
  const [value, setValue] = useState('');
  const reasonInvalid = value.trim() === '';

  return (
    <Modal
      visible={isOpen}
      onDismiss={() => {
        onClose();
        setValue('');
      }}
      header={i18n.declineModalHeader}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xxl">
            <Button
              variant="link"
              onClick={() => {
                onClose();
                setValue('');
              }}>
              {i18n.declineModalButtonBack}
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                onSubmit(value);
                setValue('');
              }}
              loading={isLoading}
              disabled={reasonInvalid}
            >
              {i18n.declineModalButtonSubmit}
            </Button>
          </SpaceBetween>
        </Box>
      }
      data-test='decline-modal'
    >
      <p>{i18n.declineModalDescriptionTop}</p>
      <b>{i18n.declineEnrolmentTextReason}<i>{i18n.declineEnrolmentTextRequired}</i></b>
      <Textarea
        onChange={({ detail }) => setValue(detail.value)}
        value={value}
      />
      <p>{i18n.declineModalDescriptionBottom}</p>
    </Modal>
  );
};