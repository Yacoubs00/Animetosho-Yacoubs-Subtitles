#!/usr/bin/env python3
# CORRECT: Episode-aware fields ADDED to working FIXED_PATTERNS_URLS foundation

import json
import urllib.request
import lzma
from collections import defaultdict
import re

# ✅ KEPT: 40+ English patterns from working version
ENGLISH_FANSUB_GROUPS = {
    'HorribleSubs', 'Erai-raws', 'SubsPlease', 'Asenshi',
    'FUNi_OCRd', 'FUNimation', 'Funi', 'SimulDub',
    'Commie', 'FFF', 'Underwater', 'GJM', 'Kametsu',
    'Coalgirls', 'UTW', 'gg', 'Mazui', 'WhyNot',
    'Doki', 'Chihiro', 'Tsundere', 'Vivid', 'Ayako',
    'Reinforce', 'Thora', 'Exiled-Destiny', 'Static-Subs',
    'SallySubs', 'Final8', 'ANE', 'Kira-Fansub',
    'DKS', 'Hatsuyuki', 'Live-eviL', 'Critter-Subs', 
    'Kaylith', 'OTR', 'naisho', 'Pirate King',
    'THORA', 'Eclipse', 'a4e', 'Ryuumaru', 'Elysium',
    'Beatrice-Raws', 'ANK-Raws', 'Moozzi2'
}

# ✅ ADDED: Episode extraction function
def extract_episode_number(filename):
    patterns = [
        r'- (\d{1,2}) \[',  # " - 01 ["
        r'_(\d{1,2})_',     # "_01_"
        r' (\d{1,2})\.mkv', # " 01.mkv"
        r'E(\d{1,2})',      # "E01"
        r'ep(\d{1,2})',     # "ep01"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

# ✅ PRESERVED: Original smart language detection
def smart_language_detection(lang, torrent_name, filename=''):
    if lang != 'und':
        return lang
    
    name_lower = torrent_name.lower()
    
    for group in ENGLISH_FANSUB_GROUPS:
        if f'[{group.lower()}]' in name_lower or f'({group.lower()})' in name_lower:
            return 'eng'
    
    return 'und'

# ✅ PRESERVED: Original download and process logic
def download_and_process():
    print("📥 Downloading AnimeTosho database...")
    files = {
        'torrents': 'https://storage.animetosho.org/dbexport/torrents-latest.txt.xz',
        'files': 'https://storage.animetosho.org/dbexport/files-latest.txt.xz',
        'attachments': 'https://storage.animetosho.org/dbexport/attachments-latest.txt.xz',
        'attachmentfiles': 'https://storage.animetosho.org/dbexport/attachmentfiles-latest.txt.xz'
    }
    
    data = {}
    for name, url in files.items():
        print(f"📥 {name}...")
        try:
            with urllib.request.urlopen(url) as response:
                compressed_data = response.read()
            decompressed_data = lzma.decompress(compressed_data)
            data[name] = decompressed_data.decode('utf-8', errors='ignore').splitlines()
            print(f"✅ {name}: {len(data[name])} lines")
        except Exception as e:
            print(f"❌ Failed to download {name}: {e}")
            return

    # ✅ PRESERVED: Original attachment size lookup
    attachment_sizes = {}
    for line in data['attachmentfiles'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                afid = int(parts[0])
                filesize = int(parts[2])
                attachment_sizes[afid] = filesize
            except:
                continue

    # ✅ PRESERVED: Original subtitle processing
    subtitle_files = {}
    for line in data['attachments'][1:]:
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
                            afid = sub['_afid']
                            afids.append(afid)
                            
                            lang = sub.get('lang', 'eng')
                            langs.append(lang)
                            
                            actual_size = attachment_sizes.get(afid, 50000)
                            sizes.append(actual_size)
                    
                    if afids:
                        subtitle_files[file_id] = {
                            'afids': afids,
                            'languages': langs,
                            'sizes': sizes
                        }
            except:
                continue

    # ✅ PRESERVED: Original torrent metadata extraction
    torrent_metadata = {}
    for line in data['torrents'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 28:
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

    # ✅ PRESERVED: Original database building with ADDED episode awareness
    torrents = {}
    language_index = defaultdict(set)
    
    for line in data['files'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                file_id, torrent_id, filename = int(parts[0]), int(parts[1]), parts[3]
                
                if file_id in subtitle_files and torrent_id in torrent_metadata:
                    if torrent_id not in torrents:
                        torrents[torrent_id] = {'files': [], 'languages': set()}
                    
                    sub_data = subtitle_files[file_id]
                    metadata = torrent_metadata[torrent_id]
                    
                    # ✅ ADDED: Episode number extraction
                    episode_num = extract_episode_number(filename)
                    
                    processed_languages = []
                    for lang in sub_data['languages']:
                        smart_lang = smart_language_detection(lang, metadata['name'], filename)
                        processed_languages.append(smart_lang)
                    
                    # ✅ ADDED: Episode number to file entry
                    torrents[torrent_id]['files'].append({
                        'filename': filename,
                        'afids': sub_data['afids'],
                        'languages': processed_languages,
                        'sizes': sub_data['sizes'],
                        'episode_number': episode_num  # ✅ ADDED
                    })
                    
                    for lang in processed_languages:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue

    # ✅ PRESERVED: Original pack detection with ADDED episode fields
    final_db = {}
    pack_count = 0
    
    for torrent_id in torrents:
        if torrent_id in torrent_metadata:
            metadata = torrent_metadata[torrent_id]
            name = metadata['name']
            subtitle_files_list = torrents[torrent_id]['files']
            
            unique_languages = set()
            total_subtitle_files = 0
            total_subtitle_size = 0
            
            for sub_file in subtitle_files_list:
                unique_languages.update(sub_file['languages'])
                total_subtitle_files += len(sub_file['afids'])
                total_subtitle_size += sum(sub_file['sizes'])
            
            # ✅ PRESERVED: Original pack detection logic
            has_pack = (
                total_subtitle_files >= 3 or
                len(unique_languages) >= 2 or
                metadata['torrent_files'] > 3 or
                metadata['total_size'] > 1073741824 or
                total_subtitle_size > 1000000 or
                any(keyword in name.lower() for keyword in [
                    'batch', 'complete', 'season', 'series', 'collection',
                    'vol.', 'volume', 'multi-subs', 'multisubs', 'dual audio'
                ])
            )
            
            if has_pack:
                pack_size = max(total_subtitle_size, 2000000)
                
                # ✅ ADDED: Episode-aware pack fields
                subtitle_files_list.append({
                    'filename': 'All Attachments (Pack)',
                    'afids': [0],
                    'languages': list(unique_languages),
                    'sizes': [pack_size],
                    'is_pack': True,
                    'pack_type': 'complete',        # ✅ ADDED for API compatibility
                    'pack_name': name,
                    'pack_url_type': 'torattachpk'  # ✅ ADDED for API compatibility
                })
                pack_count += 1
            
            final_db[str(torrent_id)] = {
                'name': name,
                'languages': list(torrents[torrent_id]['languages']),
                'subtitle_files': subtitle_files_list,
                'torrent_files': metadata['torrent_files'],
                'total_size': metadata['total_size'],
                'anidb_id': metadata['anidb_id']
            }

    # ✅ PRESERVED: Original database structure
    database = {
        'torrents': final_db,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()},
        'build_timestamp': int(__import__('time').time()),
        'version': '2.2_episode_aware_compatible'  # ✅ ADDED version bump
    }

    with open('data/subtitles.json', 'w') as f:
        json.dump(database, f, separators=(',', ':'))
    
    # Upload to blob storage if token available
    import os
    blob_token = os.environ.get('BLOB_READ_WRITE_TOKEN')
    if blob_token:
        try:
            import subprocess
            print("🔄 Uploading to Vercel Blob...")
            
            # Create upload script
            upload_script = '''
import { put } from '@vercel/blob';
import { readFileSync } from 'fs';

const database = readFileSync('data/subtitles.json', 'utf8');
const blob = await put('subtitles.json', database, {
    access: 'public',
    token: process.env.BLOB_READ_WRITE_TOKEN,
    addRandomSuffix: false
});
console.log('✅ Database uploaded:', blob.url);
'''
            
            with open('upload_temp.mjs', 'w') as f:
                f.write(upload_script)
            
            result = subprocess.run(['node', 'upload_temp.mjs'], 
                                  capture_output=True, text=True, 
                                  env={**os.environ, 'BLOB_READ_WRITE_TOKEN': blob_token})
            
            if result.returncode == 0:
                print("✅ Successfully uploaded to blob storage!")
            else:
                print(f"❌ Blob upload failed: {result.stderr}")
                
            os.remove('upload_temp.mjs')
            
        except Exception as e:
            print(f"⚠️ Blob upload skipped: {e}")
    else:
        print("⚠️ No BLOB_READ_WRITE_TOKEN found, skipping upload")
    
    size_mb = len(json.dumps(database, separators=(',', ':'))) / 1024 / 1024
    print(f"✅ Enhanced database built: {len(final_db)} torrents, {len(language_index)} languages")
    print(f"📊 Size: {size_mb:.1f}MB")
    print(f"🎯 Episode-aware fields added for API compatibility!")

if __name__ == '__main__':
    download_and_process()
