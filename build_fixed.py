#!/usr/bin/env python3
"""
Fixed TURSO build script with progress logging and timeout protection
"""
import requests
import json
import time
import os
import lzma
import urllib.parse
from collections import defaultdict

def download_and_process():
    print("📥 Downloading AnimeTosho database...")
    
    # Download files with progress
    urls = {
        'torrents': 'https://storage.animetosho.org/dbexport/torrents-latest.txt.xz',
        'files': 'https://storage.animetosho.org/dbexport/files-latest.txt.xz',
        'attachments': 'https://storage.animetosho.org/dbexport/attachments-latest.txt.xz',
        'attachmentfiles': 'https://storage.animetosho.org/dbexport/attachmentfiles-latest.txt.xz'
    }
    
    data = {}
    for name, url in urls.items():
        print(f"📥 Downloading {name}...")
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            content = lzma.decompress(response.content).decode('utf-8')
            lines = content.strip().split('\n')
            data[name] = lines
            print(f"✅ {name}: {len(lines):,} lines")
        else:
            raise Exception(f"Failed to download {name}: {response.status_code}")
    
    print("🔄 Building attachment file size lookup...")
    attachment_sizes = {}
    for i, line in enumerate(data['attachmentfiles']):
        if i == 0:  # Skip header
            continue
        if i % 100000 == 0:
            print(f"   Processing attachment files: {i:,}/{len(data['attachmentfiles']):,}")
        
        parts = line.split('\t')
        if len(parts) >= 3:
            try:
                afid = int(parts[0])
                size = int(parts[2]) if parts[2].isdigit() else 0
                attachment_sizes[afid] = size
            except ValueError:
                continue
    
    print(f"📊 Loaded {len(attachment_sizes):,} attachment file sizes")
    
    print("🔄 Processing subtitles with actual sizes...")
    subtitle_files = {}
    processed_attachments = 0
    
    for i, line in enumerate(data['attachments']):
        if i == 0:  # Skip header
            continue
        if i % 50000 == 0:
            print(f"   Processing attachments: {i:,}/{len(data['attachments']):,}")
        
        parts = line.split('\t')
        if len(parts) >= 4:
            try:
                torrent_id = int(parts[0])
                filename = parts[1]
                afid = int(parts[2]) if parts[2].isdigit() else 0
                
                # Check if it's a subtitle file
                if any(ext in filename.lower() for ext in ['.srt', '.ass', '.ssa', '.vtt', '.sub']):
                    size = attachment_sizes.get(afid, 0)
                    
                    if torrent_id not in subtitle_files:
                        subtitle_files[torrent_id] = []
                    
                    subtitle_files[torrent_id].append({
                        'filename': filename,
                        'afid': afid,
                        'size': size
                    })
                    processed_attachments += 1
            except ValueError:
                continue
    
    print(f"📊 Found {len(subtitle_files):,} torrents with subtitles")
    print(f"📊 Total subtitle files: {processed_attachments:,}")
    
    # Upload to TURSO with progress
    print("🔄 Uploading to TURSO Database...")
    
    try:
        import libsql_experimental as libsql
        
        turso_url = os.getenv('TURSO_DATABASE_URL')
        turso_token = os.getenv('TURSO_AUTH_TOKEN')
        
        conn = libsql.connect(turso_url, auth_token=turso_token)
        cursor = conn.cursor()
        
        # Create schema
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        for statement in schema.split(';'):
            if statement.strip():
                cursor.execute(statement.strip())
        
        print(f"🔄 Uploading {len(subtitle_files):,} torrents...")
        
        uploaded_torrents = 0
        uploaded_files = 0
        
        for torrent_id, files in subtitle_files.items():
            if uploaded_torrents % 10000 == 0:
                print(f"   Progress: {uploaded_torrents:,}/{len(subtitle_files):,} torrents")
            
            # Get torrent info
            torrent_name = f"Torrent_{torrent_id}"  # Simplified for speed
            
            # UPSERT torrent
            cursor.execute("""
                INSERT OR REPLACE INTO torrents 
                (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                torrent_id,
                torrent_name,
                json.dumps(["eng"]),  # Simplified
                json.dumps([1]),      # Simplified
                sum(f['size'] for f in files),
                0,  # Simplified
                json.dumps([]),  # Simplified
                int(time.time()),
                '2.3_turso_fixed'
            ))
            
            # UPSERT subtitle files
            for file_data in files:
                download_url = f"https://storage.animetosho.org/attach/{file_data['afid']:08x}/file.xz"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO subtitle_files 
                    (torrent_id, filename, language, episode_number, size, is_pack, pack_url_type, 
                     pack_name, afid, afids, target_episode, download_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    torrent_id,
                    file_data['filename'],
                    'eng',  # Simplified
                    1,      # Simplified
                    file_data['size'],
                    False,
                    'attach',
                    None,
                    file_data['afid'],
                    json.dumps([file_data['afid']]),
                    1,
                    download_url
                ))
                uploaded_files += 1
            
            uploaded_torrents += 1
            
            # Commit every 1000 torrents
            if uploaded_torrents % 1000 == 0:
                conn.commit()
        
        # Final commit
        conn.commit()
        
        # Update metadata
        cursor.execute("""
            INSERT OR REPLACE INTO build_metadata (key, value, updated_at)
            VALUES (?, ?, ?)
        """, ('last_build', json.dumps({
            'total_torrents': uploaded_torrents,
            'total_files': uploaded_files,
            'version': '2.3_turso_fixed'
        }), int(time.time())))
        
        conn.commit()
        conn.close()
        
        print(f"✅ TURSO upload complete!")
        print(f"📊 Uploaded: {uploaded_torrents:,} torrents, {uploaded_files:,} files")
        
    except Exception as e:
        print(f"❌ TURSO upload failed: {e}")
        raise

if __name__ == "__main__":
    download_and_process()
