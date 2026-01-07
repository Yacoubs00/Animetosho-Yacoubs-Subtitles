// Vercel Blob Kodi API
const BLOB_URL = 'https://kyqw0ojzrgq2c5ex.public.blob.vercel-storage.com/subtitles.json';

let cachedData = null;
let cacheTime = 0;
const CACHE_TTL = 300000;

async function loadDatabase() {
    if (cachedData && Date.now() - cacheTime < CACHE_TTL) return cachedData;
    const res = await fetch(BLOB_URL);
    cachedData = await res.json();
    cacheTime = Date.now();
    return cachedData;
}

function extractEpisode(query) {
    const match = query.match(/(?:episode|ep)\s*(\d{1,3})|(?:^|\s)(\d{1,2})(?:\s|$)/i);
    return match ? parseInt(match[1] || match[2]) : null;
}

function buildUrl(file, torrentId, torrentName) {
    const base = 'https://storage.animetosho.org';
    if (file.is_pack) {
        return `${base}/torattachpk/${torrentId}/${encodeURIComponent(torrentName)}_attachments.7z`;
    }
    const afid = Array.isArray(file.afids) ? file.afids[0] : file.afid;
    return `${base}/attach/${afid.toString(16).padStart(8, '0')}/file.xz`;
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng' } = req.query;
    if (!query) return res.status(400).json({ error: 'Query required' });

    try {
        const db = await loadDatabase();
        const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
        const episode = extractEpisode(query);

        const results = [];
        for (const [id, t] of Object.entries(db.torrents)) {
            if (results.length >= 20) break;
            
            const name = (t.name || '').toLowerCase();
            const fileNames = (t.subtitle_files || []).map(f => (f.filename || '').toLowerCase()).join(' ');
            const searchText = name + ' ' + fileNames;
            
            if (!searchTerms.every(term => searchText.includes(term))) continue;

            const files = (t.subtitle_files || []).filter(f => {
                const fileLangs = f.languages || [f.lang];
                const langMatch = lang === 'all' || fileLangs.includes(lang);
                const epMatch = !episode || !f.episode_number || f.episode_number === episode || f.is_pack;
                return langMatch && epMatch;
            });

            const torrentName = t.name || t.subtitle_files?.[0]?.filename || `Torrent ${id}`;
            
            for (const f of files.slice(0, 3)) {
                results.push({
                    filename: f.filename,
                    download: buildUrl(f, id, torrentName),
                    language: (f.languages || [f.lang])[0] || lang,
                    rating: f.is_pack ? 5 : 4,
                    size: Array.isArray(f.sizes) ? f.sizes[0] : f.size,
                    torrent_name: torrentName,
                    episode_match: episode && f.episode_number === episode
                });
                if (results.length >= 20) break;
            }
        }

        res.json(results);
    } catch (e) {
        console.error(e);
        res.status(500).json({ error: 'Query failed' });
    }
}
