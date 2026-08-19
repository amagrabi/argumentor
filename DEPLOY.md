# Deploying argumentor

> **Identifiers in this file are redacted.** This repository is public. Replace
> `<PROJECT_ID>`, `<PROJECT_NUMBER>`, `<BILLING_ACCOUNT_ID>`,
> `<SUPABASE_PROJECT_REF>`, `<CF_ACCOUNT_ID>` and `<SERVICE>` with the real
> values from your password manager before running any command below. They are
> not credentials, but they are free reconnaissance for anyone probing the setup,
> and the `*.run.app` hostname in particular bypasses Cloudflare entirely.

The app runs as a container on **Google Cloud Run** (project `<PROJECT_ID>`,
region `europe-west1`), behind **Cloudflare** for DNS, CDN, and WAF on
`argumentorai.com`. Postgres is hosted on **Supabase** (project `<SUPABASE_PROJECT_REF>`).

This replaces the previous Heroku setup, which no longer exists.

## Cost expectations

Effectively free at low traffic, but not literally $0:

| Service | Free allowance | Notes |
| --- | --- | --- |
| Cloud Run | 2M requests, 240k vCPU-s, 450k GiB-s / month | Comfortable **only** with `--min-instances=0` and default CPU throttling. At 1Gi that is 125 instance-hours/month |
| Cloud Run egress | 1 GiB/month | The real risk: `src/static/vid` is 33 MB. The Cloudflare cache rule below is what keeps this small |
| Artifact Registry | 0.5 GB | The image is 1.22 GB, so expect a few cents/month. Prune old tags |
| Secret Manager | 6 active versions, 10k accesses/month | We use ~13 secrets; slightly over |
| Cloud Build | 2,500 build-min/month | Fine |
| Cloud Scheduler | 3 jobs | We use all 3 (subscriptions, backups, visit pruning) |
| GCS (backups) | 5 GB free in us regions only | Dumps are ~17 MB; 30 days retention is well under a cent |
| Supabase | Free tier | **No backups** — hence the backup job below |
| Cloudflare | Free plan | DNS, CDN, WAF, cache rules |

Two guardrails keep this inside the free tier, both already set in
`scripts/deploy_cloudrun.sh`:

- **`--min-instances=0`.** A warm instance bills continuously and would exhaust the
  free allowance in days.
- **Default CPU throttling.** Never pass `--no-cpu-throttling`.

**A budget alert is in place** (`argumentor monthly`, €5, alerting at 50/90/100%).
Cloud Run has no spending cap, and unlike Heroku's flat $10 this bill is variable.

```bash
gcloud billing budgets create --billing-account=<BILLING_ACCOUNT_ID> --display-name="argumentor monthly" --budget-amount=5EUR --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

The amount **must be in the billing account's own currency** — this account is EUR,
and passing `5USD` fails with a bare `INVALID_ARGUMENT` that names no field.

The tradeoff you are accepting is **cold starts** — the app imports `grpcio`,
`google-cloud-aiplatform`, and `numpy` at boot. This is not a regression: Heroku Eco
dynos also slept after 30 minutes idle.

## Abuse and cost controls

Layered, cheapest first. None of these is sufficient alone.

| Layer | What it does | Where |
| --- | --- | --- |
| Cloudflare rate limit | 5 req/10s per IP on `/submit_answer`, `/transcribe_voice`, `/submit_challenge_response`, then a 10s block. Runs at the edge before Cloud Run wakes, and sees the true client IP | Security → Security rules → Rate limiting (1/1 free rules used) |
| Cloudflare custom rule | Blocks WordPress scanner paths | Security → Security rules (1/5 free rules used) |
| Vertex AI daily quota | 1M input tokens/day for `gemini-3.5-flash-lite` ≈ 600 evaluations, capping LLM spend near $2/day. The default was 5 **billion** | `gcloud quotas preferences list` |
| Vertex AI per-minute quota | 100k input tokens/min, so a burst cannot exhaust the daily budget in one minute | same |
| OpenAI hard spend cap | **Set this manually** — Project settings → Limits → Spend → enforce a hard limit. Returns 429 `project_spend_limit_exceeded` | platform.openai.com |
| App tier limits | Per-user monthly and daily caps, DB-backed so they survive restarts | `config.py` |
| Flask-Limiter | Per-instance burst backstop only. In-memory, so buckets reset on cold start — Cloudflare is the real gate | `config.py`, `extensions.py` |

Google has **no hard spend cap**. The €5 budget alert notifies; it does not stop
anything. Quotas are the only real ceiling short of a billing-disable function.

Note the residual gap: the `*.run.app` URL bypasses Cloudflare entirely, so the edge
rules can be sidestepped by anyone who finds it. Closing that means requiring a shared
secret header at the origin.

A second gap: the app tier limits are keyed on the anonymous visitor's session cookie,
so clearing cookies buys another anonymous allowance (3 evaluations, 1 voice
recording). Not persisting those visitors removed the *storage* cost of that — see
[Database size](#database-size) — but not the abuse itself. For a caller who is willing
to cycle cookies, the real ceiling is the Cloudflare per-IP rate limit and the Vertex
daily quota, not the tier limit. Making the tier limit bind would mean counting
anonymous usage per IP rather than per identity, which is a different design: it needs
storage that survives a cold start, and it lumps everyone behind a shared NAT together.

To adjust a quota:

```bash
gcloud quotas preferences create --project=<PROJECT_ID> --service=aiplatform.googleapis.com --quota-id=GlobalGenerateContentInputTokensPerDayPerBaseModel --preferred-value=2000000 --dimensions=base_model=gemini-3.5-flash-lite-qcd --preference-id=argumentor-daily-input-tokens --allow-high-percentage-quota-decrease
```

Gemini 3.x models are dimensioned as `<model>-qcd` in quotas, and only exist on the
`global` endpoint — the per-region quota rejects `global` as a region name.

## One-time setup

### 1. Authenticate

```bash
gcloud auth login && gcloud config set project <PROJECT_ID>
```

### 2. Enable APIs

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com storage.googleapis.com cloudscheduler.googleapis.com
```

### 3. Create the Artifact Registry repo and buckets

```bash
gcloud artifacts repositories create argumentor --repository-format=docker --location=europe-west1
```

```bash
gcloud storage buckets create gs://<PROJECT_ID>-backups --location=europe-west1 --uniform-bucket-level-access
```

The voice-recording bucket from the Heroku era survives as `gs://argumentor`
(EUROPE-WEST4, containing `voice_recordings/`), and is what `GCS_BUCKET` points at.
It is in a different region than the service — fine functionally, but cross-region
reads cost a little more than same-region ones.

### 4. Create the runtime service account

The app reaches Vertex AI and GCS through Application Default Credentials, resolved
from the attached service account. No JSON key file is involved, and
`GOOGLE_APPLICATION_CREDENTIALS` must stay unset.

```bash
gcloud iam service-accounts create argumentor-run --display-name="argumentor Cloud Run runtime"
```

```bash
SA="argumentor-run@<PROJECT_ID>.iam.gserviceaccount.com"; for ROLE in roles/aiplatform.user roles/storage.objectAdmin roles/secretmanager.secretAccessor; do gcloud projects add-iam-policy-binding <PROJECT_ID> --member="serviceAccount:${SA}" --role="$ROLE"; done
```

### 5. Get the Supabase connection string

**Use the pooler, not the direct connection.** Supabase's direct connection
(`db.<SUPABASE_PROJECT_REF>.supabase.co`) is IPv6-only on the free tier, and Cloud Run
egresses over IPv4 — a direct connection will simply fail to resolve.

From the Supabase dashboard → Connect, take the **Session pooler** string. It looks
like:

```
postgresql://postgres.<SUPABASE_PROJECT_REF>:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

Session mode (port 5432) suits this app better than transaction mode (6543), because
SQLAlchemy manages its own connection pool and transaction mode does not support
prepared statements. Store it with the `+psycopg2` driver prefix:

```
postgresql+psycopg2://postgres.<SUPABASE_PROJECT_REF>:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

Connection budget: `DB_POOL_SIZE=2` and `DB_MAX_OVERFLOW=3` are set per gunicorn
worker, so the worst case is 2 workers × 5 × 3 instances = 30 connections. Raise
`--max-instances` and this scales with it — check Supabase's pooler limit first.

### 6. Create the secrets

Every value has to be re-sourced from its provider; the old Heroku app is gone, so
nothing can be exported from it.

| Secret | Where to get it |
| --- | --- |
| `SECRET_KEY` | Generate fresh: `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `SQLALCHEMY_DATABASE_URI` | Supabase session pooler string from step 5 |
| `OPENAI_API_KEY` | OpenAI dashboard |
| `GOOGLE_CLIENT_ID` | Cloud console → APIs & Services → Credentials → **OAuth 2.0 Client ID** (type: Web application). Not an API key. The matching client *secret* is not needed — see `config.py` |
| `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_DEFAULT_SENDER` | Gmail app password |
| `STRIPE_SECRET_KEY` / `STRIPE_PUBLIC_KEY` | Stripe → Developers → API keys |
| `STRIPE_WEBHOOK_SECRET` | Stripe → Webhooks (recreate the endpoint against `https://argumentorai.com/...`) |
| `STRIPE_PLUS_PRICE_ID` / `STRIPE_PRO_PRICE_ID` | Stripe → Products |

Run the helper, which prompts for each value with a hidden read so nothing reaches
shell history or the process list:

```bash
./scripts/set_secrets.sh
```

Press Enter alone at the `SECRET_KEY` prompt to have it generate a random one.
Existing secrets are skipped rather than overwritten.

Check what is in place at any time:

```bash
./scripts/set_secrets.sh --verify
```

Rotate a specific value later:

```bash
./scripts/set_secrets.sh --rotate STRIPE_SECRET_KEY
```

Cloud Run resolves `:latest` at **instance startup**, so a new secret version does not
reach already-running instances. Force a fresh revision off the existing image rather
than rebuilding:

```bash
gcloud run services update argumentor --region=europe-west1 --update-secrets "STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest"
```

In `--update-secrets ENV_VAR=NAME:VERSION`, the right-hand side is a **Secret Manager
resource name, never a secret value**. Pasting the value there creates a reference to a
secret that does not exist, and the deploy fails with
`secret .../versions/latest was not found` — with the value itself now sitting in the
Service spec, your shell history, and the audit log. If that happens, repair the
reference and then roll the leaked credential at its source. Note that the failed
deploy still writes the bad spec, so "the deploy failed" does not mean nothing changed.

### 7. Restore the database into Supabase

The last production dump is at
`~/data/argumentor/b98a2406-f164-4a6a-a61d-d0a88c49314c` (Postgres custom format,
17 MB, from Heroku DB `dfo36e61ql260b`).

Restore through the pooler, with `--no-owner --no-acl` because Supabase's `postgres`
role is not a superuser and the dump carries Heroku's role grants:

```bash
pg_restore --no-owner --no-acl --clean --if-exists -d "$SUPABASE_SESSION_POOLER_URL" ~/data/argumentor/b98a2406-f164-4a6a-a61d-d0a88c49314c
```

Some `DROP` statements will warn on a fresh database — that is expected with
`--if-exists`. Afterwards confirm the Alembic revision came across, so the first
`flask db upgrade` is a no-op rather than a surprise:

```bash
psql "$SUPABASE_SESSION_POOLER_URL" -c 'select * from alembic_version;'
```

### 8. Update the Google OAuth client

On the OAuth 2.0 Client ID in the Cloud console, set **Authorized JavaScript origins**
to `https://argumentorai.com` and remove the old `*.herokuapp.com` entry.

Sign-in runs through Google Identity Services in JavaScript-callback mode
(`src/static/js/auth.js`), which posts the ID token to `/google-auth` via `fetch`.
That means JavaScript origins is the setting that matters; authorized redirect URIs
are not used by this flow.

## Deploying

```bash
./scripts/deploy_cloudrun.sh
```

Builds one image, runs `flask db upgrade` as a Cloud Run Job against it (Cloud Run has
no release phase, so migrations are an explicit gate before rollout), deploys the
service, and updates the backup job.

## Scheduled jobs

Subscription expiry (replaces Heroku Scheduler):

```bash
gcloud scheduler jobs create http argumentor-subscription-check --location=europe-west1 --schedule="0 3 * * *" --uri="https://argumentorai.com/check-subscription-expirations?api_key=YOUR_SECRET_KEY" --http-method=GET
```

The key goes in the query string because that is how the endpoint is written today,
which means it lands in Cloud Scheduler config and access logs. Worth moving to a
header at some point.

Nightly backup — Supabase's free tier takes **no** backups, so this is the only copy
of the data outside the live database. Already created, running 04:00 Europe/Berlin.

The runtime service account needs `run.invoker` **on the job** or Cloud Scheduler gets
a 403 and no execution is ever created — a silent failure, since the scheduler job
itself still looks healthy:

```bash
gcloud run jobs add-iam-policy-binding argumentor-backup --region=europe-west1 --member="serviceAccount:argumentor-run@<PROJECT_ID>.iam.gserviceaccount.com" --role=roles/run.invoker
```

```bash
gcloud scheduler jobs create http argumentor-backup --location=europe-west1 --schedule="0 4 * * *" --time-zone="Europe/Berlin" --uri="https://europe-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/argumentor-backup:run" --http-method=POST --oauth-service-account-email="argumentor-run@<PROJECT_ID>.iam.gserviceaccount.com"
```

Verify through the scheduler rather than just running the job directly — invoking the
job by hand does not exercise the IAM path that the scheduler uses:

```bash
gcloud scheduler jobs run argumentor-backup --location=europe-west1 && sleep 90 && gcloud storage ls gs://<PROJECT_ID>-backups/backups/
```

Visit pruning, keeping the `visit` table inside `VISIT_RETENTION_DAYS` (90):

```bash
gcloud scheduler jobs create http argumentor-prune-visits --location=europe-west1 --schedule="0 5 * * *" --uri="https://argumentorai.com/prune-visits?api_key=YOUR_SECRET_KEY" --http-method=GET
```

Same query-string key as the subscription job, with the same caveat. This is the third
of Cloud Scheduler's three free jobs — a fourth starts costing.

A backup you have never restored is not a backup; restore one into a scratch database
before you rely on it.

## Database security

Supabase serves a PostgREST **Data API** off the `public` schema. This app never calls
it — it reaches Postgres as `postgres` through the session pooler via SQLAlchemy — but
Supabase's default privileges had granted `anon` and `authenticated` full DML on every
table anyway, with RLS off. Any key mapping to `anon` (the legacy `anon` JWT or a
`sb_publishable_…` key, both meant to ship in public client code) could therefore have
read or deleted everything. Three things now stand between that and the data, in
increasing order of durability:

1. **The Data API is disabled**, at
   `dashboard/project/<SUPABASE_PROJECT_REF>/integrations/data_api/overview` →
   *Enable Data API* off. With it off no auto-generated endpoint responds, whatever the
   grants or RLS say. This is the only control that also stops a leaked
   `service_role` / `sb_secret_…` key, because `service_role` has `rolbypassrls` and
   walks through RLS by design. It lives only in the dashboard — nothing in the repo or
   the database records it, so it cannot be verified from code.
2. **RLS is enabled with an explicit `deny_all` policy, and the `anon`/`authenticated`
   grants are revoked** — migrations `c4e8a1d5f207` and `d7b3e05a9c14`. Safe for the app
   because `postgres` also has `rolbypassrls`. RLS with no policies already denied
   everything; the `FOR ALL USING (false) WITH CHECK (false)` policy exists so the intent
   is legible and the advisor's `rls_enabled_no_policy` can tell deny-all from an
   oversight. RLS and the policies survive a restore, the REVOKEs do not: `backup_db.py`
   dumps with `--no-acl`, which omits GRANT/REVOKE, while RLS and policies are part of
   the schema. A **new table gets none of them by default** — enable RLS and add the
   policy in the migration that creates it.
3. **`pg_stat_statements` was moved out of `public`** into `extensions`, so its views are
   not in an API-exposed schema at all. Supabase installed it in `public` and owns it as
   `supabase_admin`, and its two views keep `anon` grants that `postgres` cannot revoke;
   relocating the extension sidesteps that instead. Applied as a one-off rather than a
   migration, because it is Supabase-provisioned infra rather than app schema and a fresh
   project already places extensions in `extensions`:

   ```bash
   psql "$SUPABASE_SESSION_POOLER_URL" -c 'ALTER EXTENSION pg_stat_statements SET SCHEMA extensions;'
   ```

   `postgres` is permitted this despite not owning the extension (supautils). Reverse
   with `SET SCHEMA public` if it ever disturbs the dashboard's Query Performance page.

After restoring into a fresh project, re-check all three — then re-run the Security
Advisor, which should report zero errors and zero warnings.

## Database size

Supabase's free tier caps the database at 500 MB and gives no warning before it bites.
Two tables used to grow without bound, measured on a restored Aug 2026 backup that held
**162 answers**:

- **`users`, 86 MB.** Every visitor arriving without a session cookie got a row, on
  every non-static request — which, since bots never return a cookie, meant one row per
  bot request. 253,915 rows, 253,841 of them (99.97%) with zero answers. Anonymous
  identities now live in the session cookie only, and a row is written at the first real
  action: an answer, a voice recording, feedback, or a checkout. See
  `src/services/user_service.py`.
- **`visit`, 47 MB.** Append-only, and nothing in the app reads it. Requests that return
  no session cookie are no longer logged at all, and `/prune-visits` trims the rest
  nightly.

Both changes stop the growth. Neither removes what is already there.

### One-time purge of the backlog

Take a backup first — the nightly job is the only copy of this data:

```bash
gcloud scheduler jobs run argumentor-backup --location=europe-west1
```

Then see what would go. This touches nothing:

```bash
python scripts/purge_orphan_users.py
```

It only considers users on the anonymous tier with no credentials, no Stripe ids, **no
answers and no feedback**. The feedback condition matters: `feedback.user_uuid` is
`ON DELETE CASCADE`, so deleting the user would silently take their message with it.
`user_achievements` is the mirror image — its foreign key was created with no cascade at
all, so the script deletes those rows itself first or the users delete fails.

When the counts look right:

```bash
python scripts/purge_orphan_users.py --apply --visits
```

`--visits` also trims the visit backlog, so both tables can be reclaimed in one pass.
Deletes run in batches of 5,000 with a commit each, so the run is safe to interrupt and
re-run.

### Reclaiming the space

**Deleting rows does not shrink the database.** Postgres marks the space reusable and
leaves the file the same size, so the Supabase dashboard will barely move and you are
still as close to the 500 MB cap as you were. Getting the space back needs a rewrite:

```bash
psql "$SUPABASE_SESSION_POOLER_URL" -c 'VACUUM FULL VERBOSE users; VACUUM FULL VERBOSE visit;'
```

Two things to know before running it. `VACUUM FULL` takes an `ACCESS EXCLUSIVE` lock for
its duration, so reads *and* writes on that table block — at this size that is seconds,
but do it off-peak. And it builds the new copy before dropping the old, so it needs free
disk roughly equal to the table's current size.

Use the **session** pooler, as in the command above: `VACUUM` cannot run inside a
transaction block, which is all the transaction pooler offers. Confirm afterwards:

```bash
psql "$SUPABASE_SESSION_POOLER_URL" -c "select pg_size_pretty(pg_database_size(current_database()));"
```

The nightly `/prune-visits` job needs no VACUUM of its own — the space it frees is
immediately reused by new rows, which is exactly what autovacuum is for. VACUUM FULL is
only for recovering a backlog.

## Cloudflare setup

`argumentorai.com` is already on Cloudflare. Cloud Run's own domain mapping is the only
free way to attach the domain — a Global External Application Load Balancer costs
~$18/month and would erase the entire cost saving. Note that Google labels domain
mappings "preview, not recommended for production" on latency grounds; Cloudflare's
cache absorbs most of that for static assets.

1. Map both hostnames (`gcloud components install beta` first if needed):

```bash
gcloud beta run domain-mappings create --service=argumentor --domain=argumentorai.com --region=europe-west1 && gcloud beta run domain-mappings create --service=argumentor --domain=www.argumentorai.com --region=europe-west1
```

2. Add the records it prints. The **apex takes A/AAAA records, not a CNAME** — only the
   `www` subdomain gets a CNAME:

| Type | Name | Value |
| --- | --- | --- |
| A | `argumentorai.com` | `216.239.32.21`, `216.239.34.21`, `216.239.36.21`, `216.239.38.21` |
| AAAA | `argumentorai.com` | `2001:4860:4802:32::15`, `:34::15`, `:36::15`, `:38::15` |
| CNAME | `www` | `ghs.googlehosted.com` |

   Keep the existing `google-site-verification` TXT record — it is what lets the domain
   mapping verify ownership.

3. Create all of them **DNS-only (grey cloud)**. Google's managed certificate cannot
   validate while Cloudflare proxies the record, and proxying too early leaves you
   stuck without a cert.
4. Wait for the certificate. `DomainRoutable` goes `True` as soon as DNS is right, but
   `CertificateProvisioned` lags — Google re-polls every 5 minutes and it can take an
   hour or more:

```bash
gcloud beta run domain-mappings describe --domain=argumentorai.com --region=europe-west1 --format=json | python3 -c "import json,sys; [print(c['type'], c['status']) for c in json.load(sys.stdin)['status']['conditions']]"
```

5. Only once that reads `True`, switch the records to **proxied (orange cloud)**.
   SSL/TLS is already **Full (strict)** on this zone, which is correct — Google
   presents a valid certificate, so strict verification succeeds.
6. Cache rule for static assets — the highest-value step, since it keeps 33 MB of video
   out of Cloud Run egress:
   - Expression: `starts_with(http.request.uri.path, "/static/")`
   - Cache eligibility: Eligible for cache
   - **Leave Edge TTL unset** so Cloudflare respects the origin. The app sends
     `max-age=604800, immutable` but its assets are *not* fingerprinted (no `?v=` in
     the templates), so a longer edge TTL would keep serving stale CSS/JS for weeks
     after a deploy. Even the origin's own 7 days is aggressive for unversioned files;
     adding cache-busting query strings would be the real fix.
7. WAF: **managed rulesets are not available on the Free plan** — that section offers
   only "Upgrade plan". Free gives 5 custom rules and 1 rate-limiting rule instead. A
   custom rule named "Block WordPress scanners" blocks the unambiguous patterns at the
   edge, saving Cloud Run invocations and cold starts:

```
(lower(http.request.uri.path) contains "wp-") or (lower(http.request.uri.path) contains "wordpress") or (lower(http.request.uri.path) contains "xmlrpc.php") or (lower(http.request.uri.path) contains "wlwmanifest.xml")
```

   The broader patterns in `WP_PATTERNS` (`/blog/`, `/test/`, `/media/`, `/news/` …)
   are deliberately *not* in the edge rule — they are generic enough to collide with
   real routes later. `block_wp_scanners` in `src/middleware.py` still handles those
   and is **not** redundant.

If the domain mapping proves flaky or a certificate renewal fails, the fallback is a
Cloudflare Worker reverse-proxying to the `*.run.app` URL — fully supported, free up
to 100k requests/day, at the cost of an extra hop and some code.

Note that the `*.run.app` URL stays publicly reachable either way, so the Cloudflare
rules can be bypassed by hitting it directly. Acceptable at this stage; closing it
means requiring a shared secret header at the origin.

### Optional: move voice recordings to R2

`src/routes/transcribe.py` uploads audio to GCS. Cloudflare R2 has a 10 GB free tier
with zero egress fees and an S3-compatible API. Switching would cut the GCS bill but
is a code change (`google-cloud-storage` → `boto3`), out of scope for this migration.
