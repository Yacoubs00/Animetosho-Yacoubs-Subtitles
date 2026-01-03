let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 3600000;

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  
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
        
        torrent.subtitle_files.forEach(subFile => {
          if (subFile.is_pack) {
            // Pack download - FIXED URL
            const cleanName = torrent.name.replace(/[^a-zA-Z0-9\-_\s]/g, '').replace(/\s+/g, '_');
            const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000; // Default 2MB
            
            results.push({
              title: `${torrent.name} [PACK - ALL LANGUAGES]`,
              subtitle_url: `https://storage.animetosho.org/attachpk/${id}/${cleanName}_attachments.7z`,
              languages: subFile.languages,
              is_pack: true,
              size: packSize,
              size_formatted: formatSize(packSize),
              torrent_id: parseInt(id)
            });
          } else {
            // Individual files
            subFile.afids.forEach((afid, index) => {
              const language = subFile.languages[index] || subFile.languages[0] || 'eng';
              const afidHex = afid.toString(16).padStart(8, '0');
              const fileSize = subFile.sizes && subFile.sizes[index] ? subFile.sizes[index] : 50000; // Default 50KB
              
              results.push({
                title: `${torrent.name} [${language.toUpperCase()}]`,
                subtitle_url: `https://storage.animetosho.org/attach/${afidHex}/file.xz`,
                languages: [language],
                is_pack: false,
                size: fileSize,
                size_formatted: formatSize(fileSize),
                torrent_id: parseInt(id)
              });
            });
          }
        });
      }
    }

    res.json({ success: true, data: results, count: results.length });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
}
