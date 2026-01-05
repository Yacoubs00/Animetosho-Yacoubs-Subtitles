// TURSO-powered Kodi API - Episode-Aware
import { createClient } from '@libsql/client';

const client = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN
});

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

function buildDownloadUrl(file, torrentId) {
    const baseUrl = 'https://storage.animetosho.org';
    
    if (file.is_pack) {
        const cleanName = encodeURIComponent(file.pack_name || `torrent_${torrentId}`);
        
        if (file.pack_url_type === 'torattachpk') {
            return `${baseUrl}/torattachpk/${torrentId}/${cleanName}_attachments.7z`;
        } else {
            return `${baseUrl}/attachpk/${torrentId}/${cleanName}_attachments.7z`;
        }
    } else {
        const afidHex = file.afid.toString(16).padStart(8, '0');
        return `${baseUrl}/attach/${afidHex}/file.xz`;
    }
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng' } = req.query;
    
    if (!query) {
        return res.status(400).json({ error: 'Query parameter required' });
    }
    
    try {
        const requestedEpisode = extractEpisodeFromQuery(query);
        
        // TURSO SQL Query - Episode-Aware
        let sql = `
            SELECT 
                t.id as torrent_id,
                t.name as torrent_name,
                sf.filename,
                sf.afid,
                sf.language,
                sf.size,
                sf.episode_number,
                sf.is_pack,
                sf.pack_type,
                sf.pack_url_type
            FROM torrents t
            JOIN subtitle_files sf ON t.id = sf.torrent_id
            WHERE t.name LIKE ? AND sf.language = ?
        `;
        
        const params = [`%${query}%`, lang];
        
        // Add episode filter if requested
        if (requestedEpisode) {
            sql += ` AND (sf.episode_number = ? OR sf.pack_type = 'complete')`;
            params.push(requestedEpisode);
        }
        
        sql += ` ORDER BY 
            CASE WHEN sf.episode_number = ? THEN 0 ELSE 1 END,
            sf.is_pack DESC,
            sf.size DESC
            LIMIT 20
        `;
        params.push(requestedEpisode || 0);
        
        const result = await client.execute({ sql, args: params });
        
        const results = result.rows.map(row => ({
            filename: row.filename,
            download: buildDownloadUrl({
                is_pack: row.is_pack,
                pack_name: row.torrent_name,
                pack_url_type: row.pack_url_type,
                afid: row.afid
            }, row.torrent_id),
            sync: false,
            hearing_imp: false,
            language: lang,
            rating: row.is_pack ? 5 : 4,
            size: row.size,
            torrent_name: row.torrent_name,
            episode_match: row.episode_number === requestedEpisode,
            pack_type: row.pack_type || 'individual'
        }));
        
        res.json(results);
        
    } catch (error) {
        console.error('TURSO query error:', error);
        res.status(500).json({ error: 'Database query failed' });
    }
}
