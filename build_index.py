#!/usr/bin/env python3
import gzip
import pickle
import json
from datetime import datetime
import os
from collections import defaultdict

def build_index():
    print("Building OPTIMIZED AnimeTosho subtitles-only index...")
    
    # Structures
    torrents = {}                    # torrent_id → title (for reference)
    files = {}                       # file_id → (torrent_id, filename)
    subtitles_only = {}              # file_id → list of subtitle dicts (only if has subs)
    lang_index = defaultdict(list)   # lang → list of (file_id, sub_dict)
    all_languages = set()            # Unique languages
    
    # 1. Load torrents (title lookup)
    with open('db_raw/torrents-latest.txt', encoding='utf-8') as f:
        header = f.readline().strip().split('\t')
        tid_idx = 0  # First column is usually id
        title_idx = header.index('title') if 'title' in header else 4
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) > max(tid_idx, title_idx):
                torrents[parts[tid_idx]] = parts[title_idx]
    
    # 2. Load files (mapping)
    with open('db_raw/files-latest.txt', encoding='utf-8') as f:
        header = f.readline().strip().split('\t')
        fid_idx = 0
        tid_idx = 1
        fname_idx = 3
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) > fname_idx:
                fid = parts[fid_idx]
                files[fid] = (parts[tid_idx], parts[fname_idx])
    
    # 3. Load attachments and filter ONLY those with subtitles
    subtitle_count = 0
    with open('db_raw/attachments-latest.txt', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t', 1)
            if len(parts) != 2:
                continue
            file_id, json_blob = parts
            try:
                data = json.loads(json_blob)
            except json.JSONDecodeError:
                continue
            
            # Parse the array (up to 4 elements: fonts, subtitles, chapters_id, tags_id)
            subtitles_array = None
            if isinstance(data, list) and len(data) >= 2:
                subtitles_array = data[1]  # Second element is subtitles array
            
            if subtitles_array and isinstance(subtitles_array, list) and subtitles_array:
                # This file has subtitles → keep it
                sub_list = []
                for sub in subtitles_array:
                    if isinstance(sub, dict):
                        lang = sub.get('lang', 'und')  # 'und' = undetermined
                        codec = sub.get('codec', 'unknown')
                        tracknum = sub.get('tracknum', None)
                        afid = sub.get('_afid', None)
                        
                        sub_dict = {
                            'lang': lang,
                            'codec': codec,
                            'tracknum': tracknum,
                            'afid': afid  # For building download URL
                        }
                        sub_list.append(sub_dict)
                        all_languages.add(lang)
                        lang_index[lang].append((file_id, sub_dict))
                
                subtitles_only[file_id] = sub_list
                subtitle_count += len(sub_list)
    
    # Save optimized index
    os.makedirs('data', exist_ok=True)
    index_data = {
        'torrents': torrents,
        'files': files,
        'subtitles_only': subtitles_only,        # Only files with subs
        'lang_index': dict(lang_index),           # Fast lang → subtitles
        'all_languages': sorted(all_languages),
        'total_subtitle_tracks': subtitle_count,
        'updated': datetime.utcnow().isoformat() + 'Z'
    }
    
    with gzip.open('data/subtitles_index.pkl.gz', 'wb') as f:
        pickle.dump(index_data, f)
    
    # Metadata
    with open('data/metadata.json', 'w') as f:
        json.dump({
            'updated': datetime.utcnow().isoformat() + 'Z',
            'torrents_with_subtitles': len(set(files[fid][0] for fid in subtitles_only)),
            'files_with_subtitles': len(subtitles_only),
            'total_subtitle_tracks': subtitle_count,
            'available_languages': sorted(all_languages)
        }, f, indent=2)
    
    print(f"Done! Optimized index: {len(subtitles_only)} files with subtitles, {subtitle_count} tracks")
    print(f"Languages found: {sorted(all_languages)}")

if __name__ == '__main__':
    build_index()
