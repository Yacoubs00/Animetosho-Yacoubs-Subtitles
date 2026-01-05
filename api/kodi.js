// api/kodi.js - GENERIC Kodi API for ALL anime
let DB = null;

const fixLang = (lang) => lang === 'und' || lang === 'enm' ? 'eng' : lang;

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// GENERIC episode detection for ALL anime
function detectEpisodeRange(torrent) {
    const name = torrent.name.toLowerCase();
    const fileCount = torrent.torrent_files || 0;
    
    // 1. Explicit episode ranges in title
    const rangeMatch = name.match(/(\d{1,2})-(\d{1,2})/);
    if (rangeMatch) {
        const start = parseInt(rangeMatch[1]);
        const end = parseInt(rangeMatch[2]);
        return `${start.toString().padStart(2, '0')}-${end.toString().padStart(2, '0')}`;
    }
    
    // 2. Volume detection (generic for ALL anime)
    if (name.includes('vol.01') || name.includes('volume 1')) return '01-06';
    if (name.includes('vol.02') || name.includes('volume 2')) return '07-12';
    if (name.includes('vol.03') || name.includes('volume 3')) return '13-18';
    if (name.includes('vol.04') || name.includes('volume 4')) return '19-24';
    
    // 3. File count based detection (generic for ALL anime)
    if (fileCount >= 20) return `01-${(fileCount-1).toString().padStart(2, '0')} + Extras`;
    if (fileCount >= 10) return `01-${fileCount.toString().padStart(2, '0')}`;
    if (fileCount >= 5) return `01-${fileCount.toString().padStart(2, '0')}`;
    
    // 4. Pack/batch indicators
    if (name.includes('complete') || name.includes('batch') || name.includes('season')) {
        return 'Complete';
    }
    
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
                const firstSubFile = torrent.subtitle_files[0];
                
                if (firstSubFile) {
                    let url, size, sizeFormatted;
                    
                    if (firstSubFile.is_pack) {
                        const packName = firstSubFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
                        url = `https://storage.animetosho.org/attachpk/${id}/${packName}_attachments.7z`;
                        size = firstSubFile.sizes?.[0] || 2000000;
                    } else {
                        const afidHex = firstSubFile.afids[0].toString(16).padStart(8, '0');
                        url = `https://storage.animetosho.org/attach/${afidHex}/file.xz`;
                        size = firstSubFile.sizes?.[0] || 50000;
                    }
                    
                    sizeFormatted = formatSize(size);
                    
                    results.push({
                        title: torrent.name,
                        subtitle_url: url,
                        languages: firstSubFile.languages.map(fixLang),
                        is_pack: firstSubFile.is_pack || false,
                        size: size,
                        size_formatted: sizeFormatted,
                        torrent_id: parseInt(id),
                        episode_range: episodeRange,
                        torrent_files: torrent.torrent_files || 0,
                        total_size: torrent.total_size || 0
                    });
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
