import React, { useState } from 'react';
import axios from 'axios';
import { X, Upload } from 'lucide-react';

interface Props {
    onClose: () => void;
    onSuccess: () => void;
}

export default function IndexingModal({ onClose, onSuccess }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [fps, setFps] = useState(30);
    const [useAudio, setUseAudio] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [sourceId, setSourceId] = useState('');

    const handleIndex = async () => {
        if (!file) return;

        setProcessing(true);
        const filePath = (file as any).path; // Electron file path
        const id = sourceId || file.name.split('.')[0];

        // As per app.py: index-videos takes a JSON array "data"
        // Each item has filepath, sourceId, fps, useAudio
        try {
            await axios.post('http://localhost:5801/index-videos', {
                data: [{
                    filepath: filePath,
                    sourceId: id,
                    fps: fps,
                    useAudio: useAudio
                }],
                isVideo: true,
                dbName: "_default_db"
            });
            alert('Video indexed successfully!');
            onSuccess();
        } catch (err) {
            console.error(err);
            alert('Failed to index video');
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-card w-full max-w-lg rounded-xl border border-border shadow-lg p-6 relative">
                <button onClick={onClose} className="absolute right-4 top-4 text-muted-foreground hover:text-foreground">
                    <X size={20} />
                </button>
                <h2 className="text-xl font-bold mb-6">Index New Video</h2>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Select File</label>
                        <input
                            type="file"
                            accept="video/*"
                            onChange={(e) => setFile(e.target.files?.[0] || null)}
                            className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-primary/20 file:text-primary hover:file:bg-primary/30 file:transition-colors"
                        />
                        {file && <p className="text-xs text-muted-foreground mt-1">{(file as any).path}</p>}
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Source ID (optional)</label>
                        <input
                            type="text"
                            placeholder="e.g. vid_001"
                            value={sourceId}
                            onChange={(e) => setSourceId(e.target.value)}
                            className="w-full bg-input/50 border border-border rounded p-2 focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">FPS (Extraction Rate)</label>
                            <input
                                type="number"
                                value={fps}
                                onChange={(e) => setFps(Number(e.target.value))}
                                className="w-full bg-input/50 border border-border rounded p-2 focus:ring-2 focus:ring-primary outline-none"
                            />
                        </div>
                        <div className="flex items-center space-x-2 mt-6">
                            <input
                                type="checkbox"
                                id="useAudio"
                                checked={useAudio}
                                onChange={(e) => setUseAudio(e.target.checked)}
                                className="rounded border-border bg-input/50 text-primary focus:ring-primary"
                            />
                            <label htmlFor="useAudio" className="text-sm font-medium">Use Audio Indexing</label>
                        </div>
                    </div>
                </div>

                <div className="mt-8 flex justify-end space-x-3">
                    <button onClick={onClose} disabled={processing} className="px-4 py-2 hover:bg-muted rounded-md transition-colors">Cancel</button>
                    <button
                        onClick={handleIndex}
                        disabled={!file || processing}
                        className="bg-primary text-primary-foreground px-4 py-2 rounded-md flex items-center gap-2 disabled:opacity-50 transition-colors"
                    >
                        {processing ? 'Indexing...' : <><Upload size={16} /> Start Indexing</>}
                    </button>
                </div>
            </div>
        </div>
    );
}
