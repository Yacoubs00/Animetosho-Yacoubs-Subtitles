import requests
import json

class AnimeToshoAPI:
    def __init__(self, base_url="https://your-api.vercel.app"):
        self.base_url = base_url
    
    def search(self, query, language=None, limit=50):
        """Search anime subtitles via API"""
        params = {
            'q': query,
            'limit': limit
        }
        if language:
            params['lang'] = language
        
        try:
            response = requests.get(f"{self.base_url}/api/search", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            return {'error': str(e), 'results': []}
    
    def get_languages(self):
        """Get available subtitle languages"""
        try:
            response = requests.get(f"{self.base_url}/api/languages", timeout=5)
            response.raise_for_status()
            return response.json()['languages']
        
        except requests.RequestException:
            return ['eng', 'spa', 'fre', 'ger', 'ita', 'rus']  # Fallback
    
    def download_subtitle(self, download_url):
        """Download subtitle file"""
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            return response.content
        
        except requests.RequestException as e:
            raise Exception(f"Download failed: {e}")

# Usage in Kodi addon
def search_anime_subtitles(anime_name, episode=None):
    api = AnimeToshoAPI()
    
    # Build search query
    query = anime_name
    if episode:
        query += f" {episode}"
    
    # Search via API (no local processing)
    results = api.search(query, language='eng')
    
    # Return subtitle URLs
    return [result['download_url'] for result in results['results']]
