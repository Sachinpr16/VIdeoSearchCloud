import React, { useState } from 'react';
import axios from 'axios';
import { Search, Image as ImageIcon, Mic, Sparkles, Clock, ChevronRight, SlidersHorizontal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type Mode = 'text' | 'image' | 'audio';

const MODES: { id: Mode; label: string; icon: React.ReactNode; placeholder: string }[] = [
  { id: 'text',  label: 'Text',  icon: <Search size={14} />,    placeholder: 'Describe a scene, action, or moment…' },
  { id: 'image', label: 'Image', icon: <ImageIcon size={14} />, placeholder: 'Enter image file path…' },
  { id: 'audio', label: 'Audio', icon: <Mic size={14} />,       placeholder: 'Enter audio file path…' },
];

function formatTime(s: number) {
  if (s == null) return '—';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export default function VideoSearch() {
  const [mode, setMode] = useState<Mode>('text');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [limit, setLimit] = useState(20);
  const [showOptions, setShowOptions] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(false);

    const endpoints: Record<Mode, string> = { text: 'textsearch', image: 'imagesearch', audio: 'audiosearch' };
    const payloads: Record<Mode, object> = {
      text:  { query,           startIndex: 0, limit, dbName: '*' },
      image: { image_path: query, startIndex: 0, limit, dbName: '*' },
      audio: { audio_path: query, startIndex: 0, limit, dbName: '*' },
    };

    try {
      const res = await axios.post(`http://localhost:5801/${endpoints[mode]}`, payloads[mode]);
      setResults(res.data.results || []);
    } catch {
      alert('Search failed. Check the backend server.');
    } finally {
      setLoading(false);
      setSearched(true);
    }
  };

  const currentMode = MODES.find(m => m.id === mode)!;

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <Sparkles size={20} className="text-primary" /> Cross-Modal Search
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">Find moments in your videos using text, images, or audio</p>
      </div>

      {/* Search card */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-sm">
        {/* Mode tabs */}
        <div className="flex border-b border-border bg-muted/20">
          {MODES.map(({ id, label, icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`relative flex items-center gap-1.5 px-5 py-3 text-sm font-medium transition-colors ${
                mode === id ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {icon} {label}
              {mode === id && (
                <motion.div
                  layoutId="search-tab"
                  className="absolute bottom-0 inset-x-0 h-0.5 bg-primary rounded-full"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.3 }}
                />
              )}
            </button>
          ))}
          <div className="ml-auto flex items-center pr-3">
            <button
              onClick={() => setShowOptions(o => !o)}
              className={`h-7 w-7 rounded-md flex items-center justify-center transition-colors ${showOptions ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/40'}`}
              title="Options"
            >
              <SlidersHorizontal size={13} />
            </button>
          </div>
        </div>

        {/* Options row */}
        <AnimatePresence>
          {showOptions && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-b border-border"
            >
              <div className="flex items-center gap-4 px-4 py-3 bg-muted/10">
                <label className="text-xs text-muted-foreground font-medium">Max results</label>
                {[10, 20, 50].map(n => (
                  <button
                    key={n}
                    onClick={() => setLimit(n)}
                    className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${limit === n ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-foreground/30'}`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input */}
        <form onSubmit={handleSearch} className="flex items-center gap-3 p-3">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{currentMode.icon}</span>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={currentMode.placeholder}
              className="w-full bg-muted/30 border border-border rounded-xl py-2.5 pl-9 pr-4 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50 transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-5 py-2.5 rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-all shadow-sm"
          >
            {loading ? (
              <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
            ) : (
              <Search size={14} />
            )}
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-muted-foreground">
            <div className="h-8 w-8 rounded-full border-2 border-border border-t-primary animate-spin" />
            <p className="text-sm">Searching across all videos…</p>
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center h-40 gap-2">
            <Search size={28} className="text-muted-foreground/30" />
            <p className="text-sm font-medium text-muted-foreground">No results found</p>
            <p className="text-xs text-muted-foreground/60">Try different keywords or index more videos</p>
          </motion.div>
        )}

        {!loading && results.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-1">
            <p className="text-xs text-muted-foreground mb-3">
              <span className="text-foreground font-semibold">{results.length}</span> result{results.length !== 1 ? 's' : ''} for <span className="text-primary">"{query}"</span>
            </p>
            {results.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                className="group flex items-center gap-4 bg-card hover:bg-card/80 border border-border hover:border-primary/30 rounded-xl p-4 transition-all cursor-pointer"
              >
                {/* Thumbnail placeholder */}
                <div className="h-16 w-28 shrink-0 rounded-lg bg-gradient-to-br from-secondary to-muted flex items-center justify-center border border-border">
                  <div className="h-7 w-7 rounded-full bg-black/30 flex items-center justify-center">
                    <div className="w-0 h-0 border-t-[5px] border-t-transparent border-b-[5px] border-b-transparent border-l-[9px] border-l-white/80 ml-0.5" />
                  </div>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm truncate">{r.sourceId}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <div className="flex items-center gap-1 bg-muted/40 border border-border rounded-md px-2 py-0.5">
                      <Clock size={10} className="text-muted-foreground" />
                      <span className="text-xs text-muted-foreground font-mono">{formatTime(r.start)} – {formatTime(r.end)}</span>
                    </div>
                    {r.score !== undefined && (
                      <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-16 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
                            style={{ width: `${Math.round(r.score * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">{Math.round(r.score * 100)}%</span>
                      </div>
                    )}
                  </div>
                  {r.transcript && (
                    <p className="text-xs text-muted-foreground mt-1.5 line-clamp-1 italic">"{r.transcript}"</p>
                  )}
                </div>

                <ChevronRight size={16} className="text-muted-foreground/30 group-hover:text-muted-foreground transition-colors shrink-0" />
              </motion.div>
            ))}
          </motion.div>
        )}

        {!loading && !searched && (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground/40">
            <Sparkles size={28} />
            <p className="text-sm">Enter a query above to search your videos</p>
          </div>
        )}
      </div>
    </div>
  );
}
