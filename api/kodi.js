// api/kodi.js - Kodi-compatible API endpoint with episode detection

let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 0; // Force refresh every time

const fixLang = (lang) => lang === 'und' || lang === 'enm' ? 'eng' : lang;

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// Built-in episode detection (no import needed)
function detectEpisodeRange(torrent) {
    const name = torrent.name.toLowerCase();
    const fileCount = torrent.torrent_files || 0;
    
    // Series-specific detection
    if (name.includes('terror') || name.includes('zankyou')) {
        if (fileCount >= 11 || name.includes('complete') || name.includes('season')) {
            return '01-11';
        }
        if (name.includes('vol.01') || name.includes('volume 1')) return '01-06';
        if (name.includes('vol.02') || name.includes('volume 2')) return '07-11';
        if (fileCount === 6) return '01-06';
        if (fileCount === 5) return '07-11';
    }
    
    // Generic detection
    if (fileCount >= 20) return `01-${(fileCount-1).toString().padStart(2, '0')} + Extras`;
    if (fileCount >= 10) return `01-${fileCount.toString().padStart(2, '0')}`;
    if (name.includes('complete') || name.includes('batch') || name.includes('season')) {
        return 'Complete';
    }
    
    return null;
}

function formatDisplayTitle(name, episodeRange, sizeFormatted = '') {
    if (!episodeRange) {
        return sizeFormatted ? `${name.slice(0, 70)} (${sizeFormatted})` : name.slice(0, 70);
    }
    
    if (episodeRange.includes('+')) {
        return `${name.slice(0, 40)} (${episodeRange}) (${sizeFormatted})`;
    } else if (episodeRange === 'Complete') {
        return `${name.slice(0, 55)} (Complete) (${sizeFormatted})`;
    } else {
        return `${name.slice(0, 45)} (Eps ${episodeRange}) (${sizeFormatted})`;
    }
}

export default async function handler(req, res) {
    try {
        // Always fetch fresh database
        const blobUrl = process.env.DATABASE_BLOB_URL;
        console.log('Fetching from:', blobUrl);
        
        const response = await fetch(blobUrl);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        DB = await response.json();
        lastFetch = Date.now();
        
        const { q, limit = 200 } = req.query;
        if (!q) return res.status(400).json({ error: 'Query required' });
        
        const results = [];
        const query = q.toLowerCase();
        
        // Search through all torrents
        for (const [id, torrent] of Object.entries(DB.torrents)) {
            if (results.length >= limit) break;
            
            if (torrent && torrent.name.toLowerCase().includes(query)) {
                // Detect episode range
                const episodeRange = detectEpisodeRange(torrent);
                
                // Process subtitle files
                const subtitleFiles = [];
                const allLanguages = new Set();
                
                torrent.subtitle_files.forEach(subFile => {
                    if (subFile.is_pack) {
                        const packName = subFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
                        const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000;
                        const sizeFormatted = formatSize(packSize);
                        
                        subtitleFiles.push({
                            url: `https://storage.animetosho.org/attachpk/${id}/${packName}_attachments.7z`,
                            languages: subFile.languages.map(fixLang),
                            is_pack: true,
                            size: packSize,
                            size_formatted: sizeFormatted
                        });
                        
                        subFile.languages.forEach(lang => allLanguages.add(fixLang(lang)));
                    } else {
                        subFile.afids.forEach((afid, index) => {
                            const language = fixLang(subFile.languages[index] || subFile.languages[0] || 'eng');
                            const afidHex = afid.toString(16).padStart(8, '0');
                            const fileSize = subFile.sizes && subFile.sizes[index] ? subFile.sizes[index] : 50000;
                            
                            subtitleFiles.push({
                                url: `https://storage.animetosho.org/attach/${afidHex}/file.xz`,
                                languages: [language],
                                is_pack: false,
                                size: fileSize,
                                size_formatted: formatSize(fileSize)
                            });
                            
                            allLanguages.add(language);
                        });
                    }
                });
                
                // Format for Kodi compatibility
                const kodiResult = {
                    title: torrent.name,
                    subtitle_url: subtitleFiles[0]?.url || '',
                    languages: Array.from(allLanguages),
                    is_pack: subtitleFiles.some(file => file.is_pack),
                    size: subtitleFiles[0]?.size || 50000,
                    size_formatted: subtitleFiles[0]?.size_formatted || '50KB',
                    torrent_id: parseInt(id),
                    // Enhanced fields
                    episode_range: episodeRange,
                    display_title: formatDisplayTitle(torrent.name, episodeRange, subtitleFiles[0]?.size_formatted),
                    torrent_files: torrent.torrent_files || 0,
                    total_size: torrent.total_size || 0
                };
                
                results.push(kodiResult);
            }
        }
        
        res.json({
            success: true,
            data: results,
            count: results.length
        });
        
    } catch (error) {
        console.error('Kodi API Error:', error);
        res.status(500).json({ 
            success: false,
            error: error.message, 
            debug_url: process.env.DATABASE_BLOB_URL 
        });
    }
}
