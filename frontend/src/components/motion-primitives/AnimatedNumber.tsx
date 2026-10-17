import React, { useEffect, useState } from 'react';
import { useReducedMotion } from 'motion/react';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  duration = 800,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
}) => {
  const safeEnd = typeof value === 'number' && !isNaN(value) ? value : 0;
  const shouldReduceMotion = useReducedMotion();
  const [displayValue, setDisplayValue] = useState<number>(safeEnd);
  const prevValueRef = React.useRef(safeEnd);

  useEffect(() => {
    if (shouldReduceMotion) {
      prevValueRef.current = safeEnd;
      return;
    }

    const start = prevValueRef.current;
    const end = safeEnd;
    if (start === end) {
      return;
    }
    const startTime = performance.now();

    let animId: number;
    const update = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * eased;
      setDisplayValue(current);

      if (progress < 1) {
        animId = requestAnimationFrame(update);
      } else {
        setDisplayValue(end);
        prevValueRef.current = end;
      }
    };

    animId = requestAnimationFrame(update);
    return () => cancelAnimationFrame(animId);
  }, [safeEnd, duration, shouldReduceMotion]);

  const activeValue = shouldReduceMotion ? safeEnd : displayValue;
  const numToFormat = typeof activeValue === 'number' && !isNaN(activeValue) ? activeValue : safeEnd;
  const formatted = numToFormat.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <span className={className}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
};
