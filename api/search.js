export default function handler(req, res) {
  const { q, lang, limit = 50 } = req.query;
  if (!q) return res.status(400).json({ error: 'Query required' });

  // Mock data until we fix database storage
  const mockResults = [
    {
      name: `[SubsPlease] Attack on Titan - Final Season Part 3 - 01 [1080p]`,
      languages: ['eng'],
      download_url: 'https://animetosho.org/storage/attach/1a2b3c4d/subtitle.ass.xz'
    },
    {
      name: `[Erai-raws] Shingeki no Kyojin - The Final Season Part 3 - 01 [1080p]`,
      languages: ['eng', 'spa'],
      download_url: 'https://animetosho.org/storage/attach/5e6f7g8h/subtitle.ass.xz'
    }
  ];

  // Filter by query
  const results = mockResults.filter(r => 
    r.name.toLowerCase().includes(q.toLowerCase())
  );

  res.json({ results, total: results.length });
}
