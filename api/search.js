let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 0;

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
    if (fileCount >= 10) return `01-${fileCount.toString().padStart(2, '0')}`;  // FIXED SYNTAX
    if (fileCount >= 5) return `01-${fileCount.toString().padStart(2, '0')}`;
    
    // 4. Pack/batch indicators
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
        const blobUrl = process.env.DATABASE_BLOB_URL;
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
                const episodeRange = detectEpisodeRange(torrent);
                
                torrent.subtitle_files.forEach(subFile => {
                    if (subFile.is_pack) {
                        const packName = subFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
                        const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000;
                        const sizeFormatted = formatSize(packSize);
                        const displayTitle = formatDisplayTitle(torrent.name, episodeRange, sizeFormatted);
                        
                        downloadLinks.push({
                            language: 'ALL',
                            url: `https://storage.animetosho.org/attachpk/${id}/${packName}_attachments.7z`,
                            filename: subFile.filename,
                            is_pack: true,
                            pack_languages: subFile.languages.map(fixLang),
                            size: packSize,
                            size_formatted: sizeFormatted,
                            episode_range: episodeRange,
                            display_title: displayTitle
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
