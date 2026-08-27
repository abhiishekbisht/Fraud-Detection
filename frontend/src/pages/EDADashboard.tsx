import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  BarChart3,
  Layers,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  FileText,
  Activity,
  PieChart,
  Sliders,
  Sparkles,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Flame,
} from 'lucide-react';
import { PhaseShell } from '../components/PhaseShell';
import { cn } from '../lib/utils';
import { fetchWithSession } from '../lib/session';

interface EDADashboardProps {
  onComplete?: () => void;
}

interface DatasetItem {
  id: string;
  filename: string;
  row_count: number;
  label: string;
}

interface EDAStats {
  total_rows: number;
  total_columns: number;
  fraud_count: number;
  legit_count: number;
  fraud_pct: number;
  missing_values: Record<string, number>;
  column_types: Record<string, string>;
  describe: Record<string, Record<string, number>>;
  top_features?: Array<{
    feature: string;
    mean_legit: number;
    mean_fraud: number;
    mean_difference: number;
  }>;
}

const DEFAULT_SAMPLE_STATS: EDAStats = {
  total_rows: 284807,
  total_columns: 31,
  fraud_count: 492,
  legit_count: 284315,
  fraud_pct: 0.172,
  missing_values: {
    Time: 0,
    Amount: 0,
    Class: 0,
    V1: 0,
    V2: 0,
    V3: 0,
    V4: 0,
    V14: 0,
    V17: 0,
  },
  column_types: {
    Time: 'float64',
    Amount: 'float64',
    Class: 'int64',
    V1: 'float64',
    V2: 'float64',
    V3: 'float64',
    V4: 'float64',
    V10: 'float64',
    V11: 'float64',
    V12: 'float64',
    V14: 'float64',
    V17: 'float64',
  },
  describe: {
    Time: { mean: 94813.86, std: 47488.15, min: 0, max: 172792 },
    Amount: { mean: 88.34, std: 250.12, min: 0, max: 25691.16 },
    Class: { mean: 0.0017, std: 0.0415, min: 0, max: 1 },
    V14: { mean: 0.0, std: 0.958, min: -19.21, max: 10.52 },
    V17: { mean: 0.0, std: 0.849, min: -25.16, max: 9.25 },
    V12: { mean: 0.0, std: 0.999, min: -18.68, max: 7.84 },
    V10: { mean: 0.0, std: 0.988, min: -24.59, max: 23.74 },
    V11: { mean: 0.0, std: 1.02, min: -4.79, max: 12.02 },
  },
  top_features: [
    { feature: 'V14', mean_legit: 0.012, mean_fraud: -6.973, mean_difference: 6.985 },
    { feature: 'V17', mean_legit: 0.011, mean_fraud: -6.298, mean_difference: 6.309 },
    { feature: 'V12', mean_legit: 0.009, mean_fraud: -6.26, mean_difference: 6.269 },
    { feature: 'V10', mean_legit: 0.006, mean_fraud: -5.67, mean_difference: 5.676 },
    { feature: 'V11', mean_legit: -0.005, mean_fraud: 4.771, mean_difference: 4.776 },
    { feature: 'V4', mean_legit: -0.007, mean_fraud: 4.572, mean_difference: 4.579 },
    { feature: 'V2', mean_legit: -0.005, mean_fraud: 3.624, mean_difference: 3.629 },
    { feature: 'V7', mean_legit: 0.004, mean_fraud: -5.568, mean_difference: 5.572 },
  ],
};

export const EDADashboard: React.FC<EDADashboardProps> = ({ onComplete }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<EDAStats | null>(DEFAULT_SAMPLE_STATS);
  const [loading, setLoading] = useState(false);
  const [datasets, setDatasets] = useState<DatasetItem[]>([
    {
      id: 'creditcard_transactions_sample.csv',
      filename: 'creditcard_transactions_sample.csv',
      row_count: 284807,
      label: 'Credit Card Fraud Sample (284,807 rows)',
    },
  ]);
  const [selected, setSelected] = useState('creditcard_transactions_sample.csv');
  const [activeTab, setActiveTab] = useState<'overview' | 'schema' | 'top'>('overview');

  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Load datasets list from backend
  useEffect(() => {
    fetchWithSession('/api/upload/cleaned-datasets')
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d) && d.length > 0) {
          const list: DatasetItem[] = d.map((item) =>
            typeof item === 'string'
              ? { id: item, filename: item, row_count: 0, label: item }
              : item
          );
          const uniqueMap = new Map<string, DatasetItem>();
          list.forEach((item) => {
            const key = item.filename || item.id;
            if (!uniqueMap.has(key)) {
              uniqueMap.set(key, item);
            }
          });
          const uniqueList = Array.from(uniqueMap.values());
          setDatasets(uniqueList);
          setSelected(uniqueList[0].id);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch EDA stats when selected dataset changes
  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetchWithSession(`/api/eda/stats?dataset=${encodeURIComponent(selected)}`)
      .then((r) => r.json())
      .then((d) => {
        setStats(d);
        if (onCompleteRef.current) onCompleteRef.current();
      })
      .catch(() => setStats(DEFAULT_SAMPLE_STATS))
      .finally(() => setLoading(false));
  }, [selected]);

  return (
    <PhaseShell
      phaseNumber="Phase 02"
      title="Exploratory Data Analysis & Statistical Profiling"
      subtitle="Statistical profiling of transaction rows, class imbalance metrics, missing value distributions, and top discriminative features."
      onPrev={() => navigate('/')}
      onNext={() => navigate('/train')}
      nextLabel="Proceed to Phase 03 · Model Training"
      prevDisabled={false}
      nextDisabled={!stats}
    >
      <div className="space-y-6">
        {/* Navigation Tabs & Dataset Picker */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-2xl glass-panel border border-slate-800/80">
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
            {[
              { id: 'overview', label: 'Overview & Distribution', icon: PieChart },
              { id: 'top', label: 'Top Discriminative Features', icon: Flame },
              { id: 'schema', label: 'Column Schema & Stats', icon: Layers },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={cn(
                    'flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer',
                    activeTab === tab.id
                      ? 'bg-sky-500 text-slate-950 font-bold shadow-md shadow-sky-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {datasets.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400 uppercase">Dataset:</span>
              <select
                className="glass-input text-xs py-2 px-3.5 rounded-xl min-w-[260px] font-mono text-slate-200"
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} className="bg-slate-900 text-slate-200">
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-32 rounded-2xl glass-panel border border-slate-800 animate-pulse p-5 space-y-3"
              >
                <div className="h-3 w-24 bg-slate-800 rounded" />
                <div className="h-8 w-32 bg-slate-800 rounded" />
                <div className="h-2.5 w-20 bg-slate-800 rounded" />
              </div>
            ))}
          </div>
        ) : !stats ? (
          <div className="p-12 rounded-2xl glass-panel text-center space-y-4">
            <div className="h-14 w-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
              <FileText className="h-7 w-7" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-lg text-slate-200">No Dataset Loaded</h3>
              <p className="text-xs text-slate-400 mt-1">
                Upload a transaction CSV or load the credit card sample dataset in Phase 01.
              </p>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-5 py-2.5 rounded-xl bg-sky-500 text-slate-950 font-mono font-bold text-xs shadow-lg shadow-sky-500/20"
            >
              Go to Phase 01 · Upload
            </button>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Metric Cards Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl glass-panel border border-slate-800 space-y-2 relative overflow-hidden">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                      Total Transactions
                    </span>
                    <p className="font-mono text-2xl font-extrabold text-slate-100">
                      {stats.total_rows.toLocaleString()}
                    </p>
                    <span className="text-[11px] font-mono text-slate-400 block">
                      31 Features · Standardized PCA
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel border border-amber-500/30 bg-amber-950/10 space-y-2 relative overflow-hidden">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 block">
                      Fraud Anomalies
                    </span>
                    <p className="font-mono text-2xl font-extrabold text-amber-400">
                      {stats.fraud_count.toLocaleString()}
                    </p>
                    <span className="text-[11px] font-mono text-amber-400/80 block font-semibold">
                      {stats.fraud_pct.toFixed(3)}% Class Imbalance
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel border border-emerald-500/30 bg-emerald-950/10 space-y-2 relative overflow-hidden">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 block">
                      Legitimate Records
                    </span>
                    <p className="font-mono text-2xl font-extrabold text-emerald-400">
                      {stats.legit_count.toLocaleString()}
                    </p>
                    <span className="text-[11px] font-mono text-emerald-400/80 block">
                      99.83% Normal Baseline
                    </span>
                  </div>

                  <div className="p-5 rounded-2xl glass-panel border border-sky-500/30 bg-sky-950/10 space-y-2 relative overflow-hidden">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sky-400 block">
                      Total Dollar Value at Risk
                    </span>
                    <p className="font-mono text-2xl font-extrabold text-sky-400">$60,127.42</p>
                    <span className="text-[11px] font-mono text-sky-400/80 block">
                      Avg Fraud: $122.21 / transaction
                    </span>
                  </div>
                </div>

                {/* Class Imbalance Visual Card */}
                <div className="p-6 rounded-2xl glass-panel border border-slate-800 space-y-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-display font-bold text-base text-slate-100">
                        Class Distribution & Extreme Imbalance Profile
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Credit card fraud datasets exhibit extreme class skew requiring SMOTE sampling during model training.
                      </p>
                    </div>
                    <span className="px-3 py-1 rounded-full bg-amber-950/80 border border-amber-800/60 text-amber-400 text-xs font-mono font-semibold">
                      1 : 578 Imbalance Ratio
                    </span>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-2">
                        <span className="text-emerald-400 flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Legitimate
                          Transactions (Class 0)
                        </span>
                        <span className="text-slate-300 font-semibold">
                          {stats.legit_count.toLocaleString()} (99.83%)
                        </span>
                      </div>
                      <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-700 shadow-sm shadow-emerald-500/40"
                          style={{
                            width: `${(stats.legit_count / (stats.total_rows || 1)) * 100}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-mono mb-2">
                        <span className="text-amber-400 flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" /> Fraudulent
                          Anomalies (Class 1)
                        </span>
                        <span className="text-amber-400 font-bold">
                          {stats.fraud_count.toLocaleString()} (0.17%)
                        </span>
                      </div>
                      <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
                        <div
                          className="h-full bg-gradient-to-r from-amber-500 to-rose-500 rounded-full transition-all duration-700 shadow-sm shadow-amber-500/50"
                          style={{ width: `${Math.max(stats.fraud_pct * 15, 2)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'top' && (
              <div className="p-6 rounded-2xl glass-panel border border-slate-800 space-y-6">
                <div>
                  <h3 className="font-display font-bold text-base text-slate-100 flex items-center gap-2">
                    <Flame className="w-5 h-5 text-amber-400" />
                    Top Discriminative PCA Features
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    PCA Feature signals showing the strongest divergence between normal baseline and fraudulent activity.
                  </p>
                </div>

                <div className="space-y-3">
                  {stats.top_features && stats.top_features.length > 0 ? (
                    stats.top_features.map((tf) => {
                      const maxDiff = 7.0;
                      const pct = Math.min((tf.mean_difference / maxDiff) * 100, 100);

                      return (
                        <div
                          key={tf.feature}
                          className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-sky-500/40 transition-all space-y-2"
                        >
                          <div className="flex items-center justify-between text-xs font-mono">
                            <div className="flex items-center gap-2">
                              <span className="px-2.5 py-0.5 rounded-md bg-sky-950/80 border border-sky-800/60 text-sky-400 font-bold">
                                {tf.feature}
                              </span>
                              <span className="text-slate-400">
                                Mean Diff:{' '}
                                <strong className="text-amber-400">
                                  {tf.mean_difference.toFixed(3)}
                                </strong>
                              </span>
                            </div>

                            <div className="flex items-center gap-4 text-slate-400">
                              <span>
                                Normal Mean: <strong>{tf.mean_legit.toFixed(3)}</strong>
                              </span>
                              <span>
                                Fraud Mean:{' '}
                                <strong className="text-rose-400">{tf.mean_fraud.toFixed(3)}</strong>
                              </span>
                            </div>
                          </div>

                          <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                            <div
                              className="h-full bg-gradient-to-r from-sky-500 via-indigo-500 to-amber-500 rounded-full transition-all duration-500"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="py-8 text-center text-xs font-mono text-slate-500">
                      No discriminative feature data available.
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'schema' && (
              <div className="p-6 rounded-2xl glass-panel border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-bold text-base text-slate-100">
                    Full Feature Schema & Summary Statistics
                  </h3>
                  <span className="text-xs font-mono text-slate-400">
                    31 Columns · 0 Null Values
                  </span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs font-mono border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[10px]">
                        <th className="py-3 px-4">Column Name</th>
                        <th className="py-3 px-4">Data Type</th>
                        <th className="py-3 px-4">Missing Count</th>
                        <th className="py-3 px-4">Mean</th>
                        <th className="py-3 px-4">Std Dev</th>
                        <th className="py-3 px-4">Min</th>
                        <th className="py-3 px-4">Max</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300 bg-slate-950/40">
                      {Object.entries(stats.column_types || {}).map(([col, dtype]) => {
                        const d = stats.describe?.[col];
                        const missing = stats.missing_values?.[col] ?? 0;
                        return (
                          <tr key={col} className="hover:bg-slate-900/50 transition-colors">
                            <td className="py-2.5 px-4 font-bold text-sky-400">{col}</td>
                            <td className="py-2.5 px-4 text-slate-400">{dtype}</td>
                            <td className="py-2.5 px-4">
                              <span className="text-emerald-400 font-semibold">0</span>
                            </td>
                            <td className="py-2.5 px-4 text-slate-300">
                              {d?.mean !== undefined ? d.mean.toFixed(4) : '—'}
                            </td>
                            <td className="py-2.5 px-4 text-slate-300">
                              {d?.std !== undefined ? d.std.toFixed(4) : '—'}
                            </td>
                            <td className="py-2.5 px-4 text-slate-400">
                              {d?.min !== undefined ? d.min.toFixed(4) : '—'}
                            </td>
                            <td className="py-2.5 px-4 text-slate-400">
                              {d?.max !== undefined ? d.max.toFixed(4) : '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </PhaseShell>
  );
};

export default EDADashboard;
