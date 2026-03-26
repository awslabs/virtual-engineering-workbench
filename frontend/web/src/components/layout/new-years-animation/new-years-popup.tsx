import { Modal, SpaceBetween, Header } from '@cloudscape-design/components';
import { useEffect, useState } from 'react';
import './new-years-popup.css';
import { createConfetti } from '../../layout/new-years-animation/confetti';

const i18n = {
  headerHappy: 'Happy',
  headerYear: 'Year!',
  text: 'Sending you our warmest New Year wishes and looking forward to another year together!'
};

export const NewYearsPopup = () => {
  const [visible, setVisible] = useState(true);

  const handlePopupDismiss = () => {
    setVisible(false);
    localStorage.setItem('new-years-animation-dismissed', 'true');
  };

  const showNewYearsAnimation = () => {
    const firstDayOfWorkMorning = new Date('2025-01-02, 00:00:00').getTime();
    const firstDayOfWorkEvening = new Date('2025-01-17, 23:59:59').getTime();
    const now = new Date().getTime();
    if (now > firstDayOfWorkMorning && now < firstDayOfWorkEvening &&
      localStorage.getItem('new-years-animation-dismissed') !== 'true') {
      return true;
    }
    return false;
  };

  useEffect(() => {
    if (showNewYearsAnimation()) {
      createConfetti();
    }
  }, []);

  return (
    showNewYearsAnimation() &&
    <Modal
      onDismiss={handlePopupDismiss}
      visible={visible}
      header={
        <Header>
          <SpaceBetween size={'xl'} direction="horizontal">
            <div className="new-years-header" style={{ marginLeft: '130px' }}>{i18n.headerHappy}</div>
            <img src="logo_blue.svg" className="logo"></img>
            <div className="new-years-header">{i18n.headerYear}</div>
          </SpaceBetween>
          <div className="new-years-text" style={{}}>{i18n.text}</div>
        </Header>
      }
      size="large"
    >
      <img src="festivities.gif"></img>
    </Modal>
  );
};

