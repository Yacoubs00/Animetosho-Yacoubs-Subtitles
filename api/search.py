from flask import Flask, request, jsonify
import pickle
import gzip
import os
from functools import lru_cache

app = Flask(__name__)

# Load database once at startup
DATABASE = None

def load_database():
    global DATABASE
    if DATABASE is None:
        with gzip.open('data/optimized_db.pkl.gz', 'rb') as f:
            DATABASE = pickle.load(f)
    return DATABASE

@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip()
    language = request.args.get('lang', '')
    limit = int(request.args.get('limit', 50))
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    db = load_database()
    results = perform_search(db, query, language, limit)
    
    return jsonify(results)

@app.route('/api/languages')
def languages():
    db = load_database()
    langs = sorted(db['languages'].keys())
    return jsonify({'languages': langs})

@app.route('/api/stats')
def stats():
    db = load_database()
    return jsonify(db['stats'])

@lru_cache(maxsize=1000)
def perform_search(db_tuple, query, language, limit):
    # Convert back from tuple for caching
    db = db_tuple
    
    start_time = time.time()
    results = []
    query_lower = query.lower()
    
    # Filter by language first
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
            # Get first download URL
            first_file = torrent['subtitle_files'][0]
            first_afid = first_file['afids'][0]
            afid_hex = f"{first_afid:08x}"
            download_url = f"https://animetosho.org/storage/attach/{afid_hex}/subtitle.ass.xz"
            
            results.append({
                'torrent_id': torrent_id,
                'name': torrent['name'],
                'languages': torrent['languages'],
                'subtitle_files': len(torrent['subtitle_files']),
                'download_url': download_url,
                'afid': first_afid
            })
    
    search_time = (time.time() - start_time) * 1000
    
    return {
        'results': results,
        'total': len(results),
        'search_time_ms': search_time,
        'query': query,
        'language_filter': language
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
