// WORKING Enhanced Kodi API - Fixed JavaScript syntax
let DB = null;

const fixLang = (lang) => {
    if (lang === 'enm') return 'eng';
    return lang;
};

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function detectEpisodeRange(torrent) {
    const name = torrent.name.toLowerCase();
    const fileCount = torrent.torrent_files || 0;
    
    // Volume detection
    if (name.includes('vol.01') || name.includes('volume 1')) return '01-06';
    if (name.includes('vol.02') || name.includes('volume 2')) return '07-12';
    
    // File count detection
    if (fileCount >= 11) return `01-${fileCount.toString().padStart(2, '0')}`;
    if (fileCount >= 6) return '01-06';
    if (fileCount >= 2 && name.includes('vol.01')) return '01-06';
    
    return null;
}

export default async function handler(req, res) {
    try {
        const blobUrl = process.env.DATABASE_BLOB_URL;
        const response = await fetch(blobUrl);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        DB = await response.json();
        
        const { q, limit = 200 } = req.query;
        if (!q) return res.status(400).json({ error: 'Query required' });
        
        const results = [];
        const query = q.toLowerCase();
        
        for (const [id, torrent] of Object.entries(DB.torrents)) {
            if (results.length >= limit) break;
            
            if (torrent && torrent.name.toLowerCase().includes(query)) {
                const episodeRange = detectEpisodeRange(torrent);
                
                if (torrent.subtitle_files && torrent.subtitle_files.length > 0) {
                    // Look for pack entry
                    const packFile = torrent.subtitle_files.find(f => f.is_pack);
                    
                    if (packFile) {
                        let displayTitle = torrent.name;
                        if (episodeRange) {
                            displayTitle += ` (Eps ${episodeRange})`;
                        }
                        
                        results.push({
                            title: displayTitle,
                            subtitle_url: `https://storage.animetosho.org/attachpk/${id}/${packFile.pack_name}_attachments.7z`,
                            languages: packFile.languages.map(fixLang),
                            is_pack: true,
                            size: packFile.sizes[0],
                            size_formatted: formatSize(packFile.sizes[0]),
                            torrent_id: parseInt(id),
                            episode_range: episodeRange,
                            torrent_files: torrent.torrent_files || 0,
                            total_size: torrent.total_size || 0
                        });
                    } else {
                        // Individual files
                        const firstSubFile = torrent.subtitle_files[0];
                        const afidHex = firstSubFile.afids[0].toString(16).padStart(8, '0');
                        
                        results.push({
                            title: torrent.name,
                            subtitle_url: `https://storage.animetosho.org/attach/${afidHex}/file.xz`,
                            languages: firstSubFile.languages.map(fixLang),
                            is_pack: false,
                            size: firstSubFile.sizes[0],
                            size_formatted: formatSize(firstSubFile.sizes[0]),
                            torrent_id: parseInt(id),
                            episode_range: episodeRange,
                            torrent_files: torrent.torrent_files || 0,
                            total_size: torrent.total_size || 0
                        });
                    }
                }
            }
        }
        
        res.json({
            success: true,
            data: results,
            count: results.length
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
}
