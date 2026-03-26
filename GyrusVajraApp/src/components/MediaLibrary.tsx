import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Play, Trash2, Info } from 'lucide-react';
import { motion } from 'framer-motion';
import IndexingModal from './IndexingModal';

export default function MediaLibrary() {
    const [videos, setVideos] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [showIndexModal, setShowIndexModal] = useState(false);

    // In a real scenario we'd call an API to get the list of indexed videos.
    // The provided API doesn't seem to have a 'get-all-videos' endpoint, 
    // but we can mock it or use /search with a wildcard to get all.
    const fetchVideos = async () => {
        setLoading(true);
        try {
            const res = await axios.post('http://localhost:5801/textsearch', {
                query: "",
                startIndex: 0,
                limit: 50,
                dbName: "*"
            });
            // Assuming res.data contains results
            if (res.data && res.data.results) {
                setVideos(res.data.results);
            }
        } catch (err) {
            console.error("Error fetching videos via textsearch wildcard", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchVideos();
    }, []);

    const handleRemove = async (sourceId: string) => {
        if (!confirm('Are you sure you want to remove this video?')) return;
        try {
            await axios.post('http://localhost:5801/remove-video', {
                sourceId,
                indexType: "both"
            });
            fetchVideos();
        } catch (err) {
            console.error(err);
            alert('Failed to remove video');
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex flex-col h-full space-y-4 relative"
        >
            <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold">Media Library</h1>
                <button
                    onClick={() => setShowIndexModal(true)}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded flex items-center gap-2 hover:opacity-90"
                >
                    <Play size={16} /> Index New Video
                </button>
            </div>

            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
            ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 overflow-y-auto pb-8">
                    {videos.length === 0 ? (
                        <div className="col-span-full text-center text-muted-foreground py-12">
                            No videos found. Click "Index New Video" to get started.
                        </div>
                    ) : (
                        videos.map((v, i) => (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.05 }}
                                key={i}
                                className="group relative aspect-video bg-muted rounded-md border border-border shadow-sm overflow-hidden flex flex-col justify-end"
                            >
                                {/* Mock thumbnail or background */}
                                <div className="absolute inset-0 bg-secondary/50 flex items-center justify-center group-hover:bg-secondary/30 transition-colors">
                                    <Play size={32} className="text-white/50 group-hover:text-white transition-colors" />
                                </div>

                                <div className="relative z-10 bg-black/60 p-2 transform translate-y-full group-hover:translate-y-0 transition-transform">
                                    <div className="text-sm font-semibold truncate">{v.sourceId || `Video ${i}`}</div>
                                    <div className="flex justify-end gap-2 mt-2">
                                        <button className="p-1 hover:text-primary transition-colors" title="Info"><Info size={16} /></button>
                                        <button onClick={() => handleRemove(v.sourceId)} className="p-1 hover:text-destructive transition-colors" title="Remove"><Trash2 size={16} /></button>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            )}

            {showIndexModal && (
                <IndexingModal
                    onClose={() => setShowIndexModal(false)}
                    onSuccess={() => {
                        setShowIndexModal(false);
                        fetchVideos();
                    }}
                />
            )}
        </motion.div>
    );
}
