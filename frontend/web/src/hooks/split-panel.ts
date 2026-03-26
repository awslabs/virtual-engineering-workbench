import { useEffect, useState } from 'react';
import { useLocalStorageNumber } from './local-storage';
const DEFAULT_SPLIT_PANEL_SIZE = 300;
const SPLIT_PANEL_SIZE_LOCAL_STORAGE_KEY = 'split_panel_size';
export const useSplitPanel = <T>(selectedItems: T[], splitPanelClosed?: () => void) => {
  const [splitPanelSize, setSplitPanelSize] =
    useLocalStorageNumber(SPLIT_PANEL_SIZE_LOCAL_STORAGE_KEY, DEFAULT_SPLIT_PANEL_SIZE);
  const [splitPanelOpen, setSplitPanelOpen] = useState(false);

  const onSplitPanelResize = ({ detail: { size } }: { detail: { size: number } }) => {
    setSplitPanelSize(size);
  };

  const onSplitPanelToggle = ({ detail: { open } }: { detail: { open: boolean } }) => {
    setSplitPanelOpen(open);

    if (!open && !!splitPanelClosed) {
      splitPanelClosed();
    }
  };

  useEffect(() => {
    if (selectedItems.length) {
      setSplitPanelOpen(true);
    } else {
      setSplitPanelOpen(false);
    }
  }, [selectedItems.length]);

  return {
    splitPanelOpen,
    onSplitPanelToggle,
    splitPanelSize,
    onSplitPanelResize,
  };
};
