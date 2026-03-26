import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Multiselect,
} from '@cloudscape-design/components';
import { useComponentShareModal } from './logic';
import { i18nComponentShareModal } from './translations';
import { ComponentShareModalProps } from './interfaces';

function componentShareModal(props: ComponentShareModalProps) {
  const {
    sharePromptVisible,
    setSharePromptVisible,
    selectableOptions,
    selectedOptions,
    setSelectedOptions,
    isShareListValid,
    projectIdsForShare,
  } = useComponentShareModal({ ...props });

  const multiselect =
    <>
      <Multiselect
        selectedOptions={selectedOptions}
        onChange={({ detail }) => {
          setSelectedOptions([...detail.selectedOptions]);
        }}
        options={selectableOptions}
        placeholder={i18nComponentShareModal.choosePlaceholderText}
      />
    </>
  ;
  return (
    <Modal
      onDismiss={() => setSharePromptVisible(false)}
      visible={sharePromptVisible}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={() => setSharePromptVisible(false)}>
              {i18nComponentShareModal.cancelText}
            </Button>
            <Button
              variant="primary"
              disabled={!isShareListValid}
              onClick={() => props.shareConfirmHandler(projectIdsForShare)}
              loading={props.somethingIsPending}
            >
              {i18nComponentShareModal.confirmText}
            </Button>
          </SpaceBetween>
        </Box>
      }
      header={i18nComponentShareModal.headerText}
    >
      <SpaceBetween size="s">
        <Box variant="p">{i18nComponentShareModal.descriptionText}</Box>
        {multiselect}
      </SpaceBetween>
    </Modal>
  );
}

export { componentShareModal as ComponentShareModal };
