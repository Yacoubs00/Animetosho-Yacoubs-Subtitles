#!/usr/bin/env python3
import libsql_experimental as libsql
import os
import time
from datetime import datetime

# Expected totals from build logs
EXPECTED_TORRENTS = 437153
EXPECTED_FILES = 950000  # Approximate

def monitor_progress():
    conn = libsql.connect(
        os.getenv('TURSO_DATABASE_URL'),
        auth_token=os.getenv('TURSO_AUTH_TOKEN')
    )
    cursor = conn.cursor()
    
    start_time = time.time()
    last_torrent_count = 0
    
    print("🔄 TURSO Upload Monitor Started")
    print("=" * 60)
    print(f"📊 Expected: {EXPECTED_TORRENTS:,} torrents, ~{EXPECTED_FILES:,} files")
    print("=" * 60)
    
    while True:
        try:
            # Check torrents
            cursor.execute('SELECT COUNT(*) FROM torrents')
            torrent_count = cursor.fetchone()[0]
            torrent_pct = (torrent_count / EXPECTED_TORRENTS * 100) if EXPECTED_TORRENTS > 0 else 0
            
            # Check subtitle files
            cursor.execute('SELECT COUNT(*) FROM subtitle_files')
            file_count = cursor.fetchone()[0]
            file_pct = (file_count / EXPECTED_FILES * 100) if EXPECTED_FILES > 0 else 0
            
            # Calculate rate
            elapsed_min = (time.time() - start_time) / 60
            rate = torrent_count / elapsed_min if elapsed_min > 0 else 0
            
            # ETA calculation
            remaining = EXPECTED_TORRENTS - torrent_count
            eta_min = remaining / rate if rate > 0 else 0
            
            # Progress indicator
            progress_bar = "█" * int(torrent_pct / 5) + "░" * (20 - int(torrent_pct / 5))
            
            print(f"\r🎯 [{progress_bar}] {torrent_pct:.1f}% | "
                  f"Torrents: {torrent_count:,}/{EXPECTED_TORRENTS:,} | "
                  f"Files: {file_count:,} | "
                  f"Rate: {rate:.0f}/min | "
                  f"ETA: {eta_min:.0f}m", end="", flush=True)
            
            # Check if complete
            if torrent_count >= EXPECTED_TORRENTS:
                print(f"\n✅ UPLOAD COMPLETE! {torrent_count:,} torrents, {file_count:,} files")
                break
                
            # Check if stalled
            if torrent_count == last_torrent_count and elapsed_min > 5:
                print(f"\n⚠️  Upload may be stalled at {torrent_count:,} torrents")
            
            last_torrent_count = torrent_count
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print(f"\n❌ Monitor error: {e}")
            time.sleep(30)  # Wait longer on error
    
    conn.close()

if __name__ == "__main__":
    monitor_progress()
