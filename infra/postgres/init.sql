-- Orb Sys — PostgreSQL bootstrap
-- Roles map 1:1 to services. Each role has minimum required privileges only.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Roles
CREATE ROLE orbsys_app        WITH LOGIN PASSWORD 'change_me';
CREATE ROLE orbsys_blind      WITH LOGIN PASSWORD 'change_me';
CREATE ROLE orbsys_integrity  WITH LOGIN PASSWORD 'change_me';
CREATE ROLE orbsys_inferential WITH LOGIN PASSWORD 'change_me';
CREATE ROLE orbsys_insight    WITH LOGIN PASSWORD 'change_me';

-- Schema access
GRANT USAGE ON SCHEMA public
  TO orbsys_app, orbsys_blind, orbsys_integrity, orbsys_inferential, orbsys_insight;

-- Default privileges (applied to future tables created by migration role)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT ON TABLES TO orbsys_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT ON TABLES TO orbsys_integrity;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO orbsys_inferential;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO orbsys_insight;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE ON SEQUENCES TO orbsys_app, orbsys_integrity, orbsys_blind;

-- Specific blind role grants applied post-migration (see migrations/env.py)

-- ── Append-only trigger function ─────────────────────────────────────────────
-- Applied to: ledger_events, delta_c_events, delta_c_reviewers,
--             cell_contributions, cell_votes, stf_verdicts,
--             stf_unsealing_events, commons_posts
CREATE OR REPLACE FUNCTION enforce_append_only()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
    RAISE EXCEPTION
      'Table % is append-only. % is prohibited. '
      'Create a new row with supersedes= reference instead.',
      TG_TABLE_NAME, TG_OP;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
