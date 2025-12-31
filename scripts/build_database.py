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
    print("=== Starting JSON subtitles database build ===")
    print("Current dir:", os.getcwd())
    print("Files:", os.listdir('.'))

    torrents = {}
    files = {}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # Load torrents
    with open('torrents-latest.txt', encoding='utf-8') as f:
        header = f.readline().strip().split('\t')
        tid_idx = header.index('id')
        name_idx = header.index('name')
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) <= name_idx: continue
            tid = parts[tid_idx]
            torrents[tid] = {'name': parts[name_idx]}

    print(f"Loaded {len(torrents):,} torrents")

    # Load files
    with open('files-latest.txt', encoding='utf-8') as f:
        f.readline()  # header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4: continue
            fid = parts[0]
            files[fid] = {'torrent_id': parts[1], 'filename': parts[3]}

    print(f"Loaded {len(files):,} files")

    # Load attachments
    subtitle_count = 0
    lang_stats = defaultdict(int)
    with open('attachments-latest.txt', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t', 1)
            if len(parts) != 2: continue
            file_id, json_blob = parts
            try:
                data = json.loads(json_blob)
            except: continue

            subs_array = data[1] if isinstance(data, list) and len(data) >= 2 else None
            if not subs_array: continue

            torrent_id = files.get(file_id, {}).get('torrent_id')
            if not torrent_id or torrent_id not in torrents: continue

            if torrent_id not in db['torrents']:
                db['torrents'][torrent_id] = {
                    'name': torrents[torrent_id]['name'],
                    'languages': set(),
                    'subtitle_files': []
                }

            sub_files = []
            for sub in subs_array:
                if not isinstance(sub, dict): continue
                lang = sub.get('lang', 'und')
                afid = sub.get('_afid')
                if afid:
                    url = f"https://storage.animetosho.org/attach/{afid:08x}/file.xz"
                    sub_files.append({'lang': lang, 'afid': afid, 'url': url})
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

    for t in db['torrents'].values():
        t['languages'] = sorted(t['languages'])

    db['stats'] = {
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'torrent_count': len(db['torrents']),
        'subtitle_tracks': subtitle_count,
        'language_count': len(db['languages'])
    }

    os.makedirs('../data', exist_ok=True)

    # Save compact JSON.gz
    final_path = '../data/optimized_db.json.gz'
    with gzip.open(final_path, 'wt', encoding='utf-8') as f:
        json.dump(db, f, separators=(',', ':'))  # Super compact

    print(f"Saved {final_path} (~40-60 MB)")

    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted(lang_stats.items(), key=lambda x: -x[1])}, f, indent=2)

    print("=== JSON BUILD COMPLETE ===")

if __name__ == '__main__':
    build()
