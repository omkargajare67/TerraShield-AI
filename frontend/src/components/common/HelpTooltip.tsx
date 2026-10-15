import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface HelpTooltipProps {
  text: string;
  className?: string;
  term?: string;
}

export const HelpTooltip: React.FC<HelpTooltipProps> = ({ text, className = '', term }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <span className={`relative inline-flex items-center align-middle ${className}`}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        aria-label={term ? `Learn more about ${term}` : 'Learn more'}
        className="p-0.5 rounded-full text-terra-slate hover:text-terra-mint focus:outline-none focus:ring-1 focus:ring-terra-mint/50 transition cursor-help"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>

      {isOpen && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2.5 rounded-xl bg-terra-deep/95 border border-terra-border/80 text-[11px] text-terra-ivory font-sans font-normal leading-relaxed shadow-2xl backdrop-blur-md z-50 pointer-events-none text-left"
        >
          {term && <span className="block font-semibold text-terra-mint mb-0.5">{term}</span>}
          {text}
        </span>
      )}
    </span>
  );
};

export default HelpTooltip;
