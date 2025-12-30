#!/usr/bin/env python3
import os
import json
from datetime import datetime
from collections import defaultdict

LANGUAGE_NAMES = { ... }  # Keep same

def build():
    print("Building JSON-optimized subtitles database...")

    # Same loading code as before...

    # At end, instead of pickle:
    os.makedirs('../data', exist_ok=True)
    
    with open('../data/optimized_db.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=None)  # Compact

    # Optional: gzip it for smaller download (but load with gzip in app.py)
    import gzip
    with open('../data/optimized_db.json', 'rb') as f_in:
        with gzip.open('../data/optimized_db.json.gz', 'wb') as f_out:
            f_out.writelines(f_in)

    # Update metadata/language_stats same way

    print("JSON build complete — smaller memory footprint")
