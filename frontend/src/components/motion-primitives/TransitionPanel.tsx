import React from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';

interface TransitionPanelProps {
  activeIndex: number | string;
  children: React.ReactNode[];
  className?: string;
}

export const TransitionPanel: React.FC<TransitionPanelProps> = ({
  activeIndex,
  children,
  className = '',
}) => {
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <AnimatePresence mode="wait">
        <motion.div
          key={activeIndex}
          initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: -12 }}
          transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          className="w-full"
        >
          {children[typeof activeIndex === 'number' ? activeIndex : 0]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
