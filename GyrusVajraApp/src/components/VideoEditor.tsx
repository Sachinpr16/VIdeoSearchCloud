import React, { useState } from 'react';
import { Scissors, Upload, CheckCircle2, Film, Clock, AlignLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const INPUT_CLS = "w-full bg-muted/30 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all";

export default function VideoEditor() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [startTime, setStartTime] = useState(0);
  const [duration, setDuration]   = useState(10);
  const [processing, setProcessing] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const handleTrim = async () => {
    if (!videoFile) return;
    setProcessing(true);
    setDone(null);
    try {
      const videoPath  = (videoFile as any).path;
      const outputPath = videoPath.replace(/\.[^/.]+$/, '') + '_trimmed.mp4';
      const result = await (window as any).electronAPI?.trimVideo({
        inputPath: videoPath, outputPath, startTime, duration,
      });
      if (result?.success) setDone(result.outputPath ?? outputPath);
    } catch {
      alert('Failed to trim video.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <Scissors size={20} className="text-primary" /> Video Editor
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">Trim and export video clips</p>
      </div>

      {/* File picker */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-sm">
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-2 mb-1">
            <Film size={15} className="text-muted-foreground" />
            <span className="text-sm font-medium">Source Video</span>
          </div>

          <label className="flex flex-col items-center justify-center w-full h-28 rounded-xl border-2 border-dashed border-border hover:border-primary/40 bg-muted/10 hover:bg-primary/5 transition-all cursor-pointer group">
            <Upload size={20} className="text-muted-foreground/50 group-hover:text-primary/60 transition-colors mb-2" />
            <span className="text-xs text-muted-foreground">
              {videoFile ? videoFile.name : 'Click to select a video file'}
            </span>
            {videoFile && (
              <span className="text-[10px] text-muted-foreground/50 mt-0.5 font-mono">{(videoFile as any).path}</span>
            )}
            <input type="file" accept="video/*" className="hidden" onChange={e => { setVideoFile(e.target.files?.[0] || null); setDone(null); }} />
          </label>
        </div>

        {/* Trim settings */}
        <AnimatePresence>
          {videoFile && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-border overflow-hidden"
            >
              <div className="p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <Clock size={14} className="text-muted-foreground" />
                  <span className="text-sm font-medium">Trim Settings</span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground font-medium">Start Time (seconds)</label>
                    <input
                      type="number" min="0" value={startTime}
                      onChange={e => setStartTime(Number(e.target.value))}
                      className={INPUT_CLS}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-muted-foreground font-medium">Duration (seconds)</label>
                    <input
                      type="number" min="1" value={duration}
                      onChange={e => setDuration(Number(e.target.value))}
                      className={INPUT_CLS}
                    />
                  </div>
                </div>

                {/* Preview info pill */}
                <div className="flex items-center gap-2 bg-muted/20 border border-border rounded-lg px-3 py-2">
                  <AlignLeft size={12} className="text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    Clip: <span className="text-foreground font-medium">{startTime}s</span> → <span className="text-foreground font-medium">{startTime + duration}s</span>
                    <span className="ml-2 text-muted-foreground/60">({duration}s total)</span>
                  </span>
                </div>

                <button
                  onClick={handleTrim}
                  disabled={processing}
                  className="flex items-center gap-2 bg-primary text-primary-foreground px-5 py-2.5 rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-all shadow-sm"
                >
                  {processing ? (
                    <><div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Processing…</>
                  ) : (
                    <><Scissors size={14} /> Trim &amp; Export</>
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Success */}
      <AnimatePresence>
        {done && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="flex items-start gap-3 bg-green-500/10 border border-green-500/30 rounded-xl p-4"
          >
            <CheckCircle2 size={18} className="text-green-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-green-400">Trim complete!</p>
              <p className="text-xs text-muted-foreground mt-0.5 font-mono break-all">{done}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
