import { readFileSync } from 'fs';
import { join } from 'path';

let DB = null;

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  
  if (!DB) {
    DB = JSON.parse(readFileSync(join(process.cwd(), 'data/subtitles.json'), 'utf8'));
  }
  
  const { q, lang, limit = 50 } = req.query;
  if (!q) return res.status(400).json({ error: 'Query required' });

  const results = [];
  const query = q.toLowerCase();
  const candidates = lang && DB.languages[lang] ? DB.languages[lang] : Object.keys(DB.torrents);

  for (const id of candidates) {
    if (results.length >= limit) break;
    const torrent = DB.torrents[id];
    if (torrent.name.toLowerCase().includes(query)) {
      const afid = torrent.subtitle_files[0].afids[0];
      results.push({
        title: torrent.name,
        subtitle_url: `https://animetosho.org/storage/attach/${afid.toString(16).padStart(8, '0')}/subtitle.ass.xz`,
        languages: torrent.languages
      });
    }
  }

  res.json({ success: true, data: results });
}

