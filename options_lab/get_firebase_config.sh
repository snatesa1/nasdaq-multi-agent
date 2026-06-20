#!/bin/bash
set -e

PROJECT_ID="optimal-aurora-495912-n0"

# Get token and save to variable
TOKEN=$(gcloud auth print-access-token --project=$PROJECT_ID)

if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to get access token"
    exit 1
fi

echo "Token acquired (${#TOKEN} chars)"

# List web apps
echo "=== Listing web apps ==="
APPS=$(curl -s \
  "https://firebase.googleapis.com/v1beta1/projects/${PROJECT_ID}/webApps" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}")
echo "$APPS"

# Extract app ID
APP_ID=$(echo "$APPS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    apps = data.get('apps', [])
    if apps:
        print(apps[0]['appId'])
    else:
        print('NONE')
except:
    print('NONE')
" 2>/dev/null)

echo ""
echo "App ID: $APP_ID"

if [ "$APP_ID" != "NONE" ]; then
    echo "=== Getting config ==="
    curl -s \
      "https://firebase.googleapis.com/v1beta1/projects/${PROJECT_ID}/webApps/${APP_ID}/config" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "X-Goog-User-Project: ${PROJECT_ID}"
fi
