import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Upload, BarChart3, Cpu, ShieldAlert, Database, Command, Sparkles, X, Check } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadPresetDataset?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onLoadPresetDataset,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'phase-1',
      title: 'Phase 01 · Upload & Validate Dataset',
      subtitle: 'Ingest CSV files, check null values & schemas',
      icon: Upload,
      category: 'Navigation',
      action: () => {
        navigate('/');
        onClose();
      },
    },
    {
      id: 'phase-2',
      title: 'Phase 02 · Exploratory Analysis (EDA)',
      subtitle: 'View statistical distributions, correlations & class imbalance',
      icon: BarChart3,
      category: 'Navigation',
      action: () => {
        navigate('/eda');
        onClose();
      },
    },
    {
      id: 'phase-3',
      title: 'Phase 03 · ML Model Training Studio',
      subtitle: 'Train XGBoost, Random Forest & evaluate ROC-AUC metrics',
      icon: Cpu,
      category: 'Navigation',
      action: () => {
        navigate('/train');
        onClose();
      },
    },
    {
      id: 'phase-4',
      title: 'Phase 04 · Real-Time Fraud & SHAP Predictor',
      subtitle: 'Live transaction inference & SHAP feature contributions',
      icon: ShieldAlert,
      category: 'Navigation',
      action: () => {
        navigate('/predict');
        onClose();
      },
    },
    {
      id: 'load-preset',
      title: 'Load Preset Credit Card Fraud Dataset',
      subtitle: 'Instantly simulate 284,807 transactions with 492 fraud samples',
      icon: Database,
      category: 'Quick Action',
      action: () => {
        if (onLoadPresetDataset) onLoadPresetDataset();
        navigate('/eda');
        onClose();
      },
    },
  ];

  const filteredActions = actions.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden glass-panel">
        {/* Search Header */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-800/80 gap-3">
          <Search className="w-5 h-5 text-sky-400 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search platform (e.g. 'train', 'eda', 'preset')..."
            className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-sans"
            autoFocus
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filteredActions.length === 0 ? (
            <div className="py-8 text-center text-xs font-mono text-slate-500">
              No commands found matching "{query}"
            </div>
          ) : (
            filteredActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.id}
                  onClick={action.action}
                  className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-slate-800/60 transition-all text-left group"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="p-2 rounded-lg bg-sky-950/60 border border-sky-800/40 text-sky-400 group-hover:bg-sky-500 group-hover:text-slate-950 transition-colors">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-200 group-hover:text-white flex items-center gap-2">
                        {action.title}
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {action.category}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 group-hover:text-slate-300">
                        {action.subtitle}
                      </div>
                    </div>
                  </div>
                  <div className="text-slate-500 group-hover:text-sky-400 transition-colors">
                    <Check className="w-4 h-4 opacity-0 group-hover:opacity-100" />
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2.5 bg-slate-950/60 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <div className="flex items-center gap-2">
            <Command className="w-3 h-3 text-sky-400" />
            <span>FraudLens Navigation Engine</span>
          </div>
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">↑↓</kbd> navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">esc</kbd> close
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
