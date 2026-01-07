// TURSO Search API - Fast SQL queries with UPSERT benefits
import { createClient } from '@libsql/client';

const client = createClient({
    url: 'libsql://database-fuchsia-xylophone-vercel-icfg-leqyol2toayupqs5t2clktag.aws-us-east-1.turso.io',
    authToken: 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njc3ODI2ODMsImlkIjoiMzUxZTVkNjQtMWYzMi00ZGQ1LWE3NTktNDZlOGJmMjdhZTIwIiwicmlkIjoiYTAzMmI2NjktOTAxNy00ZGU1LWIzNmUtMGRiMmE2OTIyNWJiIn0.QushOoxk4gLxLro4Y8iaU0Izh9DYKKlQ3KS8NZYKr75mK01uoj3bEz5o256yoFHIfqoIrbwvFeVPkT2GSk7_AA'
});

function extractEpisode(query) {
    const match = query.match(/(?:episode|ep)\s*(\d{1,3})|(?:^|\s)(\d{1,2})(?:\s|$)/i);
    return match ? parseInt(match[1] || match[2]) : null;
}

export default async function handler(req, res) {
    const { q: query, lang = 'eng', limit = 50 } = req.query;
    if (!query) return res.status(400).json({ error: 'Query required' });

    try {
        const episode = extractEpisode(query);
        
        // Fast SQL query - no need to load entire database!
        let sql = `
            SELECT 
                t.id,
                t.name,
                t.languages,
                t.episodes_available,
                COUNT(sf.id) as subtitle_count
            FROM torrents t
            LEFT JOIN subtitle_files sf ON t.id = sf.torrent_id
            WHERE t.name LIKE ?
        `;
        
        const params = [`%${query}%`];
        
        // Add language filter if specified
        if (lang !== 'all') {
            sql += ` AND (t.languages LIKE ? OR sf.language = ?)`;
            params.push(`%"${lang}"%`, lang);
        }
        
        sql += ` GROUP BY t.id, t.name, t.languages, t.episodes_available ORDER BY subtitle_count DESC LIMIT ?`;
        params.push(parseInt(limit));
        
        const result = await client.execute({ sql, args: params });
        
        const results = result.rows.map(row => ({
            id: row.id,
            name: row.name,
            subtitle_count: row.subtitle_count,
            languages: JSON.parse(row.languages || '[]'),
            episodes: JSON.parse(row.episodes_available || '[]'),
            episode_match: episode && JSON.parse(row.episodes_available || '[]').includes(episode)
        }));

        res.json({ results, total: results.length, episode_requested: episode });
    } catch (e) {
        console.error('TURSO search error:', e);
        res.status(500).json({ error: 'Search failed', details: e.message });
    }
}

export const config = { maxDuration: 60 };
