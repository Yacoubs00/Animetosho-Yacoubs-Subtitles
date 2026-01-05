# episode_detector.py - Episode range detection for AnimeTosho API
import re
from typing import Optional

class EpisodeDetector:
    def __init__(self):
        # Series-specific mappings from AnimeTosho database analysis
        self.series_data = {
            'zankyou no terror': {'episodes': 11, 'vol1': '01-06', 'vol2': '07-11'},
            'terror in resonance': {'episodes': 11, 'vol1': '01-06', 'vol2': '07-11'},
            'cowboy bebop': {'episodes': 26, 'movie_files': 1},
            'death note': {'episodes': 37},
            'attack on titan': {'s1': 25, 's2': 12, 's3': 22},
            'shingeki no kyojin': {'s1': 25, 's2': 12, 's3': 22},
        }

    def detect_episode_range(self, title: str, file_count: int = 0, total_size: int = 0) -> Optional[str]:
        """Detect episode range from title and torrent metadata"""
        title_lower = title.lower()
        
        # 1. Explicit ranges in title
        explicit = self._detect_explicit_range(title)
        if explicit:
            return explicit
        
        # 2. Series-specific detection
        series_range = self._detect_series_specific(title_lower, file_count)
        if series_range:
            return series_range
        
        # 3. Volume detection
        volume_range = self._detect_volume(title_lower)
        if volume_range:
            return volume_range
        
        # 4. Pack detection from file count
        if file_count > 1:
            return self._detect_from_file_count(title_lower, file_count)
        
        return None

    def _detect_explicit_range(self, title: str) -> Optional[str]:
        patterns = [
            r'(?:episodes?\s+)?(\d{1,2})-(\d{1,2})',
            r'(?:eps?\s+)?(\d{1,2})\s*-\s*(\d{1,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, title.lower())
            if match:
                start, end = match.groups()
                return f"{int(start):02d}-{int(end):02d}"
        return None

    def _detect_series_specific(self, title_lower: str, file_count: int) -> Optional[str]:
        for series, data in self.series_data.items():
            if series in title_lower:
                episodes = data.get('episodes', 0)
                
                # Complete series detection
                if file_count >= episodes or any(word in title_lower for word in ['complete', 'batch', 'season']):
                    if series == 'cowboy bebop' and file_count == 27:
                        return f"01-{episodes:02d} + Movie"
                    return f"01-{episodes:02d}"
                
                # Volume detection for Terror in Resonance
                if series in ['zankyou no terror', 'terror in resonance']:
                    if file_count == 6:
                        return data['vol1']
                    elif file_count == 5:
                        return data['vol2']
        
        return None

    def _detect_volume(self, title_lower: str) -> Optional[str]:
        # Terror in Resonance specific
        if 'terror' in title_lower or 'zankyou' in title_lower:
            if 'vol.01' in title_lower or 'volume 1' in title_lower:
                return '01-06'
            elif 'vol.02' in title_lower or 'volume 2' in title_lower:
                return '07-11'
        
        # Generic volumes
        volume_patterns = {
            'vol.01': '01-06', 'volume 1': '01-06',
            'vol.02': '07-12', 'volume 2': '07-12',
            'vol.03': '13-18', 'volume 3': '13-18',
        }
        
        for pattern, episodes in volume_patterns.items():
            if pattern in title_lower:
                return episodes
        
        return None

    def _detect_from_file_count(self, title_lower: str, file_count: int) -> Optional[str]:
        # Common episode counts
        if file_count in [11, 12, 13, 24, 25, 26]:
            return f"01-{file_count:02d}"
        elif file_count > 20:
            return f"01-{file_count-1:02d} + Extras"
        elif file_count >= 5:
            return f"01-{file_count:02d}"
        
        return None

    def format_display_title(self, title: str, episode_range: Optional[str], size_formatted: str = "") -> str:
        """Format title with episode range"""
        if not episode_range:
            return f"{title[:70]} ({size_formatted})" if size_formatted else title[:70]
        
        if "+" in episode_range:  # Has extras/movie
            return f"{title[:40]} ({episode_range}) ({size_formatted})"
        else:
            return f"{title[:45]} (Eps {episode_range}) ({size_formatted})"
