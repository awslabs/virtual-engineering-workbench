export interface FeedbackTriggerTranslations {
  feedbackTriggerButtonText: string,
}

export interface FeedbackPopupTextItem {
  emp: string,
  text: string,
}

export interface FeedbackPopupTranslations {
  title: string,
  text: FeedbackPopupTextItem[],
  feedbackButtonText: string,
  incidentButtonText: string,
}

export interface CollectorConfig {
  collectorUrl: string,
  collectorId: string,
}

export interface FeedbackTriggerProps {
  onClick?: () => void,
  translations: FeedbackTriggerTranslations,
  feedbackPopupHidden: boolean,
}

export interface FeedbackPopupProps {
  showCollectorDialogFunc?: () => void,
  setShowCollectorDialogFunc: (func: () => void) => void,
  onCloseClick?: () => void,
  onFeedbackButtonClick?: () => void,
  onIncidentButtonClick?: () => void,
  translations: FeedbackPopupTranslations,
  collector: CollectorConfig,
}

export interface FeedbackProps {
  collector: CollectorConfig,
}