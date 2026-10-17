import React from 'react';
import { motion, useReducedMotion } from 'motion/react';

interface TextEffectProps {
  children: string;
  per?: 'word' | 'char';
  as?: keyof React.JSX.IntrinsicElements;
  className?: string;
  delay?: number;
}

export const TextEffect: React.FC<TextEffectProps> = ({
  children,
  per = 'word',
  as: Component = 'div',
  className = '',
  delay = 0,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const MotionTag = ((motion as any)[Component] || motion.div) as typeof motion.div;

  if (shouldReduceMotion) {
    return <Component className={className}>{children}</Component>;
  }

  const tokens = per === 'word' ? children.split(' ') : children.split('');

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: per === 'word' ? 0.08 : 0.02,
        delayChildren: delay,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 14, filter: 'blur(4px)' },
    visible: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: {
        type: 'spring' as const,
        damping: 18,
        stiffness: 150,
      },
    },
  };

  return (
    <MotionTag
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {tokens.map((token, i) => (
        <motion.span
          key={i}
          variants={itemVariants}
          className="inline-block"
          style={{ marginRight: per === 'word' ? '0.25em' : '0' }}
        >
          {token}
        </motion.span>
      ))}
    </MotionTag>
  );
};
