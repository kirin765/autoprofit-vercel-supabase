# Autoprofit

Autoprofit turns trend signals into revenue pages and deploys them automatically.

## Architecture

1. Fetch trend keywords from Google Trends RSS with local fallback keywords.
2. Match each keyword to configured affiliate offers.
3. Generate long-form monetization pages into `public/posts`.
4. Publish on Vercel (same project) with FastAPI endpoints for redirects, cron trigger, metrics, and Stripe.
5. Store operational data in `DATABASE_URL` (Postgres recommended) or local SQLite fallback.
6. Supports Supabase Postgres as first-class backend (`SUPABASE_DB_URL` or `SUPABASE_DB_*` fields).

Core files:

- Pipeline: `autoprofit/pipeline.py`
- API: `autoprofit/web.py`
- Storage: `autoprofit/database.py`
- Vercel API entrypoint: `api/index.py`
- Vercel rewrites config: `vercel.json`

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
autoprofit db-check
autoprofit init
autoprofit run --limit 2
autoprofit serve --host 0.0.0.0 --port 8000
```

Generated static output:

- `public/index.html`
- `public/posts/*.html`

## API endpoints

- `GET /health`
- `POST /api/cron/run` (optional `X-Cron-Token`)
- `GET /api/metrics`
- `GET /go/{slug}` (affiliate redirect + click log)
- `POST /api/stripe/checkout`
- `POST /api/stripe/webhook`
- `GET /api/subscription/status?email=...`

## Vercel CI/CD

Workflows:

- `.github/workflows/ci.yml`
  - `push`/`pull_request`: tests
  - PR (non-fork): preview deploy
  - `main` push: production deploy
- `.github/workflows/autopilot.yml`
  - hourly schedule: generate + deploy production

Required GitHub Secrets:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `DOMAIN_URL`
- `API_BASE_URL`
- `AFFILIATE_TAG`
- `DATABASE_URL` (or Supabase secrets below)
- `CRON_TOKEN`
- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`

Optional:

- `ALERT_WEBHOOK_URL` (failure notifications)
- Supabase alternatives:
  - `SUPABASE_DB_URL`
  - `SUPABASE_DB_HOST`
  - `SUPABASE_DB_PORT`
  - `SUPABASE_DB_NAME`
  - `SUPABASE_DB_USER`
  - `SUPABASE_DB_PASSWORD`
  - `SUPABASE_DB_SSLMODE`
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`

## Production checklist

1. Use managed Postgres in `DATABASE_URL` or `SUPABASE_DB_URL` (do not rely on ephemeral filesystem DB in serverless).
2. Configure Stripe webhook endpoint to `https://<your-domain>/api/stripe/webhook`.
3. Set `STRIPE_WEBHOOK_SECRET` from Stripe dashboard.
4. Confirm affiliate disclosures are compliant for each partner network.
5. Run a test purchase flow and confirm subscription status is persisted.

## Supabase quick setup

1. In Supabase dashboard, open `Project Settings > Database`.
2. Copy the Postgres connection string (prefer pooler host for serverless workloads).
3. Set one of:
   - `SUPABASE_DB_URL` directly, or
   - `SUPABASE_DB_HOST`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_NAME`.
4. Keep `SUPABASE_DB_SSLMODE=require` (default in this project).

## Compliance references

- FTC endorsement guides
- Amazon Associates requirements
- Stripe Checkout subscriptions
- Google Search spam policies

Details and links are in `references/monetization-research.md`.
