import React, { useState } from 'react';
import axios from 'axios';
import { X, Upload, Film, Tag, Gauge, Mic2, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

const INPUT_CLS = "w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all placeholder:text-muted-foreground/50";

export default function IndexingModal({ onClose, onSuccess }: Props) {
  const [file, setFile]         = useState<File | null>(null);
  const [fps, setFps]           = useState(30);
  const [useAudio, setUseAudio] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [sourceId, setSourceId] = useState('');
  const [filePath, setFilePath] = useState('');
  const [dbName, setDbName]     = useState('_default_db');
  const [error, setError]       = useState('');
  const [done, setDone]         = useState(false);

  const handleIndex = async () => {
    if (!filePath.trim()) return;
    setProcessing(true);
    setError('');
    const id = sourceId.trim() || (file ? file.name.split('.')[0] : filePath.split('/').pop()?.split('.')[0] || 'video');
    try {
      await axios.post('http://localhost:5801/index-videos', {
        data: [{ filepath: filePath.trim(), sourceId: id, fps, useAudio }],
        isVideo: true,
        dbName: dbName.trim() || '_default_db',
      });
      setDone(true);
      setTimeout(() => { onSuccess(); }, 900);
    } catch (err: any) {
      const msg = err?.response?.data?.indexingstatus?.error
        || err?.response?.data?.error
        || `HTTP ${err?.response?.status ?? 'unknown'}`;
      setError(`Indexing failed: ${msg}`);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ duration: 0.18 }}
        className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Film size={16} className="text-primary" />
            </div>
            <div>
              <p className="font-semibold text-sm">Index New Video</p>
              <p className="text-[10px] text-muted-foreground">Add to the searchable library</p>
            </div>
          </div>
          <button onClick={onClose} className="h-7 w-7 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted/40 hover:text-foreground transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* File picker */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Film size={11} /> Video File</label>
            <label className="flex items-center gap-3 w-full p-3 rounded-xl border-2 border-dashed border-border hover:border-primary/40 bg-muted/10 hover:bg-primary/5 transition-all cursor-pointer group">
              <div className="h-9 w-9 rounded-lg bg-muted/40 flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors">
                <Upload size={15} className="text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{file ? file.name : 'Choose a video file'}</p>
                {file
                  ? <p className="text-[10px] text-muted-foreground/60 font-mono truncate">{filePath || <span className="italic opacity-50">path not detected</span>}</p>
                  : <p className="text-xs text-muted-foreground/50">MP4, MOV, AVI, MKV…</p>
                }
              </div>
              <input type="file" accept="video/*" className="hidden" onChange={e => {
                const f = e.target.files?.[0] || null;
                setFile(f);
                if (f) {
                  const p = (f as any).path;
                  if (p) setFilePath(p);
                }
              }} />
            </label>
          </div>

          {/* File path — always editable; auto-filled from Electron */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">File Path <span className="text-muted-foreground/50 font-normal">(absolute path on server)</span></label>
            <input
              type="text"
              placeholder="/absolute/path/to/video.mp4"
              value={filePath}
              onChange={e => setFilePath(e.target.value)}
              className={INPUT_CLS}
            />
          </div>

          {/* Source ID */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Tag size={11} /> Source ID <span className="text-muted-foreground/50 font-normal">(optional)</span></label>
            <input type="text" placeholder={file ? file.name.split('.')[0] : 'e.g. interview_2024'} value={sourceId} onChange={e => setSourceId(e.target.value)} className={INPUT_CLS} />
          </div>

          {/* Settings row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Gauge size={11} /> Frame Rate (FPS)</label>
              <input type="number" min="1" max="60" value={fps} onChange={e => setFps(Number(e.target.value))} className={INPUT_CLS} />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Mic2 size={11} /> Audio Indexing</label>
              <button
                onClick={() => setUseAudio(a => !a)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-sm transition-all ${
                  useAudio ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-muted/20 text-muted-foreground'
                }`}
              >
                <span>{useAudio ? 'Enabled' : 'Disabled'}</span>
                <div className={`h-4 w-8 rounded-full transition-colors flex items-center px-0.5 ${ useAudio ? 'bg-primary' : 'bg-border' }`}>
                  <div className={`h-3 w-3 rounded-full bg-white shadow transition-transform ${ useAudio ? 'translate-x-4' : 'translate-x-0' }`} />
                </div>
              </button>
            </div>
          </div>

          {/* DB Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5"><Tag size={11} /> Database Name</label>
            <input type="text" placeholder="_default_db" value={dbName} onChange={e => setDbName(e.target.value)} className={INPUT_CLS} />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mx-6 mb-3 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-xs">
            {error}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 pb-5">
          <button onClick={onClose} disabled={processing} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/30 rounded-lg transition-colors disabled:opacity-50">Cancel</button>
          <button
            onClick={handleIndex}
            disabled={!filePath.trim() || processing || done}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-5 py-2 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-all shadow-sm"
          >
            {done ? (
              <><CheckCircle2 size={14} /> Done!</>
            ) : processing ? (
              <><div className="h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Indexing…</>
            ) : (
              <><Upload size={14} /> Start Indexing</>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
