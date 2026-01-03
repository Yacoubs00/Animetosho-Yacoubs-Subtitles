export default function handler(req, res) {
  const { q } = req.query;
  if (!q) return res.status(400).json({ error: 'Query required' });

  // Test response
  const results = [
    {
      name: `Attack on Titan - Test Result for "${q}"`,
      languages: ['eng', 'jpn'],
      download_url: 'https://animetosho.org/storage/attach/12345678/subtitle.ass.xz'
    }
  ];

  res.json({ results, total: 1 });
}
