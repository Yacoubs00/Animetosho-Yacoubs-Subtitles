let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 0; // Force refresh every time

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export default async function handler(req, res) {
  try {
    // Always fetch fresh database (remove the if condition)
    const blobUrl = process.env.DATABASE_BLOB_URL;
    console.log('Fetching from:', blobUrl); // Debug log
    
    const response = await fetch(blobUrl);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    DB = await response.json();
    lastFetch = Date.now();

    const { q, lang, limit = 50 } = req.query;
    if (!q) return res.status(400).json({ error: 'Query required' });

    const results = [];
    const query = q.toLowerCase();
    const candidates = lang && DB.languages[lang] ? DB.languages[lang] : Object.keys(DB.torrents);

    for (const id of candidates) {
      if (results.length >= limit) break;
      const torrent = DB.torrents[id];
      if (torrent && torrent.name.toLowerCase().includes(query)) {
        
        const downloadLinks = [];
        const allLanguages = new Set();
        
        torrent.subtitle_files.forEach(subFile => {
          if (subFile.is_pack) {
            const packName = subFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
            const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000; // Default 2MB
            
            downloadLinks.push({
              language: 'ALL',
              url: `https://animetosho.org/storage/attachpk/${id}/${packName}_attachments.7z`,
              filename: subFile.filename,
              is_pack: true,
              pack_languages: subFile.languages,
              size: packSize,
              size_formatted: formatSize(packSize)
            });
            
            subFile.languages.forEach(lang => allLanguages.add(lang));
          } else {
            subFile.afids.forEach((afid, index) => {
              const language = subFile.languages[index] || subFile.languages[0] || 'eng';
              const afidHex = afid.toString(16).padStart(8, '0');
              const fileSize = subFile.sizes && subFile.sizes[index] ? subFile.sizes[index] : 50000; // Default 50KB
              
              downloadLinks.push({
                language: language,
                url: `https://animetosho.org/storage/attach/${afidHex}/subtitle.ass.xz`,
                filename: subFile.filename,
                is_pack: false,
                size: fileSize,
                size_formatted: formatSize(fileSize)
              });
              
              allLanguages.add(language);
            });
          }
        });
        
        results.push({
          name: torrent.name,
          languages: Array.from(allLanguages),
          download_links: downloadLinks,
          subtitle_count: downloadLinks.length,
          torrent_id: parseInt(id)
        });
      }
    }

    res.json({ results, total: results.length });
  } catch (error) {
    res.status(500).json({ error: error.message, debug_url: process.env.DATABASE_BLOB_URL });
  }
}
