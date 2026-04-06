'use client';

import { useEffect, useState } from 'react';

interface ProcessingTimerProps {
  startTime: number | null;
  isActive: boolean;
}

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export function ProcessingTimer({ startTime, isActive }: ProcessingTimerProps) {
  const [display, setDisplay] = useState('00:00');

  useEffect(() => {
    if (!isActive || startTime === null) {
      setDisplay('00:00');
      return;
    }

    const tick = () => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setDisplay(formatDuration(elapsed >= 0 ? elapsed : 0));
    };

    tick();
    const timerId = setInterval(tick, 1000);

    return () => clearInterval(timerId);
  }, [isActive, startTime]);

  return <span>{display}</span>;
}