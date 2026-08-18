import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BarChart2, Layers, AlertCircle, ArrowRight, RefreshCw, FileText, Activity } from 'lucide-react';
import { PhaseShell } from '../components/PhaseShell';
import { cn } from '../lib/utils';

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
  top_features?: Array<{ feature: string; mean_legit: number; mean_fraud: number; mean_difference: number }>;
}

export const EDADashboard: React.FC<EDADashboardProps> = ({ onComplete }) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<EDAStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [selected, setSelected] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'schema' | 'top'>('overview');

  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Load available datasets list
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
        if (list[0]) setSelected(list[0].id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Fetch EDA stats when selected dataset changes
  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetch(`/api/eda/stats?dataset=${encodeURIComponent(selected)}`)
      .then((r) => r.json())
      .then((d) => {
        setStats(d);
        if (onCompleteRef.current) onCompleteRef.current();
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [selected]);

  return (
    <PhaseShell
      title="02 · Exploratory Analysis"
      subtitle="Statistical profiling of transaction rows, class imbalance metrics, missing value distributions, and top discriminative features."
      onPrev={() => navigate('/')}
      onNext={() => navigate('/train')}
      nextLabel="Proceed to Model Training"
      prevDisabled={false}
      nextDisabled={!stats}
    >
      <div className="space-y-6">
        {/* Selector & Tabs */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-1.5 p-1 rounded-lg bg-zinc-900 border border-zinc-800">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'schema', label: 'Schema' },
              { id: 'top', label: 'Top Features' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
                  activeTab === tab.id
                    ? 'bg-zinc-800 text-zinc-100 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {datasets.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-zinc-500 uppercase">Dataset:</span>
              <select
                className="input-lead text-xs py-1.5 px-3 w-auto min-w-[260px] font-mono"
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
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
              <div key={i} className="h-28 rounded-lg bg-zinc-900/60 border border-zinc-800 animate-pulse flex flex-col justify-between p-4">
                <div className="h-3 w-20 bg-zinc-800 rounded" />
                <div className="h-6 w-24 bg-zinc-800 rounded" />
                <div className="h-2.5 w-16 bg-zinc-800 rounded" />
              </div>
            ))}
          </div>
        ) : !stats ? (
          <div className="card-lead text-center py-12 space-y-4">
            <div className="h-12 w-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-zinc-500">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-display font-semibold text-base text-zinc-200">No Dataset Staged</h3>
              <p className="text-xs text-zinc-500 mt-1">Upload a transaction CSV file in Step 01 to view EDA metrics.</p>
            </div>
            <button onClick={() => navigate('/')} className="btn-lead btn-lead-primary text-xs">
              Go to Step 01 · Upload
            </button>
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="card-lead space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Total Records</span>
                    <p className="font-mono text-2xl font-bold text-zinc-100">{stats.total_rows.toLocaleString()}</p>
                    <span className="text-[11px] text-zinc-500 block">Transaction rows</span>
                  </div>
                  <div className="card-lead space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Feature Columns</span>
                    <p className="font-mono text-2xl font-bold text-zinc-100">{stats.total_columns}</p>
                    <span className="text-[11px] text-zinc-500 block">V1..V28 + Time, Amount</span>
                  </div>
                  <div className="card-lead space-y-1 border-red-500/20 bg-red-950/5">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-red-400">Fraud Cases</span>
                    <p className="font-mono text-2xl font-bold text-red-400">{stats.fraud_count.toLocaleString()}</p>
                    <span className="text-[11px] text-red-400/70 block font-mono">{stats.fraud_pct.toFixed(3)}% imbalance</span>
                  </div>
                  <div className="card-lead space-y-1 border-emerald-500/20 bg-emerald-950/5">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400">Legitimate</span>
                    <p className="font-mono text-2xl font-bold text-emerald-400">{stats.legit_count.toLocaleString()}</p>
                    <span className="text-[11px] text-emerald-400/70 block">Standard transactions</span>
                  </div>
                </div>

                {/* Class Distribution Bar */}
                <div className="card-lead space-y-4">
                  <h3 className="font-display font-semibold text-sm text-zinc-200">Class Imbalance Profile</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1.5">
                        <span className="text-emerald-400">Legitimate (0)</span>
                        <span className="text-zinc-400">
                          {stats.legit_count.toLocaleString()} ({((stats.legit_count / (stats.total_rows || 1)) * 100).toFixed(2)}%)
                        </span>
                      </div>
                      <div className="w-full h-2 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
                        <div
                          className="h-full bg-emerald-500 transition-all duration-500"
                          style={{ width: `${(stats.legit_count / (stats.total_rows || 1)) * 100}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1.5">
                        <span className="text-red-400">Fraudulent (1)</span>
                        <span className="text-red-400 font-semibold">
                          {stats.fraud_count.toLocaleString()} ({stats.fraud_pct.toFixed(2)}%)
                        </span>
                      </div>
                      <div className="w-full h-2 bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
                        <div
                          className="h-full bg-red-500 transition-all duration-500"
                          style={{ width: `${Math.max(stats.fraud_pct, 1)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'schema' && (
              <div className="card-lead overflow-hidden p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse font-mono">
                    <thead>
                      <tr className="border-b border-zinc-800 bg-zinc-900/60 text-zinc-400 uppercase tracking-wider text-[10px]">
                        <th className="py-3 px-4">Column</th>
                        <th className="py-3 px-4">Type</th>
                        <th className="py-3 px-4">Missing</th>
                        <th className="py-3 px-4">Mean</th>
                        <th className="py-3 px-4">Std Dev</th>
                        <th className="py-3 px-4">Min</th>
                        <th className="py-3 px-4">Max</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                      {Object.entries(stats.column_types || {}).map(([col, dtype]) => {
                        const d = stats.describe?.[col];
                        const missing = stats.missing_values?.[col] ?? 0;
                        return (
                          <tr key={col} className="hover:bg-zinc-900/30">
                            <td className="py-2.5 px-4 text-amber-400 font-semibold">{col}</td>
                            <td className="py-2.5 px-4 text-zinc-500">{dtype}</td>
                            <td className="py-2.5 px-4">
                              {missing > 0 ? (
                                <span className="text-amber-500 font-bold">{missing}</span>
                              ) : (
                                <span className="text-zinc-600">0</span>
                              )}
                            </td>
                            <td className="py-2.5 px-4 text-zinc-400">{d?.mean?.toFixed(4) ?? '—'}</td>
                            <td className="py-2.5 px-4 text-zinc-400">{d?.std?.toFixed(4) ?? '—'}</td>
                            <td className="py-2.5 px-4 text-zinc-400">{d?.min?.toFixed(4) ?? '—'}</td>
                            <td className="py-2.5 px-4 text-zinc-400">{d?.max?.toFixed(4) ?? '—'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'top' && (
              <div className="card-lead space-y-4">
                <h3 className="font-display font-semibold text-sm text-zinc-200">Top Discriminative Features</h3>
                <p className="text-xs text-zinc-400">Features ranked by absolute difference in mean value between fraud and legit classes.</p>
                <div className="space-y-2">
                  {stats.top_features && stats.top_features.length > 0 ? (
                    stats.top_features.map((tf) => (
                      <div key={tf.feature} className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800 flex items-center justify-between text-xs font-mono">
                        <span className="text-amber-400 font-bold w-16">{tf.feature}</span>
                        <span className="text-zinc-400">Legit mean: {tf.mean_legit.toFixed(4)}</span>
                        <span className="text-red-400">Fraud mean: {tf.mean_fraud.toFixed(4)}</span>
                        <span className="text-amber-500 font-semibold">Diff: {tf.mean_difference.toFixed(4)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs font-mono text-zinc-500 py-4 text-center">No discriminative feature rankings available for this dataset.</p>
                  )}
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
