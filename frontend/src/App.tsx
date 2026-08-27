import React, { useState, useCallback, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Background3D } from './components/Background3D';
import { CommandPalette } from './components/CommandPalette';
import UploadPage from './pages/UploadPage';
import EDADashboard from './pages/EDADashboard';
import TrainDashboard from './pages/TrainDashboard';
import PredictDashboard from './pages/PredictDashboard';

const AppContent: React.FC = () => {
  const location = useLocation();
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Track completed steps based on route navigation
  React.useEffect(() => {
    if (location.pathname === '/eda') {
      setCompletedSteps((prev) => new Set([...prev, 1]));
    } else if (location.pathname === '/train') {
      setCompletedSteps((prev) => new Set([...prev, 1, 2]));
    } else if (location.pathname === '/predict') {
      setCompletedSteps((prev) => new Set([...prev, 1, 2, 3]));
    }
  }, [location.pathname]);

  const handleUploadComplete = useCallback(() => {
    setCompletedSteps((prev) => new Set([...prev, 1]));
  }, []);

  const handleEDAComplete = useCallback(() => {
    setCompletedSteps((prev) => new Set([...prev, 1, 2]));
  }, []);

  const handleTrainComplete = useCallback(() => {
    setCompletedSteps((prev) => new Set([...prev, 1, 2, 3]));
  }, []);

  return (
    <div className="min-h-screen bg-[#07080c] text-slate-100 flex flex-col font-sans relative selection:bg-sky-500 selection:text-slate-950">
      {/* 3D Interactive Cyber Background */}
      <Background3D />

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onLoadPresetDataset={handleUploadComplete}
      />

      {/* Glass Top Header Navbar */}
      <Navbar
        completedSteps={completedSteps}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      <main className="flex-1 pt-4 relative z-10">
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 rounded-full border-2 border-sky-500/20 border-t-sky-400 animate-spin-custom" />
                <span className="text-xs font-mono text-slate-400">Initializing FraudLens engine...</span>
              </div>
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<UploadPage onComplete={handleUploadComplete} />} />
            <Route path="/eda" element={<EDADashboard onComplete={handleEDAComplete} />} />
            <Route path="/train" element={<TrainDashboard onComplete={handleTrainComplete} />} />
            <Route path="/predict" element={<PredictDashboard />} />
          </Routes>
        </Suspense>
      </main>

      <footer className="py-6 border-t border-slate-900/80 text-center text-xs font-mono text-slate-400 bg-slate-950/60 backdrop-blur-md relative z-10">
        FraudLens · High-Performance Machine Learning Anomaly & Real-Time Fraud Detection Engine
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}
