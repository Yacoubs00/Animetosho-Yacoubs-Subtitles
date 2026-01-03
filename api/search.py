import { readFileSync } from 'fs';
import { join } from 'path';

let DATABASE = null;

function loadDatabase() {
  if (!DATABASE) {
    const dbPath = join(process.cwd(), 'data', 'subtitles.json');
    DATABASE = JSON.parse(readFileSync(dbPath, 'utf8'));
  }
  return DATABASE;
}

export default function handler(req, res) {
  const { q: query, lang: language, limit = 50 } = req.query;
  
  if (!query) {
    return res.status(400).json({ error: 'Query required' });
  }

  const db = loadDatabase();
  const results = [];
  const queryLower = query.toLowerCase();
  
  // Filter torrents
  const candidates = language && db.languages[language] 
    ? new Set(db.languages[language])
    : Object.keys(db.torrents);

  for (const torrentId of candidates) {
    if (results.length >= limit) break;
    
    const torrent = db.torrents[torrentId];
    if (torrent.name.toLowerCase().includes(queryLower)) {
      const firstFile = torrent.subtitle_files[0];
      const afidHex = firstFile.afids[0].toString(16).padStart(8, '0');
      
      results.push({
        torrent_id: torrentId,
        name: torrent.name,
        languages: torrent.languages,
        download_url: `https://animetosho.org/storage/attach/${afidHex}/subtitle.ass.xz`
      });
    }
  }

  res.json({
    results,
    total: results.length,
    query
  });
}
