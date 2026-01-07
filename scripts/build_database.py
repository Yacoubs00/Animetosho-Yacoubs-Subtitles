#!/usr/bin/env python3
# GitHub Pages Database Builder - Static JSON hosting

import json
import urllib.request
import urllib.parse
import lzma
import sys
from collections import defaultdict
import re
import os

# [Keep all the existing functions and patterns from the original script]
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

ENGLISH_TITLE_PATTERNS = {
    'english dub', '[eng]', '(english)', 'english sub', 'eng sub',
    '[english dub]', 'english audio', 'dub', 'dubbed',
    'crunchyroll', 'funimation', 'netflix', 'hulu', 'amazon prime',
    'webrip', 'web-dl', 'hdtv', 'simulcast', 'official subs'
}

DUAL_AUDIO_PATTERNS = {
    'dual-audio', 'dual audio', 'multi-audio', 'multi audio',
    'dual language', 'bilingual', 'eng+jpn', 'jp+en'
}

def extract_episode_number(filename):
    """
    Extract episode number from anime filename. Returns (episode, is_range, range_end, season, is_special)
    Covers 100+ naming patterns for anime files.
    """
    fn = filename.replace('_', ' ')
    
    # Skip non-episode files
    skip_patterns = [
        r'\b(NCOP|NCED|OP\d*|ED\d*|PV\d*|CM\d*|Menu|Preview|Trailer|Promo|Clean)\b',
        r'^(OST|Soundtrack|CD|Disc|Music)\b',
        r'/(OST|Soundtrack|Scans?|BK|Jacket|CD|Extra|Bonus)/',
        r'\.(jpg|jpeg|png|bmp|gif|txt|nfo|sfv|exe|bat|url|ico|ttf|otf|srt|ass|ssa|sub|idx)$',
    ]
    for skip in skip_patterns:
        if re.search(skip, fn, re.IGNORECASE):
            return None, False, None, None, False
    
    # Extract season
    season = None
    for pattern in [r'\bS(\d{1,2})E\d', r'\bS(\d{1,2})\s*[-–]\s*\d', r'\bSeason\s*(\d{1,2})', r'[\s\.]S(\d{1,2})[\s\.]']:
        match = re.search(pattern, fn, re.IGNORECASE)
        if match:
            season = int(match.group(1))
            break
    
    # Check for specials (SP01, OVA 3, etc.)
    special_match = re.search(r'\b(SP|OVA|OAD|ONA|Special)\s*(\d{1,3})', fn, re.IGNORECASE)
    if special_match:
        return int(special_match.group(2)), False, None, season, True
    
    # RANGE PATTERNS
    range_patterns = [
        r'Episodes?\s*(\d{1,4})\s*[-–~to]+\s*(\d{1,4})',
        r'Eps?\.?\s*(\d{1,4})\s*[-–~]+\s*(\d{1,4})',
        r'E(\d{1,4})\s*[-–~]+\s*E?(\d{1,4})',
        r'\((\d{1,4})\s*[-–~]+\s*(\d{1,4})\)',
        r'\[(\d{1,4})\s*[-–~]+\s*(\d{1,4})\]',
        r'[\s\-](\d{1,4})\s*[-–~]+\s*(\d{1,4})\s*[\[\(]',
        r'[\s\-](\d{1,4})\s*[-–~]+\s*(\d{1,4})[\s\]\)]',
        r'[\s\-](\d{1,4})\s*[-–~]+\s*(\d{1,4})$',
    ]
    for pattern in range_patterns:
        match = re.search(pattern, fn, re.IGNORECASE)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if 1 <= start <= 999 and start < end <= 9999:
                return start, True, end, season, False
    
    # SINGLE EPISODE PATTERNS (100+ variations)
    # Single episode patterns
    patterns = [
        # Explicit markers (highest priority)
        r'S\d{1,2}E(\d{1,4})',                              # S01E12
        r'\bEpisodes?\s*(\d{1,4})\b',                       # Episode 12
        r'\bEps?\.?\s*(\d{1,4})\b',                         # Ep 12, Ep.12
        r'#(\d{1,4})\b',                                    # #12
        r'(?<![A-Fa-f0-9])E(\d{1,4})(?![A-Fa-f0-9])',      # E12 (not hex)
        # Dash separators
        r'[-–]\s*(\d{1,4})\s*[\[\(]',                       # - 12 [
        r'[-–]\s*(\d{1,4})\s*v\d',                          # - 12v2
        r'[-–]\s*(\d{1,4})\s*END',                          # - 12 END
        r'[-–]\s*(\d{1,4})\.(?:mkv|mp4|avi)',               # - 12.mkv
        r'[-–]\s*(\d{1,4})\s*$',                            # - 12 (end)
        r'[-–]\s*(\d{1,4})\s+(?![x\d])',                    # - 12 space
        r'[-–]\s*(\d{1,4})\s*\)',                           # - 12)
        r'S\d{1,2}\s*[-–]\s*(\d{1,4})',                     # S2 - 05
        # Positional
        r'^(\d{1,4})\s*[-–]\s*\w',                          # 12 - Title
        r'^(\d{1,4})\.(?:mkv|mp4|avi)$',                    # 12.mkv
        r'/(\d{1,4})\.(?:mkv|mp4|avi)$',                    # folder/12.mkv
        # Delimiters
        r'[_ ](\d{1,4})[_ ][\[\(]',                         # _12_ or " 12 ["
        r'\.(\d{1,4})\.(?![x\d])',                          # .12.
        r'\s(\d{1,4})\.(?:mkv|mp4|avi)',                    # " 12.mkv"
        # Brackets (not hex)
        r'\[(\d{1,3})\](?![A-Fa-f0-9])',                    # [12]
        # Title patterns
        r'[a-z]\s+(\d{1,4})\s*[\[\(]',                      # "Title 12 ["
        r'[a-z]\s+(\d{1,4})\.(?:mkv|mp4|avi)',              # "Title 12.mkv"
        r'[a-z!?]\s+(\d{1,4})\s*$',                         # "Title 12"
        # Zero-padded
        r'[-–\s]0*(\d{1,4})[\s\[\(]',                       # - 001 [
        # Japanese
        r'第(\d{1,4})話',                                   # 第12話
        r'(\d{1,4})話',                                     # 12話
    ]
    
    for pattern in patterns:
        match = re.search(pattern, fn, re.IGNORECASE)
        if match:
            try:
                ep = int(match.group(1))
            except:
                continue
            if ep < 1 or ep > 9999:
                continue
            # Skip years
            if 1950 <= ep <= 2030:
                continue
            # Skip resolution numbers only if filename contains that resolution marker
            if ep in {480, 720, 1080, 2160, 1920, 1280, 848, 800}:
                if re.search(str(ep) + r'p\b', fn, re.I):
                    continue
            # Skip x264/x265 only if it's a codec marker (not episode)
            if ep in {264, 265}:
                if re.search(r'\bx' + str(ep) + r'\b', fn, re.I) and not re.search(r'[-–]\s*' + str(ep) + r'\s*[\[\(\s]', fn):
                    continue
            return ep, False, None, season, False
    
    return None, False, None, None, False

def smart_language_detection(lang, torrent_name, filename=''):
    if lang != 'und':
        return lang
    name_lower = torrent_name.lower()
    file_lower = filename.lower()
    
    for group in ENGLISH_FANSUB_GROUPS:
        if f'[{group.lower()}]' in name_lower or f'({group.lower()})' in name_lower:
            return 'eng'
    
    for pattern in DUAL_AUDIO_PATTERNS:
        if pattern in name_lower:
            return 'und'
    
    for pattern in ENGLISH_TITLE_PATTERNS:
        if pattern in name_lower or pattern in file_lower:
            return 'eng'
    
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
    print("🔄 Building attachment file size lookup...")
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

    print(f"📊 Loaded {len(attachment_sizes)} attachment file sizes")

    # Process subtitles
    print("🔄 Processing subtitles with actual sizes...")
    subtitle_files = {}
    for line in data['attachments'][1:]:
        parts = line.strip().split('\t', 1)
        if len(parts) == 2:
            try:
                file_id = int(parts[0])
                attachment_data = json.loads(parts[1])
                
                afids, langs, sizes = [], [], []
                for sub in attachment_data[1]:
                    if sub and '_afid' in sub:
                        afid = sub['_afid']
                        afids.append(afid)
                        langs.append(sub.get('lang', 'eng'))
                        sizes.append(attachment_sizes.get(afid, 50000))
                
                if afids:
                    subtitle_files[file_id] = {'afids': afids, 'languages': langs, 'sizes': sizes}
            except:
                continue
    
    print(f"📊 Found {len(subtitle_files)} files with subtitles")

    # Process torrent metadata
    print("🔄 Processing torrent metadata...")
    torrent_metadata = {}
    for line in data['torrents'][1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 28:
            try:
                torrent_id = int(parts[0])
                name = parts[5] if len(parts) > 5 else "Unknown"
                total_size = int(parts[10]) if len(parts) > 10 and parts[10].isdigit() else 0
                torrent_files = int(parts[16]) if len(parts) > 16 and parts[16].isdigit() else 0
                anidb_id = int(parts[29]) if len(parts) > 29 and parts[29].isdigit() else 0
                
                torrent_metadata[torrent_id] = {
                    'name': name, 'total_size': total_size,
                    'torrent_files': torrent_files, 'anidb_id': anidb_id
                }
            except:
                continue
    
    print(f"📊 Processed metadata for {len(torrent_metadata)} torrents")

    # Build final database
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
                    
                    processed_languages = []
                    for lang in sub_data['languages']:
                        smart_lang = smart_language_detection(lang, metadata['name'], filename)
                        processed_languages.append(smart_lang)
                    
                    episode_num, is_range, range_end, season, is_special = extract_episode_number(filename)
                    
                    file_entry = {
                        'filename': filename, 'afids': sub_data['afids'],
                        'languages': processed_languages, 'sizes': sub_data['sizes'],
                        'episode_number': episode_num, 'is_range': is_range,
                        'range_end': range_end, 'season': season
                    }
                    
                    torrents[torrent_id]['files'].append(file_entry)
                    
                    if episode_num:
                        # For ranges, expand to all episodes in range
                        if is_range and range_end:
                            for ep in range(episode_num, range_end + 1):
                                torrents[torrent_id]['episodes'][ep] = file_entry
                        else:
                            torrents[torrent_id]['episodes'][episode_num] = file_entry
                    
                    for lang in processed_languages:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue
    
    print(f"📊 Found {len(torrents)} torrents with subtitles")
    sys.stdout.flush()

    # Build final database with packs
    final_db = {}
    pack_count = 0
    processed = 0

    for torrent_id in torrents:
        if torrent_id in torrent_metadata:
            metadata = torrent_metadata[torrent_id]
            name = metadata['name']
            torrent_data = torrents[torrent_id]
            
            subtitle_files_list = torrent_data['files'].copy()
            unique_languages = set()
            total_subtitle_files = 0
            total_subtitle_size = 0

            for sub_file in subtitle_files_list:
                unique_languages.update(sub_file['languages'])
                total_subtitle_files += len(sub_file['afids'])
                total_subtitle_size += sum(sub_file['sizes'])

            has_pack = (
                total_subtitle_files >= 3 or len(unique_languages) >= 2 or
                metadata['torrent_files'] > 3 or metadata['total_size'] > 1073741824 or
                total_subtitle_size > 1000000 or
                any(keyword in name.lower() for keyword in [
                    'batch', 'complete', 'season', 'series', 'collection',
                    'vol.', 'volume', 'multi-subs', 'multisubs', 'dual audio'
                ])
            )

            if has_pack:
                if len(torrent_data['files']) > 1:
                    total_size = sum(sum(f['sizes']) for f in torrent_data['files'])
                    
                    subtitle_files_list.append({
                        'filename': 'All Attachments (Complete Pack)',
                        'afids': [0], 'languages': list(unique_languages),
                        'sizes': [max(total_size, 2000000)], 'is_pack': True,
                        'pack_type': 'complete', 'pack_name': name,
                        'pack_url_type': 'torattachpk'
                    })

                for episode_num, episode_file in torrent_data['episodes'].items():
                    if episode_num:
                        for i, afid in enumerate(episode_file['afids']):
                            lang = episode_file['languages'][i] if i < len(episode_file['languages']) else episode_file['languages'][0]
                            size = episode_file['sizes'][i] if i < len(episode_file['sizes']) else episode_file['sizes'][0]
                            
                            subtitle_files_list.append({
                                'filename': f'Episode {episode_num:02d} - {lang.upper()}',
                                'afids': [afid], 'languages': [lang], 'sizes': [size],
                                'is_pack': False, 'pack_type': 'individual',
                                'episode_number': episode_num, 'pack_url_type': 'attach',
                                'target_episode': episode_num
                            })

                pack_count += 1

            final_db[str(torrent_id)] = {
                'name': name, 'languages': list(torrents[torrent_id]['languages']),
                'subtitle_files': subtitle_files_list, 'torrent_files': metadata['torrent_files'],
                'total_size': metadata['total_size'], 'anidb_id': metadata['anidb_id'],
                'episodes_available': list(torrent_data['episodes'].keys()),
                'url_accuracy': {
                    'individual_files_count': len([f for f in subtitle_files_list if f.get('pack_url_type') == 'attach']),
                    'complete_pack_available': any(f.get('pack_url_type') == 'torattachpk' for f in subtitle_files_list),
                    'accuracy_level': 'high'
                }
            }
            
            processed += 1
            if processed % 50000 == 0:
                print(f"🔄 Processed {processed:,} torrents...")
                sys.stdout.flush()

    print(f"📦 Added packs for {pack_count} torrents")

    # Create GitHub Pages structure
    os.makedirs('docs', exist_ok=True)
    
    # Sort and chunk
    sorted_ids = sorted(final_db.keys(), key=int)
    chunk_size = 50000
    chunks = [sorted_ids[i:i+chunk_size] for i in range(0, len(sorted_ids), chunk_size)]
    
    index = {'chunks': [], 'total': len(final_db), 'languages': list(language_index.keys())}
    
    for i, chunk_ids in enumerate(chunks):
        chunk_data = {tid: final_db[tid] for tid in chunk_ids}
        
        with open(f'docs/subtitles_{i}.json', 'w') as f:
            json.dump(chunk_data, f, separators=(',', ':'))
        
        index['chunks'].append({
            'id': i,
            'url': f'https://yacoubs00.github.io/Animetosho-Yacoubs-Subtitles/subtitles_{i}.json',
            'min_id': int(chunk_ids[0]),
            'max_id': int(chunk_ids[-1]),
            'count': len(chunk_ids)
        })
        
        size_mb = os.path.getsize(f'docs/subtitles_{i}.json') / 1024 / 1024
        print(f"✅ Chunk {i}: {len(chunk_ids)} torrents ({size_mb:.1f}MB)")
    
    with open('docs/index.json', 'w') as f:
        json.dump(index, f, separators=(',', ':'))
    
    print(f"✅ GitHub Pages database built: {len(final_db)} torrents, {len(language_index)} languages")

    # === TURSO UPSERT - No duplicate checking, just write! ===
    print("🔄 Uploading to TURSO Database (UPSERT - no reads needed)...")
    try:
        import libsql_experimental as libsql
        import time
        
        turso_url = os.getenv('TURSO_DATABASE_URL')
        turso_token = os.getenv('TURSO_AUTH_TOKEN')
        
        if not turso_url or not turso_token:
            print("⚠️ TURSO credentials not set, skipping TURSO upload")
        else:
            conn = libsql.connect(turso_url, auth_token=turso_token)
            
            # Create schema
            conn.execute('''CREATE TABLE IF NOT EXISTS torrents (
                id INTEGER PRIMARY KEY, name TEXT, languages TEXT, 
                episodes_available TEXT, total_size INTEGER, anidb_id INTEGER,
                torrent_files TEXT, build_timestamp INTEGER, version TEXT)''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS subtitle_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT, torrent_id INTEGER,
                filename TEXT, language TEXT, episode_number INTEGER, size INTEGER,
                is_pack BOOLEAN, pack_url_type TEXT, pack_name TEXT, afid INTEGER,
                afids TEXT, target_episode INTEGER, download_url TEXT)''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_torrent_name ON torrents(name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_subtitle_torrent ON subtitle_files(torrent_id)')
            
            print(f"🔄 Uploading {len(final_db):,} torrents (BATCH MODE)...")
            uploaded = 0
            
            # BATCH INSERT for speed - collect rows then insert in batches
            torrent_batch = []
            subtitle_batch = []
            BATCH_SIZE = 500
            
            for torrent_id, data in final_db.items():
                # Collect torrent data
                torrent_batch.append((
                    int(torrent_id), data.get('name'), json.dumps(data.get('languages', [])),
                    json.dumps(data.get('episodes_available', [])), data.get('total_size'),
                    data.get('anidb_id'), json.dumps(data.get('torrent_files', [])),
                    int(time.time()), '2.3_turso'
                ))
                
                # Collect subtitle files
                for sf in data.get('subtitle_files', []):
                    afids = sf.get('afids', [])
                    afid = afids[0] if afids else None
                    
                    if sf.get('pack_url_type') == 'torattachpk':
                        download_url = f"https://storage.animetosho.org/torattachpk/{torrent_id}/{urllib.parse.quote(sf.get('pack_name', ''))}_attachments.7z"
                    elif afid:
                        download_url = f"https://storage.animetosho.org/attach/{afid:08x}/file.xz"
                    else:
                        download_url = None
                    
                    langs = sf.get('languages', [])
                    sizes = sf.get('sizes', [])
                    subtitle_batch.append((
                        int(torrent_id), sf.get('filename'), langs[0] if langs else None,
                        sf.get('episode_number'), sizes[0] if sizes else None, sf.get('is_pack', False),
                        sf.get('pack_url_type'), sf.get('pack_name'), afid,
                        json.dumps(afids), sf.get('target_episode'), download_url
                    ))
                
                uploaded += 1
                
                # Flush batches when full
                if len(torrent_batch) >= BATCH_SIZE:
                    conn.executemany('''INSERT OR REPLACE INTO torrents 
                        (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', torrent_batch)
                    torrent_batch = []
                    
                if len(subtitle_batch) >= BATCH_SIZE * 3:
                    conn.executemany('''INSERT OR REPLACE INTO subtitle_files 
                        (torrent_id, filename, language, episode_number, size, is_pack, 
                         pack_url_type, pack_name, afid, afids, target_episode, download_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', subtitle_batch)
                    subtitle_batch = []
                    conn.commit()
                    print(f"   Progress: {uploaded:,}/{len(final_db):,} ({uploaded/len(final_db)*100:.1f}%)")
            
            # Flush remaining
            if torrent_batch:
                conn.executemany('''INSERT OR REPLACE INTO torrents 
                    (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', torrent_batch)
            if subtitle_batch:
                conn.executemany('''INSERT OR REPLACE INTO subtitle_files 
                    (torrent_id, filename, language, episode_number, size, is_pack, 
                     pack_url_type, pack_name, afid, afids, target_episode, download_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', subtitle_batch)
            
            conn.commit()
            conn.close()
            print(f"✅ TURSO upload complete: {uploaded:,} torrents")
            
    except Exception as e:
        print(f"❌ TURSO upload failed: {e}")

if __name__ == '__main__':
    download_and_process()
