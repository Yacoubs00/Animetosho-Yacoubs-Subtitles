# Anime Subtitles API

REST API for searching anime subtitles from AnimeTosho database.

## Endpoints

### Search Subtitles

**GET** `/api/search`

Search for anime subtitles by name and episode. Returns both single episodes and packs.

**Query Parameters:**
- `name` (required): Anime name to search for
- `episode` (optional): Episode number
- `language` (optional): Filter by language code (eng, jpn, por, etc.)

**Examples:**

```bash
# Search for all Zankyou no Terror torrents
curl "https://your-domain.vercel.app/api/search?name=Zankyou%20no%20Terror"

# Search for episode 3 specifically
curl "https://your-domain.vercel.app/api/search?name=Zankyou%20no%20Terror&episode=3"

# Search for English subtitles only
curl "https://your-domain.vercel.app/api/search?name=Zankyou%20no%20Terror&episode=3&language=eng"
```

**Response:**

```json
{
  "query": {
    "name": "Zankyou no Terror",
    "episode": "3",
    "language": null
  },
  "count": 5,
  "results": [
    {
      "torrent_id": 97921,
      "name": "[FFF] Zankyou no Terror - 03 [5BE3B540].mkv",
      "languages": ["eng"],
      "episodes_available": [3],
      "has_episode": true,
      "total_size": 367845376,
      "subtitle_files": [
        {
          "filename": "[FFF] Zankyou no Terror - 03 [5BE3B540].mkv",
          "language": "eng",
          "size": 1080945,
          "episode": 3,
          "is_pack": false,
          "download_url": "https://storage.animetosho.org/attach/0000b551/file.xz"
        }
      ]
    },
    {
      "torrent_id": 144551,
      "name": "[SallySubs] Zankyou no Terror - Vol.03 [BD 1080p FLAC]",
      "languages": ["eng"],
      "episodes_available": [5, 6],
      "has_episode": false,
      "total_size": 8589934592,
      "subtitle_files": [
        {
          "filename": "All Attachments (Complete Pack)",
          "language": "eng",
          "size": 5000000,
          "episode": null,
          "is_pack": true,
          "download_url": "https://storage.animetosho.org/torattachpk/144551/..."
        }
      ]
    }
  ]
}
```

**Response Fields:**
- `has_episode`: `true` if torrent has the exact episode, `false` if it's a pack that might contain it
- `is_pack`: `true` for pack files (complete season/volume), `false` for single episode
- `episodes_available`: Array of episode numbers available in this torrent

## Deployment

1. Install Vercel CLI: `npm i -g vercel`
2. Set environment variables:
   ```bash
   vercel env add TURSO_DATABASE_URL
   vercel env add TURSO_AUTH_TOKEN
   ```
3. Deploy: `vercel --prod`

## For Kodi Integration

The API returns both:
- **Single episodes**: Direct subtitle files for specific episodes
- **Packs**: Complete season/volume packs that may contain the episode

Kodi addon should:
1. Prioritize results where `has_episode: true`
2. Show pack files as alternative options
3. Use `download_url` to fetch subtitle files
