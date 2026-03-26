import { useEffect } from 'react';

/* This hook detecs mouse clicks outside of a specified component. */
export function useOutsideClickDetector(
  ref: React.MutableRefObject<Element | null>,
  onOutsideClick: () => void
) {
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (ref?.current && !ref.current.contains(event.target as Node)) {
        onOutsideClick();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [ref]);
}