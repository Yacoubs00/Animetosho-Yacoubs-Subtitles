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
        # Leading digits (for files like "01 title.mkv", "07 sv13 720.mkv")
        r'^0*(\d{1,2})\s+\w',                               # 01 title, 07 sv13
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
            if ep < 0 or ep > 9999:
                continue
            # Skip years
            if 1950 <= ep <= 2030:
                continue
            # Skip resolution numbers (with or without 'p')
            if ep in {480, 720, 1080, 2160, 1920, 1280, 848, 800}:
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
                        # Store episode (ranges stay as single entry with range_end info)
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
            
            # Get existing torrent IDs to avoid re-uploading (RESUME SUPPORT)
            print(f"🔍 Checking existing torrents...")
            existing_ids = set()
            try:
                result = conn.execute("SELECT id FROM torrents").fetchall()
                existing_ids = {row[0] for row in result}
                print(f"   Found {len(existing_ids):,} existing, will skip them")
            except:
                print("   Starting fresh")
            
            print(f"🔄 Uploading {len(final_db):,} torrents (BATCH MODE, RESUME FROM {len(existing_ids):,})...")
            uploaded = 0
            skipped = 0
            processed = 0
            
            # Build SQL batch string instead of using executemany
            batch_sql = ["BEGIN"]
            batch_count = 0
            BATCH_SIZE = 5000  # Larger batches for batch API
            last_print_time = time.time()
            
            for torrent_id, data in final_db.items():
                processed += 1
                # SKIP if already exists
                if int(torrent_id) in existing_ids:
                    skipped += 1
                    continue
                
                # Build INSERT statements as SQL strings
                name = data.get('name', '').replace("'", "''")
                langs = json.dumps(data.get('languages', [])).replace("'", "''")
                eps = json.dumps(data.get('episodes_available', [])).replace("'", "''")
                tfiles = json.dumps(data.get('torrent_files', [])).replace("'", "''")
                
                batch_sql.append(f"""INSERT INTO torrents (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version) 
                    VALUES ({int(torrent_id)}, '{name}', '{langs}', '{eps}', {data.get('total_size', 0)}, {data.get('anidb_id', 0)}, '{tfiles}', {int(time.time())}, '2.3_turso')""")
                
                # Add subtitle files
                for sf in data.get('subtitle_files', []):
                    afids = sf.get('afids', [])
                    afid = afids[0] if afids else None
                    
                    if sf.get('pack_url_type') == 'torattachpk':
                        download_url = f"https://storage.animetosho.org/torattachpk/{torrent_id}/{urllib.parse.quote(sf.get('pack_name', ''))}_attachments.7z"
                    elif afid:
                        download_url = f"https://storage.animetosho.org/attach/{afid:08x}/file.xz"
                    else:
                        download_url = None
                    
                    filename = sf.get('filename', '').replace("'", "''")
                    langs = sf.get('languages', [])
                    lang = langs[0].replace("'", "''") if langs else 'NULL'
                    sizes = sf.get('sizes', [])
                    size = sizes[0] if sizes else 'NULL'
                    ep = sf.get('episode_number')
                    ep_str = str(ep) if ep is not None else 'NULL'
                    is_pack = 1 if sf.get('is_pack', False) else 0
                    pack_type = sf.get('pack_url_type', '')
                    pack_type_str = f"'{pack_type}'" if pack_type else 'NULL'
                    pack_name = sf.get('pack_name', '').replace("'", "''")
                    pack_name_str = f"'{pack_name}'" if pack_name else 'NULL'
                    afid_str = str(afid) if afid else 'NULL'
                    afids_json = json.dumps(afids).replace("'", "''")
                    target_ep = sf.get('target_episode')
                    target_ep_str = str(target_ep) if target_ep is not None else 'NULL'
                    url_str = f"'{download_url}'" if download_url else 'NULL'
                    
                    batch_sql.append(f"""INSERT INTO subtitle_files (torrent_id, filename, language, episode_number, size, is_pack, pack_url_type, pack_name, afid, afids, target_episode, download_url) 
                        VALUES ({int(torrent_id)}, '{filename}', '{lang}', {ep_str}, {size}, {is_pack}, {pack_type_str}, {pack_name_str}, {afid_str}, '{afids_json}', {target_ep_str}, {url_str})""")
                
                uploaded += 1
                batch_count += 1
                
                # Execute batch when full
                if batch_count >= BATCH_SIZE:
                    batch_sql.append("COMMIT")
                    conn.executescript("; ".join(batch_sql))
                    batch_sql = ["BEGIN"]
                    batch_count = 0
                    
                    # Print progress every 60 seconds
                    if time.time() - last_print_time > 60:
                        print(f"   Progress: {processed:,}/{len(final_db):,} ({processed/len(final_db)*100:.1f}%) | Uploaded: {uploaded:,} | Skipped: {skipped:,}")
                        last_print_time = time.time()
            
            # Flush remaining batch
            if batch_count > 0:
                batch_sql.append("COMMIT")
                conn.executescript("; ".join(batch_sql))
            conn.close()
            print(f"✅ TURSO upload complete: {uploaded:,} torrents")
            
    except Exception as e:
        print(f"❌ TURSO upload failed: {e}")

if __name__ == '__main__':
    download_and_process()
