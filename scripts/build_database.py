#!/usr/bin/env python3
import json
import urllib.request
import lzma
from collections import defaultdict

def download_and_process():
    print("📥 Downloading AnimeTosho database...")
    
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
                    afids = []
                    langs = []
                    sizes = []
                    
                    for sub in attachment_data[1]:
                        if sub and '_afid' in sub:
                            afids.append(sub['_afid'])
                            lang = sub.get('lang', 'eng')
                            if lang == 'und': lang = 'eng'
                            elif lang == 'enm': lang = 'eng'
                            langs.append(lang)
                            # Extract size from attachment data (usually in bytes)
                            size = sub.get('size', 0) or sub.get('_size', 0) or 50000  # Default 50KB
                            sizes.append(size)
                    
                    if afids:
                        subtitle_files[file_id] = {
                            'afids': afids,
                            'languages': langs,
                            'sizes': sizes
                        }
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
                        'languages': sub_data['languages'],
                        'sizes': sub_data['sizes']
                    })
                    
                    for lang in sub_data['languages']:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue
    
    print(f"📊 Found {len(torrents)} torrents with subtitles")
    
    final_db = {}
    pack_count = 0
    
    for line in data['torrents'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 5:
            try:
                torrent_id, name = int(parts[0]), parts[4]
                
                if torrent_id in torrents:
                    subtitle_files_list = torrents[torrent_id]['files']
                    unique_languages = set()
                    total_subtitle_files = 0
                    total_size = 0
                    
                    for sub_file in subtitle_files_list:
                        unique_languages.update(sub_file['languages'])
                        total_subtitle_files += len(sub_file['afids'])
                        total_size += sum(sub_file['sizes'])
                    
                    has_pack = (
                        total_subtitle_files >= 3 or
                        len(unique_languages) >= 3 or
                        any(keyword in name.lower() for keyword in [
                            'batch', 'complete', 'season', 'series', 'collection',
                            'multi-subs', 'multisubs', 'dual audio'
                        ])
                    )
                    
                    if has_pack:
                        clean_name = name.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
                        clean_name = ''.join(c for c in clean_name if c.isalnum() or c in '.-_ ')
                        clean_name = '.'.join(clean_name.split())
                        
                        # Estimate pack size (usually 2-10MB for subtitle packs)
                        pack_size = max(total_size, 2000000)  # Minimum 2MB for packs
                        
                        subtitle_files_list.append({
                            'filename': 'All Attachments (Pack)',
                            'afids': [0],
                            'languages': list(unique_languages),
                            'sizes': [pack_size],
                            'is_pack': True,
                            'pack_name': clean_name
                        })
                        pack_count += 1
                    
                    final_db[str(torrent_id)] = {
                        'name': name,
                        'languages': list(torrents[torrent_id]['languages']),
                        'subtitle_files': subtitle_files_list
                    }
            except:
                continue
    
    print(f"📦 Added packs for {pack_count} torrents")
    
    database = {
        'torrents': final_db,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()},
        'build_timestamp': int(__import__('time').time())
    }
    
    with open('data/subtitles.json', 'w') as f:
        json.dump(database, f, separators=(',', ':'))
    
    size_mb = len(json.dumps(database, separators=(',', ':'))) / 1024 / 1024
    print(f"✅ Database built: {len(final_db)} torrents, {len(language_index)} languages")
    print(f"📊 Size: {size_mb:.1f}MB")

if __name__ == '__main__':
    download_and_process()
