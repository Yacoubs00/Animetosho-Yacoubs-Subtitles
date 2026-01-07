// Vercel Blob Search API - with streaming for large JSON
const BLOB_URL = 'https://kyqw0ojzrgq2c5ex.public.blob.vercel-storage.com/subtitles.json';

let cachedData = null;
let cacheTime = 0;
const CACHE_TTL = 300000;

async function loadDatabase() {
    if (cachedData && Date.now() - cacheTime < CACHE_TTL) return cachedData;
    
    const res = await fetch(BLOB_URL);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    
    const text = await res.text();
    cachedData = JSON.parse(text);
    cacheTime = Date.now();
    return cachedData;
}

function extractEpisode(query) {
    const match = query.match(/(?:episode|ep)\s*(\d{1,3})|(?:^|\s)(\d{1,2})(?:\s|$)/i);
    return match ? parseInt(match[1] || match[2]) : null;
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng', limit = 50 } = req.query;
    if (!query) return res.status(400).json({ error: 'Query required' });

    try {
        const db = await loadDatabase();
        const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
        const episode = extractEpisode(query);

        const results = [];
        for (const [id, t] of Object.entries(db.torrents)) {
            if (results.length >= parseInt(limit)) break;
            
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

        res.json({ results, total: results.length, episode_requested: episode });
    } catch (e) {
        res.status(500).json({ error: 'Search failed', details: e.message });
    }
}

export const config = {
    maxDuration: 60
};
