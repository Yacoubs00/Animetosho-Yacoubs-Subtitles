// api/episode_detector.js - GENERIC episode detector for ALL anime
export class EpisodeDetector {
    constructor() {
        // No hardcoded series - works for ALL anime
    }

    detectEpisodeRange(title, fileCount = 0, totalSize = 0) {
        const titleLower = title.toLowerCase();
        
        // 1. Explicit ranges in title
        const explicit = this._detectExplicitRange(title);
        if (explicit) return explicit;
        
        // 2. Volume detection (generic)
        const volumeRange = this._detectVolume(titleLower);
        if (volumeRange) return volumeRange;
        
        // 3. Pack detection from file count (generic)
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

    _detectVolume(titleLower) {
        // Generic volume patterns for ALL anime
        const volumePatterns = {
            'vol.01': '01-06', 'volume 1': '01-06',
            'vol.02': '07-12', 'volume 2': '07-12',
            'vol.03': '13-18', 'volume 3': '13-18',
            'vol.04': '19-24', 'volume 4': '19-24'
        };
        
        for (const [pattern, episodes] of Object.entries(volumePatterns)) {
            if (titleLower.includes(pattern)) {
                return episodes;
            }
        }
        
        return null;
    }

    _detectFromFileCount(titleLower, fileCount) {
        // Generic file count detection for ALL anime
        if (fileCount >= 20) {
            return `01-${(fileCount - 1).toString().padStart(2, '0')} + Extras`;
        }
        if (fileCount >= 10) {
            return `01-${fileCount.toString().padStart(2, '0')}`;
        }
        if (fileCount >= 5) {
            return `01-${fileCount.toString().padStart(2, '0')}`;
        }
        
        // Pack/batch indicators
        if (titleLower.includes('complete') || titleLower.includes('batch') || titleLower.includes('season')) {
            return 'Complete';
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
