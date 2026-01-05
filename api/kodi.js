// api/kodi.js - Kodi-compatible API endpoint with episode detection
import { EpisodeDetector } from './episode_detector.js';

let DB = null;
let lastFetch = 0;
const CACHE_DURATION = 0; // Force refresh every time

const fixLang = (lang) => lang === 'und' || lang === 'enm' ? 'eng' : lang;

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// Initialize episode detector
const episodeDetector = new EpisodeDetector();

export default async function handler(req, res) {
    try {
        // Always fetch fresh database
        const blobUrl = process.env.DATABASE_BLOB_URL;
        console.log('Fetching from:', blobUrl);
        
        const response = await fetch(blobUrl);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        DB = await response.json();
        lastFetch = Date.now();
        
        const { q, limit = 200 } = req.query;
        if (!q) return res.status(400).json({ error: 'Query required' });
        
        const results = [];
        const query = q.toLowerCase();
        
        // Search through all torrents
        for (const [id, torrent] of Object.entries(DB.torrents)) {
            if (results.length >= limit) break;
            
            if (torrent && torrent.name.toLowerCase().includes(query)) {
                const downloadLinks = [];
                const allLanguages = new Set();
                
                // Detect episode range using torrent metadata
                const episodeRange = episodeDetector.detectEpisodeRange(
                    torrent.name,
                    torrent.torrent_files || 0,
                    torrent.total_size || 0
                );
                
                torrent.subtitle_files.forEach(subFile => {
                    if (subFile.is_pack) {
                        const packName = subFile.pack_name || torrent.name.replace(/[^a-zA-Z0-9.-_\s]/g, '').replace(/\s+/g, '.');
                        const packSize = subFile.sizes && subFile.sizes[0] ? subFile.sizes[0] : 2000000;
                        const sizeFormatted = formatSize(packSize);
                        
                        // Enhanced display title with episode range
                        const displayTitle = episodeDetector.formatDisplayTitle(
                            torrent.name, 
                            episodeRange, 
                            sizeFormatted
                        );
                        
                        downloadLinks.push({
                            language: 'ALL',
                            url: `https://storage.animetosho.org/attachpk/${id}/${packName}_attachments.7z`,
                            filename: subFile.filename,
                            is_pack: true,
                            pack_languages: subFile.languages.map(fixLang),
                            size: packSize,
                            size_formatted: sizeFormatted,
                            episode_range: episodeRange,
                            display_title: displayTitle
                        });
                        
                        subFile.languages.forEach(lang => allLanguages.add(fixLang(lang)));
                    } else {
                        subFile.afids.forEach((afid, index) => {
                            const language = fixLang(subFile.languages[index] || subFile.languages[0] || 'eng');
                            const afidHex = afid.toString(16).padStart(8, '0');
                            const fileSize = subFile.sizes && subFile.sizes[index] ? subFile.sizes[index] : 50000;
                            
                            downloadLinks.push({
                                language: language,
                                url: `https://storage.animetosho.org/attach/${afidHex}/file.xz`,
                                filename: subFile.filename,
                                is_pack: false,
                                size: fileSize,
                                size_formatted: formatSize(fileSize)
                            });
                            
                            allLanguages.add(language);
                        });
                    }
                });
                
                // Format for Kodi compatibility
                const kodiResult = {
                    title: torrent.name,
                    subtitle_url: downloadLinks[0]?.url || '',
                    languages: Array.from(allLanguages),
                    is_pack: downloadLinks.some(link => link.is_pack),
                    size: downloadLinks[0]?.size || 50000,
                    size_formatted: downloadLinks[0]?.size_formatted || '50KB',
                    torrent_id: parseInt(id),
                    // Enhanced fields
                    episode_range: episodeRange,
                    display_title: downloadLinks.find(link => link.display_title)?.display_title || torrent.name,
                    torrent_files: torrent.torrent_files || 0,
                    total_size: torrent.total_size || 0
                };
                
                results.push(kodiResult);
            }
        }
        
        res.json({
            success: true,
            data: results,
            count: results.length
        });
        
    } catch (error) {
        console.error('Kodi API Error:', error);
        res.status(500).json({ 
            success: false,
            error: error.message, 
            debug_url: process.env.DATABASE_BLOB_URL 
        });
    }
}# Add this to the top of your api/kodi.py file:
from .episode_detector import EpisodeDetector

# Initialize detector globally
episode_detector = EpisodeDetector()

# In your main API handler function, add this processing:
def process_results_with_episode_detection(raw_results):
    """Process results and add episode range information"""
    enhanced_results = []
    
    for result in raw_results:
        title = result.get('title', '')
        file_count = result.get('torrent_files', 0)  # From your database query
        total_size = result.get('total_size', 0)     # From your database query
        
        # Detect episode range
        episode_range = episode_detector.detect_episode_range(title, file_count, total_size)
        
        # Add enhanced fields
        result['episode_range'] = episode_range
        result['display_title'] = episode_detector.format_display_title(
            title, episode_range, result.get('size_formatted', '')
        )
        
        enhanced_results.append(result)
    
    return enhanced_results

# In your main API handler, call this function:
# raw_results = your_existing_database_query(query, limit)
# enhanced_results = process_results_with_episode_detection(raw_results)
# return {'success': True, 'data': enhanced_results, 'count': len(enhanced_results)}
# Add this to the top of your api/kodi.py file:
from .episode_detector import EpisodeDetector

# Initialize detector globally
episode_detector = EpisodeDetector()

# In your main API handler function, add this processing:
def process_results_with_episode_detection(raw_results):
    """Process results and add episode range information"""
    enhanced_results = []
    
    for result in raw_results:
        title = result.get('title', '')
        file_count = result.get('torrent_files', 0)  # From your database query
        total_size = result.get('total_size', 0)     # From your database query
        
        # Detect episode range
        episode_range = episode_detector.detect_episode_range(title, file_count, total_size)
        
        # Add enhanced fields
        result['episode_range'] = episode_range
        result['display_title'] = episode_detector.format_display_title(
            title, episode_range, result.get('size_formatted', '')
        )
        
        enhanced_results.append(result)
    
    return enhanced_results

# In your main API handler, call this function:
# raw_results = your_existing_database_query(query, limit)
# enhanced_results = process_results_with_episode_detection(raw_results)
# return {'success': True, 'data': enhanced_results, 'count': len(enhanced_results)}
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
