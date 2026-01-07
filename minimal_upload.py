#!/usr/bin/env python3
"""
Minimal TURSO upload - just upload sample data to verify everything works
"""
import json
import time
import os

def minimal_upload():
    print("🚀 MINIMAL TURSO UPLOAD TEST")
    print("=" * 40)
    
    try:
        import libsql_experimental as libsql
        
        conn = libsql.connect(
            os.getenv('TURSO_DATABASE_URL'),
            auth_token=os.getenv('TURSO_AUTH_TOKEN')
        )
        cursor = conn.cursor()
        
        # Create schema
        print("1️⃣ Creating schema...")
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        for statement in schema.split(';'):
            if statement.strip():
                cursor.execute(statement.strip())
        
        # Clear existing data
        print("2️⃣ Clearing existing data...")
        cursor.execute('DELETE FROM subtitle_files')
        cursor.execute('DELETE FROM torrents')
        cursor.execute('DELETE FROM language_index')
        cursor.execute('DELETE FROM build_metadata')
        
        # Upload sample data
        print("3️⃣ Uploading sample data...")
        
        # Sample torrents with subtitles
        sample_data = [
            {
                'id': 100001,
                'name': '[SubsPlease] Anime Title 01 [1080p]',
                'files': [
                    {'filename': 'episode01.eng.srt', 'afid': 12345, 'size': 45000},
                    {'filename': 'episode01.jpn.srt', 'afid': 12346, 'size': 38000}
                ]
            },
            {
                'id': 100002, 
                'name': '[Erai-raws] Another Anime 02 [720p]',
                'files': [
                    {'filename': 'ep02.english.ass', 'afid': 12347, 'size': 52000}
                ]
            }
        ]
        
        for i in range(1000):  # Upload 1000 sample torrents
            torrent_id = 100000 + i
            
            # UPSERT torrent
            cursor.execute("""
                INSERT OR REPLACE INTO torrents 
                (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                torrent_id,
                f"Sample Anime {i:04d} [1080p]",
                json.dumps(["eng", "jpn"]),
                json.dumps([1, 2, 3]),
                150000,
                50000 + i,
                json.dumps([f"anime{i:04d}.mkv"]),
                int(time.time()),
                '2.3_minimal_test'
            ))
            
            # UPSERT subtitle files (2-3 per torrent)
            for j in range(2):
                afid = 20000 + (i * 10) + j
                cursor.execute("""
                    INSERT OR REPLACE INTO subtitle_files 
                    (torrent_id, filename, language, episode_number, size, is_pack, pack_url_type, 
                     pack_name, afid, afids, target_episode, download_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    torrent_id,
                    f"episode{j+1:02d}.eng.srt",
                    'eng',
                    j + 1,
                    45000 + (j * 1000),
                    False,
                    'attach',
                    None,
                    afid,
                    json.dumps([afid]),
                    j + 1,
                    f"https://storage.animetosho.org/attach/{afid:08x}/file.xz"
                ))
            
            if i % 100 == 0:
                print(f"   Uploaded {i:,}/1,000 torrents...")
                conn.commit()
        
        # Final commit
        conn.commit()
        
        # Verify upload
        cursor.execute('SELECT COUNT(*) FROM torrents')
        torrent_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM subtitle_files')
        file_count = cursor.fetchone()[0]
        
        print(f"✅ Upload complete!")
        print(f"📊 Torrents: {torrent_count:,}")
        print(f"📊 Subtitle files: {file_count:,}")
        
        # Check database size
        cursor.execute('PRAGMA page_count')
        pages = cursor.fetchone()[0]
        cursor.execute('PRAGMA page_size')
        page_size = cursor.fetchone()[0]
        size_mb = (pages * page_size) / (1024 * 1024)
        
        print(f"💾 Database size: {size_mb:.2f} MB")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    minimal_upload()
