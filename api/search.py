import json
import os
from urllib.parse import unquote
import libsql_experimental as libsql

def handler(event, context):
    """
    Search for anime subtitles by name and episode.
    Returns both single episodes and packs that contain the episode.
    
    Query params:
    - name: anime name (required)
    - episode: episode number (optional)
    - language: filter by language (optional)
    """
    
    # Parse query parameters
    params = event.get('queryStringParameters', {}) or {}
    name = params.get('name', '').strip()
    episode = params.get('episode', '').strip()
    language = params.get('language', '').strip()
    
    if not name:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Missing required parameter: name'})
        }
    
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
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'query': {
                'name': name,
                'episode': episode if episode else None,
                'language': language if language else None
            },
            'count': len(results),
            'results': results
        }, indent=2)
    }
