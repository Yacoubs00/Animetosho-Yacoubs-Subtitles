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
                            if lang == 'und':
                                lang = 'eng'
                            elif lang == 'enm':
                                lang = 'eng'
                            langs.append(lang)
                            
                            size = sub.get('size', 0) or sub.get('_size', 0) or 50000
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
    
    # NEW: Extract torrent metadata for episode detection
    print("🔄 Processing torrent metadata...")
    torrent_metadata = {}
    for line in data['torrents'][1:]:  # Skip header
        parts = line.strip().split('\t')
        if len(parts) >= 28:  # Ensure we have enough fields
            try:
                torrent_id = int(parts[0])
                name = parts[4]
                total_size = int(parts[9]) if parts[9] else 0
                torrent_files = int(parts[15]) if parts[15] else 0
                anidb_id = int(parts[27]) if parts[27] and parts[27] != '0' else 0
                
                torrent_metadata[torrent_id] = {
                    'name': name,
                    'total_size': total_size,
                    'torrent_files': torrent_files,
                    'anidb_id': anidb_id
                }
            except:
                continue
    
    print(f"📊 Processed metadata for {len(torrent_metadata)} torrents")
    
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
    
    # UPDATED: Enhanced final database building with torrent metadata
    final_db = {}
    pack_count = 0
    
    for torrent_id in torrents:
        if torrent_id in torrent_metadata:
            metadata = torrent_metadata[torrent_id]
            name = metadata['name']
            subtitle_files_list = torrents[torrent_id]['files']
            
            unique_languages = set()
            total_subtitle_files = 0
            total_size = 0
            
            for sub_file in subtitle_files_list:
                unique_languages.update(sub_file['languages'])
                total_subtitle_files += len(sub_file['afids'])
                total_size += sum(sub_file['sizes'])
            
            # Enhanced pack detection using torrent metadata
            has_pack = (
                total_subtitle_files >= 3 or
                len(unique_languages) >= 3 or
                metadata['torrent_files'] > 5 or  # NEW: Use file count
                metadata['total_size'] > 1073741824 or  # NEW: Use size (>1GB)
                any(keyword in name.lower() for keyword in [
                    'batch', 'complete', 'season', 'series', 'collection',
                    'multi-subs', 'multisubs', 'dual audio'
                ])
            )
            
            if has_pack:
                clean_name = name.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
                clean_name = ''.join(c for c in clean_name if c.isalnum() or c in '.-_ ')
                clean_name = '.'.join(clean_name.split())
                
                pack_size = max(total_size, 2000000)
                subtitle_files_list.append({
                    'filename': 'All Attachments (Pack)',
                    'afids': [0],
                    'languages': list(unique_languages),
                    'sizes': [pack_size],
                    'is_pack': True,
                    'pack_name': clean_name
                })
                pack_count += 1
            
            # NEW: Include torrent metadata in final database
            final_db[str(torrent_id)] = {
                'name': name,
                'languages': list(torrents[torrent_id]['languages']),
                'subtitle_files': subtitle_files_list,
                # NEW FIELDS for episode detection:
                'torrent_files': metadata['torrent_files'],
                'total_size': metadata['total_size'],
                'anidb_id': metadata['anidb_id']
            }
    
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
    print(f"🎯 Enhanced with episode detection metadata!")

if __name__ == '__main__':
    download_and_process()
