// Vercel Blob Search API - Chunked Loading
const INDEX_URL = 'https://kyqw0ojzrgq2c5ex.public.blob.vercel-storage.com/index.json';

let indexCache = null;
let chunkCache = {};

async function loadIndex() {
    if (indexCache) return indexCache;
    const res = await fetch(INDEX_URL);
    indexCache = await res.json();
    return indexCache;
}

async function loadChunk(chunkInfo) {
    if (chunkCache[chunkInfo.id]) return chunkCache[chunkInfo.id];
    const res = await fetch(chunkInfo.url);
    const data = await res.json();
    chunkCache[chunkInfo.id] = data;
    return data;
}

function extractEpisode(query) {
    const match = query.match(/(?:episode|ep)\s*(\d{1,3})|(?:^|\s)(\d{1,2})(?:\s|$)/i);
    return match ? parseInt(match[1] || match[2]) : null;
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng', limit = 50 } = req.query;
    if (!query) return res.status(400).json({ error: 'Query required' });

    try {
        const index = await loadIndex();
        const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
        const episode = extractEpisode(query);
        const results = [];
        const maxLimit = parseInt(limit);

        // Search through all chunks
        for (const chunk of index.chunks) {
            if (results.length >= maxLimit) break;
            
            const data = await loadChunk(chunk);
            
            for (const [id, t] of Object.entries(data)) {
                if (results.length >= maxLimit) break;
                
                const name = (t.name || '').toLowerCase();
                const fileNames = (t.subtitle_files || []).map(f => (f.filename || '').toLowerCase()).join(' ');
                const searchText = name + ' ' + fileNames;
                
                if (!searchTerms.every(term => searchText.includes(term))) continue;
                if (lang !== 'all' && !t.languages?.includes(lang)) continue;

                results.push({
                    id: parseInt(id),
                    name: t.name || t.subtitle_files?.[0]?.filename || `Torrent ${id}`,
                    subtitle_count: t.subtitle_files?.length || 0,
                    languages: t.languages || [],
                    episodes: t.episodes_available || [],
                    episode_match: episode && t.episodes_available?.includes(episode)
                });
            }
        }

        res.json({ results, total: results.length, episode_requested: episode });
    } catch (e) {
        res.status(500).json({ error: 'Search failed', details: e.message });
    }
}

export const config = { maxDuration: 60 };
