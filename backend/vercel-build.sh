#!/usr/bin/env bash
# Vercel build step. Production deploys apply migrations before the new code
# goes live; a failed migration fails the build, so the previous deployment
# keeps serving. Preview builds never touch the production database.
set -euo pipefail
python3 -m pip install --quiet -r requirements.txt
python3 manage.py check --deploy --fail-level ERROR
if [ "${VERCEL_ENV:-}" = "production" ]; then
  python3 manage.py migrate --noinput
else
  echo "VERCEL_ENV=${VERCEL_ENV:-unset}: skipping migrations"
fi
