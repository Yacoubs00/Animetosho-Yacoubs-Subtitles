#!/usr/bin/env python3
import os
import json
import gzip
import pickle
from datetime import datetime
from collections import defaultdict

LANGUAGE_NAMES = {
    'eng': 'English', 'spa': 'Spanish', 'por': 'Portuguese', 'fre': 'French',
    'ger': 'German', 'ita': 'Italian', 'rus': 'Russian', 'ara': 'Arabic',
    'jpn': 'Japanese', 'chi': 'Chinese', 'und': 'Unknown'
}

def build():
    print("Building optimized subtitles database...")

    torrents = {}  # torrent_id → {'name': str}
    files = {}     # file_id → {'torrent_id': int, 'filename': str}
    db = {'torrents': {}, 'languages': defaultdict(list), 'stats': {}}

    # Load torrents
    with open('raw_db/torrents-latest.txt', encoding='utf-8') as f:
        header = next(f).strip().split('\t')
        tid_idx = header.index('id') if 'id' in header else 0
        name_idx = header.index('title') if 'title' in header else 4
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) > max(tid_idx, name_idx):
                tid = parts[tid_idx]
                torrents[tid] = {'name': parts[name_idx]}

    # Load files
    with open('raw_db/files-latest.txt', encoding='utf-8') as f:
        header = next(f).strip().split('\t')
        fid_idx, tid_idx, fname_idx = 0, 1, 3
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) > fname_idx:
                fid = parts[fid_idx]
                files[fid] = {'torrent_id': parts[tid_idx], 'filename': parts[fname_idx]}

    # Load attachments & filter subtitles
    subtitle_count = 0
    lang_stats = defaultdict(int)
    with open('raw_db/attachments-latest.txt', encoding='utf-8') as f:
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
                    sub_files.append({
                        'lang': lang,
                        'afid': afid,
                        'url': url
                    })
                    db['torrents'][torrent_id]['languages'].add(lang)
                    db['languages'][lang].append(torrent_id)
                    lang_stats[lang] += 1
                    subtitle_count += 1

            db['torrents'][torrent_id]['subtitle_files'].append({
                'file_id': file_id,
                'filename': files.get(file_id, {}).get('filename', ''),
                'subs': sub_files
            })

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

    os.makedirs('../data', exist_ok=True)
    with gzip.open('../data/optimized_db.pkl.gz', 'wb') as f:
        pickle.dump(db, f)

    with open('../data/metadata.json', 'w') as f:
        json.dump(db['stats'], f, indent=2)

    with open('../data/language_stats.json', 'w') as f:
        json.dump({LANGUAGE_NAMES.get(k, k): v for k, v in sorted(lang_stats.items(), key=lambda x: -x[1])}, f, indent=2)

    print("Build complete!")

if __name__ == '__main__':
    build()
