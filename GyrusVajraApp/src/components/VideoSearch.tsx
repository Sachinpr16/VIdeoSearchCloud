import React, { useState } from 'react';
import axios from 'axios';
import { Search, Image as ImageIcon, Mic } from 'lucide-react';
import { motion } from 'framer-motion';

export default function VideoSearch() {
    const [activeTab, setActiveTab] = useState<'text' | 'image' | 'audio'>('text');
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query) return;

        setLoading(true);
        let endpoint = 'textsearch';
        let payload: any = { startIndex: 0, limit: 20, dbName: "*" };

        if (activeTab === 'text') {
            endpoint = 'textsearch';
            payload.query = query;
        } else if (activeTab === 'image') {
            endpoint = 'imagesearch';
            payload.image_path = query; // Assuming query is a path for now, in real UI it would be a file picker
        } else if (activeTab === 'audio') {
            endpoint = 'audiosearch';
            payload.audio_path = query;
        }

        try {
            const res = await axios.post(`http://localhost:5801/${endpoint}`, payload);
            setResults(res.data.results || []);
        } catch (err) {
            console.error(err);
            alert('Search failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="flex flex-col h-full space-y-6"
        >
            <h1 className="text-2xl font-bold">Cross-Modal Search</h1>

            <div className="flex space-x-2 border-b border-border pb-2">
                <button onClick={() => setActiveTab('text')} className={`flex items-center gap-2 px-4 py-2 ${activeTab === 'text' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground'}`}>
                    <Search size={16} /> Text
                </button>
                <button onClick={() => setActiveTab('image')} className={`flex items-center gap-2 px-4 py-2 ${activeTab === 'image' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground'}`}>
                    <ImageIcon size={16} /> Image
                </button>
                <button onClick={() => setActiveTab('audio')} className={`flex items-center gap-2 px-4 py-2 ${activeTab === 'audio' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground'}`}>
                    <Mic size={16} /> Audio
                </button>
            </div>

            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-3 text-muted-foreground" size={18} />
                    <input
                        type="text"
                        className="w-full bg-input/50 border border-border rounded-md py-2 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-primary text-foreground"
                        placeholder={activeTab === 'text' ? "Search for moments..." : "Enter file path to search..."}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                </div>
                <button type="submit" disabled={loading} className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-md disabled:opacity-50 transition-colors">
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </form>

            <div className="flex-1 overflow-y-auto">
                <h3 className="text-lg font-semibold mb-4">Results</h3>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                    {results.length === 0 ? (
                        <div className="col-span-full text-muted-foreground py-8">No results found.</div>
                    ) : (
                        results.map((r, i) => (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                key={i}
                                className="p-4 bg-card border border-border rounded-md shadow-sm"
                            >
                                <div className="font-semibold">{r.sourceId}</div>
                                <div className="text-sm text-muted-foreground mt-1">Match: {Math.round(r.score * 100)}%</div>
                                <div className="text-xs text-muted-foreground mt-2 bg-black/20 p-2 rounded">
                                    Time: {r.start}s - {r.end}s
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
            </div>
        </motion.div>
    );
}
