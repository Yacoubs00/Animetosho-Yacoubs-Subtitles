-- TURSO Database Schema for Animetosho Subtitles
-- Optimized for UPSERT operations and fast searches

-- Main torrents table
CREATE TABLE IF NOT EXISTS torrents (
    id INTEGER PRIMARY KEY,
    name TEXT,
    languages TEXT, -- JSON array of languages
    episodes_available TEXT, -- JSON array of episode numbers
    total_size INTEGER,
    anidb_id INTEGER,
    torrent_files TEXT, -- JSON array of torrent files
    build_timestamp INTEGER,
    version TEXT DEFAULT '2.3_turso_enhanced'
);

-- Subtitle files table
CREATE TABLE IF NOT EXISTS subtitle_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    torrent_id INTEGER NOT NULL,
    filename TEXT,
    language TEXT,
    episode_number INTEGER,
    size INTEGER,
    is_pack BOOLEAN DEFAULT 0,
    pack_url_type TEXT, -- 'attach' or 'torattachpk'
    pack_name TEXT,
    afid INTEGER,
    afids TEXT, -- JSON array of AFIDs
    target_episode INTEGER,
    download_url TEXT,
    FOREIGN KEY (torrent_id) REFERENCES torrents(id)
);

-- Indexes for fast searches
CREATE INDEX IF NOT EXISTS idx_torrent_name ON torrents(name);
CREATE INDEX IF NOT EXISTS idx_torrent_languages ON torrents(languages);
CREATE INDEX IF NOT EXISTS idx_subtitle_torrent_id ON subtitle_files(torrent_id);
CREATE INDEX IF NOT EXISTS idx_subtitle_language ON subtitle_files(language);
CREATE INDEX IF NOT EXISTS idx_subtitle_episode ON subtitle_files(episode_number);
CREATE INDEX IF NOT EXISTS idx_subtitle_pack ON subtitle_files(is_pack);

-- Language index table for fast language-based searches
CREATE TABLE IF NOT EXISTS language_index (
    language TEXT PRIMARY KEY,
    torrent_ids TEXT -- JSON array of torrent IDs
);

-- Build metadata table
CREATE TABLE IF NOT EXISTS build_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER
);
