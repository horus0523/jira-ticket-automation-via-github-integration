#!/bin/bash
set -euo pipefail

SERVICE_URL="${SERVICE_URL:-http://localhost:5000}"
MAX_RETRIES=5
RETRY_DELAY=5
RESPONSE_BODY_FILE="$(mktemp)"

trap 'rm -f "$RESPONSE_BODY_FILE"' EXIT

for i in $(seq 1 $MAX_RETRIES); do
    HTTP_STATUS=$(curl -sS -o "$RESPONSE_BODY_FILE" -w "%{http_code}" "$SERVICE_URL/health" || true)
    if [ "$HTTP_STATUS" -eq 200 ]; then
        echo "OK: Health check passed"
        exit 0
    fi
    echo "Attempt $i/$MAX_RETRIES: Health check failed (HTTP $HTTP_STATUS)"
    if [ -s "$RESPONSE_BODY_FILE" ]; then
        echo "Response body:"
        cat "$RESPONSE_BODY_FILE"
    fi
    [ $i -lt $MAX_RETRIES ] && sleep $RETRY_DELAY
done

echo "ERROR: Health check failed after $MAX_RETRIES attempts"
exit 1
