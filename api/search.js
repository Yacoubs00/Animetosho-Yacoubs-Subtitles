// Episode-Aware Search API (minimal changes to existing)
import fs from 'fs';

let DB = null;

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
    
    return episodePack || subtitleFiles.find(f => 
        !f.is_pack && f.episode_number === requestedEpisode
    ) || subtitleFiles[0];
}

export default function handler(req, res) {
    const { q: query, lang = 'eng' } = req.query;
    
    if (!DB) {
        DB = JSON.parse(fs.readFileSync('data/subtitles.json', 'utf8'));
    }
    
    const requestedEpisode = extractEpisodeFromQuery(query);
    const results = [];
    
    for (const [torrentId, torrent] of Object.entries(DB.torrents)) {
        if (torrent.name.toLowerCase().includes(query.toLowerCase())) {
            const languageFiles = torrent.subtitle_files.filter(file => 
                file.languages.includes(lang)
            );
            
            if (languageFiles.length === 0) continue;
            
            const selectedFile = smartPackSelection(languageFiles, requestedEpisode);
            
            results.push({
                id: torrentId,
                name: torrent.name,
                filename: selectedFile.filename,
                size: Math.max(...selectedFile.sizes),
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
    
    res.json(results.slice(0, 50));
}
