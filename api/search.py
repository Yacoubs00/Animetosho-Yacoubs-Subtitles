import json
import os
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import libsql_experimental as libsql

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        
        # Get first value from each param list
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
        
        # Connect to TURSO
        conn = libsql.connect(
            os.getenv('TURSO_DATABASE_URL'),
            auth_token=os.getenv('TURSO_AUTH_TOKEN')
        )
        
        results = []
        
        if episode:
            ep_num = int(episode)
            
            # Search for torrents that have this specific episode OR are packs containing it
            query = '''
                SELECT DISTINCT t.id, t.name, t.languages, t.episodes_available, t.total_size
                FROM torrents t
                JOIN subtitle_files sf ON t.id = sf.torrent_id
                WHERE t.name LIKE ?
                  AND (
                    sf.episode_number = ?
                    OR sf.is_pack = 1
                  )
            '''
            
            params_sql = (f'%{name}%', ep_num)
            
            if language:
                query += ' AND sf.language = ?'
                params_sql = (f'%{name}%', ep_num, language)
            
            query += ' LIMIT 50'
            
            torrents = conn.execute(query, params_sql).fetchall()
            
            for t in torrents:
                torrent_id, torrent_name, langs, eps_available, total_size = t
                eps_list = json.loads(eps_available) if eps_available else []
                
                # Check if this torrent actually has the episode
                has_episode = ep_num in eps_list
                
                # Get subtitle files for this episode
                subs_query = '''
                    SELECT filename, language, size, episode_number, is_pack, download_url
                    FROM subtitle_files
                    WHERE torrent_id = ? AND (episode_number = ? OR is_pack = 1)
                '''
                
                if language:
                    subs_query += ' AND language = ?'
                    subs = conn.execute(subs_query, (torrent_id, ep_num, language)).fetchall()
                else:
                    subs = conn.execute(subs_query, (torrent_id, ep_num)).fetchall()
                
                subtitle_files = []
                for s in subs:
                    subtitle_files.append({
                        'filename': s[0],
                        'language': s[1],
                        'size': s[2],
                        'episode': s[3],
                        'is_pack': bool(s[4]),
                        'download_url': s[5]
                    })
                
                if subtitle_files:
                    results.append({
                        'torrent_id': torrent_id,
                        'name': torrent_name,
                        'languages': json.loads(langs) if langs else [],
                        'episodes_available': eps_list,
                        'has_episode': has_episode,
                        'total_size': total_size,
                        'subtitle_files': subtitle_files
                    })
        
        else:
            # No episode specified, return all torrents matching name
            query = '''
                SELECT id, name, languages, episodes_available, total_size
                FROM torrents
                WHERE name LIKE ?
                LIMIT 50
            '''
            
            torrents = conn.execute(query, (f'%{name}%',)).fetchall()
            
            for t in torrents:
                torrent_id, torrent_name, langs, eps_available, total_size = t
                
                results.append({
                    'torrent_id': torrent_id,
                    'name': torrent_name,
                    'languages': json.loads(langs) if langs else [],
                    'episodes_available': json.loads(eps_available) if eps_available else [],
                    'total_size': total_size
                })
        
        response_data = json.dumps({
            'query': {
                'name': name,
                'episode': episode if episode else None,
                'language': language if language else None
            },
            'count': len(results),
            'results': results
        }, indent=2)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_data.encode())
