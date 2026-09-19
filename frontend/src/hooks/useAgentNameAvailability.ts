import { useEffect, useState } from 'react';
import { useDebounce } from 'use-debounce';
import { checkAgentName } from '../services/fetchService';

export function useAgentNameAvailability(name: string, editingAgentName?: string) {
  const [debouncedName] = useDebounce(name, 500);
  const [availability, setAvailability] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  useEffect(() => {
    const trimmedName = debouncedName.trim();
    const unchangedName = editingAgentName
      && trimmedName.toLowerCase() === editingAgentName.trim().toLowerCase();

    if (trimmedName.length < 3) {
      setAvailability(null);
      setIsChecking(false);
      return;
    }
    if (unchangedName) {
      setAvailability(true);
      setIsChecking(false);
      return;
    }

    let cancelled = false;
    setIsChecking(true);
    setAvailability(null);
    checkAgentName(trimmedName)
      .then(result => { if (!cancelled) setAvailability(result.available); })
      .catch(() => { if (!cancelled) setAvailability(null); })
      .finally(() => { if (!cancelled) setIsChecking(false); });

    return () => { cancelled = true; };
  }, [debouncedName, editingAgentName]);

  return { availability, isChecking };
}
