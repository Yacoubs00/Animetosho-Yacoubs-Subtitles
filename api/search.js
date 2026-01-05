let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 0; // Force refresh every time

const fixLang = (lang) => lang === 'und' || lang === 'enm' ? 'eng' : lang;

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// NEW: Episode detection function
function detectEpisodeRange(torrent) {
    const name = torrent.name.toLowerCase();
    const fileCount = torrent.torrent_files || 0;
    const totalSize = torrent.total_size || 0;
    
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
    if (fileCount >= 20) return `01-${fileCount-1} + Extras`;
    if (fileCount >= 10) return `01-${fileCount:02d}`;
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
        
        const { q, lang, limit = 100 } = req.query;
        if (!q) return res.status(400).json({ error: 'Query required' });
        
        const results = [];
        const query = q.toLowerCase();
        const candidates = lang && DB.languages[lang] ? DB.languages[lang] : Object.keys(DB.torrents);
        
        for (const id of candidates) {
            if (results.length >= limit) break;
            
            const torrent = DB.torrents[id];
            if (torrent && torrent.name.toLowerCase().includes(query)) {
                const downloadLinks = [];
                const allLanguages = new Set();
                
                // NEW: Detect episode range
                const episodeRange = detectEpisodeRange(torrent);
                
                torrent.subtitle_files.forEach(subFile => {
                    if (subFile.is_pack) {
                        const packName = subFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
                        const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000;
                        const sizeFormatted = formatSize(packSize);
                        
                        // NEW: Enhanced display title with episode range
                        const displayTitle = formatDisplayTitle(torrent.name, episodeRange, sizeFormatted);
                        
                        downloadLinks.push({
                            language: 'ALL',
                            url: `https://storage.animetosho.org/attachpk/${id}/${packName}_attachments.7z`,
                            filename: subFile.filename,
                            is_pack: true,
                            pack_languages: subFile.languages.map(fixLang),
                            size: packSize,
                            size_formatted: sizeFormatted,
                            episode_range: episodeRange,  // NEW
                            display_title: displayTitle   // NEW
                        });
                        
                        subFile.languages.forEach(lang => allLanguages.add(fixLang(lang)));
                    } else {
                        subFile.afids.forEach((afid, index) => {
                            const language = fixLang(subFile.languages[index] || subFile.languages[0] || 'eng');
                            const afidHex = afid.toString(16).padStart(8, '0');
                            const fileSize = subFile.sizes && subFile.sizes[index] ? subFile.sizes[index] : 50000;
                            
                            downloadLinks.push({
                                language: language,
                                url: `https://storage.animetosho.org/attach/${afidHex}/file.xz`,
                                filename: subFile.filename,
                                is_pack: false,
                                size: fileSize,
                                size_formatted: formatSize(fileSize)
                            });
                            
                            allLanguages.add(language);
                        });
                    }
                });
                
                results.push({
                    name: torrent.name,
                    languages: Array.from(allLanguages),
                    download_links: downloadLinks,
                    subtitle_count: downloadLinks.length,
                    torrent_id: parseInt(id),
                    // NEW: Include torrent metadata
                    torrent_files: torrent.torrent_files || 0,
                    total_size: torrent.total_size || 0,
                    episode_range: episodeRange
                });
            }
        }
        
        res.json({ results, total: results.length });
    } catch (error) {
        res.status(500).json({ 
            error: error.message, 
            debug_url: process.env.DATABASE_BLOB_URL 
        });
    }
}
