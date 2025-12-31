#!/usr/bin/env python3
import os
import json
import gzip
from datetime import datetime
from collections import defaultdict

LANGUAGE_NAMES = {
    'eng': 'English', 'spa': 'Spanish', 'por': 'Portuguese', 'fre': 'French',
    'ger': 'German', 'ita': 'Italian', 'rus': 'Russian', 'ara': 'Arabic',
    'jpn': 'Japanese', 'chi': 'Chinese', 'und': 'Unknown'
}

def build():
    print("=== Starting optimized subtitles database build ===")
    print("Current directory:", os.getcwd())
    print("Files in current dir:", os.listdir('.'))

    torrents = {}
    files = {}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # === Load torrents ===
    print("\n=== Loading torrents-latest.txt ===")
    with open('torrents-latest.txt', encoding='utf-8') as f:
        header_line = f.readline().strip()
        header = header_line.split('\t')
        print(f"Header columns ({len(header)}):", ' | '.join(header[:15]) + '...' if len(header) > 15 else header)

        # Find indexes safely
        tid_idx = header.index('id') if 'id' in header else 0
        name_idx = header.index('name') if 'name' in header else 4  # Logs show 'name' exists

        print(f"Using torrent_id index: {tid_idx} ('id')")
        print(f"Using name index: {name_idx} ('name')")

        for line_num, line in enumerate(f, start=2):
            parts = line.strip().split('\t')
            if len(parts) <= max(tid_idx, name_idx):
                continue  # Skip malformed
            tid = parts[tid_idx]
            name = parts[name_idx]
            torrents[tid] = {'name': name}

    print(f"Successfully loaded {len(torrents):,} torrents")

    # === Load files ===
    print("\n=== Loading files-latest.txt ===")
    with open('files-latest.txt', encoding='utf-8') as f:
        header_line = f.readline().strip()
        header = header_line.split('\t')
        print(f"Files header columns ({len(header)}):", header[:10])

        fid_idx = 0
        tid_idx = 1
        fname_idx = 3

        file_count = 0
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) <= fname_idx:
                continue
            fid = parts[fid_idx]
            files[fid] = {
                'torrent_id': parts[tid_idx],
                'filename': parts[fname_idx]
            }
            file_count += 1

    print(f"Successfully loaded {file_count:,} files")

    # === Load attachments ===
    print("\n=== Loading attachments-latest.txt ===")
    subtitle_count = 0
    lang_stats = defaultdict(int)
    processed_files = 0

    with open('attachments-latest.txt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            parts = line.strip().split('\t', 1)
            if len(parts) != 2:
                continue
            file_id, json_blob = parts
            try:
                data = json.loads(json_blob)
            except json.JSONDecodeError as e:
                if line_num <= 5:
                    print(f"Bad JSON on line {line_num}: {e}")
                continue

            subs_array = data[1] if isinstance(data, list) and len(data) >= 2 else None
            if not subs_array or not isinstance(subs_array, list):
                continue

            torrent_id = files.get(file_id, {}).get('torrent_id')
            if not torrent_id or torrent_id not in torrents:
                continue

            if torrent_id not in db['torrents']:
                db['torrents'][torrent_id] = {
                    'name': torrents[torrent_id]['name'],
                    'languages': set(),
                    'subtitle_files': []
                }

            sub_files = []
            for sub in subs_array:
                if not isinstance(sub, dict):
                    continue
                lang = sub.get('lang', 'und')
                afid = sub.get('_afid')
                if afid is not None:
                    hex_afid = f"{int(afid):08x}"
                    url = f"https://storage.animetosho.org/attach/{hex_afid}/file.xz"
                    sub_files.append({
                        'lang': lang,
                        'afid': int(afid),
                        'url': url
                    })
                    db['torrents'][torrent_id]['languages'].add(lang)
                    db['languages'][lang].append(torrent_id)
                    lang_stats[lang] += 1
                    subtitle_count += 1

            if sub_files:
                db['torrents'][torrent_id]['subtitle_files'].append({
                    'file_id': file_id,
                    'filename': files.get(file_id, {}).get('filename', 'Unknown.mkv'),
                    'subs': sub_files
                })
                processed_files += 1

    print(f"Processed {processed_files:,} files with subtitles")
    print(f"Total subtitle tracks: {subtitle_count:,}")

    # Convert sets to lists
    for t in db['torrents'].values():
        t['languages'] = sorted(t['languages'])

    # Stats
    db['stats'] = {
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'torrent_count': len(db['torrents']),
        'subtitle_tracks': subtitle_count,
        'language_count': len(db['languages'])
    }

    # Save compact JSON + gzip
    os.makedirs('../data', exist_ok=True)
    temp_json = '../data/optimized_db_temp.json'
    final_gz = '../data/optimized_db.json.gz'

    print("\n=== Saving compact JSON ===")
    with open(temp_json, 'w', encoding='utf-8') as f:
        json.dump(db, f, separators=(',', ':'))  # Super compact

    with open(temp_json, 'rb') as f_in:
        with gzip.open(final_gz, 'wb') as f_out:
            f_out.writelines(f_in)

    os.remove(temp_json)
    file_size_mb = os.path.getsize(final_gz) // 1024 // 1024
    print(f"Saved {final_gz} ({file_size_mb} MB compressed)")

    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        sorted_stats = sorted(lang_stats.items(), key=lambda x: -x[1])
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted_stats}, f, indent=2)

    print("=== BUILD COMPLETE SUCCESSFULLY ===")

if __name__ == '__main__':
    build()
