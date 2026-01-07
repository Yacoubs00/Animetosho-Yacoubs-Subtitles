// Debug endpoint - test blob connectivity
const BLOB_URL = 'https://kyqw0ojzrgq2c5ex.public.blob.vercel-storage.com/subtitles.json';

export default async function handler(req, res) {
    try {
        const response = await fetch(BLOB_URL, { method: 'HEAD' });
        const size = response.headers.get('content-length');
        
        res.json({
            blob_url: BLOB_URL,
            blob_accessible: response.ok,
            blob_size_mb: size ? (parseInt(size) / 1024 / 1024).toFixed(1) : null,
            status: 'Vercel Blob mode',
            env_vars: Object.keys(process.env).filter(k => k.includes('BLOB') || k.includes('TURSO'))
        });
    } catch (e) {
        res.json({ error: e.message, blob_url: BLOB_URL });
    }
}
