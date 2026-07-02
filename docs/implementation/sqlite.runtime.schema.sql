PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    session_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT NULL,
    device_id TEXT NOT NULL,
    operator_id TEXT NULL,
    guest_ref TEXT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS shots (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    shot_index INTEGER NOT NULL,
    capture_type TEXT NOT NULL,
    raw_asset_path TEXT NULL,
    preview_asset_path TEXT NULL,
    capture_started_at_utc TEXT NOT NULL,
    capture_completed_at_utc TEXT NULL,
    technical_score REAL NULL,
    ai_pick_score REAL NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS output_assets (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    template_version_id TEXT NULL,
    storage_scope TEXT NOT NULL,
    local_path TEXT NULL,
    remote_url TEXT NULL,
    checksum TEXT NULL,
    created_at_utc TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    scheduled_at_utc TEXT NOT NULL,
    last_error_code TEXT NULL,
    last_error_message TEXT NULL
);

CREATE TABLE IF NOT EXISTS consent_records (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    granted INTEGER NOT NULL,
    granted_at_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_event_time
    ON sessions(event_id, started_at_utc);

CREATE INDEX IF NOT EXISTS idx_jobs_status_priority_time
    ON jobs(status, priority, scheduled_at_utc);

CREATE INDEX IF NOT EXISTS idx_output_assets_session
    ON output_assets(session_id, asset_type);
