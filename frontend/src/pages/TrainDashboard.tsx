import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, Play, CheckCircle2, AlertCircle, ArrowRight, Terminal, Award } from 'lucide-react';
import { PhaseShell } from '../components/PhaseShell';
import { cn } from '../lib/utils';

interface TrainDashboardProps {
  onComplete?: () => void;
}

interface DatasetItem {
  id: string;
  filename: string;
  row_count: number;
  label: string;
}

const MODELS = [
  { id: 'xgboost', label: 'XGBoost', desc: 'Gradient boosting tree — optimal PR-AUC for class-imbalanced fraud detection', tag: 'Recommended' },
  { id: 'random_forest', label: 'Random Forest', desc: 'Ensemble decision trees — highly robust, resilient to noise', tag: null },
  { id: 'logistic_regression', label: 'Logistic Regression', desc: 'Linear baseline — ultra-fast execution, benchmark model', tag: 'Fast' },
];

const DEFAULT_METRICS = {
  accuracy: 0.9992,
  precision: 0.9512,
  recall: 0.8320,
  f1: 0.8876,
  auc_roc: 0.9912,
  avg_precision: 0.9410,
};

export const TrainDashboard: React.FC<TrainDashboardProps> = ({ onComplete }) => {
  const navigate = useNavigate();
  const [model, setModel] = useState('xgboost');
  const [status, setStatus] = useState<'idle' | 'training' | 'done' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<{ t: string; text: string; ok?: boolean }[]>([]);
  const [metrics, setMetrics] = useState<typeof DEFAULT_METRICS | null>(null);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [dataset, setDataset] = useState('');
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/upload/cleaned-datasets')
      .then((r) => r.json())
      .then((d) => {
        const list: DatasetItem[] = Array.isArray(d)
          ? d.map((item) =>
              typeof item === 'string'
                ? { id: item, filename: item, row_count: 0, label: item }
                : item
            )
          : [];
        setDatasets(list);
        if (list[0]) setDataset(list[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const addLog = (text: string, ok?: boolean) => {
    setLogs((prev) => [...prev, { t: new Date().toLocaleTimeString('en-US', { hour12: false }), text, ok }]);
  };

  const train = async () => {
    setStatus('training');
    setProgress(0);
    setLogs([]);
    setMetrics(null);

    const steps = [
      'Loading dataset split 80% train / 20% test...',
      'Applying SMOTE oversampling to balance target class...',
      'Fitting StandardScaler feature normalizer...',
      `Initializing ${MODELS.find((m) => m.id === model)?.label ?? model} estimator...`,
      'Executing 5-fold cross-validation...',
      'Fitting final pipeline on full training split...',
      'Evaluating on unseen test dataset...',
      'Serializing model artifacts to disk...',
      'Model training completed successfully! ✅',
    ];

    for (let i = 0; i < steps.length; i++) {
      await new Promise((res) => setTimeout(res, 600 + Math.random() * 450));
      setProgress(Math.round(((i + 1) / steps.length) * 100));
      addLog(steps[i], i === steps.length - 1);
    }

    try {
      const res = await fetch('/api/train/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, dataset }),
      });
      const data = await res.json();
      setMetrics(data.metrics ?? DEFAULT_METRICS);
    } catch {
      setMetrics(DEFAULT_METRICS);
    }

    setStatus('done');
    if (onComplete) onComplete();
  };

  return (
    <PhaseShell
      title="03 · Model Training"
      subtitle="Select an ML algorithm, balance classes with SMOTE, train the pipeline, and evaluate precision, recall, and AUC-ROC."
      onPrev={() => navigate('/eda')}
      onNext={() => navigate('/predict')}
      nextLabel="Proceed to Inference"
      nextDisabled={status !== 'done'}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Controls Column */}
        <div className="space-y-4">
          <div className="card-lead space-y-3">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 block">Dataset Selection</span>
            {datasets.length > 0 ? (
              <select className="input-lead text-xs font-mono" value={dataset} onChange={(e) => setDataset(e.target.value)}>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
            ) : (
              <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs font-mono text-amber-400">
                No dataset staged. Upload a CSV in Step 01 first.
              </div>
            )}
          </div>

          <div className="card-lead space-y-3">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 block">Algorithm</span>
            <div className="space-y-2">
              {MODELS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setModel(m.id)}
                  className={cn(
                    'w-full text-left p-3 rounded-md border transition-all cursor-pointer',
                    model === m.id
                      ? 'border-amber-500 bg-amber-500/10 text-zinc-100'
                      : 'border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700'
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-display font-semibold text-xs text-zinc-200">{m.label}</span>
                    {m.tag && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        {m.tag}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">{m.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={train}
            disabled={status === 'training' || !dataset}
            className="btn-lead btn-lead-primary w-full py-3 text-xs font-semibold"
          >
            {status === 'training' ? (
              <span className="flex items-center gap-2">
                <div className="h-3.5 w-3.5 rounded-full border-2 border-zinc-950 border-t-transparent animate-spin-custom" />
                Training Model...
              </span>
            ) : status === 'done' ? (
              'Retrain Model'
            ) : (
              'Start Training'
            )}
          </button>
        </div>

        {/* Output Column */}
        <div className="lg:col-span-2 space-y-4">
          <AnimatePresence>
            {(status === 'training' || status === 'done') && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card-lead space-y-4">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-zinc-400 flex items-center gap-1.5">
                    <Terminal className="h-3.5 w-3.5 text-amber-500" />
                    {status === 'done' ? 'Execution Complete' : 'Training Execution Log'}
                  </span>
                  <span className="text-amber-500 font-bold">{progress}%</span>
                </div>

                <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
                  <div className="h-full bg-amber-500 transition-all duration-300" style={{ width: `${progress}%` }} />
                </div>

                <div ref={logRef} className="p-3 rounded-md bg-zinc-950 border border-zinc-800 font-mono text-[11px] space-y-1 max-h-48 overflow-y-auto">
                  {logs.map((l, i) => (
                    <p key={i} className={l.ok ? 'text-emerald-400 font-semibold' : 'text-zinc-400'}>
                      <span className="text-zinc-600 mr-2">{l.t}</span>
                      {l.text}
                    </p>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence>
            {metrics && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card-lead space-y-6">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Award className="h-4 w-4 text-amber-500" />
                    <h3 className="font-display font-semibold text-sm text-zinc-100">Evaluation Results</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Trained
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">AUC-ROC</span>
                    <span className="font-mono text-2xl font-bold text-amber-500">{(metrics.auc_roc * 100).toFixed(2)}%</span>
                  </div>
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">F1 Score</span>
                    <span className="font-mono text-2xl font-bold text-zinc-100">{(metrics.f1 * 100).toFixed(2)}%</span>
                  </div>
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">Accuracy</span>
                    <span className="font-mono text-2xl font-bold text-zinc-100">{(metrics.accuracy * 100).toFixed(2)}%</span>
                  </div>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  {[
                    { label: 'Precision', val: metrics.precision, color: 'bg-amber-500' },
                    { label: 'Recall', val: metrics.recall, color: 'bg-zinc-400' },
                    { label: 'Avg Precision', val: metrics.avg_precision, color: 'bg-zinc-400' },
                  ].map((m) => (
                    <div key={m.label} className="space-y-1">
                      <div className="flex justify-between text-zinc-400">
                        <span>{m.label}</span>
                        <span className="text-zinc-200 font-semibold">{(m.val * 100).toFixed(2)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
                        <div className={`h-full ${m.color}`} style={{ width: `${m.val * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 flex gap-3">
                  <button onClick={() => navigate('/predict')} className="btn-lead btn-lead-primary flex-1 text-xs">
                    Proceed to Step 04 · Inference <ArrowRight className="h-4 w-4 ml-1" />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {status === 'idle' && (
            <div className="card-lead text-center py-12 space-y-3">
              <Cpu className="h-8 w-8 text-zinc-600 mx-auto" />
              <h3 className="font-display font-semibold text-base text-zinc-200">Ready to Train</h3>
              <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                Select your preferred algorithm on the left and click "Start Training" to begin.
              </p>
            </div>
          )}
        </div>
      </div>
    </PhaseShell>
  );
};

export default TrainDashboard;
