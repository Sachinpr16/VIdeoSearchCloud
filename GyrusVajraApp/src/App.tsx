import React, { useState, useEffect } from 'react';
import MediaLibrary from './components/MediaLibrary';
import VideoSearch from './components/VideoSearch';
import VideoEditor from './components/VideoEditor';

export default function App() {
  const [licenseValid, setLicenseValid] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<'library' | 'search' | 'editor'>('library');

  useEffect(() => {
    // Check license on mount
    const checkLicense = async () => {
      try {
        const response = await fetch('http://localhost:5801/licence-requirement', {
          method: 'POST',
        });
        const data = await response.json();
        if (response.status === 200 && data.licensestatus.status === 'License valid') {
          setLicenseValid(true);
        } else {
          setLicenseValid(false);
        }
      } catch (error) {
        setLicenseValid(false);
      }
    };
    checkLicense();
  }, []);

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
        <div className="bg-card p-8 rounded-lg border border-border max-w-md w-full text-center">
          <h2 className="text-xl font-semibold mb-2">License Invalid or Missing</h2>
          <p className="text-muted-foreground mb-4">Please ensure your license server is running and your key is valid.</p>
          <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity">
            Check Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background text-foreground select-none">
      <header className="h-12 border-b border-border flex items-center px-4" style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}>
        <div className="font-semibold text-primary">Gyrus Vajra</div>
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
