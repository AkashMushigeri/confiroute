-- ConfiRoute SQLite Schema
-- Tracks queries, multi-signal confidence scores, routing decisions,
-- human review audit log, reference costs, and safety alerts.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS queries (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_letter TEXT,
    subject TEXT,
    topic TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    s1 REAL,
    s2 REAL,
    s3 REAL,
    combined REAL NOT NULL,
    mean_logprob REAL,
    agreement_stats_json TEXT,
    effective_weights_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    route TEXT NOT NULL,           -- 'direct', 'tier2', 'human'
    status TEXT NOT NULL,          -- 'completed', 'pending_tier2', 'pending_human'
    color TEXT NOT NULL,           -- 'green', 'yellow', 'red'
    ai_draft_answer TEXT,
    final_answer TEXT,
    tier_used TEXT,
    is_high_risk INTEGER NOT NULL, -- 0 or 1
    risk_reason TEXT,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    reviewer_name TEXT,
    decision TEXT,                 -- 'approved', 'edited', 'rejected'
    corrected_answer TEXT,
    notes TEXT,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    real_cost REAL DEFAULT 0.0,
    equivalent_cost REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at);
CREATE INDEX IF NOT EXISTS idx_routes_status ON routes(status);
CREATE INDEX IF NOT EXISTS idx_routes_query ON routes(query_id);
