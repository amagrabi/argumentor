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

**Probing a model id over REST needs `v1beta1`, not `v1`.** On the `global`
endpoint `v1` returns Google's *HTML* 404 page for every model, including ones
that exist — so a model-availability probe on `v1` reports that nothing is
available. The same probe is also flaky when fired in a tight loop: retry twice
with a pause before believing a 404. Measured Aug 2026, the ids that answer are
`gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-2.5-pro`
and `gemini-2.5-flash`. There is **no Gemini 3.x Pro** — `gemini-3.5-pro` and
`gemini-3.6-pro` both 404. `scripts/compare_deep_analysis_models.py` has the
working request shape, and runs without ADC off a `gcloud` access token.

**Thinking tokens are billed and counted as output.** They come out of
`max_output_tokens`, so a thinking model on the scored pass's 8192 can spend the
whole budget on thoughts and return `MAX_TOKENS` with an empty body. Deep
analysis uses 16384 for that reason.

**Two question-render paths exist.** `updateQuestionDisplay` in
`src/static/js/helpers.js` and `fetchNewQuestion` in `src/static/js/main.js`,
which writes the element directly via `typeWriter`. Anything that reacts to the
current question must be called from **both**, or it will silently never fire on
page load. `syncExampleButton` exists because of this.

**Static assets are cached for 7 days as `immutable` and are not fingerprinted.**
A CSS or JS change will not reach returning visitors, or Cloudflare's edge, for a
week. There is no cache-busting query string. Budget for this when shipping
frontend changes.

This bites `src/static/translations/*.json` too, which is worse than it sounds:
the templates carry English fallback text inside every `data-i18n` element, and
`applyTranslations` only assigns when the key resolves, so **English silently
falls back to whatever the template says while German goes live immediately** —
whichever file happened to be at the edge decides. Deep analysis shipped in that
state. Give any string the JS reads a hardcoded fallback, or purge the edge.

A *new* filename dodges the cache exactly once. `deepAnalysis.js` was split out
of `main.js` for that reason and it worked — then the follow-up fix to the same
new file was stale at the edge twenty minutes later. Land new frontend files
right the first time, or purge.

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

## Deep analysis: the one deliberately expensive call

`/deep_analysis` runs a second, unscored pass over an already-evaluated argument
on `gemini-2.5-pro` — ~$43 per 1000 calls against the scored pass's $2.65, and
40-52s per call. That ratio is the whole design: it is Plus/Pro only, capped
monthly, and never automatic. Measurements and the rejected alternatives are in
`DEEP_ANALYSIS_MODEL` in `config.py`; re-run
`scripts/compare_deep_analysis_models.py` before changing the model.

Two things follow from the latency. The result is stored on `answer` so a revisit
costs nothing, and a failed call must not count against the allowance — both are
covered in `tests/test_deep_analysis.py`. And a ~45s response has to clear
Cloudflare's 100s free-plan origin timeout; gunicorn's `--timeout 30` is *not* a
per-request deadline under `gthread`, because the worker heartbeats from its own
event loop independently of request threads.

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
