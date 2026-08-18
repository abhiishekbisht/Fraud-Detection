import React from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import { cn } from '../lib/utils';

interface PhaseShellProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  onPrev?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  prevDisabled?: boolean;
}

export const PhaseShell: React.FC<PhaseShellProps> = ({
  title,
  subtitle,
  children,
  onPrev,
  onNext,
  nextLabel = 'Next phase',
  nextDisabled = false,
  prevDisabled = false,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="max-w-6xl mx-auto px-4 sm:px-6 pb-28"
    >
      <header className="mb-8 border-b border-zinc-800/60 pb-6">
        <h1 className="font-display text-3xl sm:text-4xl text-zinc-100 font-bold tracking-tight">
          {title}
        </h1>
        <p className="text-zinc-400 mt-2 text-sm sm:text-base max-w-2xl leading-relaxed">
          {subtitle}
        </p>
      </header>

      <div>{children}</div>

      {/* Fixed bottom navigation bar from lead-to-launch */}
      <div className="fixed bottom-0 inset-x-0 z-40 border-t border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <button
            onClick={onPrev}
            disabled={prevDisabled || !onPrev}
            className={cn(
              'btn-lead btn-lead-outline text-xs h-9 px-4',
              (!onPrev || prevDisabled) && 'opacity-40 cursor-not-allowed'
            )}
          >
            <ChevronLeft className="h-4 w-4 mr-1" strokeWidth={1.75} /> Back
          </button>
          <button
            onClick={onNext}
            disabled={nextDisabled || !onNext}
            className={cn(
              'btn-lead btn-lead-primary text-xs h-9 px-5 font-semibold',
              (!onNext || nextDisabled) && 'opacity-40 cursor-not-allowed'
            )}
          >
            {nextLabel} <ChevronRight className="h-4 w-4 ml-1" strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
