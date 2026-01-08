from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            from libsql_client import create_client_sync
            
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            name = params.get('name', [''])[0].strip()
            episode = params.get('episode', [''])[0].strip()
            language = params.get('language', [''])[0].strip()
            
            if not name:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing required parameter: name'}).encode())
                return
            
            client = create_client_sync(
                url=os.getenv('TURSO_DATABASE_URL').replace('libsql://', 'https://'),
                auth_token=os.getenv('TURSO_AUTH_TOKEN')
            )
            
            results = []
            
            if episode:
                ep_num = int(episode)
                query = '''
                    SELECT DISTINCT t.id, t.name, t.languages, t.episodes_available, t.total_size
                    FROM torrents t
                    JOIN subtitle_files sf ON t.id = sf.torrent_id
                    WHERE t.name LIKE ? AND (sf.episode_number = ? OR sf.is_pack = 1)
                    LIMIT 50
                '''
                result = client.execute(query, (f'%{name}%', ep_num))
                
                for t in result.rows:
                    torrent_id, torrent_name, langs, eps_available, total_size = t
                    eps_list = json.loads(eps_available) if eps_available else []
                    has_episode = ep_num in eps_list
                    
                    subs_query = '''SELECT filename, language, size, episode_number, is_pack, download_url
                        FROM subtitle_files WHERE torrent_id = ? AND (episode_number = ? OR is_pack = 1)'''
                    subs_result = client.execute(subs_query, (torrent_id, ep_num))
                    
                    subtitle_files = [{
                        'filename': s[0], 'language': s[1], 'size': s[2],
                        'episode': s[3], 'is_pack': bool(s[4]), 'download_url': s[5]
                    } for s in subs_result.rows]
                    
                    if subtitle_files:
                        results.append({
                            'torrent_id': torrent_id, 'name': torrent_name,
                            'languages': json.loads(langs) if langs else [],
                            'episodes_available': eps_list, 'has_episode': has_episode,
                            'total_size': total_size, 'subtitle_files': subtitle_files
                        })
            else:
                query = 'SELECT id, name, languages, episodes_available, total_size FROM torrents WHERE name LIKE ? LIMIT 50'
                result = client.execute(query, (f'%{name}%',))
                
                for t in result.rows:
                    results.append({
                        'torrent_id': t[0], 'name': t[1],
                        'languages': json.loads(t[2]) if t[2] else [],
                        'episodes_available': json.loads(t[3]) if t[3] else [],
                        'total_size': t[4]
                    })
            
            response = json.dumps({
                'query': {'name': name, 'episode': episode or None, 'language': language or None},
                'count': len(results), 'results': results
            }, indent=2)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
