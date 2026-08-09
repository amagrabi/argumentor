# Deploying argumentor

The app runs as a container on **Google Cloud Run** (project `argumentor-449922`,
region `europe-west1`), behind **Cloudflare** for DNS, CDN, and WAF on
`argumentorai.com`. Postgres is hosted on **Supabase** (project `ujkqrggdodazhldrcgbx`).

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
| Cloud Scheduler | 3 jobs | We use 2 (subscriptions, backups) |
| GCS (backups) | 5 GB free in us regions only | Dumps are ~17 MB; 30 days retention is well under a cent |
| Supabase | Free tier | **No backups** — hence the backup job below |
| Cloudflare | Free plan | DNS, CDN, WAF, cache rules |

Two guardrails keep this inside the free tier, both already set in
`scripts/deploy_cloudrun.sh`:

- **`--min-instances=0`.** A warm instance bills continuously and would exhaust the
  free allowance in days.
- **Default CPU throttling.** Never pass `--no-cpu-throttling`.

**Set a budget alert before going live.** Cloud Run has no spending cap, and unlike
Heroku's flat $10 this bill is variable:

```bash
gcloud billing budgets create --billing-account=$(gcloud billing projects describe argumentor-449922 --format='value(billingAccountName)' | cut -d/ -f2) --display-name="argumentor" --budget-amount=5USD --threshold-rule=percent=0.5 --threshold-rule=percent=1.0
```

The tradeoff you are accepting is **cold starts** — the app imports `grpcio`,
`google-cloud-aiplatform`, and `numpy` at boot. This is not a regression: Heroku Eco
dynos also slept after 30 minutes idle.

## One-time setup

### 1. Authenticate

```bash
gcloud auth login && gcloud config set project argumentor-449922
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
gcloud storage buckets create gs://argumentor-449922-backups --location=europe-west1 --uniform-bucket-level-access
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
SA="argumentor-run@argumentor-449922.iam.gserviceaccount.com"; for ROLE in roles/aiplatform.user roles/storage.objectAdmin roles/secretmanager.secretAccessor; do gcloud projects add-iam-policy-binding argumentor-449922 --member="serviceAccount:${SA}" --role="$ROLE"; done
```

### 5. Get the Supabase connection string

**Use the pooler, not the direct connection.** Supabase's direct connection
(`db.ujkqrggdodazhldrcgbx.supabase.co`) is IPv6-only on the free tier, and Cloud Run
egresses over IPv4 — a direct connection will simply fail to resolve.

From the Supabase dashboard → Connect, take the **Session pooler** string. It looks
like:

```
postgresql://postgres.ujkqrggdodazhldrcgbx:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

Session mode (port 5432) suits this app better than transaction mode (6543), because
SQLAlchemy manages its own connection pool and transaction mode does not support
prepared statements. Store it with the `+psycopg2` driver prefix:

```
postgresql+psycopg2://postgres.ujkqrggdodazhldrcgbx:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
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
of the data outside the live database:

```bash
gcloud scheduler jobs create http argumentor-backup --location=europe-west1 --schedule="0 4 * * *" --uri="https://europe-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/argumentor-449922/jobs/argumentor-backup:run" --http-method=POST --oauth-service-account-email="argumentor-run@argumentor-449922.iam.gserviceaccount.com"
```

Verify it end to end before trusting it — a backup you have never restored is not a
backup:

```bash
gcloud run jobs execute argumentor-backup --region=europe-west1 --wait && gcloud storage ls gs://argumentor-449922-backups/backups/
```

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
