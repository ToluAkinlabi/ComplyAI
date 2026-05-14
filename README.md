# ComplyAI

ComplyAI is an AI tool for cybersecurity compliance and audit assessment. It compares an organization's current security policies against industry frameworks, identifies gaps, and provides prioritized recommendations.

## Steps

- Run `scripts/framework_loader.py` to convert framework source documents to JSON. Place source files in `data/frameworks_raw`.
- When controls change, rebuild the semantic index by running `scripts/rebuild_index.py`.
- If historical JSON reports do not include a `priority` field but are still needed for dashboard filters, run `scripts/patch_priority_in_reports.py`.

## Environment

### Backend

- `OPENAI_API_KEY`: required for AI-generated suggestions.
- `OPENAI_MODEL`: recommendation model, defaults to `gpt-4.1-mini`.
- `JWT_SECRET`: recommended explicit JWT signing key.
- `DEFAULT_ADMIN_EMAIL`: bootstrap admin email for local/admin auth.
- `DEFAULT_ADMIN_PASSWORD_HASH`: bcrypt password hash for bootstrap admin user.
- `DEFAULT_ORG_NAME`: default organization seeded for bootstrap admin.
- `DEFAULT_ORG_SLUG`: optional slug override for the seeded default organization.
- `DATABASE_URL`: SQLAlchemy connection string, defaults to `sqlite:///./complyai.db`.
- `AUTO_INIT_DB`: set to `false` to disable auto table creation at startup.
- `STRICT_MIGRATIONS`: set to `true` to require all tables to already exist (migration-only mode).
- `USE_DB_AUTH`: set to `false` to disable DB-backed auth and use in-memory fallback.
- `REQUIRE_AUTH`: set to `true` to require bearer authentication for report and dashboard API endpoints.
- `ENABLE_SUPABASE_STORAGE`: set to `true` to mirror report artifacts to Supabase Storage.
- `SUPABASE_URL`: Supabase project URL used for storage upload.
- `SUPABASE_SERVICE_ROLE_KEY`: service role key used for storage upload API calls.
- `SUPABASE_STORAGE_BUCKET`: storage bucket name for report artifact mirroring.
- `SEMANTIC_MODEL`: embedding model for semantic retrieval.
- `ENABLE_RERANKER`: set to `true` to enable cross-encoder reranking over top retrieval candidates.
- `RERANKER_MODEL`: reranker model name, defaults to `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- `RERANKER_CANDIDATE_MULTIPLIER`: candidate expansion factor before reranking.
- `RERANKER_TOP_N`: minimum number of candidates considered for reranking.
- `ALIGNED_THRESHOLD`: base semantic threshold for aligned classification.
- `WEAK_THRESHOLD`: base semantic threshold for weak classification.
- `MIN_CONFIDENCE_MARGIN`: minimum top1-top2 score gap for high-confidence alignment.
- `KEYWORD_OVERLAP_ALIGNED`: lexical overlap threshold that can support aligned classification.
- `KEYWORD_OVERLAP_WEAK`: lexical overlap threshold that can support weak classification.

### Frontend

- `VITE_API_BASE_URL`: backend API origin used by frontend requests, for example `http://localhost:8000`.
- `VITE_IS_ADMIN_UI`: set to `true` to show admin actions such as semantic index rebuild.

## SaaS Roadmap

- Execution checklist: `docs/saas-rollout-checklist.md`

## Supabase Setup

1. Copy backend env template:
   - `cp .env.example .env` (or create `.env` manually on Windows)
2. Set `DATABASE_URL` in `.env` to your Supabase Postgres connection string.
3. Keep `DB_SSLMODE=require` for Supabase.
4. Ensure dependencies are installed:
   - `pip install -r requirements.txt`
5. Supabase GitHub migration files are in:
   - `supabase/migrations/20260514120000_initial_multitenant_schema.sql`
   - `supabase/seed.sql`

### Backfill Existing Reports Into Registry

- If you already have historical reports in `reports/`, migrate them into DB registry:
  - Dry run: `python scripts/migrate_reports_registry.py --dry-run`
  - Execute: `python scripts/migrate_reports_registry.py`

### Strict Migration Mode

- For migration-only production startup, set:
  - `AUTO_INIT_DB=false`
  - `STRICT_MIGRATIONS=true`
- In this mode, API startup fails fast if required tables are missing.

## Multi-tenant Report Scope

- New reports are registered in the database with `organization_id` and `created_by_user_id`.
- Dashboard/report endpoints now resolve report access through this registry, enforcing org scope when auth is enabled.
- Report history endpoint with pagination/search/status filtering: `GET /reports/history`.
