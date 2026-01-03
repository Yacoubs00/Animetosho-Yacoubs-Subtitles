class AnimeSearch {
    constructor(database) {
        this.database = database;
    }

    search(query, language = '', limit = 50) {
        const startTime = performance.now();
        const results = [];
        const queryLower = query.toLowerCase().trim();
        
        if (!queryLower) return { results: [], searchTime: 0, total: 0 };

        // Get candidate torrent IDs
        let candidates;
        if (language && this.database.languages[language]) {
            candidates = new Set(this.database.languages[language]);
        } else {
            candidates = new Set(Object.keys(this.database.torrents));
        }

        // Search through candidates
        for (const torrentId of candidates) {
            const torrent = this.database.torrents[torrentId];
            if (!torrent) continue;

            if (torrent.name.toLowerCase().includes(queryLower)) {
                // Extract episode info
                const episode = this.extractEpisode(torrent.name);
                const quality = this.extractQuality(torrent.name);
                const group = this.extractGroup(torrent.name);

                // Get download URLs
                const downloadUrls = torrent.subtitle_files.map(file => ({
                    language: file.languages[0] || 'eng',
                    url: this.constructDownloadUrl(file.afids[0]),
                    afid: file.afids[0],
                    filename: file.filename
                }));

                results.push({
                    torrent_id: parseInt(torrentId),
                    name: torrent.name,
                    languages: torrent.languages,
                    subtitle_files: torrent.subtitle_files.length,
                    download_urls: downloadUrls,
                    episode: episode,
                    quality: quality,
                    group: group
                });

                if (results.length >= limit) break;
            }
        }

        const searchTime = performance.now() - startTime;
        
        return {
            results: results,
            total: results.length,
            search_time_ms: searchTime,
            language_filter: language
        };
    }

    constructDownloadUrl(afid) {
        const afidHex = afid.toString(16).padStart(8, '0');
        return `https://animetosho.org/storage/attach/${afidHex}/subtitle.ass.xz`;
    }

    extractEpisode(name) {
        const episodeMatch = name.match(/(?:episode|ep|e)[\s\-_]*(\d+)/i) || 
                           name.match(/\s(\d{2,3})\s/) ||
                           name.match(/\-\s*(\d+)\s*\[/);
        return episodeMatch ? episodeMatch[1] : null;
    }

    extractQuality(name) {
        const qualityMatch = name.match(/(480p|720p|1080p|2160p|4K)/i);
        return qualityMatch ? qualityMatch[1] : null;
    }

    extractGroup(name) {
        const groupMatch = name.match(/^\[([^\]]+)\]/);
        return groupMatch ? groupMatch[1] : null;
    }
}
