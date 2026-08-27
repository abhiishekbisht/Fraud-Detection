import React from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, ChevronLeft, Sparkles, ShieldCheck } from 'lucide-react';
import { cn } from '../lib/utils';

interface PhaseShellProps {
  phaseNumber?: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  onPrev?: () => void;
  onNext?: () => void;
  nextLabel?: string;
  nextDisabled?: boolean;
  prevDisabled?: boolean;
  extraHeaderAction?: React.ReactNode;
}

export const PhaseShell: React.FC<PhaseShellProps> = ({
  phaseNumber,
  title,
  subtitle,
  children,
  onPrev,
  onNext,
  nextLabel = 'Next phase',
  nextDisabled = false,
  prevDisabled = false,
  extraHeaderAction,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="max-w-7xl mx-auto px-4 sm:px-6 pb-28 pt-2 relative z-10"
    >
      {/* Header Banner */}
      <header className="mb-8 p-6 rounded-2xl glass-panel border border-slate-800/80 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="space-y-2 relative z-10">
          {phaseNumber && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-md bg-sky-950/80 border border-sky-800/60 text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3 h-3" /> {phaseNumber}
              </span>
            </div>
          )}
          <h1 className="font-display text-2xl sm:text-3xl lg:text-4xl text-slate-100 font-bold tracking-tight">
            {title}
          </h1>
          <p className="text-slate-400 text-sm sm:text-base max-w-3xl leading-relaxed">
            {subtitle}
          </p>
        </div>

        {extraHeaderAction && (
          <div className="shrink-0 relative z-10">{extraHeaderAction}</div>
        )}
      </header>

      {/* Main Content Area */}
      <div>{children}</div>

      {/* Sticky Glass Bottom Navigation Bar */}
      <div className="fixed bottom-0 inset-x-0 z-40 border-t border-slate-800/80 bg-slate-950/85 backdrop-blur-xl shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between gap-3">
          <button
            onClick={onPrev}
            disabled={prevDisabled || !onPrev}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-medium border border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-800/60 transition-all',
              (!onPrev || prevDisabled) && 'opacity-40 cursor-not-allowed hover:bg-slate-900/60 hover:border-slate-800'
            )}
          >
            <ChevronLeft className="h-4 w-4" strokeWidth={2} /> Back
          </button>
          
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-slate-400">
            <ShieldCheck className="w-4 h-4 text-sky-400" />
            <span>FraudLens Automated Pipeline</span>
          </div>

          <button
            onClick={onNext}
            disabled={nextDisabled || !onNext}
            className={cn(
              'flex items-center gap-2 px-6 py-2 rounded-xl text-xs font-mono font-semibold bg-sky-500 hover:bg-sky-400 text-slate-950 shadow-lg shadow-sky-500/20 hover:shadow-sky-500/30 transition-all transform hover:-translate-y-0.5',
              (!onNext || nextDisabled) && 'opacity-40 cursor-not-allowed hover:bg-sky-500 hover:translate-y-0 shadow-none'
            )}
          >
            {nextLabel} <ChevronRight className="h-4 w-4" strokeWidth={2} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
