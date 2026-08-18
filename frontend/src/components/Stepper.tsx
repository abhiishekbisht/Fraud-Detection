import React from 'react';
import { motion } from 'framer-motion';
import { Check, Upload, BarChart2, Cpu, ShieldCheck } from 'lucide-react';
import { cn } from '../lib/utils';

export const STEPS = [
  { id: 1, label: 'Upload',   path: '/',        icon: Upload },
  { id: 2, label: 'Analysis', path: '/eda',     icon: BarChart2 },
  { id: 3, label: 'Train',    path: '/train',   icon: Cpu },
  { id: 4, label: 'Predict',  path: '/predict', icon: ShieldCheck },
];

interface StepperProps {
  current: number;
  completed: Set<number>;
  onJump: (stepId: number) => void;
}

export const Stepper: React.FC<StepperProps> = ({ current, completed, onJump }) => {
  return (
    <div className="max-w-4xl mx-auto px-4 pt-4 pb-6" role="navigation" aria-label="Pipeline progress">
      <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500 text-center mb-4 font-mono">
        Step <span className="text-amber-500 font-semibold">{String(current).padStart(2, '0')}</span> of <span className="text-zinc-400">04</span> · {STEPS[current - 1]?.label}
      </div>
      <div className="w-full flex items-center justify-between gap-2">
        {STEPS.map((step, i) => {
          const isDone = completed.has(step.id);
          const isCurrent = current === step.id;
          const Icon = step.icon;

          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <button
                type="button"
                onClick={() => onJump(step.id)}
                aria-label={`Phase ${step.id} of ${STEPS.length}: ${step.label}`}
                className={cn(
                  'flex flex-col items-center gap-2 group transition-opacity rounded-md p-1 cursor-pointer w-full',
                  !isCurrent && !isDone && 'opacity-60 hover:opacity-100'
                )}
              >
                <motion.div
                  initial={false}
                  animate={{
                    scale: isCurrent ? 1.05 : 1,
                    backgroundColor: isCurrent ? '#f59e0b' : isDone ? '#27272a' : '#141417',
                  }}
                  transition={{ type: 'spring', stiffness: 300, damping: 24 }}
                  className={cn(
                    'h-10 w-10 rounded-full flex items-center justify-center border',
                    isCurrent
                      ? 'border-amber-400 text-zinc-950 shadow-md shadow-amber-500/20'
                      : isDone
                      ? 'border-zinc-700 text-amber-500'
                      : 'border-zinc-800 text-zinc-500'
                  )}
                >
                  {isDone && !isCurrent ? (
                    <Check className="h-4 w-4" strokeWidth={2.2} />
                  ) : (
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  )}
                </motion.div>
                <span className={cn('text-[11px] tracking-wider uppercase font-medium', isCurrent ? 'text-amber-500' : 'text-zinc-400')}>
                  0{step.id} · {step.label}
                </span>
              </button>
              {i < STEPS.length - 1 && (
                <div className="flex-1 h-px mx-2 relative overflow-hidden bg-zinc-800">
                  <motion.div
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: isDone ? 1 : 0 }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                    style={{ originX: 0 }}
                    className="absolute inset-0 bg-amber-500/60"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
