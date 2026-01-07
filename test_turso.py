#!/usr/bin/env python3
# Test TURSO connection and create schema

import libsql_experimental as libsql
import json

def test_turso_connection():
    print("🔄 Testing TURSO connection...")
    
    try:
        # Connect to TURSO
        turso_url = "libsql://database-fuchsia-xylophone-vercel-icfg-leqyol2toayupqs5t2clktag.aws-us-east-1.turso.io"
        turso_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Njc3ODI2ODMsImlkIjoiMzUxZTVkNjQtMWYzMi00ZGQ1LWE3NTktNDZlOGJmMjdhZTIwIiwicmlkIjoiYTAzMmI2NjktOTAxNy00ZGU1LWIzNmUtMGRiMmE2OTIyNWJiIn0.QushOoxk4gLxLro4Y8iaU0Izh9DYKKlQ3KS8NZYKr75mK01uoj3bEz5o256yoFHIfqoIrbwvFeVPkT2GSk7_AA"
        
        conn = libsql.connect(
            "libsql://database-fuchsia-xylophone-vercel-icfg-leqyol2toayupqs5t2clktag.aws-us-east-1.turso.io",
            auth_token=turso_token
        )
        
        print("✅ Connected to TURSO successfully!")
        
        # Create schema
        print("📋 Creating database schema...")
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        # Execute schema creation
        for statement in schema.split(';'):
            if statement.strip():
                conn.execute(statement.strip())
        
        print("✅ Schema created successfully!")
        
        # Test insert
        print("🧪 Testing UPSERT operation...")
        conn.execute("""
            INSERT OR REPLACE INTO torrents 
            (id, name, languages, episodes_available, build_timestamp, version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            999999,
            "Test Anime",
            json.dumps(["eng", "jpn"]),
            json.dumps([1, 2, 3]),
            1767782683,
            "2.3_turso_test"
        ))
        
        # Test query
        result = conn.execute("SELECT * FROM torrents WHERE id = ?", (999999,))
        if result.fetchone():
            print("✅ UPSERT test successful!")
        
        # Clean up test data
        conn.execute("DELETE FROM torrents WHERE id = ?", (999999,))
        
        conn.commit()
        conn.close()
        
        print("🎉 TURSO setup complete and ready for migration!")
        
    except Exception as e:
        print(f"❌ TURSO test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_turso_connection()
