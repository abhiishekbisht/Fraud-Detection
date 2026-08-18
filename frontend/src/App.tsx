import React, { useState, useCallback, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import UploadPage from './pages/UploadPage';
import EDADashboard from './pages/EDADashboard';
import TrainDashboard from './pages/TrainDashboard';
import PredictDashboard from './pages/PredictDashboard';

const AppContent: React.FC = () => {
  const location = useLocation();
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());

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
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans">
      <Navbar completedSteps={completedSteps} />
      <main className="flex-1 pt-4">
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 rounded-full border-2 border-amber-500/20 border-t-amber-500 animate-spin-custom" />
                <span className="text-xs font-mono text-zinc-500">Loading phase...</span>
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
      <footer className="py-6 border-t border-zinc-800/60 text-center text-xs font-mono text-zinc-500">
        FraudLens · Machine Learning Anomaly & Fraud Detection Engine
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
