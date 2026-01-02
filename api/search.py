from flask import Flask, request, jsonify
import pickle
import gzip
import requests  # To fetch DB from GitHub

app = Flask(__name__)

DB_URL = 'https://raw.githubusercontent.com/Yacoubs00/animetosho-attachments-viewer/main/data/optimized_db.pkl.gz'
db = None

def load_db():
    global db
    if not db:
        response = requests.get(DB_URL)
        response.raise_for_status()
        with gzip.GzipFile(fileobj=response.content) as f:
            db = pickle.load(f)
    return db

@app.before_first_request
def init_db():
    load_db()

@app.route('/api/search')
def search():
    q = request.args.get('q', '').lower()
    lang = request.args.get('lang', '')
    limit = int(request.args.get('limit', 50))
    
    results = []
    for tid, data in db['torrents'].items():
        if q and not (tid in q or q in data['name'].lower()): continue
        if lang and lang not in data['languages']: continue
        results.append({
            'torrent_id': tid,
            'name': data['name'],
            'languages': data['languages'],
            'subtitle_files': data['subtitle_files']
        })
    return jsonify({'results': results[:limit], 'total': len(results)})

@app.route('/api/languages')
def languages():
    return jsonify(sorted(db['languages'].keys()))

@app.route('/api/stats')
def stats():
    return jsonify(db['stats'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
