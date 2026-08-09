#!/usr/bin/env bash
#
# Create (or rotate) the Secret Manager entries the Cloud Run service needs.
#
# Prompts for each value with a silent read, so nothing lands in shell history,
# in the process list, or on screen. Values go straight to `gcloud secrets`
# via stdin.
#
# Usage:
#   ./scripts/set_secrets.sh           # create missing secrets, prompt per value
#   ./scripts/set_secrets.sh --verify  # report which secrets exist, no values read
#   ./scripts/set_secrets.sh --rotate NAME [NAME...]   # add a new version
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-argumentor-449922}"

# name|prompt
SECRETS=(
  "SECRET_KEY|Flask secret key (press Enter alone to generate a random one)"
  "SQLALCHEMY_DATABASE_URI|Supabase session pooler URL (postgresql+psycopg2://...:5432/postgres)"
  "OPENAI_API_KEY|OpenAI API key (sk-...)"
  "GOOGLE_CLIENT_ID|Google OAuth client ID (OAuth 2.0 Client ID, Web application)"
  "MAIL_USERNAME|Gmail address used to send mail"
  "MAIL_PASSWORD|Gmail app password"
  "MAIL_DEFAULT_SENDER|Default From: address"
  "STRIPE_SECRET_KEY|Stripe secret key (sk_live_... or sk_test_...)"
  "STRIPE_PUBLIC_KEY|Stripe publishable key (pk_...)"
  "STRIPE_WEBHOOK_SECRET|Stripe webhook signing secret (whsec_...)"
  "STRIPE_PLUS_PRICE_ID|Stripe price ID for the Plus plan (price_...)"
  "STRIPE_PRO_PRICE_ID|Stripe price ID for the Pro plan (price_...)"
)

exists() {
  gcloud secrets describe "$1" --project "$PROJECT_ID" >/dev/null 2>&1
}

store() {
  # $1 = secret name, value on stdin
  if exists "$1"; then
    gcloud secrets versions add "$1" --project "$PROJECT_ID" --data-file=- >/dev/null
    echo "  rotated $1 (new version)"
  else
    gcloud secrets create "$1" --project "$PROJECT_ID" --data-file=- >/dev/null
    echo "  created $1"
  fi
}

verify() {
  local missing=0
  echo "Secrets in project ${PROJECT_ID}:"
  for entry in "${SECRETS[@]}"; do
    local name="${entry%%|*}"
    if exists "$name"; then
      printf '  [ok]      %s\n' "$name"
    else
      printf '  [MISSING] %s\n' "$name"
      missing=$((missing + 1))
    fi
  done
  if [[ $missing -gt 0 ]]; then
    echo
    echo "${missing} secret(s) missing. Run without --verify to add them."
    return 1
  fi
  echo
  echo "All ${#SECRETS[@]} secrets present."
}

prompt_and_store() {
  local name="$1" prompt="$2" value=""
  read -rsp "  ${prompt}: " value
  echo

  if [[ -z "$value" && "$name" == "SECRET_KEY" ]]; then
    value="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "  generated a random 64-char SECRET_KEY"
  fi

  if [[ -z "$value" ]]; then
    echo "  skipped ${name} (empty input)"
    return
  fi

  printf '%s' "$value" | store "$name"
  unset value
}

main() {
  if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
    echo "Not authenticated. Run: gcloud auth login" >&2
    exit 1
  fi

  case "${1:-}" in
    --verify)
      verify
      ;;
    --rotate)
      shift
      [[ $# -gt 0 ]] || { echo "--rotate needs at least one secret name" >&2; exit 1; }
      for name in "$@"; do
        local found=""
        for entry in "${SECRETS[@]}"; do
          [[ "${entry%%|*}" == "$name" ]] && found="${entry#*|}"
        done
        [[ -n "$found" ]] || { echo "Unknown secret: ${name}" >&2; exit 1; }
        echo "${name}:"
        prompt_and_store "$name" "$found"
      done
      ;;
    "")
      echo "Creating secrets in ${PROJECT_ID}. Input is hidden; press Enter to skip one."
      echo
      for entry in "${SECRETS[@]}"; do
        local name="${entry%%|*}" prompt="${entry#*|}"
        if exists "$name"; then
          echo "${name}: already exists, skipping (use --rotate ${name} to replace)"
          continue
        fi
        echo "${name}:"
        prompt_and_store "$name" "$prompt"
      done
      echo
      verify
      ;;
    *)
      echo "Usage: $0 [--verify | --rotate NAME...]" >&2
      exit 1
      ;;
  esac
}

main "$@"
