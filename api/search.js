// TURSO-powered Search API - Episode-Aware
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

export default async function handler(req, res) {
    const { q: query, lang = 'eng', limit = 50 } = req.query;
    
    if (!query) {
        return res.status(400).json({ error: 'Query parameter required' });
    }
    
    try {
        const requestedEpisode = extractEpisodeFromQuery(query);
        
        // TURSO SQL Query for Search
        let sql = `
            SELECT 
                t.id,
                t.name,
                COUNT(sf.id) as subtitle_count,
                GROUP_CONCAT(DISTINCT sf.language) as languages,
                MAX(sf.size) as max_size,
                COUNT(CASE WHEN sf.episode_number = ? THEN 1 END) as episode_matches
            FROM torrents t
            JOIN subtitle_files sf ON t.id = sf.torrent_id
            WHERE t.name LIKE ?
        `;
        
        const params = [requestedEpisode || 0, `%${query}%`];
        
        if (lang !== 'all') {
            sql += ` AND sf.language = ?`;
            params.push(lang);
        }
        
        sql += ` 
            GROUP BY t.id, t.name
            ORDER BY episode_matches DESC, max_size DESC
            LIMIT ?
        `;
        params.push(parseInt(limit));
        
        const result = await client.execute({ sql, args: params });
        
        const results = result.rows.map(row => ({
            id: row.id,
            name: row.name,
            subtitle_count: row.subtitle_count,
            languages: row.languages ? row.languages.split(',') : [],
            size: row.max_size,
            episode_match: row.episode_matches > 0
        }));
        
        res.json({
            results,
            total: results.length,
            episode_requested: requestedEpisode
        });
        
    } catch (error) {
        console.error('TURSO search error:', error);
        res.status(500).json({ error: 'Database search failed' });
    }
}
