#!/usr/bin/env python3
import libsql_experimental as libsql
import os

conn = libsql.connect(
    os.getenv('TURSO_DATABASE_URL'),
    auth_token=os.getenv('TURSO_AUTH_TOKEN')
)

print('🔍 Finding torrents with duplicate subtitle files...')
# Get torrents that have duplicates
torrents_with_dupes = conn.execute('''
    SELECT DISTINCT torrent_id
    FROM subtitle_files
    GROUP BY torrent_id, filename
    HAVING COUNT(*) > 1
''').fetchall()

print(f'Found {len(torrents_with_dupes):,} torrents with duplicates')

deleted = 0
for i, (torrent_id,) in enumerate(torrents_with_dupes):
    # For this torrent, find all duplicate groups
    dupes = conn.execute('''
        SELECT filename, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
        FROM subtitle_files
        WHERE torrent_id = ?
        GROUP BY filename
        HAVING COUNT(*) > 1
    ''', (torrent_id,)).fetchall()
    
    for filename, keep_id, all_ids_str in dupes:
        all_ids = [int(x) for x in all_ids_str.split(',')]
        delete_ids = [x for x in all_ids if x != keep_id]
        
        for del_id in delete_ids:
            conn.execute('DELETE FROM subtitle_files WHERE id = ?', (del_id,))
            deleted += 1
    
    if (i + 1) % 50 == 0:
        conn.commit()
        pct = (i + 1) / len(torrents_with_dupes) * 100
        print(f'  [{pct:5.1f}%] Processed {i+1:,}/{len(torrents_with_dupes):,} torrents, deleted {deleted:,} duplicates')

conn.commit()
print(f'✅ Deleted {deleted:,} duplicate subtitle files')

# Verify
remaining = conn.execute('SELECT COUNT(*) FROM subtitle_files').fetchone()[0]
print(f'✅ Remaining subtitle files: {remaining:,}')
