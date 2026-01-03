export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  
  const { q, lang, limit = 50 } = req.query;
  if (!q) return res.status(400).json({ error: 'Query required' });

  const mockResults = [
    {
      title: `[SubsPlease] Attack on Titan - Final Season Part 3 - 01 [1080p]`,
      subtitle_url: 'https://animetosho.org/storage/attach/1a2b3c4d/subtitle.ass.xz',
      languages: ['eng']
    }
  ];

  const results = mockResults.filter(r => 
    r.title.toLowerCase().includes(q.toLowerCase())
  );

  res.json({ success: true, data: results, count: results.length });
}

