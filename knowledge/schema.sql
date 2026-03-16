CREATE TABLE IF NOT EXISTS company_registry (
    account_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    incorporation_date TEXT,
    status TEXT,  -- active, dormant, dissolved
    directors TEXT,
    filing_status TEXT,  -- up_to_date, overdue, none
    country TEXT
);

CREATE TABLE IF NOT EXISTS adverse_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    headline TEXT NOT NULL,
    source TEXT,
    published_date TEXT,
    severity TEXT  -- low, medium, high
);

CREATE TABLE IF NOT EXISTS payment_history (
    account_id TEXT PRIMARY KEY,
    total_transactions INTEGER,
    avg_amount_gbp REAL,
    large_tx_count INTEGER,
    flagged_count INTEGER,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS sanctions_pep (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    list_type TEXT,  -- sanctions, pep, watchlist
    reason TEXT,
    listed_date TEXT
);
