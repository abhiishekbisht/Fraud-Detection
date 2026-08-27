import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, RefreshCw, Trash2, Command, Search, Sparkles } from 'lucide-react';
import { Stepper, STEPS } from './Stepper';
import { fetchWithSession, resetSessionData } from '../lib/session';

interface NavbarProps {
  completedSteps: Set<number>;
  onResetSession?: () => void;
  onOpenCommandPalette: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  completedSteps,
  onResetSession,
  onOpenCommandPalette,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [apiLive, setApiLive] = React.useState<boolean | null>(null);
  const [resetting, setResetting] = React.useState(false);

  const currentStep = React.useMemo(() => {
    const found = STEPS.find((s) => s.path === location.pathname);
    return found ? found.id : 1;
  }, [location.pathname]);

  React.useEffect(() => {
    fetchWithSession('/api/health')
      .then((r) => r.ok)
      .then((ok) => setApiLive(ok))
      .catch(() => setApiLive(false));
  }, []);

  const handleJump = (stepId: number) => {
    const step = STEPS.find((s) => s.id === stepId);
    if (step) navigate(step.path);
  };

  const handleResetSession = async () => {
    if (confirm('Clear active session and reset all uploaded datasets and trained models?')) {
      setResetting(true);
      await resetSessionData();
      if (onResetSession) onResetSession();
      setResetting(false);
      navigate('/');
      window.location.reload();
    }
  };

  return (
    <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand Logo & Tag */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="h-9 w-9 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 group-hover:bg-sky-500/20 group-hover:scale-105 transition-all neon-glow-cyan">
            <Shield className="h-5 w-5" strokeWidth={2} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-lg text-slate-100 tracking-tight">
                Fraud<span className="text-sky-400">Lens</span>
              </span>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-sky-950/80 border border-sky-800/50 text-sky-400">
                PRO ML v2.4
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400 hidden sm:block">
              Real-time Transaction Anomaly & Risk Intelligence
            </span>
          </div>
        </Link>

        {/* Command Palette Button */}
        <button
          onClick={onOpenCommandPalette}
          className="hidden md:flex items-center gap-3 px-3.5 py-1.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-sky-500/40 text-slate-400 hover:text-slate-200 transition-all shadow-inner font-sans text-xs group"
        >
          <Search className="w-3.5 h-3.5 text-sky-400 group-hover:scale-110 transition-transform" />
          <span>Quick Command Search...</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 border border-slate-700 flex items-center gap-0.5">
            <Command className="w-2.5 h-2.5" /> K
          </kbd>
        </button>

        {/* API Status & Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/70 border border-slate-800/80 text-xs text-slate-300 font-mono">
            <span
              className={`h-2 w-2 rounded-full ${
                apiLive === true
                  ? 'bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]'
                  : apiLive === false
                  ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]'
                  : 'bg-slate-600'
              }`}
            />
            <span className="hidden sm:inline">
              {apiLive === true ? 'Backend Engine Online' : 'Simulation Mode'}
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <button
            onClick={handleResetSession}
            disabled={resetting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-800 hover:border-rose-900/50 bg-slate-900/60 hover:bg-rose-950/20 text-xs font-mono text-slate-400 hover:text-rose-400 transition-all"
            title="Reset Session Data"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{resetting ? 'Resetting...' : 'New Session'}</span>
          </button>

          <button
            onClick={() => window.location.reload()}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-all border border-transparent hover:border-slate-800"
            title="Reload Dashboard"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Pipeline Stepper Navigation */}
      <div className="border-t border-slate-900/60 bg-slate-950/40 backdrop-blur-md">
        <Stepper current={currentStep} completed={completedSteps} onJump={handleJump} />
      </div>
    </header>
  );
};

export default Navbar;
