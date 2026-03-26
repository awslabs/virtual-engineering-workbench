/* eslint @stylistic/max-len: off */

export const i18n = {
  title: 'Help us improve VEW by providing feedback',
  text: [
    { emp: 'Share thoughts ', text: 'on your experience with VEW, highlight pain points and offer ideas for improvement.' },
    { emp: 'Report an issue ', text: 'to submit incidents or specific technical requests through the ServiceDesk & DevOps portal.' },
  ],
  feedbackButtonText: 'Share your thoughts',
  incidentButtonText: 'Report an issue',
  jiraIssueSummaryTemplate: (userName: string) => `Virtual Engineering Workbench feedback by ${userName}`,
  feedbackTriggerButtonText: 'Feedback',
};