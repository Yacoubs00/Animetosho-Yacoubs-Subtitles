#!/usr/bin/env python3
import json
import urllib.request
from collections import defaultdict

def download_and_process():
    print("📥 Downloading AnimeTosho database...")
    
    # CORRECT URLs - no trailing slash, correct path
    files = {
        'torrents': 'https://animetosho.org/storage/dbexport/torrents-latest.txt',
        'files': 'https://animetosho.org/storage/dbexport/files-latest.txt', 
        'attachments': 'https://animetosho.org/storage/dbexport/attachments-latest.txt'
    }
    
    data = {}
    for name, url in files.items():
        print(f"📥 {name}...")
        try:
            with urllib.request.urlopen(url) as response:
                data[name] = response.read().decode('utf-8', errors='ignore').splitlines()
            print(f"✅ {name}: {len(data[name])} lines")
        except Exception as e:
            print(f"❌ Failed to download {name}: {e}")
            return
    
    print("🔄 Processing subtitles...")
    
    subtitle_files = {}
    for line in data['attachments']:
        parts = line.strip().split('\t', 1)
        if len(parts) == 2:
            try:
                file_id = int(parts[0])
                attachment_data = json.loads(parts[1])
                if len(attachment_data) >= 2 and attachment_data[1]:
                    afids = [sub['_afid'] for sub in attachment_data[1] if sub and '_afid' in sub]
                    langs = [sub.get('lang', 'eng') for sub in attachment_data[1] if sub]
                    if afids:
                        subtitle_files[file_id] = {'afids': afids, 'languages': langs}
            except:
                continue
    
    print(f"📊 Found {len(subtitle_files)} files with subtitles")
    
    torrents = {}
    language_index = defaultdict(set)
    
    for line in data['files'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                file_id, torrent_id, filename = int(parts[0]), int(parts[1]), parts[3]
                if file_id in subtitle_files:
                    if torrent_id not in torrents:
                        torrents[torrent_id] = {'files': [], 'languages': set()}
                    
                    sub_data = subtitle_files[file_id]
                    torrents[torrent_id]['files'].append({
                        'filename': filename,
                        'afids': sub_data['afids'],
                        'languages': sub_data['languages']
                    })
                    
                    for lang in sub_data['languages']:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue
    
    print(f"📊 Found {len(torrents)} torrents with subtitles")
    
    final_db = {}
    for line in data['torrents'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 5:
            try:
                torrent_id, name = int(parts[0]), parts[4]
                if torrent_id in torrents:
                    final_db[str(torrent_id)] = {
                        'name': name,
                        'languages': list(torrents[torrent_id]['languages']),
                        'subtitle_files': torrents[torrent_id]['files']
                    }
            except:
                continue
    
    database = {
        'torrents': final_db,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()}
    }
    
    with open('data/subtitles.json', 'w') as f:
        json.dump(database, f, separators=(',', ':'))
    
    size_mb = len(json.dumps(database, separators=(',', ':'))) / 1024 / 1024
    print(f"✅ Database built: {len(final_db)} torrents, {len(language_index)} languages")
    print(f"📊 Size: {size_mb:.1f}MB")

if __name__ == '__main__':
    download_and_process()

