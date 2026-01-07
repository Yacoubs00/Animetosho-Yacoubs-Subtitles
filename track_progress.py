#!/usr/bin/env python3
import time
import requests
from datetime import datetime

def track_via_github_action():
    """Track progress via GitHub Action status and TURSO dashboard info"""
    
    print("📊 TURSO Upload Progress Tracker")
    print("=" * 60)
    print("🔍 Tracking via:")
    print("   • GitHub Action runtime")
    print("   • TURSO dashboard metrics (manual check)")
    print("   • Expected completion estimates")
    print("=" * 60)
    
    # Expected totals based on build logs
    expected_torrents = 437153
    expected_files = 950000  # Approximate subtitle files
    expected_total_rows = expected_torrents + expected_files + 136 + 10  # torrents + files + languages + metadata
    
    start_time = time.time()
    
    print(f"📈 Expected Data:")
    print(f"   • Torrents: {expected_torrents:,}")
    print(f"   • Subtitle Files: {expected_files:,}")
    print(f"   • Total Rows: {expected_total_rows:,}")
    print(f"   • Expected Size: ~100-200 MB (not 1.46 MB!)")
    print("=" * 60)
    
    while True:
        elapsed_min = (time.time() - start_time) / 60
        
        print(f"\n⏱️  Runtime: {elapsed_min:.1f} minutes")
        print("📊 Check TURSO Dashboard manually:")
        print("   https://app.turso.tech/vercel-icfg-leqyol2toayupqs5t2clktag")
        print("   Look for 'Rows Written' count")
        
        # Estimate based on typical upload patterns
        if elapsed_min < 5:
            phase = "Data Download & Processing"
            estimated_progress = "0-10%"
        elif elapsed_min < 15:
            phase = "Data Processing (732K → 437K torrents)"
            estimated_progress = "10-30%"
        elif elapsed_min < 25:
            phase = "TURSO Upload (UPSERT operations)"
            estimated_progress = "30-90%"
        else:
            phase = "Finalizing & Indexing"
            estimated_progress = "90-100%"
        
        print(f"🔄 Current Phase: {phase}")
        print(f"📈 Estimated Progress: {estimated_progress}")
        
        # Size analysis
        print(f"\n💾 Size Analysis:")
        print(f"   • 1.46 MB is WAY too small for {expected_total_rows:,} rows")
        print(f"   • Expected: 100-200 MB minimum")
        print(f"   • Possible: TURSO shows compressed size or partial data")
        
        print("\n" + "=" * 60)
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    track_via_github_action()
