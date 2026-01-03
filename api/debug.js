export default function handler(req, res) {
  res.json({
    DATABASE_BLOB_URL: process.env.DATABASE_BLOB_URL,
    all_env_vars: Object.keys(process.env).filter(key => key.includes('DATABASE'))
  });
}
