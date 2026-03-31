import React, { useState, useEffect, useCallback } from 'react';
import MediaLibrary from './components/MediaLibrary';
import VideoSearch from './components/VideoSearch';
import VideoEditor from './components/VideoEditor';

export default function App() {
  const [licenseValid, setLicenseValid] = useState<boolean | null>(null);
  const [licenseMessage, setLicenseMessage] = useState<string>('');
  const [remainingCredits, setRemainingCredits] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'library' | 'search' | 'editor'>('library');

  const checkLicense = useCallback(async () => {
    setLicenseValid(null);
    try {
      const response = await fetch('http://localhost:5801/licence-requirement', {
        method: 'POST',
      });
      const data = await response.json();
      const status = data?.licensestatus?.status ?? '';
      if (response.ok && status === 'License valid') {
        setRemainingCredits(data.licensestatus['Remaining Hourly Credits'] ?? null);
        setLicenseValid(true);
      } else {
        setLicenseMessage(status || data?.licensestatus?.status || 'License validation failed.');
        setLicenseValid(false);
      }
    } catch {
      setLicenseMessage('Unable to reach the license server. Please check your network and server configuration.');
      setLicenseValid(false);
    }
  }, []);

  useEffect(() => {
    checkLicense();
  }, [checkLicense]);

  if (licenseValid === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!licenseValid) {
    return (
      <div className="flex flex-col h-screen items-center justify-center bg-background text-foreground space-y-4">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">Gyrus Vajra Media Search</h1>
        <div className="bg-card p-8 rounded-lg border border-border max-w-lg w-full text-center space-y-4">
          <h2 className="text-xl font-semibold text-destructive">License Invalid or Missing</h2>
          <p className="text-muted-foreground text-sm leading-relaxed">{licenseMessage}</p>
          <div className="bg-muted/40 rounded-md p-4 text-left text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-foreground mb-1">Required Docker environment variables:</p>
            <p><span className="text-primary font-mono">LICENSE_KEY</span> — JWT token issued to your account</p>
            <p><span className="text-primary font-mono">LICENSE_SERVER_URL</span> — Cloud license server URL</p>
          </div>
          <button
            onClick={checkLicense}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity"
          >
            Check Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background text-foreground select-none">
      <header className="h-12 border-b border-border flex items-center justify-between px-4" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}>
        <div className="font-semibold text-primary">Gyrus Vajra</div>
        {remainingCredits !== null && (
          <div className="text-xs text-muted-foreground" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
            Credits remaining: <span className="text-foreground font-medium">{remainingCredits.toFixed(1)} h</span>
          </div>
        )}
      </header>
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-64 border-r border-border bg-card/50 flex flex-col p-4 space-y-2">
          <div
            onClick={() => setActiveTab('library')}
            className={`px-3 py-2 rounded-md cursor-pointer transition-colors ${activeTab === 'library' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-white/5'}`}
          >
            Media Library
          </div>
          <div
            onClick={() => setActiveTab('search')}
            className={`px-3 py-2 rounded-md cursor-pointer transition-colors ${activeTab === 'search' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-white/5'}`}
          >
            Video Search
          </div>
          <div
            onClick={() => setActiveTab('editor')}
            className={`px-3 py-2 rounded-md cursor-pointer transition-colors ${activeTab === 'editor' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-white/5'}`}
          >
            Video Editor
          </div>
        </aside>
        <main className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'library' && <MediaLibrary />}
          {activeTab === 'search' && <VideoSearch />}
          {activeTab === 'editor' && <VideoEditor />}
        </main>
      </div>
    </div>
  );
}
