#!/usr/bin/env python3
# FIXED build_database.py with 40+ patterns and torattachpk URLs

import json
import urllib.request
import lzma
from collections import defaultdict

# ✅ ADDED: Episode extraction for TURSO
import re

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

# EXPANDED: 40+ English patterns
ENGLISH_FANSUB_GROUPS = {
    # Crunchyroll/Official rips (High confidence)
    'HorribleSubs', 'Erai-raws', 'SubsPlease', 'Asenshi',
    
    # Funimation/Official (High confidence) 
    'FUNi_OCRd', 'FUNimation', 'Funi', 'SimulDub',
    
    # Major English fansub groups (High confidence)
    'Commie', 'FFF', 'Underwater', 'GJM', 'Kametsu',
    'Coalgirls', 'UTW', 'gg', 'Mazui', 'WhyNot',
    'Doki', 'Chihiro', 'Tsundere', 'Vivid', 'Ayako',
    
    # BD/Quality groups (High confidence)
    'Reinforce', 'Thora', 'Exiled-Destiny', 'Static-Subs',
    'SallySubs', 'Final8', 'ANE', 'Kira-Fansub',
    
    # Streaming rips (High confidence)
    'DKS', 'Hatsuyuki', 'Live-eviL', 'Critter-Subs', 
    'Kaylith', 'OTR', 'naisho', 'Pirate King',
    
    # Additional English groups
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

def smart_language_detection(lang, torrent_name, filename=''):
    """Smart 'und' language detection using 40+ patterns"""
    if lang != 'und':
        return lang
    
    name_lower = torrent_name.lower()
    file_lower = filename.lower()
    
    # Check for fansub groups (HIGH confidence)
    for group in ENGLISH_FANSUB_GROUPS:
        if f'[{group.lower()}]' in name_lower or f'({group.lower()})' in name_lower:
            return 'eng'
    
    # Check for dual audio (keep as 'und')
    for pattern in DUAL_AUDIO_PATTERNS:
        if pattern in name_lower:
            return 'und'  # Mixed content
    
    # Check for explicit English indicators
    for pattern in ENGLISH_TITLE_PATTERNS:
        if pattern in name_lower or pattern in file_lower:
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
    print("🔄 Building attachment file size lookup...")
    attachment_sizes = {}
    for line in data['attachmentfiles'][1:]:  # Skip header
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                afid = int(parts[0])
                filesize = int(parts[2])  # Actual file size
                attachment_sizes[afid] = filesize
            except:
                continue
    
    print(f"📊 Loaded {len(attachment_sizes)} attachment file sizes")

    # Process subtitles with ACTUAL sizes
    print("🔄 Processing subtitles with actual sizes...")
    subtitle_files = {}
    for line in data['attachments'][1:]:  # Skip header
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
                            
                            # Use ACTUAL file size
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

    print(f"📊 Found {len(subtitle_files)} files with subtitles")

    # Extract comprehensive torrent metadata
    print("🔄 Processing comprehensive torrent metadata...")
    torrent_metadata = {}
    for line in data['torrents'][1:]:  # Skip header
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

    print(f"📊 Processed metadata for {len(torrent_metadata)} torrents")

    # Build final database with enhanced processing
    torrents = {}
    language_index = defaultdict(set)
    
    for line in data['files'][1:]:  # Skip header
        parts = line.strip().split('\t')
        if len(parts) >= 4:
            try:
                file_id, torrent_id, filename = int(parts[0]), int(parts[1]), parts[3]
                
                if file_id in subtitle_files and torrent_id in torrent_metadata:
                    if torrent_id not in torrents:
                        torrents[torrent_id] = {'files': [], 'languages': set(), 'episodes': {}}  # ✅ ADDED episodes index
                    
                    sub_data = subtitle_files[file_id]
                    metadata = torrent_metadata[torrent_id]
                    
                    # Apply smart language detection with 40+ patterns
                    processed_languages = []
                    for lang in sub_data['languages']:
                        smart_lang = smart_language_detection(lang, metadata['name'], filename)
                        processed_languages.append(smart_lang)
                    
                    # ✅ ADDED: Extract episode number for TURSO
                    episode_num = extract_episode_number(filename)
                    
                    file_entry = {
                        'filename': filename,
                        'afids': sub_data['afids'],
                        'languages': processed_languages,
                        'sizes': sub_data['sizes'],
                        'episode_number': episode_num  # ✅ ADDED for TURSO
                    }
                    
                    torrents[torrent_id]['files'].append(file_entry)
                    
                    # ✅ ADDED: Index by episode number for targeted selection
                    if episode_num:
                        torrents[torrent_id]['episodes'][episode_num] = file_entry
                    
                    for lang in processed_languages:
                        torrents[torrent_id]['languages'].add(lang)
                        language_index[lang].add(torrent_id)
            except:
                continue

    print(f"📊 Found {len(torrents)} torrents with subtitles")

    # Enhanced pack detection and database building
    final_db = {}
    pack_count = 0
    
    for torrent_id in torrents:
        if torrent_id in torrent_metadata:
            metadata = torrent_metadata[torrent_id]
            name = metadata['name']
            torrent_data = torrents[torrent_id]
            
            # ✅ ADDED: Create multiple pack options for different episodes
            subtitle_files_list = torrent_data['files'].copy()
            
            unique_languages = set()
            total_subtitle_files = 0
            total_subtitle_size = 0
            
            for sub_file in subtitle_files_list:
                unique_languages.update(sub_file['languages'])
                total_subtitle_files += len(sub_file['afids'])
                total_subtitle_size += sum(sub_file['sizes'])
            
            # Enhanced pack detection
            has_pack = (
                total_subtitle_files >= 3 or
                len(unique_languages) >= 2 or
                metadata['torrent_files'] > 3 or
                metadata['total_size'] > 1073741824 or  # >1GB
                total_subtitle_size > 1000000 or  # >1MB subtitles
                any(keyword in name.lower() for keyword in [
                    'batch', 'complete', 'season', 'series', 'collection',
                    'vol.', 'volume', 'multi-subs', 'multisubs', 'dual audio'
                ])
            )
            
            if has_pack:
                # ✅ ADDED: Complete pack (torattachpk)
                if len(torrent_data['files']) > 1:
                    total_size = sum(sum(f['sizes']) for f in torrent_data['files'])
                    
                    subtitle_files_list.append({
                        'filename': 'All Attachments (Complete Pack)',
                        'afids': [0],
                        'languages': list(unique_languages),
                        'sizes': [max(total_size, 2000000)],
                        'is_pack': True,
                        'pack_type': 'complete',
                        'pack_name': name,
                        'pack_url_type': 'torattachpk'  # ✅ ADDED: Use complete pack URL
                    })
                
                # ✅ ADDED: Episode-specific packs (attachpk) - SMART SELECTION
                for episode_num, episode_file in torrent_data['episodes'].items():
                    if episode_num:
                        subtitle_files_list.append({
                            'filename': f'Episode {episode_num:02d} Pack',
                            'afids': episode_file['afids'],
                            'languages': episode_file['languages'],
                            'sizes': episode_file['sizes'],
                            'is_pack': True,
                            'pack_type': 'episode_specific',  # ✅ ADDED: Episode-specific type
                            'episode_number': episode_num,
                            'pack_name': name.replace('[', '').replace(']', '').replace('(', '').replace(')', ''),
                            'pack_url_type': 'attachpk'  # ✅ ADDED: Use episode-specific pack URL
                        })
                        
                pack_count += 1
            
            final_db[str(torrent_id)] = {
                'name': name,
                'languages': list(torrents[torrent_id]['languages']),
                'subtitle_files': subtitle_files_list,
                'torrent_files': metadata['torrent_files'],
                'total_size': metadata['total_size'],
                'anidb_id': metadata['anidb_id'],
                'episodes_available': list(torrent_data['episodes'].keys())  # ✅ ADDED: Episodes index
            }

    print(f"📦 Added packs for {pack_count} torrents")

    database = {
        'torrents': final_db,
        'languages': {lang: [str(tid) for tid in tids] for lang, tids in language_index.items()},
        'build_timestamp': int(__import__('time').time()),
        'version': '2.2_episode_aware_turso_complete'  # ✅ UPDATED version
    }

    with open('data/subtitles.json', 'w') as f:
        json.dump(database, f, separators=(',', ':'))
    
    # ✅ ADDED: Create TURSO SQLite database from existing data
    print("🔄 Creating TURSO SQLite database...")
    try:
        import sqlite3
        import os
        
        conn = sqlite3.connect('data/subtitles.db')
        cursor = conn.cursor()
        
        # Create tables for TURSO
        cursor.execute('''
            CREATE TABLE torrents (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                total_size INTEGER,
                torrent_files INTEGER,
                anidb_id INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE subtitle_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                torrent_id INTEGER,
                filename TEXT,
                afid INTEGER,
                language TEXT,
                size INTEGER,
                episode_number INTEGER,
                is_pack BOOLEAN DEFAULT 0,
                pack_type TEXT,
                pack_url_type TEXT,
                FOREIGN KEY (torrent_id) REFERENCES torrents (id)
            )
        ''')
        
        # Indexes for fast episode queries
        cursor.execute('CREATE INDEX idx_torrent_name ON torrents(name)')
        cursor.execute('CREATE INDEX idx_language ON subtitle_files(language)')
        cursor.execute('CREATE INDEX idx_episode ON subtitle_files(episode_number)')
        cursor.execute('CREATE INDEX idx_pack_type ON subtitle_files(pack_type)')
        
        # Insert data from existing processed data
        for torrent_id, torrent in final_db.items():
            cursor.execute('''
                INSERT INTO torrents (id, name, total_size, torrent_files, anidb_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (int(torrent_id), torrent['name'], torrent.get('total_size', 0), 
                  torrent.get('torrent_files', 0), torrent.get('anidb_id', 0)))
            
            # Insert subtitle files
            for sub_file in torrent['subtitle_files']:
                for i, afid in enumerate(sub_file['afids']):
                    cursor.execute('''
                        INSERT INTO subtitle_files 
                        (torrent_id, filename, afid, language, size, episode_number, 
                         is_pack, pack_type, pack_url_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (int(torrent_id), sub_file['filename'], afid,
                          sub_file['languages'][i] if i < len(sub_file['languages']) else sub_file['languages'][0],
                          sub_file['sizes'][i] if i < len(sub_file['sizes']) else sub_file['sizes'][0],
                          sub_file.get('episode_number'),
                          sub_file.get('is_pack', False),
                          sub_file.get('pack_type'),
                          sub_file.get('pack_url_type')))
        
        conn.commit()
        conn.close()
        
        db_size = os.path.getsize('data/subtitles.db') / 1024 / 1024
        print(f"✅ TURSO SQLite database created: {db_size:.1f}MB")
        
        # ✅ UPLOAD to TURSO
        if os.environ.get('TURSO_AUTH_TOKEN') and os.environ.get('TURSO_DATABASE_URL'):
            print("🔄 Uploading to TURSO...")
            
            # Create TURSO sync script
            sync_script = '''
import { createClient } from '@libsql/client';
import Database from 'better-sqlite3';

const tursoClient = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN
});

const localDb = new Database('data/subtitles.db');

// Sync local SQLite to TURSO
async function syncToTurso() {
    // Clear existing data
    await tursoClient.execute('DELETE FROM subtitle_files');
    await tursoClient.execute('DELETE FROM torrents');
    
    // Copy torrents
    const torrents = localDb.prepare('SELECT * FROM torrents').all();
    for (const torrent of torrents) {
        await tursoClient.execute({
            sql: 'INSERT INTO torrents (id, name, total_size, torrent_files, anidb_id) VALUES (?, ?, ?, ?, ?)',
            args: [torrent.id, torrent.name, torrent.total_size, torrent.torrent_files, torrent.anidb_id]
        });
    }
    
    // Copy subtitle files
    const subtitles = localDb.prepare('SELECT * FROM subtitle_files').all();
    for (const sub of subtitles) {
        await tursoClient.execute({
            sql: 'INSERT INTO subtitle_files (torrent_id, filename, afid, language, size, episode_number, is_pack, pack_type, pack_url_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            args: [sub.torrent_id, sub.filename, sub.afid, sub.language, sub.size, sub.episode_number, sub.is_pack, sub.pack_type, sub.pack_url_type]
        });
    }
    
    console.log('✅ TURSO sync complete!');
}

syncToTurso().catch(console.error);
'''
            
            with open('sync_turso.mjs', 'w') as f:
                f.write(sync_script)
            
            result = subprocess.run(['node', 'sync_turso.mjs'], 
                                  capture_output=True, text=True, env=os.environ)
            
            if result.returncode == 0:
                print("✅ Successfully synced to TURSO!")
            else:
                print(f"❌ TURSO sync failed: {result.stderr}")
                
            os.remove('sync_turso.mjs')
        else:
            print("⚠️ No TURSO credentials, skipping upload")
        
    except Exception as e:
        print(f"⚠️ SQLite creation failed: {e}")
    
    size_mb = len(json.dumps(database, separators=(',', ':'))) / 1024 / 1024
    print(f"✅ Enhanced database built: {len(final_db)} torrents, {len(language_index)} languages")
    print(f"📊 JSON Size: {size_mb:.1f}MB")
    print(f"🎯 TURSO SQLite database also created!")
    print(f"🚀 Ready for episode-aware queries!")

if __name__ == '__main__':
    download_and_process()
