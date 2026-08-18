import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, Activity, RefreshCw } from 'lucide-react';
import { Stepper, STEPS } from './Stepper';

interface NavbarProps {
  completedSteps: Set<number>;
}

export const Navbar: React.FC<NavbarProps> = ({ completedSteps }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [apiLive, setApiLive] = React.useState<boolean | null>(null);

  const currentStep = React.useMemo(() => {
    const found = STEPS.find((s) => s.path === location.pathname);
    return found ? found.id : 1;
  }, [location.pathname]);

  React.useEffect(() => {
    fetch('/api/health')
      .then((r) => r.ok)
      .then((ok) => setApiLive(ok))
      .catch(() => setApiLive(false));
  }, []);

  const handleJump = (stepId: number) => {
    const step = STEPS.find((s) => s.id === stepId);
    if (step) navigate(step.path);
  };

  return (
    <header className="sticky top-0 z-50 bg-zinc-950/90 backdrop-blur-md border-b border-zinc-800/80">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group text-decoration-none">
          <div className="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 group-hover:bg-amber-500/20 transition-colors">
            <Shield className="h-4.5 w-4.5" strokeWidth={2} />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-display font-bold text-base text-zinc-100 tracking-tight">
              Fraud<span className="text-amber-500">Lens</span>
            </span>
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">
              ML Pipeline
            </span>
          </div>
        </Link>

        {/* API Status indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-mono">
            <span
              className={`h-2 w-2 rounded-full ${
                apiLive === true
                  ? 'bg-emerald-500 animate-pulse'
                  : apiLive === false
                  ? 'bg-red-500'
                  : 'bg-zinc-600'
              }`}
            />
            {apiLive === true ? 'API Connected' : apiLive === false ? 'API Offline' : 'Connecting...'}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors"
            title="Reload application"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Stepper bar */}
      <Stepper current={currentStep} completed={completedSteps} onJump={handleJump} />
    </header>
  );
};

export default Navbar;
