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
    print("Starting build — current dir files:")
    print(os.listdir('.'))

    torrents = {}
    files = {}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # Robust torrents load
    print("\n=== Loading torrents-latest.txt ===")
    with open('torrents-latest.txt', encoding='utf-8') as f:
        header_line = f.readline().strip()
        print("Header:", header_line)
        header = header_line.split('\t')
        tid_idx = header.index('id') if 'id' in header else 0
        name_idx = header.index('title') if 'title' in header else header.index('name') if 'name' in header else 4
        print(f"torrent_id column: {tid_idx}, name column: {name_idx}")

        for line_num, line in enumerate(f, 2):
            parts = line.strip().split('\t')
            if len(parts) <= max(tid_idx, name_idx):
                print(f"Short line {line_num}: {line.strip()}")
                continue
            tid = parts[tid_idx]
            name = parts[name_idx]
            torrents[tid] = {'name': name}

    # Robust files load
    print("\n=== Loading files-latest.txt ===")
    with open('files-latest.txt', encoding='utf-8') as f:
        header_line = f.readline().strip()
        print("Header:", header_line)
        header = header_line.split('\t')
        fid_idx = header.index('id') if 'id' in header else 0
        tid_idx = header.index('torrent_id') if 'torrent_id' in header else 1
        fname_idx = header.index('filename') if 'filename' in header else 3
        print(f"file_id: {fid_idx}, torrent_id: {tid_idx}, filename: {fname_idx}")

        for line in f:
            parts = line.strip().split('\t')
            if len(parts) <= fname_idx: continue
            fid = parts[fid_idx]
            files[fid] = {'torrent_id': parts[tid_idx], 'filename': parts[fname_idx]}

    # Attachments load (rest same)
    print("\n=== Loading attachments-latest.txt ===")
    subtitle_count = 0
    lang_stats = defaultdict(int)
    with open('attachments-latest.txt', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t', 1)
            if len(parts) != 2: continue
            file_id, json_blob = parts
            try:
                data = json.loads(json_blob)
            except Exception as e:
                print("JSON error:", e)
                continue

            subs_array = data[1] if isinstance(data, list) and len(data) >= 2 else None
            if not subs_array: continue

            torrent_id = files.get(file_id, {}).get('torrent_id')
            if not torrent_id: continue

            if torrent_id not in db['torrents']:
                db['torrents'][torrent_id] = {
                    'name': torrents.get(torrent_id, {}).get('name', 'Unknown'),
                    'languages': set(),
                    'subtitle_files': []
                }

            sub_files = []
            for sub in subs_array:
                if not isinstance(sub, dict): continue
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
    with gzip.open('../data/optimized_db.pkl.gz', 'wb') as f:
        pickle.dump(db, f)

    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted(lang_stats.items(), key=lambda x: -x[1])}, f, indent=2)

    print("Build complete! Files created in ../data/")

if __name__ == '__main__':
    build()
