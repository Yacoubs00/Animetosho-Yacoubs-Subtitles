import { list } from '@vercel/blob';

let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 3600000; // 1 hour

export default async function handler(req, res) {
  try {
    // Refresh database cache every hour
    if (!DB || Date.now() - lastFetch > CACHE_DURATION) {
      const response = await fetch('https://your-blob-url/subtitles.json');
      DB = await response.json();
      lastFetch = Date.now();
    }

    const { q, lang, limit = 50 } = req.query;
    if (!q) return res.status(400).json({ error: 'Query required' });

    const results = [];
    const query = q.toLowerCase();
    const candidates = lang && DB.languages[lang] ? DB.languages[lang] : Object.keys(DB.torrents);

    for (const id of candidates) {
      if (results.length >= limit) break;
      const torrent = DB.torrents[id];
      if (torrent && torrent.name.toLowerCase().includes(query)) {
        const afid = torrent.subtitle_files[0].afids[0];
        results.push({
          name: torrent.name,
          languages: torrent.languages,
          download_url: `https://animetosho.org/storage/attach/${afid.toString(16).padStart(8, '0')}/subtitle.ass.xz`
        });
      }
    }

    res.json({ results, total: results.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

