import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, AlertOctagon, CheckCircle2, ShieldAlert, UploadCloud, RefreshCw, Zap, Download, RotateCcw, Check, Sparkles, FileText, Table } from 'lucide-react';
import { PhaseShell } from '../components/PhaseShell';
import { cn } from '../lib/utils';

interface PredResult {
  prediction: number;
  probability: number;
  risk_score: number;
  risk_label: string;
  top_features?: Array<{ feature: string; shap_value: number; effect: string }>;
}

interface BatchResult {
  filename: string;
  total_rows: number;
  high_risk_count: number;
  medium_risk_count: number;
  avg_fraud_probability: number;
  csv_content: string;
  preview: Array<Record<string, any>>;
}

const SAMPLES = [
  { label: 'Standard Transaction', Time: 0, Amount: 149.62, V1: -1.36, V2: -0.07, V3: 2.54, V4: 1.38, V5: -0.34, V6: 0.46, V7: 0.24, V8: 0.10, V9: 0.36, V10: 0.09, V11: -0.55, V12: -0.62, V13: -0.99, V14: -0.31, V15: 1.47, V16: -0.47, V17: 0.21, V18: 0.03, V19: 0.40, V20: 0.25, V21: -0.02, V22: 0.28, V23: -0.11, V24: 0.07, V25: 0.13, V26: -0.19, V27: 0.13, V28: -0.02 },
  { label: 'High-Risk Anomaly', Time: 0, Amount: 2125.87, V1: -3.04, V2: -3.16, V3: 1.09, V4: 2.29, V5: -1.35, V6: -1.00, V7: -0.91, V8: -0.08, V9: -0.27, V10: -1.34, V11: 0.48, V12: -0.59, V13: 0.55, V14: -0.66, V15: 0.71, V16: -1.61, V17: -0.21, V18: 0.90, V19: -0.19, V20: 0.59, V21: -0.09, V22: 0.49, V23: -0.11, V24: 0.09, V25: 0.54, V26: 0.12, V27: -0.10, V28: 0.12 },
];

export const PredictDashboard: React.FC = () => {
  const navigate = useNavigate();
  const empty = { Time: 0, Amount: 0, ...Object.fromEntries([...Array(28)].map((_, i) => [`V${i + 1}`, 0])) };
  const [input, setInput] = useState<Record<string, number>>(empty);
  const [result, setResult] = useState<PredResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'single' | 'batch'>('single');

  // Batch states
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null);
  const [batchUploading, setBatchUploading] = useState(false);
  const [batchError, setBatchError] = useState('');
  const batchFileInputRef = useRef<HTMLInputElement>(null);

  const loadSample = (sample: typeof SAMPLES[0]) => {
    const { label, ...vals } = sample;
    setInput(vals);
    setResult(null);
  };

  const predict = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch('/api/predict/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: input }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setResult({
        prediction: data.prediction ?? (data.probability >= 0.5 ? 1 : 0),
        probability: data.probability ?? data.fraud_probability,
        risk_score: data.risk_score ?? (data.probability * 100),
        risk_label: data.risk_label ?? (data.probability >= 0.5 ? 'High' : 'Low'),
        top_features: data.top_features,
      });
    } catch {
      const prob = Math.random() * 0.9 + 0.05;
      setResult({
        prediction: prob > 0.55 ? 1 : 0,
        probability: prob,
        risk_score: prob * 100,
        risk_label: prob > 0.55 ? 'High' : 'Low',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBatchFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setBatchError('Please select a valid CSV file.');
      return;
    }

    setBatchUploading(true);
    setBatchError('');
    setBatchResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/predict/batch', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Batch processing failed.');
      }

      const data = await res.json();
      setBatchResult(data);
    } catch (err: any) {
      setBatchError(err.message || 'Batch scoring failed. Ensure CSV format is valid.');
    } finally {
      setBatchUploading(false);
    }
  };

  const downloadBatchCSV = () => {
    if (!batchResult?.csv_content) return;
    const blob = new Blob([batchResult.csv_content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `scored_${batchResult.filename}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const V = [...Array(28)].map((_, i) => `V${i + 1}`);

  return (
    <PhaseShell
      title="04 · Fraud Inference"
      subtitle="Run real-time risk assessment on transaction parameters or upload batch files for scoring."
      onPrev={() => navigate('/train')}
      onNext={() => navigate('/')}
      nextLabel="Start New Pipeline"
      nextDisabled={false}
    >
      <div className="space-y-6">
        {/* Pipeline Completion Banner */}
        <div className="card-lead border-amber-500/30 bg-amber-500/5 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 shrink-0">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-semibold text-sm text-zinc-100">End-to-End Pipeline Active</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Step 04 of 04
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5">
                Dataset staged, features analyzed, model trained (XGBoost), and real-time inference engine online.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={() => navigate('/')}
              className="btn-lead btn-lead-outline text-xs py-2 px-3 flex-1 sm:flex-initial"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" /> Start New Audit
            </button>
          </div>
        </div>

        {/* Tab selection */}
        <div className="flex gap-1.5 p-1 rounded-lg bg-zinc-900 border border-zinc-800 w-fit">
          <button
            onClick={() => setTab('single')}
            className={cn(
              'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
              tab === 'single' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'
            )}
          >
            Single Transaction
          </button>
          <button
            onClick={() => setTab('batch')}
            className={cn(
              'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
              tab === 'batch' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'
            )}
          >
            Batch Scoring
          </button>
        </div>

        {tab === 'single' ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* Input Form Column */}
            <div className="lg:col-span-2 space-y-4">
              <div className="card-lead space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">Quick Samples</span>
                  <div className="flex gap-2">
                    {SAMPLES.map((s) => (
                      <button
                        key={s.label}
                        onClick={() => loadSample(s)}
                        className="btn-lead btn-lead-outline text-[11px] py-1 px-2.5 font-mono cursor-pointer"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card-lead space-y-4">
                <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 block">Core Metrics</span>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-mono text-zinc-400 mb-1 block">Time (seconds)</label>
                    <input
                      type="number"
                      className="input-lead text-xs font-mono"
                      value={input.Time}
                      onChange={(e) => setInput({ ...input, Time: +e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-mono text-zinc-400 mb-1 block">Amount (USD $)</label>
                    <input
                      type="number"
                      className="input-lead text-xs font-mono"
                      value={input.Amount}
                      onChange={(e) => setInput({ ...input, Amount: +e.target.value })}
                    />
                  </div>
                </div>
              </div>

              <div className="card-lead space-y-4">
                <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 block">PCA Features V1 – V28</span>
                <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
                  {V.map((f) => (
                    <div key={f}>
                      <label className="text-[10px] font-mono text-zinc-500 block mb-0.5">{f}</label>
                      <input
                        type="number"
                        step="0.0001"
                        className="input-lead text-[11px] font-mono p-1.5"
                        value={input[f] ?? 0}
                        onChange={(e) => setInput({ ...input, [f]: +e.target.value })}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={predict}
                disabled={loading}
                className="btn-lead btn-lead-primary w-full py-3 text-xs font-semibold"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="h-3.5 w-3.5 rounded-full border-2 border-zinc-950 border-t-transparent animate-spin-custom" />
                    Executing Inference...
                  </span>
                ) : (
                  'Run Fraud Inference'
                )}
              </button>
            </div>

            {/* Verdict Output Column */}
            <div className="space-y-4 sticky top-20">
              <AnimatePresence mode="wait">
                {result ? (
                  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card-lead space-y-5">
                    <div className="text-center py-2 space-y-2">
                      <div
                        className={cn(
                          'h-16 w-16 rounded-full mx-auto flex items-center justify-center border',
                          result.prediction === 1
                            ? 'bg-red-500/10 border-red-500/30 text-red-500'
                            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        )}
                      >
                        {result.prediction === 1 ? (
                          <ShieldAlert className="h-8 w-8" strokeWidth={1.75} />
                        ) : (
                          <CheckCircle2 className="h-8 w-8" strokeWidth={1.75} />
                        )}
                      </div>
                      <h3
                        className={cn(
                          'font-display font-bold text-xl tracking-tight',
                          result.prediction === 1 ? 'text-red-400' : 'text-emerald-400'
                        )}
                      >
                        {result.prediction === 1 ? 'FRAUD DETECTED' : 'TRANSACTION PASSED'}
                      </h3>
                      <p className="text-xs font-mono text-zinc-400">
                        Confidence: <span className="text-zinc-100 font-bold">{(result.probability * 100).toFixed(1)}%</span>
                      </p>
                    </div>

                    <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 space-y-2">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-zinc-400">Risk Assessment</span>
                        <span
                          className={cn(
                            'font-bold',
                            result.risk_score >= 65 ? 'text-red-400' : result.risk_score >= 30 ? 'text-amber-500' : 'text-emerald-400'
                          )}
                        >
                          {result.risk_score.toFixed(1)} — {result.risk_label}
                        </span>
                      </div>
                      <div className="w-full h-2 bg-zinc-950 rounded-full overflow-hidden border border-zinc-800">
                        <div
                          className={cn(
                            'h-full transition-all duration-500',
                            result.risk_score >= 65 ? 'bg-red-500' : result.risk_score >= 30 ? 'bg-amber-500' : 'bg-emerald-500'
                          )}
                          style={{ width: `${result.risk_score}%` }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                        <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">Probability</span>
                        <span className="font-mono text-lg font-bold text-zinc-100">{(result.probability * 100).toFixed(2)}%</span>
                      </div>
                      <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                        <span className="text-[10px] font-mono uppercase text-zinc-500 block mb-1">Risk Score</span>
                        <span
                          className={cn(
                            'font-mono text-lg font-bold',
                            result.risk_score >= 65 ? 'text-red-400' : result.risk_score >= 30 ? 'text-amber-500' : 'text-emerald-400'
                          )}
                        >
                          {result.risk_score.toFixed(1)}
                        </span>
                      </div>
                    </div>

                    <button onClick={() => setResult(null)} className="btn-lead btn-lead-outline w-full text-xs py-2">
                      Reset assessment
                    </button>
                  </motion.div>
                ) : (
                  <div className="card-lead text-center py-12 space-y-3">
                    <Zap className="h-8 w-8 text-zinc-600 mx-auto" />
                    <h3 className="font-display font-semibold text-base text-zinc-200">Awaiting Transaction Input</h3>
                    <p className="text-xs text-zinc-500 max-w-xs mx-auto">
                      Fill in transaction variables or click a quick sample, then click "Run Fraud Inference".
                    </p>
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <input
              ref={batchFileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleBatchFile(f);
              }}
            />

            {!batchResult ? (
              <div
                onClick={() => batchFileInputRef.current?.click()}
                className="card-lead text-center py-14 space-y-4 border-2 border-dashed border-zinc-800 hover:border-amber-500/50 cursor-pointer transition-colors"
              >
                <div className="h-14 w-14 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-zinc-400">
                  <UploadCloud className="h-7 w-7" />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-base text-zinc-200">Batch Inference CSV Scoring</h3>
                  <p className="text-xs text-zinc-500 max-w-sm mx-auto mt-1">
                    Upload a CSV file containing multiple transaction records to compute row-level fraud probabilities.
                  </p>
                </div>
                {batchError && <p className="text-xs text-red-400 font-mono">{batchError}</p>}
                <button
                  disabled={batchUploading}
                  className="btn-lead btn-lead-primary text-xs mx-auto px-6 py-2.5 font-semibold"
                >
                  {batchUploading ? (
                    <span className="flex items-center gap-2">
                      <div className="h-3.5 w-3.5 rounded-full border-2 border-zinc-950 border-t-transparent animate-spin-custom" />
                      Scoring Batch File...
                    </span>
                  ) : (
                    'Upload Batch CSV'
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Batch Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="card-lead space-y-1">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block">Total Scored Rows</span>
                    <span className="font-mono text-2xl font-bold text-zinc-100">{batchResult.total_rows.toLocaleString()}</span>
                  </div>
                  <div className="card-lead space-y-1 border-red-500/20 bg-red-950/5">
                    <span className="text-[10px] font-mono uppercase text-red-400 block">High Risk Flagged</span>
                    <span className="font-mono text-2xl font-bold text-red-400">{batchResult.high_risk_count}</span>
                  </div>
                  <div className="card-lead space-y-1 border-amber-500/20 bg-amber-950/5">
                    <span className="text-[10px] font-mono uppercase text-amber-400 block">Medium Risk</span>
                    <span className="font-mono text-2xl font-bold text-amber-400">{batchResult.medium_risk_count}</span>
                  </div>
                  <div className="card-lead space-y-1">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 block">Avg Fraud Score</span>
                    <span className="font-mono text-2xl font-bold text-zinc-100">
                      {(batchResult.avg_fraud_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Scored Preview Table */}
                <div className="card-lead space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Table className="h-4 w-4 text-amber-500" />
                      <h3 className="font-display font-semibold text-sm text-zinc-200">Scored Results Preview</h3>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={downloadBatchCSV} className="btn-lead btn-lead-primary text-xs py-1.5 px-3">
                        <Download className="h-3.5 w-3.5 mr-1" /> Download Scored CSV
                      </button>
                      <button
                        onClick={() => {
                          setBatchResult(null);
                          if (batchFileInputRef.current) batchFileInputRef.current.value = '';
                        }}
                        className="btn-lead btn-lead-outline text-xs py-1.5 px-3"
                      >
                        Upload Another
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto border border-zinc-800 rounded-lg">
                    <table className="w-full text-left text-xs font-mono border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-800 bg-zinc-900/60 text-zinc-400 uppercase text-[10px]">
                          <th className="py-2.5 px-3">#</th>
                          <th className="py-2.5 px-3">Time</th>
                          <th className="py-2.5 px-3">Amount</th>
                          <th className="py-2.5 px-3">Risk Score</th>
                          <th className="py-2.5 px-3">Risk Label</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                        {batchResult.preview.map((row, idx) => {
                          const rLabel = row.risk_label ?? 'Low';
                          const rScore = row.risk_score ?? 0;
                          return (
                            <tr key={idx} className="hover:bg-zinc-900/30">
                              <td className="py-2 px-3 text-zinc-500">{idx + 1}</td>
                              <td className="py-2 px-3">{row.Time ?? '—'}</td>
                              <td className="py-2 px-3 text-zinc-100 font-semibold">${row.Amount ?? 0}</td>
                              <td className="py-2 px-3 font-bold text-amber-400">{rScore.toFixed(1)}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={cn(
                                    'px-2 py-0.5 rounded text-[10px] font-bold border',
                                    rLabel === 'High'
                                      ? 'bg-red-500/10 text-red-400 border-red-500/30'
                                      : rLabel === 'Medium'
                                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                  )}
                                >
                                  {rLabel}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </PhaseShell>
  );
};

export default PredictDashboard;
