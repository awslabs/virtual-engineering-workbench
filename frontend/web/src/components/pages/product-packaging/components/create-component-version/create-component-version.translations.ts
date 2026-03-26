export const i18n = {
  breadcrumbLevel1: 'Product management: Components',
  breadcrumbLevel2: 'View component',
  breadcrumbLevel3: 'Create component version',
  header: 'Create version',
  headerDescription: 'Create a new component version by specifying a YAML definition',
  cancelButtonText: 'Cancel',
  createButtonText: 'Create component version',
  createSuccessMessageHeader: 'Version creation started successfully',
  createSuccessMessageContent: 'Version creation may take a few minutes. Refer to table below for status.',
  createFailMessageHeader: 'Failed to create version',
  step1infoPanelHeader: 'Enter details',
  step1infoPanelLabel1: 'How do I fill this information in?',
  step1infoPanelMessage1: `The creation of a new component version requires details such as the description 
  of the new changes, the software vendor developing the software included in the component version 
  (including its version).`,
  step1infoPanelMessage2: `If the software included in the component version consumes licences 
  that are monitored, a license dashboard URL should be provided: filling this field is not mandatory.`,
  step1infoPanelMessage3: `If the installed software contains multiple tools, please list the 
  all in the Notes field.`,
  step1infoPanelMessage4: `A release type must be selected accordingly to the changes included 
  in the new component version:`,
  step1infoPanelPoint1: `Major release: to be selected in case of major or breaking changes of the software 
  included in the new component version (version format: 1.0.0-rc.1)`,
  step1infoPanelPoint2: `Minor release: to be selected in case of minor changes of the software 
  included in the new component version (version format: 1.1.0-rc.1)`,
  step1infoPanelPoint3: `Patch release: to be selected in case of patch releases or changes 
  to the installation script of the software included in the new component version (version 
  format: 1.0.1-rc.1)`,
  step2infoPanelHeader: 'Define YAML',
  step2infoPanelLabel1: 'How do I fill this information in?',
  step2infoPanelMessage1: `To build a component using AWS Task Orchestrator and Executor (AWSTOE), 
  you must provide a YAML-based document that represents the phases and steps that apply for the 
  component you create.`,
  step2infoPanelMessage2: `For YAML schema, definitions for a document, phase and step, as well as examples, 
  follow the ‘Learn more’ link below. `,
  step2LearnMoreLabel: 'Learn more ',
  step2Link: 'YAML schema, definitions and examples',
  step3infoPanelHeader: 'Define component dependencies and order of execution',
  step3infoPanelLabel1: 'How do I fill this information in?',
  step3infoPanelMessage1: `If the current component version requires other components to be installed as 
  dependency, these have to be added to the dependency list.`,
  step3infoPanelMessage2: `Testing the component YAML definition, and those of its dependencies, will be 
  executed following the order in the dependency list.`,
  step4infoPanelHeader: 'Review and create',
  step4infoPanelMessage1: `Review the entered information before creating your component version. 
  This allows you to ensure that everything is correct. Some of the entered information may not be 
  able to be edited after creation.`,
};