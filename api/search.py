// api/search.js
import fs from 'fs';
import { gunzipSync } from 'zlib';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let db = null;

function loadDB() {
  if (db) return db;
  const filePath = path.join(__dirname, '..', 'data', 'optimized_db.json.gz');
  const compressed = fs.readFileSync(filePath);
  const decompressed = gunzipSync(compressed);
  db = JSON.parse(decompressed.toString('utf-8'));
  return db;
}

export default function handler(req, res) {
  try {
    const database = loadDB();

    const { q = '', lang = '', limit = '50' } = req.query;
    const query = q.toLowerCase().trim();
    const selectedLang = lang.toLowerCase();
    const maxResults = Math.min(parseInt(limit) || 50, 200); // Safety cap

    const results = [];

    for (const [torrentId, info] of Object.entries(database.torrents)) {
      // Search in torrent name or ID
      const matchesQuery = !query || 
        info.name.toLowerCase().includes(query) || 
        torrentId.includes(query);

      // Language filter
      const matchesLang = !selectedLang || info.languages.includes(selectedLang);

      if (matchesQuery && matchesLang) {
        results.push({
          torrent_id: torrentId,
          name: info.name,
          languages: info.languages,
          subtitle_count: info.subtitle_files.reduce((sum, sf) => sum + sf.subs.length, 0),
          downloads: info.subtitle_files.flatMap(sf => 
            sf.subs.map(sub => ({
              lang: sub.lang.toUpperCase(),
              url: sub.url,
              filename: sf.filename || `subtitle_${sub.lang}.ass`
            }))
          ),
          pack_url: `https://animetosho.org/storage/torattachpk/${torrentId}/${encodeURIComponent(info.name)}_attachments.7z`
        });

        if (results.length >= maxResults) break;
      }
    }

    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=86400');
    res.setHeader('Access-Control-Allow-Origin', '*'); // Crucial for Kodi addons
    res.status(200).json({
      success: true,
      results,
      total: results.length,
      cached: !!db,
      last_updated: database.stats.last_updated
    });

  } catch (error) {
    console.error(error);
    res.status(500).json({
      success: false,
      error: 'Server error - database load failed'
    });
  }
}

export const config = {
  api: {
    bodyParser: false
  }
};
