PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS hash_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    actor TEXT,
    location TEXT,
    doc_title TEXT,
    filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mimetype TEXT,
    algo_primary TEXT NOT NULL,
    sha256 TEXT,
    sha512 TEXT,
    blake2b TEXT,
    sha1 TEXT,
    md5 TEXT,
    notes TEXT,
    acta_blob BLOB,
    acta_filename TEXT
);
CREATE INDEX IF NOT EXISTS idx_hash_sha256 ON hash_events(sha256);