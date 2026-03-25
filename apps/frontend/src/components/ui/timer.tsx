"use client";

import { useEffect, useRef, useState } from "react";

interface TimerProps {
  startTime: number | null;
  isActive: boolean;
}

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function Timer({ startTime, isActive }: TimerProps) {
  const intervalRef = useRef<number | null>(null);
  const [display, setDisplay] = useState("00:00");

  useEffect(() => {
    if (!isActive || startTime === null) {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDisplay("00:00");
      return;
    }

    if (intervalRef.current !== null) {
      return;
    }

    const tick = () => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setDisplay(formatDuration(elapsed >= 0 ? elapsed : 0));
    };

    tick();
    intervalRef.current = window.setInterval(tick, 1000);

    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, startTime]);

  return <span>{display}</span>;
}
