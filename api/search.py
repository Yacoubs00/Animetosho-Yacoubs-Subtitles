import fs from 'fs';
import { gunzipSync } from 'zlib';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let db = null;

function loadDB() {
  if (db) return db;
  const compressedPath = path.join(__dirname, '..', 'data', 'optimized_db.json.gz');
  const compressed = fs.readFileSync(compressedPath);
  const decompressed = gunzipSync(compressed);
  db = JSON.parse(decompressed.toString('utf-8'));
  return db;
}

export default function handler(req, res) {
  try {
    const db = loadDB();

    const { q = '', lang = '', limit = '50' } = req.query;
    const query = q.toLowerCase();
    const limitNum = parseInt(limit, 10) || 50;

    const results = [];

    for (const [tid, info] of Object.entries(db.torrents)) {
      const matchesQuery = !query || tid.includes(query) || info.name.toLowerCase().includes(query);
      const matchesLang = !lang || info.languages.includes(lang);

      if (matchesQuery && matchesLang) {
        results.push({
          torrent_id: tid,
          name: info.name,
          languages: info.languages,
          subtitle_files: info.subtitle_files.length,
          download_urls: info.subtitle_files.flatMap(sf => 
            sf.subs.map(s => ({
              lang: s.lang,
              url: s.url,
              afid: s.afid
            }))
          )
        });
        if (results.length >= limitNum) break;
      }
    }

    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=86400');
    res.status(200).json({
      results,
      total: results.length,
      search_time_ms: 0, // Add timing if needed
      last_updated: db.stats.last_updated
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to load or search database' });
  }
}

export const config = {
  api: {
    bodyParser: false // Not needed for GET search
  }
};
