// api/episode_detector.js - JavaScript version of episode detector
export class EpisodeDetector {
    constructor() {
        // Series-specific mappings from AnimeTosho database analysis
        this.seriesData = {
            'zankyou no terror': { episodes: 11, vol1: '01-06', vol2: '07-11' },
            'terror in resonance': { episodes: 11, vol1: '01-06', vol2: '07-11' },
            'cowboy bebop': { episodes: 26, movieFiles: 1 },
            'death note': { episodes: 37 },
            'attack on titan': { s1: 25, s2: 12, s3: 22 },
            'shingeki no kyojin': { s1: 25, s2: 12, s3: 22 }
        };
    }

    detectEpisodeRange(title, fileCount = 0, totalSize = 0) {
        const titleLower = title.toLowerCase();
        
        // 1. Explicit ranges in title
        const explicit = this._detectExplicitRange(title);
        if (explicit) return explicit;
        
        // 2. Series-specific detection
        const seriesRange = this._detectSeriesSpecific(titleLower, fileCount);
        if (seriesRange) return seriesRange;
        
        // 3. Volume detection
        const volumeRange = this._detectVolume(titleLower);
        if (volumeRange) return volumeRange;
        
        // 4. Pack detection from file count
        if (fileCount > 1) {
            return this._detectFromFileCount(titleLower, fileCount);
        }
        
        return null;
    }

    _detectExplicitRange(title) {
        const patterns = [
            /(?:episodes?\s+)?(\d{1,2})-(\d{1,2})/i,
            /(?:eps?\s+)?(\d{1,2})\s*-\s*(\d{1,2})/i
        ];
        
        for (const pattern of patterns) {
            const match = title.match(pattern);
            if (match) {
                const start = parseInt(match[1]);
                const end = parseInt(match[2]);
                return `${start.toString().padStart(2, '0')}-${end.toString().padStart(2, '0')}`;
            }
        }
        return null;
    }

    _detectSeriesSpecific(titleLower, fileCount) {
        for (const [series, data] of Object.entries(this.seriesData)) {
            if (titleLower.includes(series)) {
                const episodes = data.episodes || 0;
                
                // Complete series detection
                const completeWords = ['complete', 'batch', 'season'];
                if (fileCount >= episodes || completeWords.some(word => titleLower.includes(word))) {
                    if (series === 'cowboy bebop' && fileCount === 27) {
                        return `01-${episodes.toString().padStart(2, '0')} + Movie`;
                    }
                    return `01-${episodes.toString().padStart(2, '0')}`;
                }
                
                // Volume detection for Terror in Resonance
                if (series === 'zankyou no terror' || series === 'terror in resonance') {
                    if (fileCount === 6) return data.vol1;
                    if (fileCount === 5) return data.vol2;
                }
            }
        }
        return null;
    }

    _detectVolume(titleLower) {
        // Terror in Resonance specific
        if (titleLower.includes('terror') || titleLower.includes('zankyou')) {
            if (titleLower.includes('vol.01') || titleLower.includes('volume 1')) {
                return '01-06';
            }
            if (titleLower.includes('vol.02') || titleLower.includes('volume 2')) {
                return '07-11';
            }
        }
        
        // Generic volumes
        const volumePatterns = {
            'vol.01': '01-06', 'volume 1': '01-06',
            'vol.02': '07-12', 'volume 2': '07-12',
            'vol.03': '13-18', 'volume 3': '13-18'
        };
        
        for (const [pattern, episodes] of Object.entries(volumePatterns)) {
            if (titleLower.includes(pattern)) {
                return episodes;
            }
        }
        
        return null;
    }

    _detectFromFileCount(titleLower, fileCount) {
        // Common episode counts
        if ([11, 12, 13, 24, 25, 26].includes(fileCount)) {
            return `01-${fileCount.toString().padStart(2, '0')}`;
        }
        if (fileCount > 20) {
            return `01-${(fileCount - 1).toString().padStart(2, '0')} + Extras`;
        }
        if (fileCount >= 5) {
            return `01-${fileCount.toString().padStart(2, '0')}`;
        }
        
        return null;
    }

    formatDisplayTitle(title, episodeRange, sizeFormatted = '') {
        if (!episodeRange) {
            return sizeFormatted ? `${title.slice(0, 70)} (${sizeFormatted})` : title.slice(0, 70);
        }
        
        if (episodeRange.includes('+')) {
            return `${title.slice(0, 40)} (${episodeRange}) (${sizeFormatted})`;
        } else if (episodeRange === 'Complete') {
            return `${title.slice(0, 55)} (Complete) (${sizeFormatted})`;
        } else {
            return `${title.slice(0, 45)} (Eps ${episodeRange}) (${sizeFormatted})`;
        }
    }
}
