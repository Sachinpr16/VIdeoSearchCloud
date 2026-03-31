import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Library, Search, Scissors, Zap, KeyRound, RefreshCw, Clock } from 'lucide-react';
import MediaLibrary from './components/MediaLibrary';
import VideoSearch from './components/VideoSearch';
import VideoEditor from './components/VideoEditor';

type Tab = 'library' | 'search' | 'editor';

const NAV_ITEMS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'library', label: 'Media Library', icon: <Library size={18} /> },
  { id: 'search',  label: 'Search',         icon: <Search  size={18} /> },
  { id: 'editor',  label: 'Video Editor',   icon: <Scissors size={18} /> },
];

export default function App() {
  const [licenseValid, setLicenseValid] = useState<boolean | null>(null);
  const [licenseMessage, setLicenseMessage] = useState<string>('');
  const [remainingCredits, setRemainingCredits] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('library');
  const [checking, setChecking] = useState(false);

  const checkLicense = useCallback(async () => {
    setChecking(true);
    setLicenseValid(null);
    try {
      const response = await fetch('http://localhost:5801/licence-requirement', { method: 'POST' });
      const data = await response.json();
      const status = data?.licensestatus?.status ?? '';
      if (response.ok && status === 'License valid') {
        setRemainingCredits(data.licensestatus['Remaining Hourly Credits'] ?? null);
        setLicenseValid(true);
      } else {
        setLicenseMessage(status || 'License validation failed.');
        setLicenseValid(false);
      }
    } catch {
      setLicenseMessage('Unable to reach the backend server. Make sure the service is running on port 5801.');
      setLicenseValid(false);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => { checkLicense(); }, [checkLicense]);

  /* ── Loading splash ── */
  if (licenseValid === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="flex flex-col items-center gap-6">
          <div className="relative">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
              <Zap size={32} className="text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 h-5 w-5 rounded-full border-2 border-background bg-primary animate-pulse" />
          </div>
          <div className="text-center space-y-1">
            <p className="font-semibold text-foreground">Gyrus Vajra</p>
            <p className="text-xs text-muted-foreground">Validating license…</p>
          </div>
        </div>
      </div>
    );
  }

  /* ── License error screen ── */
  if (!licenseValid) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md space-y-6"
        >
          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
              <Zap size={32} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Gyrus Vajra</h1>
            <p className="text-xs text-muted-foreground">AI-Powered Media Search</p>
          </div>

          {/* Card */}
          <div className="bg-card rounded-2xl border border-border shadow-xl overflow-hidden">
            <div className="h-1 w-full bg-gradient-to-r from-destructive/60 to-destructive" />
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-destructive/10 flex items-center justify-center">
                  <KeyRound size={16} className="text-destructive" />
                </div>
                <div>
                  <p className="font-semibold text-sm">License Required</p>
                  <p className="text-xs text-muted-foreground">Access restricted</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed bg-muted/30 rounded-lg p-3">{licenseMessage}</p>
              <div className="rounded-lg bg-muted/20 border border-border p-3 space-y-2 text-xs">
                <p className="font-medium text-foreground">Required environment variables</p>
                <div className="space-y-1 text-muted-foreground">
                  <p><code className="text-primary bg-primary/10 px-1 rounded">LICENSE_KEY</code> — JWT token issued to your account</p>
                  <p><code className="text-primary bg-primary/10 px-1 rounded">LICENSE_SERVER_URL</code> — License server base URL</p>
                </div>
              </div>

              <button
                onClick={checkLicense}
                disabled={checking}
                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-2.5 rounded-lg font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-all"
              >
                <RefreshCw size={14} className={checking ? 'animate-spin' : ''} />
                {checking ? 'Checking…' : 'Retry Validation'}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  /* ── Main app ── */
  return (
    <div className="flex flex-col h-screen bg-background text-foreground select-none overflow-hidden">
      {/* Title bar */}
      <header
        className="h-11 shrink-0 flex items-center justify-between px-4 border-b border-border/60 bg-card/40 backdrop-blur-sm"
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      >
        <div className="flex items-center gap-2.5">
          <div className="h-6 w-6 rounded-md bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Zap size={12} className="text-white" />
          </div>
          <span className="font-semibold text-sm tracking-tight">Gyrus Vajra</span>
        </div>

        {remainingCredits !== null && (
          <div
            className="flex items-center gap-1.5 text-xs bg-muted/40 px-2.5 py-1 rounded-full border border-border/60"
            style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
          >
            <Clock size={11} className="text-primary" />
            <span className="text-muted-foreground">Credits:</span>
            <span className="font-semibold text-foreground">{remainingCredits.toFixed(1)} h</span>
          </div>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 shrink-0 border-r border-border/60 bg-card/30 flex flex-col py-3 gap-1 px-2">
          <p className="text-[10px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-3 py-1 mt-1">Navigation</p>
          {NAV_ITEMS.map(({ id, label, icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 text-left w-full ${
                activeTab === id
                  ? 'bg-primary/15 text-primary shadow-sm'
                  : 'text-muted-foreground hover:bg-white/5 hover:text-foreground'
              }`}
            >
              {activeTab === id && (
                <motion.div
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-lg bg-primary/10 border border-primary/20"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.35 }}
                />
              )}
              <span className={`relative z-10 ${activeTab === id ? 'text-primary' : ''}`}>{icon}</span>
              <span className="relative z-10">{label}</span>
            </button>
          ))}

          <div className="mt-auto px-3 py-2">
            <div className="rounded-lg bg-muted/20 border border-border/40 p-2.5 space-y-1">
              <p className="text-[10px] text-muted-foreground/70 font-medium uppercase tracking-wider">Backend</p>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-muted-foreground">localhost:5801</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="h-full overflow-y-auto p-6"
            >
              {activeTab === 'library' && <MediaLibrary />}
              {activeTab === 'search'  && <VideoSearch />}
              {activeTab === 'editor'  && <VideoEditor />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
