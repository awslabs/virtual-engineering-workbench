import { useState, useEffect } from 'react';

export function useTutorialLogic() {
  const [showTutorial, setShowTutorial] = useState(false);

  useEffect(() => {
    const hasSeenTutorial = localStorage.getItem('hasSeenTutorial');
    if (!hasSeenTutorial) {
      setShowTutorial(true);
      localStorage.setItem('hasSeenTutorial', 'true');
    }
  }, []);

  const hideTutorial = () => {
    setShowTutorial(false);
  };

  return {
    showTutorial,
    hideTutorial,
  };
}
