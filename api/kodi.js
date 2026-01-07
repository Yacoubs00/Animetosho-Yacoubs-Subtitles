// TURSO Kodi API - Fast SQL queries with pre-built download URLs
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
    const { q: query, lang = 'eng' } = req.query;
    if (!query) return res.status(400).json({ error: 'Query required' });

    try {
        const episode = extractEpisode(query);
        
        // Fast SQL query with JOINs - much faster than loading entire database
        let sql = `
            SELECT 
                sf.filename,
                sf.download_url,
                sf.language,
                sf.size,
                sf.is_pack,
                sf.episode_number,
                t.name as torrent_name
            FROM subtitle_files sf
            JOIN torrents t ON sf.torrent_id = t.id
            WHERE t.name LIKE ?
        `;
        
        const params = [`%${query}%`];
        
        // Add language filter
        if (lang !== 'all') {
            sql += ` AND sf.language = ?`;
            params.push(lang);
        }
        
        // Add episode filter if specified
        if (episode) {
            sql += ` AND (sf.episode_number = ? OR sf.is_pack = 1)`;
            params.push(episode);
        }
        
        sql += ` ORDER BY sf.is_pack DESC, sf.size DESC LIMIT 20`;
        
        const result = await client.execute({ sql, args: params });
        
        const results = result.rows.map(row => ({
            filename: row.filename,
            download: row.download_url,
            language: row.language || lang,
            rating: row.is_pack ? 5 : 4,
            size: row.size,
            torrent_name: row.torrent_name,
            episode_match: episode && row.episode_number === episode
        }));

        res.json(results);
    } catch (e) {
        console.error('TURSO Kodi API error:', e);
        res.status(500).json({ error: 'Query failed', details: e.message });
    }
}

export const config = { maxDuration: 60 };
