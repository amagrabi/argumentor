"""Measure latency and per-call cost of candidate deep-analysis models.

Deep analysis is the one place this app calls an expensive model on purpose, so
the model choice needs measuring rather than assuming — the same way
gemini-3.5-flash-lite was picked for the scored pass. This uses the *production*
deep-analysis prompt and the fixed EN/DE cases from `scripts/test_llm.py`,
against the Vertex REST API with a gcloud access token, so it runs on a laptop
with no ADC (see CLAUDE.md: `import app` cannot work locally).

    python scripts/compare_deep_analysis_models.py

Only the `global` endpoint is probed. Gemini 3.x is served nowhere else, and
`v1` 404s on it — `v1beta1` is the working path.
"""

import json
import subprocess
import sys
import time
import types
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# services.llm reaches Google credentials at import time via extensions, which is
# exactly what cannot be resolved off-GCP. Only the prompt text is needed here —
# the calls below go out over REST — so a stub keeps the import graph satisfied.
_stub = types.ModuleType("extensions")
_stub.google_credentials = None
try:
    from flask_sqlalchemy import SQLAlchemy

    _stub.db = SQLAlchemy()
except ImportError:  # pragma: no cover - only needed for models.py import
    _stub.db = None
sys.modules.setdefault("extensions", _stub)

from test_llm import TEST_DATA  # noqa: E402

from services.deep_analysis import build_deep_analysis_prompt  # noqa: E402
from services.llm import (  # noqa: E402
    DEEP_ANALYSIS_INSTRUCTION_DE,
    DEEP_ANALYSIS_INSTRUCTION_EN,
    DEEP_ANALYSIS_SCHEMA,
)

PROJECT = "argumentor-449922"
BASE = (
    f"https://aiplatform.googleapis.com/v1beta1/projects/{PROJECT}"
    "/locations/global/publishers/google/models"
)

# USD per 1M tokens on the global endpoint, from
# cloud.google.com/vertex-ai/generative-ai/pricing (Aug 2026). Thinking tokens
# are billed as output, which is the whole reason a Pro model costs what it does.
PRICES = {
    "gemini-3.5-flash-lite": (0.30, 2.50),  # the scored pass, for reference
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.6-flash": (1.50, 7.50),
    "gemini-2.5-pro": (1.25, 10.00),
}

CANDIDATES = ["gemini-2.5-pro", "gemini-3.6-flash", "gemini-3.5-flash"]

SAFETY = [
    {"category": c, "threshold": "OFF"}
    for c in (
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_HARASSMENT",
    )
]


def token():
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()


def call(model, system_instruction, prompt, access_token):
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "safetySettings": SAFETY,
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 16384,
            "responseMimeType": "application/json",
            "responseSchema": DEEP_ANALYSIS_SCHEMA,
        },
    }
    req = urllib.request.Request(
        f"{BASE}/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as e:
        return None, time.monotonic() - started, e.read().decode()[:400]
    return payload, time.monotonic() - started, None


def usage(payload):
    meta = payload.get("usageMetadata", {})
    prompt_tokens = meta.get("promptTokenCount", 0)
    # thoughtsTokenCount is reported separately but billed as output.
    thoughts = meta.get("thoughtsTokenCount", 0)
    candidates = meta.get("candidatesTokenCount", 0)
    return prompt_tokens, candidates, thoughts


def text_of(payload):
    parts = payload["candidates"][0]["content"].get("parts") or []
    return "".join(p.get("text", "") for p in parts if "text" in p)


def main():
    access_token = token()
    for language in ("en", "de"):
        data = TEST_DATA[language]
        instruction = (
            DEEP_ANALYSIS_INSTRUCTION_DE
            if language == "de"
            else DEEP_ANALYSIS_INSTRUCTION_EN
        )
        prompt = build_deep_analysis_prompt(
            data["question"],
            data["claim"],
            data["argument"],
            data["counterargument"],
            language=language,
        )
        for model in CANDIDATES:
            payload, elapsed, error = call(model, instruction, prompt, access_token)
            if error:
                print(f"{model} [{language}] FAILED after {elapsed:.1f}s: {error}")
                continue

            prompt_tokens, out_tokens, thought_tokens = usage(payload)
            in_price, out_price = PRICES[model]
            cost = (
                prompt_tokens * in_price + (out_tokens + thought_tokens) * out_price
            ) / 1_000_000

            body = text_of(payload)
            try:
                parsed = json.loads(body)
                shape = (
                    f"{len(parsed.get('reconstruction', []))} steps, "
                    f"{len(parsed.get('unstated_assumptions', []))} assumptions, "
                    f"{len(parsed.get('counterarguments', []))} objections, "
                    f"{len(parsed.get('rebuild', []))} rebuild steps"
                )
            except json.JSONDecodeError:
                parsed, shape = None, "UNPARSEABLE"

            print(
                f"{model:24} [{language}] {elapsed:6.1f}s  "
                f"${cost * 1000:7.2f}/1k  "
                f"in={prompt_tokens:5} out={out_tokens:5} thought={thought_tokens:5} "
                f"chars={len(body):5}  {shape}"
            )
            # tmp/ is gitignored: these are for reading side by side, not keeping.
            out = ROOT / "tmp" / "deep_analysis_models" / f"{model}.{language}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False) if parsed else body,
                encoding="utf-8",
            )
            print(f"    -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
