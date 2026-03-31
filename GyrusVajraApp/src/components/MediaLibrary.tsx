import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Trash2, VideoIcon, Plus, RefreshCw, Film, Clock, LayoutGrid } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import IndexingModal from './IndexingModal';

function formatTime(seconds: number) {
  if (!seconds && seconds !== 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function MediaLibrary() {
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showIndexModal, setShowIndexModal] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchVideos = async () => {
    setLoading(true);
    try {
      const res = await axios.get('http://localhost:5801/status');
      const indexedData: Record<string, { video?: string[]; text?: string[] }> = res.data?.indexed_data ?? {};
      const videoList: any[] = [];
      for (const [dbName, dbData] of Object.entries(indexedData)) {
        for (const sourceId of dbData.video ?? []) {
          videoList.push({ sourceId, dbName });
        }
      }
      setVideos(videoList);
    } catch (err: any) {
      console.error('Error fetching videos', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchVideos(); }, []);

  const handleRemove = async (sourceId: string) => {
    if (!confirm(`Remove "${sourceId}" from the index?`)) return;
    setDeleting(sourceId);
    try {
      await axios.post('http://localhost:5801/remove-video', { sourceId, indexType: 'both' });
      setVideos(v => v.filter(x => x.sourceId !== sourceId));
    } catch {
      alert('Failed to remove video');
    } finally {
      setDeleting(null);
    }
  };

  // Deduplicate by sourceId to show one card per video
  const uniqueVideos = videos.reduce((acc: any[], v) => {
    if (!acc.find(x => x.sourceId === v.sourceId)) acc.push(v);
    return acc;
  }, []);

  return (
    <div className="flex flex-col h-full gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
            <LayoutGrid size={20} className="text-primary" /> Media Library
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {uniqueVideos.length} video{uniqueVideos.length !== 1 ? 's' : ''} indexed
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchVideos}
            disabled={loading}
            className="h-9 w-9 flex items-center justify-center rounded-lg border border-border hover:bg-muted/40 transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin text-primary' : 'text-muted-foreground'} />
          </button>
          <button
            onClick={() => setShowIndexModal(true)}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity shadow-sm"
          >
            <Plus size={15} /> Index Video
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-border border-t-primary" />
          <p className="text-sm">Loading library…</p>
        </div>
      ) : uniqueVideos.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="flex-1 flex flex-col items-center justify-center gap-4"
        >
          <div className="h-20 w-20 rounded-2xl bg-muted/30 border border-border flex items-center justify-center">
            <Film size={36} className="text-muted-foreground/40" />
          </div>
          <div className="text-center space-y-1">
            <p className="font-semibold text-foreground">No videos indexed yet</p>
            <p className="text-sm text-muted-foreground">Click "Index Video" to add your first video</p>
          </div>
          <button
            onClick={() => setShowIndexModal(true)}
            className="flex items-center gap-2 bg-primary/10 text-primary border border-primary/20 px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/20 transition-colors"
          >
            <Plus size={15} /> Get started
          </button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 overflow-y-auto pb-4">
          <AnimatePresence>
            {uniqueVideos.map((v, i) => (
              <motion.div
                key={v.sourceId ?? i}
                initial={{ opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: i * 0.04, duration: 0.2 }}
                className="group relative aspect-video rounded-xl border border-border bg-card overflow-hidden cursor-pointer shadow-sm hover:shadow-md hover:border-primary/30 transition-all duration-200"
              >
                {/* Gradient thumbnail background */}
                <div className="absolute inset-0 bg-gradient-to-br from-secondary/80 via-muted/60 to-card" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-12 w-12 rounded-full bg-black/30 backdrop-blur-sm flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Play size={22} className="text-white/80 translate-x-0.5" fill="currentColor" />
                  </div>
                </div>

                {/* Top badge */}
                <div className="absolute top-2 left-2">
                  <div className="flex items-center gap-1 bg-black/50 backdrop-blur-sm text-white/80 text-[10px] font-medium px-2 py-0.5 rounded-full">
                    <VideoIcon size={9} />
                    <span>VIDEO</span>
                  </div>
                </div>

                {/* Hover overlay with info */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-end p-3">
                  <p className="text-white text-xs font-semibold truncate">{v.sourceId}</p>
                  {(v.start !== undefined || v.end !== undefined) && (
                    <div className="flex items-center gap-1 mt-1">
                      <Clock size={9} className="text-white/60" />
                      <span className="text-white/60 text-[10px]">
                        {formatTime(v.start)} – {formatTime(v.end)}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-end mt-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRemove(v.sourceId); }}
                      disabled={deleting === v.sourceId}
                      className="h-7 w-7 rounded-lg bg-destructive/80 hover:bg-destructive flex items-center justify-center transition-colors disabled:opacity-50"
                      title="Remove"
                    >
                      {deleting === v.sourceId
                        ? <div className="h-3 w-3 rounded-full border border-white border-t-transparent animate-spin" />
                        : <Trash2 size={12} className="text-white" />
                      }
                    </button>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {showIndexModal && (
        <IndexingModal
          onClose={() => setShowIndexModal(false)}
          onSuccess={() => { setShowIndexModal(false); fetchVideos(); }}
        />
      )}
    </div>
  );
}
