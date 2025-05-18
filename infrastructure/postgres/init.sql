CREATE TABLE IF NOT EXISTS raw_events (
  id           SERIAL PRIMARY KEY,
  symbol       TEXT,
  event_type   TEXT,
  headline     TEXT,
  published_at TIMESTAMPTZ,
  raw_text     TEXT,
  source       TEXT,
  meta         JSONB
);
CREATE TABLE IF NOT EXISTS analysis (
  id            SERIAL PRIMARY KEY,
  event_id      INT REFERENCES raw_events(id),
  macro_view    TEXT,
  industry_view TEXT,
  peer_compare  TEXT,
  technical_view TEXT,
  impact_score  NUMERIC
);
