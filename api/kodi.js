// GitHub Pages Kodi API
const INDEX_URL = 'https://yacoubs00.github.io/Animetosho-Yacoubs-Subtitles/index.json';

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
        const index = await loadIndex();
        const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 2);
        const episode = extractEpisode(query);
        const results = [];

        for (const chunk of index.chunks) {
            if (results.length >= 20) break;
            
            const data = await loadChunk(chunk);
            
            for (const [id, t] of Object.entries(data)) {
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
        }

        res.json(results);
    } catch (e) {
        res.status(500).json({ error: 'Query failed', details: e.message });
    }
}

export const config = { maxDuration: 60 };
