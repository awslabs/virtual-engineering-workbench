export interface SelectableOption {
  label?: string,
  value?: string,
  description?: string,
  disabled?: boolean,
}
export interface ComponentShareModalProps {
  somethingIsPending: boolean,
  associatedProjectIds: string[],
  sharePromptVisible: boolean,
  setSharePromptVisible: (value: boolean) => void,
  shareConfirmHandler: (values: string[]) => void,
}

export interface ComponentShareModalHookProps {
  associatedProjectIds: string[],
  sharePromptVisible: boolean,
  setSharePromptVisible: (value: boolean) => void,
}
export interface ComponentShareModalHookResult
  extends Omit<
    ComponentShareModalProps,
  'shareConfirmHandler' | 'somethingIsPending'
  > {
  selectableOptions: SelectableOption[],
  selectedOptions: SelectableOption[],
  setSelectedOptions: (value: SelectableOption[]) => void,
  isShareListValid: boolean,
  projectIdsForShare: string[],
}
