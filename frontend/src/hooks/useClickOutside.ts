import { useEffect, useRef } from 'react';

type ElementRef = { current: HTMLElement | null };

interface UseClickOutsideOptions {
  enabled?: boolean;
  closeOnEscape?: boolean;
}

export function useClickOutside(
  refs: ElementRef | ElementRef[],
  onDismiss: () => void,
  { enabled = true, closeOnEscape = true }: UseClickOutsideOptions = {},
) {
  const latestOnDismiss = useRef(onDismiss);
  latestOnDismiss.current = onDismiss;

  useEffect(() => {
    if (!enabled) return;

    const elements = Array.isArray(refs) ? refs : [refs];
    const handlePointerDown = (event: MouseEvent) => {
      if (!elements.some(ref => ref.current?.contains(event.target as Node))) {
        latestOnDismiss.current();
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (closeOnEscape && event.key === 'Escape') latestOnDismiss.current();
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [closeOnEscape, enabled, refs]);
}
