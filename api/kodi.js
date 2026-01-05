// Fixed Kodi API - fetches from Vercel blob storage
const DATABASE_URL = 'https://uyuh9nxvcluovu3u.public.blob.vercel-storage.com/subtitles.json';

let DB = null;
let lastFetch = 0;

async function loadDatabase() {
    if (DB && Date.now() - lastFetch < 300000) return DB; // 5min cache
    
    try {
        const response = await fetch(DATABASE_URL);
        DB = await response.json();
        lastFetch = Date.now();
        return DB;
    } catch (error) {
        console.error('Database fetch error:', error);
        return null;
    }
}

function extractEpisodeFromQuery(query) {
    const patterns = [
        /episode\s+(\d{1,2})/i,
        /ep\s*(\d{1,2})/i,
        /\s(\d{1,2})\s/,
        /-\s*(\d{1,2})\s*$/
    ];
    
    for (const pattern of patterns) {
        const match = query.match(pattern);
        if (match) return parseInt(match[1]);
    }
    return null;
}

function smartPackSelection(subtitleFiles, requestedEpisode) {
    if (!requestedEpisode) {
        const completePack = subtitleFiles.find(f => 
            f.is_pack && f.pack_type === 'complete'
        );
        return completePack || subtitleFiles[0];
    }
    
    const episodePack = subtitleFiles.find(f => 
        f.is_pack && 
        f.pack_type === 'episode_specific' && 
        f.episode_number === requestedEpisode
    );
    
    if (episodePack) return episodePack;
    
    const individualFile = subtitleFiles.find(f => 
        !f.is_pack && f.episode_number === requestedEpisode
    );
    
    return individualFile || subtitleFiles[0];
}

function buildDownloadUrl(file, torrentId, torrentName) {
    const baseUrl = 'https://storage.animetosho.org';
    
    if (file.is_pack) {
        const cleanName = encodeURIComponent(file.pack_name || torrentName);
        
        if (file.pack_url_type === 'torattachpk') {
            return `${baseUrl}/torattachpk/${torrentId}/${cleanName}_attachments.7z`;
        } else {
            return `${baseUrl}/attachpk/${torrentId}/${cleanName}_attachments.7z`;
        }
    } else {
        const afid = file.afids[0];
        const afidHex = afid.toString(16).padStart(8, '0');
        return `${baseUrl}/attach/${afidHex}/file.xz`;
    }
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng' } = req.query;
    
    if (!query) {
        return res.status(400).json({ error: 'Query parameter required' });
    }
    
    const database = await loadDatabase();
    if (!database) {
        return res.status(500).json({ error: 'Database unavailable' });
    }
    
    const requestedEpisode = extractEpisodeFromQuery(query);
    const results = [];
    
    for (const [torrentId, torrent] of Object.entries(database.torrents)) {
        if (torrent.name.toLowerCase().includes(query.toLowerCase())) {
            
            const languageFiles = torrent.subtitle_files.filter(file => 
                file.languages.includes(lang)
            );
            
            if (languageFiles.length === 0) continue;
            
            const selectedFile = smartPackSelection(languageFiles, requestedEpisode);
            
            const downloadUrl = buildDownloadUrl(selectedFile, torrentId, torrent.name);
            
            results.push({
                filename: selectedFile.filename,
                download: downloadUrl,
                sync: false,
                hearing_imp: false,
                language: lang,
                rating: selectedFile.is_pack ? 5 : 4,
                size: Math.max(...selectedFile.sizes),
                torrent_name: torrent.name,
                episode_match: selectedFile.episode_number === requestedEpisode,
                pack_type: selectedFile.pack_type || 'individual'
            });
        }
    }
    
    results.sort((a, b) => {
        if (a.episode_match !== b.episode_match) {
            return b.episode_match - a.episode_match;
        }
        return b.size - a.size;
    });
    
    res.json(results.slice(0, 20));
}
