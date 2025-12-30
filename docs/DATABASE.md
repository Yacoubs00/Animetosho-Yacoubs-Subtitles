Database Schema – Optimized AnimeTosho Subtitles Index
The optimized database is stored as a compressed pickle file (optimized_db.pkl.gz). It contains only torrents that have at least one extracted subtitle track.
Top-Level Structure
Python{
    'torrents': dict,        # torrent_id (str) → torrent data
    'languages': dict,       # language_code (str) → list of torrent_ids
    'stats': dict            # metadata and counts
}
Torrents Dictionary
Key: torrent ID (string representation of the internal AnimeTosho torrent identifier)
Value:
Python{
    'name': str,                     # Torrent title from torrents table
    'languages': list[str],          # Sorted list of unique language codes present
    'subtitle_files': list[dict]     # List of files containing subtitles
}
Each entry in subtitle_files:
Python{
    'file_id': str,                  # Internal file identifier
    'filename': str,                 # Original filename from the torrent
    'subs': list[dict]               # List of subtitle tracks
}
Each subtitle track:
Python{
    'lang': str,                     # Language code (e.g., "eng", "ara", "jpn", "und")
    'afid': int,                     # Attachment file ID used for downloads
    'url': str                       # Pre-computed direct download URL
}
Languages Index
Key: language code (string)
Value: list of torrent IDs that contain subtitles in that language. Useful for quick filtering.
Stats Dictionary
Python{
    'last_updated': str,             # ISO 8601 timestamp (UTC)
    'torrent_count': int,            # Number of torrents with subtitles
    'subtitle_tracks': int,          # Total number of individual subtitle tracks
    'language_count': int            # Number of distinct languages found
}
Language Codes
Common codes include:

eng – English
spa – Spanish
por – Portuguese
fre – French
ger – German
ita – Italian
rus – Russian
ara – Arabic
jpn – Japanese
chi – Chinese
und – Unknown/undetermined

Additional codes follow ISO 639-2/3 standards.
Download URL Construction
Use the url field provided in each subtitle entry, or construct manually from afid:
texthttps://storage.animetosho.org/attach/{printf("%08x", afid)}/file.xz
This schema enables fast client-side searches by torrent name, ID, or language while keeping the database size small and load times short.
