#!/usr/bin/env python3
# SMART Episode-Aware Database Builder
# Creates episode-specific packs instead of random selection

import json
import urllib.request
import lzma
from collections import defaultdict
import re

# 40+ English patterns (same as before)
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
    'THORA', 'Eclipse', 'a4e', 'Ryuumaru', 'Elysium'
}

def extract_episode_number(filename):
    """Extract episode number from filename"""
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

def smart_language_detection(lang, torrent_name, filename=''):
    """Smart language detection with 40+ patterns"""
    if lang != 'und':
        return lang
    
    name_lower = torrent_name.lower()
    
    # Check for fansub groups
    for group in ENGLISH_FANSUB_GROUPS:
        if f'[{group.lower()}]' in name_lower or f'({group.lower()})' in name_lower:
            return 'eng'
    
    # Keep as 'und' when uncertain
    return 'und'

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

    # Build attachment file size lookup
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

    # Process subtitles with episode awareness
    print("🔄 Processing subtitles with episode awareness...")
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

    # Extract torrent metadata
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

    # Build episode-aware database
    torrents = {}
    language_index = defaultdict(set)
    
    for line in data['files'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                file_id, torrent_id, filename = int(parts[0]), int(parts[1]), parts[3]
                
                if file_id in subtitle_files and torrent_id in torrent_metadata:
                    if torrent_id not in torrents:
                        torrents[torrent_id] = {'files': [], 'languages': set(), 'episodes': {}}
                    
                    sub_data = subtitle_files[file_id]
                    metadata = torrent_metadata[torrent_id]
                    
                    # Extract episode number from filename
                    episode_num = extract_episode_number(filename)
                    
                    # Apply smart language detection
                    processed_languages = []
                    for lang in sub_data['languages']:
                        smart_lang = smart_language_detection(lang, metadata['name'], filename)
                        processed_languages.append(smart_lang)
                    
                    file_entry = {
                        'filename': filename,
                        'afids': sub_data['afids'],
                        'languages': processed_languages,
                        'sizes': sub_data['sizes'],
                        'episode_number': episode_num
                    }
                    
                    torrents[torrent_id]['files'].append(file_entry)
                    
                    # SMART: Index by episode number for targeted selection
                    if episode_num:
                        torrents[torrent_id]['episodes'][episode_num] = file_entry
                    
                    for lang in processed_languages:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue

    # Build final database with episode-specific pack options
    final_db = {}
    
    for torrent_id in torrents:
        if torrent_id in torrent_metadata:
            metadata = torrent_metadata[torrent_id]
            name = metadata['name']
            torrent_data = torrents[torrent_id]
            
            # Create multiple pack options for different episodes
            subtitle_files_list = torrent_data['files'].copy()
            
            # Add complete pack (torattachpk)
            if len(torrent_data['files']) > 1:
                total_size = sum(sum(f['sizes']) for f in torrent_data['files'])
                
                subtitle_files_list.append({
                    'filename': 'All Attachments (Complete Pack)',
                    'afids': [0],
                    'languages': list(torrent_data['languages']),
                    'sizes': [max(total_size, 2000000)],
                    'is_pack': True,
                    'pack_type': 'complete',
                    'pack_name': name,
                    'pack_url_type': 'torattachpk'  # Use complete pack URL
                })
            
            # Add episode-specific packs (attachpk) - SMART SELECTION
            for episode_num, episode_file in torrent_data['episodes'].items():
                if episode_num:
                    subtitle_files_list.append({
                        'filename': f'Episode {episode_num:02d} Pack',
                        'afids': episode_file['afids'],
                        'languages': episode_file['languages'],
                        'sizes': episode_file['sizes'],
                        'is_pack': True,
                        'pack_type': 'episode_specific',
                        'episode_number': episode_num,
                        'pack_name': name.replace('[', '').replace(']', '').replace('(', '').replace(')', ''),
                        'pack_url_type': 'attachpk'  # Use episode-specific pack URL
                    })
            
            final_db[str(torrent_id)] = {
                'name': name,
                'languages': list(torrent_data['languages']),
                'subtitle_files': subtitle_files_list,
                'torrent_files': metadata['torrent_files'],
                'total_size': metadata['total_size'],
                'anidb_id': metadata['anidb_id'],
                'episodes_available': list(torrent_data['episodes'].keys())
            }

    database = {
        'torrents': final_db,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()},
        'build_timestamp': int(__import__('time').time()),
        'version': '3.0_episode_aware'
    }

    with open('data/subtitles.json', 'w') as f:
        json.dump(database, f, separators=(',', ':'))
    
    print(f"✅ Episode-aware database built!")
    print(f"🎯 Now supports targeted episode selection in packs!")

if __name__ == '__main__':
    download_and_process()
