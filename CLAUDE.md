# argumentor

Flask app that scores user-written arguments with Gemini and gives structured
feedback. Runs on Google Cloud Run behind Cloudflare, with Supabase Postgres.

See [DEPLOY.md](DEPLOY.md) for infrastructure, secrets and cost controls.

## Things that will waste your time if you don't know them

**You cannot run the app locally without GCP credentials.** `src/extensions.py`
resolves Google credentials at import time, so `import app` fails with
`DefaultCredentialsError` on any machine without ADC. That error is the expected
"everything else imported fine" signal when smoke-testing in Docker:

```bash
docker run --rm -v "$PWD":/app --entrypoint python argumentor:cloudrun-test -c "
import sys; sys.path.insert(0,'/app'); sys.path.insert(0,'/app/src'); import app"
```

Reaching `DefaultCredentialsError` means the import graph is sound. Anything
earlier is a real break. Verification therefore happens by deploying and checking
the live site, not locally.

**`src/` is not a package.** There is no `src/__init__.py`. gunicorn runs
`src.app:app` from `/app`, and modules inside import each other bare
(`from routes.answers import ...`, `from config import ...`). It works because
both the repo root and `src/` end up on `sys.path`. Don't "fix" the imports.

**Vertex AI location must be `global`.** Gemini 3.x is served only from the global
endpoint and 404s in `us-central1`. `GCLOUD_PROJECT_REGION` is the location for
the genai clients, nothing else.

**Two question-render paths exist.** `updateQuestionDisplay` in
`src/static/js/helpers.js` and `fetchNewQuestion` in `src/static/js/main.js`,
which writes the element directly via `typeWriter`. Anything that reacts to the
current question must be called from **both**, or it will silently never fire on
page load. `syncExampleButton` exists because of this.

**Static assets are cached for 7 days as `immutable` and are not fingerprinted.**
A CSS or JS change will not reach returning visitors, or Cloudflare's edge, for a
week. There is no cache-busting query string. Budget for this when shipping
frontend changes.

**Tailwind comes from the Play CDN.** Some variants do not behave as documented —
`group-open:rotate-90` computed to the identity matrix, and a plain
`details[open] > summary .disclosure-chevron` rule lost to something in the
cascade even though the rule was in the loaded stylesheet and its selector
matched. When a transform silently doesn't apply, stop debugging the cascade and
set it from JS.

## Verifying changes

Deploy is the test loop: `./scripts/deploy_cloudrun.sh`. Then check the live
site — the browser is the only place most of this can be confirmed.

Measure rather than assume. Several bugs in this codebase looked like one thing
and were another:

- A "stale CSS cache" that was actually a cascade conflict.
- A "transition timing artifact" that was also the cascade conflict.
- A scroll that overshot by 15,000px because `focus()` re-scrolled while the
  results panel was still growing. Use `focus({preventScroll: true})`.

When a UI value looks wrong, read it out of the live DOM with
`getComputedStyle` / `querySelector` before theorising.

## Product context that should shape decisions

Real usage is tiny: 74 people have ever submitted an argument, 162 answers total
over 17 months, 16 registered, **zero** paying. The `visit` table is inflated by
bots and is not a traffic measure. Google Analytics is configured and is the
better source.

Consequences:

- Optimising conversion rates or upsell copy is premature. Distribution is the
  binding constraint.
- Quota-based paywalls cannot convert engaged users — the most active free user
  ever averaged 3 answers/month against a 30/month allowance. Paid tiers need
  capability differences, not bigger numbers.
- Anonymous users are cheap to create and their quota is keyed on a session
  cookie, so it is bypassable by clearing cookies. The real ceilings are the
  Cloudflare per-IP rate limit and the Vertex daily token quota.

## Evaluation prompt: measured behaviour

The prompts live in `src/services/llm.py`. Measured across 162 evaluations
(all `gemini-2.5-flash`):

- **Six dimensions, ~3 independent signals.** corr(Logic, Clarity) = 0.84,
  corr(Depth, Creativity) = 0.75, corr(Objectivity, Clarity) = 0.73. The model
  does not really distinguish them.
- **Relevance is a gate, not a grade.** sd 3.80, nearly double the others:
  off-topic → 1, on-topic → 8–10. It is excluded from
  `EVALUATION_CATEGORIES` and surfaced as its own notice.
- **Depth tracked length** (corr 0.60) despite the prompt saying it shouldn't.
  Fixed by defining depth operationally. If you touch that wording, re-measure.
- **~17% of feedback opened with one of eight stock phrases** despite the prompt
  forbidding templates.

Prompt changes need empirical checking. `scripts/test_llm.py` holds fixed EN/DE
cases. The tone instruction must name its output language explicitly: describing
it as "the language of these instructions" made the model answer the English
prompt in German, reproducibly.

## Conventions

- Commit messages: imperative subject, then *why* — the measurement or failure
  that motivated the change, not a restatement of the diff.
- Comments explain non-obvious constraints and rejected alternatives. Don't
  narrate what the code plainly does.
- Translations in `src/static/translations/{en,de}.json` are the single source of
  truth for user-facing strings **and** the question bank, and are read
  server-side by `question_service` and `_load_meta`.
- Never put a secret value in `--set-secrets` / `--update-secrets`; the
  right-hand side is a Secret Manager resource **name**. See DEPLOY.md.
