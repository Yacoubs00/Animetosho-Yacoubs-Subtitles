import { put } from '@vercel/blob';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const database = req.body;
    
    const blob = await put('subtitles.json', JSON.stringify(database), {
      access: 'public',
      token: process.env.BLOB_READ_WRITE_TOKEN
    });

    res.json({ success: true, url: blob.url });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

