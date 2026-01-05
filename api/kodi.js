// Enhanced API - Properly handles improved database with all 5 goals
let DB = null;
const fixLang = (lang) => {
    // GOAL 2: Improved language accuracy - don't auto-convert 'und'
    if (lang === 'enm') return 'eng';  // English-Modified → English
    return lang;  // Keep 'und' as is (GOAL 3)
};

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// GOAL 1: Enhanced episode detection using actual torrent metadata
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
    
    // 2. Volume detection (GOAL 1: Fixed patterns)
    if (name.includes('vol.01') || name.includes('volume 1')) return '01-06';
    if (name.includes('vol.02') || name.includes('volume 2')) return '07-12';
    if (name.includes('vol.03') || name.includes('volume 3')) return '13-18';
    if (name.includes('vol.04') || name.includes('volume 4')) return '19-24';
    
    // 3. File count based detection (GOAL 5: Using actual metadata)
    if (fileCount >= 20) return `01-${(fileCount-1).toString().padStart(2, '0')} + Extras`;
    if (fileCount >= 11) return `01-${fileCount.toString().padStart(2, '0')}`;  // Complete series
    if (fileCount >= 6) return `01-06`;  // Volume 1
    if (fileCount >= 2 && name.includes('vol.01')) return '01-06';  // SallySubs case
    
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
                
                // GOAL 1: Process subtitle files correctly
                if (torrent.subtitle_files && torrent.subtitle_files.length > 0) {
                    // GOAL 1: Look for pack entry first
                    const packFile = torrent.subtitle_files.find(f => f.is_pack);
                    
                    if (packFile) {
                        // GOAL 1: Use pack data with actual sizes
                        let displayTitle = torrent.name;
                        if (episodeRange) {
                            displayTitle += ` (Eps ${episodeRange})`;
                        }
                        
                        results.push({
                            title: displayTitle,
                            subtitle_url: `https://storage.animetosho.org/attachpk/${id}/${packFile.pack_name}_attachments.7z`,
                            languages: packFile.languages.map(fixLang),
                            is_pack: true,  // GOAL 1: Correctly identified
                            size: packFile.sizes[0],  // GOAL 1: Actual pack size
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
                            size: firstSubFile.sizes[0],  // GOAL 1: Actual file size
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
            count: results.length,
            version: DB.version || '1.0'  // Show database version
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
}
