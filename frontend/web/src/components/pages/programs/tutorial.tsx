import '@cloudscape-design/global-styles/dark-mode-utils.css';
import { Modal, Wizard } from '@cloudscape-design/components';
import React, { useState } from 'react';

interface TutorialProps {
  visible: boolean,
  onDismiss: () => void,
}

const tutorial: React.FC<TutorialProps> = ({ visible, onDismiss }) => {
  const stepIndexStart = 1;
  const stepIndexEnd = 5;
  /* eslint @typescript-eslint/no-magic-numbers: "off" */
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  const handleCancel = () => {
    onDismiss();
  };

  return (
    <Modal
      data-test="tutorial-modal"
      size="max"
      onDismiss={() => onDismiss()}
      visible={visible}
      header={'User tutorial'}
    >
      <Wizard
        i18nStrings={{
          stepNumberLabel: (stepNumber) => {
            if (stepNumber === stepIndexStart || stepNumber === stepIndexEnd) {
              return '';
            }
            return `Step ${stepNumber - 1}`;
          },
          collapsedStepsLabel: (stepNumber, stepsCount) =>
            `Step ${stepNumber} of ${stepsCount}`,
          skipToButtonLabel: (step) => `Skip to ${step.title}`,
          navigationAriaLabel: 'Steps',
          cancelButton: activeStepIndex === 0 ? 'Maybe later' : 'Skip',
          nextButton: activeStepIndex === 0 ? 'Yes, sure' : 'Next',
          previousButton: 'Previous',
          submitButton: 'Finish',
          optional: 'optional',
        }}
        onNavigate={({ detail }) =>
          setActiveStepIndex(detail.requestedStepIndex)
        }
        activeStepIndex={activeStepIndex}
        allowSkipTo
        onSubmit={handleCancel}
        onCancel={handleCancel}
        steps={[
          {
            title: 'Welcome',
            content:
              <div style={{ textAlign: 'center' }}>
                <h2>
                  Welcome to the Virtual Engineering Workbench! <br /> Let's get
                  you started...
                </h2>
                <p>
                  Take a look at these 3 basic steps to start using workbenches.{' '}
                  <br /> Are you up for a quick tour?
                </p>
                <img
                  style={{ width: '100%' }}
                  className="awsui-util-hide-in-dark-mode"
                  src="tutorial_welcome.png"
                  alt="Welcome"
                />
                <img
                  className="awsui-util-show-in-dark-mode"
                  src="tutorial_welcome_dark_mode.png"
                  alt="Welcome"
                  style={{ width: '100%', marginTop: '30px' }}
                />
              </div>
            ,
          },
          {
            title: 'Select or switch a program',
            content:
              <div>
                <video
                  style={{ maxWidth: '100%' }}
                  src="step_1.mp4"
                  controls
                  autoPlay
                />
              </div>
            ,
          },
          {
            title: 'Create a workbench',
            content:
              <video
                style={{ maxWidth: '100%' }}
                src="step_2.mp4"
                controls
                autoPlay
              />
            ,
          },
          {
            title: 'Connect to a workbench',
            content:
              <video
                style={{ maxWidth: '100%' }}
                src="step_3.mp4"
                controls
                autoPlay
              />
            ,
          },
          {
            title: 'Goodbye',
            content:
              <div style={{ textAlign: 'center' }}>
                <h2>
                  Great, you're all set! <br /> Before you move on to the
                  next...
                </h2>
                <p>
                  Please be aware that, in the future, <br /> you can find this
                  and other resources in the Help page.
                </p>
                <img
                  src="tutorial_goodbye.png"
                  alt="Welcome"
                  style={{ maxWidth: '40%', height: 'auto' }}
                />
              </div>
            ,
          },
        ]}
      />
    </Modal>
  );
};

export { tutorial as Tutorial };
