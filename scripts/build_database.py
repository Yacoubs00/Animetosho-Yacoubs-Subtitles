#!/usr/bin/env python3
import json
import urllib.request
import lzma
from collections import defaultdict

def download_and_process():
    print("📥 Downloading AnimeTosho database...")
    
    # CORRECT URLs with .xz extension
    files = {
        'torrents': 'https://storage.animetosho.org/dbexport/torrents-latest.txt.xz',
        'files': 'https://storage.animetosho.org/dbexport/files-latest.txt.xz', 
        'attachments': 'https://storage.animetosho.org/dbexport/attachments-latest.txt.xz'
    }
    
    data = {}
    for name, url in files.items():
        print(f"📥 {name}...")
        try:
            with urllib.request.urlopen(url) as response:
                compressed_data = response.read()
                print(f"📦 Downloaded {len(compressed_data) / 1024 / 1024:.1f}MB compressed")
                
                # Decompress XZ data
                decompressed_data = lzma.decompress(compressed_data)
                data[name] = decompressed_data.decode('utf-8', errors='ignore').splitlines()
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
    
    # ADD ATTACHMENT PACKS SUPPORT
    print("🔄 Processing attachment packs (torattachpk)...")
    pack_torrents = set()
    
    for torrent_id_str, torrent_data in final_db.items():
        # Add pack download for torrents with multiple subtitle files
        if len(torrent_data['subtitle_files']) >= 2:
            pack_torrents.add(torrent_id_str)
            
            # Add pack download option
            torrent_data['subtitle_files'].append({
                'filename': 'All Attachments (Pack)',
                'afids': [0],  # Special marker for pack
                'languages': torrent_data['languages'],
                'is_pack': True
            })
    
    print(f"📦 Added packs for {len(pack_torrents)} torrents")
    
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

