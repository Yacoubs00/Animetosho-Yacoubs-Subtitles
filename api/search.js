let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 3600000;

export default async function handler(req, res) {
  try {
    if (!DB || Date.now() - lastFetch > CACHE_DURATION) {
      const blobUrl = process.env.DATABASE_BLOB_URL;
      const response = await fetch(blobUrl);
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
        
        // Create download links for ALL subtitle files
        const downloadLinks = [];
        const allLanguages = new Set();
        
        torrent.subtitle_files.forEach(subFile => {
          subFile.afids.forEach((afid, index) => {
            const language = subFile.languages[index] || subFile.languages[0] || 'eng';
            const afidHex = afid.toString(16).padStart(8, '0');
            
            downloadLinks.push({
              language: language,
              url: `https://animetosho.org/storage/attach/${afidHex}/subtitle.ass.xz`,
              filename: subFile.filename
            });
            
            allLanguages.add(language);
          });
        });
        
        results.push({
          name: torrent.name,
          languages: Array.from(allLanguages),
          download_links: downloadLinks, // ✅ All individual links
          subtitle_count: downloadLinks.length
        });
      }
    }

    res.json({ results, total: results.length });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
