#!/usr/bin/env python3
import os
import json
import gzip
import pickle  # <-- Critical import added
from datetime import datetime, UTC
from collections import defaultdict

LANGUAGE_NAMES = {
    'eng': 'English', 'spa': 'Spanish', 'por': 'Portuguese', 'fre': 'French',
    'ger': 'German', 'ita': 'Italian', 'rus': 'Russian', 'ara': 'Arabic',
    'jpn': 'Japanese', 'chi': 'Chinese', 'und': 'Unknown'
}

def build():
    print("Starting optimized subtitles database build...")
    print("Files in current directory:", os.listdir('.'))

    torrents = {}
    files = {}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # Load torrents
    print("\n=== Loading torrents-latest.txt ===")
    with open('torrents-latest.txt', encoding='utf-8') as f:
        header = next(f).strip().split('\t')
        print("Header sample:", ' | '.join(header[:10]) + '...' if len(header) > 10 else header)
        tid_idx = header.index('id') if 'id' in header else 0
        name_idx = header.index('name') if 'name' in header else 4
        print(f"Using torrent_id index: {tid_idx}, name index: {name_idx}")

        for line_num, line in enumerate(f, start=2):
            parts = line.strip().split('\t')
            if len(parts) <= max(tid_idx, name_idx):
                continue
            tid = parts[tid_idx]
            name = parts[name_idx]
            torrents[tid] = {'name': name}

    print(f"Loaded {len(torrents)} torrents")

    # Load files
    print("\n=== Loading files-latest.txt ===")
    with open('files-latest.txt', encoding='utf-8') as f:
        header = next(f).strip().split('\t')
        fid_idx = 0
        tid_idx = 1
        fname_idx = 3
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) <= fname_idx:
                continue
            fid = parts[fid_idx]
            files[fid] = {'torrent_id': parts[tid_idx], 'filename': parts[fname_idx]}

    print(f"Loaded {len(files)} files")

    # Load attachments
    print("\n=== Loading attachments-latest.txt ===")
    subtitle_count = 0
    lang_stats = defaultdict(int)
    bad_json_count = 0
    with open('attachments-latest.txt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            parts = line.strip().split('\t', 1)
            if len(parts) != 2:
                continue
            file_id, json_blob = parts
            if not json_blob.strip():
                continue
            try:
                data = json.loads(json_blob)
            except json.JSONDecodeError as e:
                bad_json_count += 1
                if bad_json_count <= 5:
                    print(f"Bad JSON line {line_num}: {e}")
                continue

            subs_array = data[1] if isinstance(data, list) and len(data) >= 2 else None
            if not subs_array:
                continue

            torrent_id = files.get(file_id, {}).get('torrent_id')
            if not torrent_id:
                continue

            if torrent_id not in db['torrents']:
                db['torrents'][torrent_id] = {
                    'name': torrents.get(torrent_id, {}).get('name', 'Unknown'),
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
                        'afid': afid,
                        'url': url
                    })
                    db['torrents'][torrent_id]['languages'].add(lang)
                    db['languages'][lang].append(torrent_id)
                    lang_stats[lang] += 1
                    subtitle_count += 1

            if sub_files:
                db['torrents'][torrent_id]['subtitle_files'].append({
                    'file_id': file_id,
                    'filename': files.get(file_id, {}).get('filename', ''),
                    'subs': sub_files
                })

    # Finalize
    for t in db['torrents'].values():
        t['languages'] = sorted(t['languages'])

    db['stats'] = {
        'last_updated': datetime.now(UTC).isoformat() + 'Z',
        'torrent_count': len(db['torrents']),
        'subtitle_tracks': subtitle_count,
        'language_count': len(db['languages']),
        'bad_json_skipped': bad_json_count
    }

    # Save as compact JSON + gzip (lower RAM)
    os.makedirs('../data', exist_ok=True)

    # Compact JSON (no whitespace)
    temp_json = '../data/optimized_db_temp.json'
    with open(temp_json, 'w', encoding='utf-8') as f:
        json.dump(db, f, separators=(',', ':'))  # Minimal size

    # Gzip it
    with open(temp_json, 'rb') as f_in:
        with gzip.open('../data/optimized_db.json.gz', 'wb') as f_out:
            f_out.writelines(f_in)

    os.remove(temp_json)  # Clean up

    # Keep metadata and language_stats as JSON (already are)
    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        sorted_stats = sorted(lang_stats.items(), key=lambda x: -x[1])
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted_stats}, f, indent=2)

    print(f"JSON build complete! File: optimized_db.json.gz (~{os.path.getsize('../data/optimized_db.json.gz') // 1024 // 1024} MB compressed)")
