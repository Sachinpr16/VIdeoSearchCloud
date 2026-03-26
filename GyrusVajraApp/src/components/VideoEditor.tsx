import React, { useState } from 'react';
import { Scissors, Save } from 'lucide-react';

export default function VideoEditor() {
    const [videoFile, setVideoFile] = useState<File | null>(null);
    const [startTime, setStartTime] = useState<number>(0);
    const [duration, setDuration] = useState<number>(10);
    const [processing, setProcessing] = useState(false);

    const handleTrim = async () => {
        if (!videoFile) return;

        setProcessing(true);
        try {
            // Create a dummy output path for now
            const videoPath = (videoFile as any).path;
            const outputPath = videoPath.replace(/\.[^/.]+$/, "") + "_trimmed.mp4";

            // Use the exposed electronAPI
            const result = await (window as any).electronAPI.trimVideo({
                inputPath: videoPath,
                outputPath: outputPath,
                startTime: startTime,
                duration: duration
            });

            if (result.success) {
                alert('Video trimmed successfully! Saved to: ' + result.outputPath);
            }
        } catch (error) {
            console.error('Trim error:', error);
            alert('Failed to trim video.');
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div className="flex flex-col h-full space-y-6">
            <h1 className="text-2xl font-bold">Video Editor</h1>

            <div className="bg-card border border-border p-6 rounded-lg shadow-sm space-y-6 max-w-2xl">
                <div>
                    <label className="block text-sm font-medium mb-2">Select Video</label>
                    <input
                        type="file"
                        accept="video/*"
                        className="block w-full text-sm text-muted-foreground
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-semibold
                      file:bg-primary file:text-primary-foreground
                      hover:file:bg-primary/90 file:transition-colors"
                        onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
                    />
                </div>

                {videoFile && (
                    <div className="space-y-4 pt-4 border-t border-border">
                        <h3 className="font-semibold">Trim Settings</h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Start Time (sec)</label>
                                <input
                                    type="number"
                                    min="0"
                                    value={startTime}
                                    onChange={(e) => setStartTime(Number(e.target.value))}
                                    className="w-full bg-input/50 border border-border rounded p-2 focus:ring-2 focus:ring-primary outline-none"
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-muted-foreground mb-1">Duration (sec)</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={duration}
                                    onChange={(e) => setDuration(Number(e.target.value))}
                                    className="w-full bg-input/50 border border-border rounded p-2 focus:ring-2 focus:ring-primary outline-none"
                                />
                            </div>
                        </div>

                        <button
                            onClick={handleTrim}
                            disabled={processing}
                            className="mt-4 bg-accent hover:bg-accent/90 text-accent-foreground px-4 py-2 rounded-md flex items-center gap-2 disabled:opacity-50 transition-colors"
                        >
                            {processing ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Processing...
                                </>
                            ) : (
                                <>
                                    <Scissors size={18} /> Trim & Export
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
