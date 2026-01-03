#!/usr/bin/env python3
import json
import gzip
import time
from collections import defaultdict

def build_json_database():
    print("🚀 Building JSON database for web API...")
    start_time = time.time()
    
    # Load subtitle files with languages
    subtitle_files = {}
    with open('/home/ycoub/Downloads/attachments-latest.txt', 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t', 1)
            if len(parts) == 2:
                try:
                    file_id = int(parts[0])
                    attachment_data = json.loads(parts[1])
                    
                    if len(attachment_data) >= 2 and attachment_data[1]:
                        subtitles = attachment_data[1]
                        languages = []
                        afids = []
                        
                        for sub in subtitles:
                            if sub and isinstance(sub, dict) and '_afid' in sub:
                                afids.append(sub['_afid'])
                                lang = sub.get('lang', 'eng')
                                if lang in ['und', '']:
                                    lang = 'eng'
                                languages.append(lang)
                        
                        if afids:
                            subtitle_files[file_id] = {
                                'languages': list(set(languages)),
                                'afids': afids
                            }
                except (ValueError, json.JSONDecodeError, TypeError):
                    continue
    
    # Map to torrents
    torrents_with_subs = {}
    language_index = defaultdict(set)
    
    with open('/home/ycoub/Downloads/files-latest.txt', 'r', encoding='utf-8', errors='ignore') as f:
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                try:
                    file_id = int(parts[0])
                    torrent_id = int(parts[1])
                    filename = parts[3]
                    
                    if file_id in subtitle_files:
                        if torrent_id not in torrents_with_subs:
                            torrents_with_subs[torrent_id] = {
                                'files': [],
                                'languages': set()
                            }
                        
                        sub_info = subtitle_files[file_id]
                        torrents_with_subs[torrent_id]['files'].append({
                            'file_id': file_id,
                            'filename': filename,
                            'languages': sub_info['languages'],
                            'afids': sub_info['afids']
                        })
                        
                        for lang in sub_info['languages']:
                            torrents_with_subs[torrent_id]['languages'].add(lang)
                            language_index[lang].add(torrent_id)
                
                except (ValueError, IndexError):
                    continue
    
    # Add torrent names
    final_database = {}
    with open('/home/ycoub/Downloads/torrents-latest.txt', 'r', encoding='utf-8', errors='ignore') as f:
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                try:
                    torrent_id = int(parts[0])
                    name = parts[4]
                    
                    if torrent_id in torrents_with_subs:
                        final_database[str(torrent_id)] = {  # JSON keys must be strings
                            'name': name,
                            'languages': list(torrents_with_subs[torrent_id]['languages']),
                            'subtitle_files': torrents_with_subs[torrent_id]['files']
                        }
                
                except (ValueError, IndexError):
                    continue
    
    # Convert language index
    language_index = {lang: list(torrents) for lang, torrents in language_index.items()}
    
    # Create final JSON structure
    json_data = {
        'torrents': final_database,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()},
        'stats': {
            'build_time': time.time() - start_time,
            'torrent_count': len(final_database),
            'language_count': len(language_index),
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    }
    
    # Save as compressed JSON
    with gzip.open('data/optimized_db.json.gz', 'wt', encoding='utf-8') as f:
        json.dump(json_data, f, separators=(',', ':'), ensure_ascii=False)
    
    import os
    size_mb = os.path.getsize('data/optimized_db.json.gz') / 1024 / 1024
    print(f"✅ JSON database saved: {size_mb:.1f} MB")
    print(f"📊 Torrents: {len(final_database):,}")
    print(f"🌐 Languages: {len(language_index)}")

if __name__ == "__main__":
    build_json_database()
