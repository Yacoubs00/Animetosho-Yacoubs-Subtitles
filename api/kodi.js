// EPISODE-AWARE Kodi API - Built on working FINAL.js foundation
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
        const blobUrl = process.env.DATABASE_BLOB_URL;  // ✅ KEPT WORKING DATABASE LOADING
        const response = await fetch(blobUrl);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        DB = await response.json();
        
        const { q, limit = 200, lang = 'eng' } = req.query;
        if (!q) return res.status(400).json({ error: 'Query required' });
        
        const requestedEpisode = extractEpisodeFromQuery(q);  // ✅ ADDED EPISODE DETECTION
        const results = [];
        const query = q.toLowerCase();
        
        for (const [id, torrent] of Object.entries(DB.torrents)) {
            if (results.length >= limit) break;
            
            if (torrent && torrent.name.toLowerCase().includes(query)) {
                const episodeRange = detectEpisodeRange(torrent);
                
                if (torrent.subtitle_files && torrent.subtitle_files.length > 0) {
                    // Filter by language
                    const languageFiles = torrent.subtitle_files.filter(file => 
                        file.languages.includes(lang)
                    );
                    
                    if (languageFiles.length === 0) continue;
                    
                    // ✅ SMART: Select best file for the request
                    const selectedFile = smartPackSelection(languageFiles, requestedEpisode);
                    
                    let subtitleUrl;
                    if (selectedFile.is_pack) {
                        const encodedName = encodeURIComponent(selectedFile.pack_name || torrent.name);
                        
                        if (selectedFile.pack_url_type === 'torattachpk') {
                            // Complete pack
                            subtitleUrl = `https://animetosho.org/storage/torattachpk/${id}/${encodedName}_attachments.7z`;
                        } else {
                            // Episode-specific pack
                            subtitleUrl = `https://storage.animetosho.org/attachpk/${id}/${encodedName}_attachments.7z`;
                        }
                    } else {
                        // Individual file
                        const afidHex = selectedFile.afids[0].toString(16).padStart(8, '0');
                        subtitleUrl = `https://storage.animetosho.org/attach/${afidHex}/file.xz`;
                    }
                    
                    results.push({
                        filename: selectedFile.filename,
                        download: subtitleUrl,
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
        }
        
        // ✅ Sort: exact episode matches first, then by size
        results.sort((a, b) => {
            if (a.episode_match !== b.episode_match) {
                return b.episode_match - a.episode_match;
            }
            return b.size - a.size;
        });
        
        res.json(results.slice(0, 20));
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
}
