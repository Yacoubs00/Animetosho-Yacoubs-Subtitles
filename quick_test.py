#!/usr/bin/env python3
"""
Quick TURSO upload test - minimal version to identify the bottleneck
"""
import requests
import json
import time
import os
import sys

def quick_turso_test():
    print("🚀 QUICK TURSO TEST - Finding the bottleneck")
    print("=" * 50)
    
    try:
        # Test TURSO connection first
        print("1️⃣ Testing TURSO connection...")
        import libsql_experimental as libsql
        
        turso_url = os.getenv('TURSO_DATABASE_URL', "libsql://database-fuchsia-xylophone-vercel-icfg-leqyol2toayupqs5t2clktag.aws-us-east-1.turso.io")
        turso_token = os.getenv('TURSO_AUTH_TOKEN', "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njc3ODI2ODMsImlkIjoiMzUxZTVkNjQtMWYzMi00ZGQ1LWE3NTktNDZlOGJmMjdhZTIwIiwicmlkIjoiYTAzMmI2NjktOTAxNy00ZGU1LWIzNmUtMGRiMmE2OTIyNWJiIn0.QushOoxk4gLxLro4Y8iaU0Izh9DYKKlQ3KS8NZYKr75mK01uoj3bEz5o256yoFHIfqoIrbwvFeVPkT2GSk7_AA")
        
        conn = libsql.connect(turso_url, auth_token=turso_token)
        cursor = conn.cursor()
        
        # Create schema
        print("2️⃣ Creating schema...")
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        for statement in schema.split(';'):
            if statement.strip():
                cursor.execute(statement.strip())
        
        print("✅ TURSO connection and schema OK")
        
        # Test data download (this is where it might hang)
        print("3️⃣ Testing AnimeTosho download...")
        start_time = time.time()
        
        response = requests.get('https://storage.animetosho.org/dbexport/torrents-latest.txt.xz', timeout=30)
        if response.status_code == 200:
            print(f"✅ Downloaded {len(response.content):,} bytes in {time.time() - start_time:.1f}s")
        else:
            print(f"❌ Download failed: {response.status_code}")
            return
        
        # Test small upload
        print("4️⃣ Testing small TURSO upload...")
        cursor.execute("""
            INSERT OR REPLACE INTO torrents 
            (id, name, languages, episodes_available, total_size, anidb_id, torrent_files, build_timestamp, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            999999,
            "Test Torrent",
            json.dumps(["eng"]),
            json.dumps([1, 2, 3]),
            1024000,
            12345,
            json.dumps(["test.mkv"]),
            int(time.time()),
            '2.3_turso_test'
        ))
        
        conn.commit()
        
        # Verify upload
        cursor.execute('SELECT COUNT(*) FROM torrents')
        count = cursor.fetchone()[0]
        print(f"✅ Test upload successful: {count} rows")
        
        conn.close()
        
        print("\n🎯 DIAGNOSIS:")
        print("   • TURSO connection: ✅ Working")
        print("   • Schema creation: ✅ Working") 
        print("   • Data download: ✅ Working")
        print("   • TURSO upload: ✅ Working")
        print("   • CONCLUSION: Issue is in data PROCESSING loop!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_turso_test()
