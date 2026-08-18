import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Database, Shield, ArrowRight } from 'lucide-react';
import { PhaseShell } from '../components/PhaseShell';
import { cn } from '../lib/utils';

interface UploadPageProps {
  onComplete?: () => void;
}

interface UploadedFile {
  name: string;
  size: number;
  rows?: number;
  columns?: number;
}

const fmtBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const UploadPage: React.FC<UploadPageProps> = ({ onComplete }) => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<'idle' | 'dragging' | 'uploading' | 'success' | 'error'>('idle');
  const [file, setFile] = useState<UploadedFile | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (uploadedFile: File) => {
      if (!uploadedFile.name.toLowerCase().endsWith('.csv')) {
        setError('Invalid file type. Please upload a .csv file.');
        setStatus('error');
        return;
      }

      setStatus('uploading');
      setProgress(0);
      setError('');

      const formData = new FormData();
      formData.append('file', uploadedFile);

      try {
        const timer = setInterval(() => {
          setProgress((p) => (p >= 85 ? (clearInterval(timer), 85) : p + Math.random() * 12));
        }, 180);

        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        clearInterval(timer);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Upload failed');
        }

        const data = await res.json();
        setProgress(100);

        setTimeout(() => {
          setStatus('success');
          setFile({
            name: uploadedFile.name,
            size: uploadedFile.size,
            rows: data.rows,
            columns: data.columns,
          });
          if (onComplete) onComplete();
        }, 300);
      } catch (err: any) {
        setError(err.message || 'Upload failed. Please try again.');
        setStatus('error');
      }
    },
    [onComplete]
  );

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFile(droppedFile);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) handleFile(selectedFile);
  };

  const reset = () => {
    setStatus('idle');
    setFile(null);
    setProgress(0);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <PhaseShell
      title="01 · Upload Dataset"
      subtitle="Upload transaction records in CSV format. The pipeline validates schemas, handles nulls, and sets up data isolation automatically."
      onNext={status === 'success' ? () => navigate('/eda') : undefined}
      nextLabel="Proceed to Analysis"
      nextDisabled={status !== 'success'}
      prevDisabled={true}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main dropzone area */}
        <div className="lg:col-span-2 space-y-4">
          <AnimatePresence mode="wait">
            {status === 'success' && file ? (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="card-lead border-emerald-500/30 bg-emerald-950/10 text-center py-10 px-6 space-y-6"
              >
                <div className="h-14 w-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400">
                  <CheckCircle2 className="h-7 w-7" strokeWidth={2} />
                </div>

                <div>
                  <h3 className="font-display font-semibold text-lg text-zinc-100">Dataset Staged Successfully</h3>
                  <p className="text-xs text-zinc-400 mt-1 font-mono">Ready for statistical analysis & feature profiling</p>
                </div>

                <div className="grid grid-cols-3 gap-3 text-left">
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-1">File Name</span>
                    <span className="text-xs font-mono text-zinc-200 truncate block">{file.name}</span>
                  </div>
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-1">File Size</span>
                    <span className="text-xs font-mono text-zinc-200 block">{fmtBytes(file.size)}</span>
                  </div>
                  <div className="p-3 rounded-md bg-zinc-900/60 border border-zinc-800">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-1">Rows Scanned</span>
                    <span className="text-xs font-mono text-amber-500 font-bold block">{file.rows?.toLocaleString() ?? '—'}</span>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => navigate('/eda')}
                    className="btn-lead btn-lead-primary flex-1 py-2.5 font-semibold text-xs"
                  >
                    Continue to Phase 02 · Analysis <ArrowRight className="h-4 w-4 ml-1" />
                  </button>
                  <button onClick={reset} className="btn-lead btn-lead-outline py-2.5 text-xs">
                    Upload another
                  </button>
                </div>
              </motion.div>
            ) : (
              <div
                className={cn(
                  'border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer relative overflow-hidden',
                  status === 'dragging'
                    ? 'border-amber-500 bg-amber-500/5'
                    : 'border-zinc-800 hover:border-zinc-700 bg-zinc-900/30'
                )}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setStatus('dragging');
                }}
                onDragLeave={() => setStatus('idle')}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleInputChange}
                  className="hidden"
                />

                <AnimatePresence mode="wait">
                  {status === 'uploading' ? (
                    <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 py-4">
                      <div className="h-12 w-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-500">
                        <div className="h-6 w-6 rounded-full border-2 border-amber-500 border-t-transparent animate-spin-custom" />
                      </div>
                      <div className="max-w-xs mx-auto space-y-2">
                        <div className="flex justify-between text-xs font-mono text-zinc-400">
                          <span>Parsing CSV...</span>
                          <span className="text-amber-500 font-semibold">{Math.round(progress)}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 transition-all duration-300" style={{ width: `${progress}%` }} />
                        </div>
                      </div>
                    </motion.div>
                  ) : (
                    <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 py-4">
                      <div className="h-14 w-14 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto text-zinc-400 group-hover:text-amber-500 transition-colors">
                        <UploadCloud className="h-7 w-7" strokeWidth={1.5} />
                      </div>
                      <div>
                        <p className="font-display font-semibold text-base text-zinc-200">
                          {status === 'dragging' ? 'Release file to upload' : 'Drop your transaction CSV file here'}
                        </p>
                        <p className="text-xs text-zinc-500 mt-1">
                          or <span className="text-amber-500 underline underline-offset-2">click to browse</span> from your system
                        </p>
                        {error && (
                          <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-red-400 font-mono">
                            <AlertCircle className="h-3.5 w-3.5" />
                            {error}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center justify-center gap-4 text-[11px] font-mono text-zinc-500 pt-2">
                        <span>CSV format</span>
                        <span>·</span>
                        <span>Max 200 MB</span>
                        <span>·</span>
                        <span>Isolated session</span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </AnimatePresence>
        </div>

        {/* Sidebar details */}
        <div className="space-y-4">
          <div className="card-lead space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
              <Shield className="h-3.5 w-3.5 text-amber-500" /> Automated Pipeline
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Once uploaded, the pipeline parses features, checks for missing data, computes statistical distributions, and prepares training matrices.
            </p>
          </div>

          <div className="card-lead space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-zinc-400">
              <Database className="h-3.5 w-3.5 text-amber-500" /> Expected Schema
            </div>
            <div className="flex flex-wrap gap-1.5">
              {['Time', 'Amount', 'Class', 'V1..V28'].map((col) => (
                <span key={col} className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-amber-400">
                  {col}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </PhaseShell>
  );
};

export default UploadPage;
