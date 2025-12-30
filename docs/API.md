AnimeTosho Fast Subtitle Search API
This repository provides a client-side search system for extracted subtitles and fonts from AnimeTosho-processed torrents. There is no server-side API. All search functionality runs in the browser using a pre-built optimized database loaded from the repository.
The database is updated daily via GitHub Actions and contains only torrents that have extracted subtitle tracks.
Data Files

data/optimized_db.pkl.gz – The main database file (compressed pickle format, approximately 40–60 MB).
data/metadata.json – Basic statistics and last update timestamp.
data/language_stats.json – Number of torrents that contain subtitles for each language.

Loading the Database in JavaScript
The web interface uses the picklejs library to read the compressed pickle file directly in the browser:
HTML<script src="https://cdn.jsdelivr.net/npm/picklejs@1.0.2/dist/pickle.min.js"></script>

<script>
  async function loadDatabase() {
    const response = await fetch('data/optimized_db.pkl.gz');
    const buffer = await response.arrayBuffer();
    const db = await Pickle.load(buffer);
    return db;
  }
</script>
The loaded object has the following structure (see DATABASE.md for details).
Performing a Search (Client-Side)
All searches are performed in JavaScript after the database is loaded. Example:
JavaScriptasync function search(query, language = '') {
  const db = await loadDatabase();
  const results = [];

  for (const [torrentId, torrent] of Object.entries(db.torrents)) {
    // Match by torrent name or ID
    if (query && 
        !torrent.name.toLowerCase().includes(query.toLowerCase()) &&
        !torrentId.includes(query)) {
      continue;
    }

    // Optional language filter
    if (language && !torrent.languages.includes(language)) {
      continue;
    }

    results.push({
      torrent_id: torrentId,
      name: torrent.name,
      languages: torrent.languages,
      subtitle_files: torrent.subtitle_files
    });
  }

  return results;
}
Generating Download Links
Each subtitle entry contains an _afid value. The direct download URL is constructed as follows:
texthttps://storage.animetosho.org/attach/<8-digit-hex-afid>/file.xz
Example in JavaScript:
JavaScriptfunction getSubtitleUrl(afid) {
  const hex = afid.toString(16).padStart(8, '0');
  return `https://storage.animetosho.org/attach/${hex}/file.xz`;
}
A full attachment pack for the entire torrent (when available) can be accessed via:
texthttps://animetosho.org/storage/torattachpk/<torrent_id>/<url-encoded-name>_attachments.7z
Usage Notes

The database is loaded once per page visit and cached in memory.
Searches are instantaneous because they operate on pre-indexed in-memory data.
No authentication or rate limiting is required.
The system relies entirely on public AnimeTosho exports and links only to files hosted by AnimeTosho.
