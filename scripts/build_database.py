#!/usr/bin/env python3
import os
import json
import gzip
import pickle  # <-- Added!
from datetime import datetime
from collections import defaultdict

LANGUAGE_NAMES = {
    'eng': 'English', 'spa': 'Spanish', 'por': 'Portuguese', 'fre': 'French',
    'ger': 'German', 'ita': 'Italian', 'rus': 'Russian', 'ara': 'Arabic',
    'jpn': 'Japanese', 'chi': 'Chinese', 'und': 'Unknown'
}

def build():
    print("Starting optimized subtitles database build...")

    torrents = {}
    files = {}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # Load torrents
    print("Loading torrents-latest.txt")
    with open('torrents-latest.txt', encoding='utf-8') as f:
        header = next(f).strip().split('\t')
        tid_idx = header.index('id') if 'id' in header else 0
        name_idx = header.index('name') if 'name' in header else 4  # 'name' is column 4
        print(f"Using torrent_id index: {tid_idx}, name index: {name_idx}")

        for line in f:
            parts = line.strip().split('\t')
            if len(parts) <= max(tid_idx, name_idx):
                continue
            tid = parts[tid_idx]
            name = parts[name_idx]
            torrents[tid] = {'name': name}

    # Load files
    print("Loading files-latest.txt")
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

    # Load attachments — skip bad JSON
    print("Loading attachments-latest.txt (skipping invalid JSON)")
    subtitle_count = 0
    lang_stats = defaultdict(int)
    bad_lines = 0
    with open('attachments-latest.txt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split('\t', 1)
            if len(parts) != 2:
                continue
            file_id, json_blob = parts
            if not json_blob.strip():  # Skip empty
                continue
            try:
                data = json.loads(json_blob)
            except json.JSONDecodeError:
                bad_lines += 1
                if bad_lines < 10:
                    print(f"Bad JSON on line {line_num}")
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
                if afid:
                    hex_afid = f"{afid:08x}"
                    url = f"https://storage.animetosho.org/attach/{hex_afid}/file.xz"
                    sub_files.append({'lang': lang, 'afid': afid, 'url': url})
                    db['torrents'][torrent_id]['languages'].add(lang)
                    db['languages'][lang].append(torrent_id)
                    lang_stats[lang] += 1
                    subtitle_count += 1

            if sub_files:  # Only append if has subs
                db['torrents'][torrent_id]['subtitle_files'].append({
                    'file_id': file_id,
                    'filename': files.get(file_id, {}).get('filename', ''),
                    'subs': sub_files
                })

    # Finalize
    for t in db['torrents'].values():
        t['languages'] = sorted(t['languages'])

    db['stats'] = {
        'last_updated': datetime.now(datetime.UTC).isoformat() + 'Z',  # Fixed deprecation
        'torrent_count': len(db['torrents']),
        'subtitle_tracks': subtitle_count,
        'language_count': len(db['languages'])
    }

    os.makedirs('../data', exist_ok=True)
    with gzip.open('../data/optimized_db.pkl.gz', 'wb') as f:
        pickle.dump(db, f)

    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        sorted_stats = sorted(lang_stats.items(), key=lambda x: -x[1])
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted_stats}, f, indent=2)

    print(f"Build complete! {len(db['torrents'])} torrents with subtitles, {subtitle_count} tracks")
    print(f"Skipped {bad_lines} bad JSON lines")

if __name__ == '__main__':
    build()
