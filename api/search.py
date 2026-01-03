from flask import Flask, request, jsonify
import json
import gzip
import os
import time

app = Flask(__name__)

# Global database cache
_database_cache = None
_cache_time = 0
CACHE_DURATION = 3600  # 1 hour

def get_database():
    global _database_cache, _cache_time
    
    current_time = time.time()
    if _database_cache is None or (current_time - _cache_time) > CACHE_DURATION:
        # Load from data directory
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'optimized_db.json.gz')
        
        with gzip.open(db_path, 'rt', encoding='utf-8') as f:
            _database_cache = json.load(f)
        
        _cache_time = current_time
    
    return _database_cache

def handler(request):
    """Vercel serverless function handler"""
    
    if request.method == 'GET':
        query = request.args.get('q', '').strip()
        language = request.args.get('lang', '')
        limit = int(request.args.get('limit', 50))
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        # Load database
        db = get_database()
        
        # Perform search
        start_time = time.time()
        results = []
        query_lower = query.lower()
        
        # Filter candidates
        if language and language in db['languages']:
            candidates = set(db['languages'][language])
        else:
            candidates = set(db['torrents'].keys())
        
        # Search
        for torrent_id in candidates:
            if len(results) >= limit:
                break
                
            torrent = db['torrents'][torrent_id]
            if query_lower in torrent['name'].lower():
                # Get download URL
                first_file = torrent['subtitle_files'][0]
                first_afid = first_file['afids'][0]
                afid_hex = f"{first_afid:08x}"
                download_url = f"https://animetosho.org/storage/attach/{afid_hex}/subtitle.ass.xz"
                
                results.append({
                    'torrent_id': int(torrent_id),
                    'name': torrent['name'],
                    'languages': torrent['languages'],
                    'subtitle_files': len(torrent['subtitle_files']),
                    'download_url': download_url
                })
        
        search_time = (time.time() - start_time) * 1000
        
        return jsonify({
            'results': results,
            'total': len(results),
            'search_time_ms': search_time,
            'query': query,
            'language_filter': language
        })
    
    return jsonify({'error': 'Method not allowed'}), 405

# For Vercel
def main(request):
    return handler(request)

