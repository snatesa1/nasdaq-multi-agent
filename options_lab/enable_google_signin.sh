#!/bin/bash
# Enable/Update Google Sign-In provider in Identity Platform
set -e
PROJECT_ID="optimal-aurora-495912-n0"

CLIENT_ID=$1
CLIENT_SECRET=$2

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "Usage: ./enable_google_signin.sh <CLIENT_ID> <CLIENT_SECRET>"
    exit 1
fi

TOKEN=$(gcloud auth print-access-token --project=$PROJECT_ID 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to acquire GCP access token. Please run 'gcloud auth login' or verify your credentials."
    exit 1
fi
echo "Token acquired successfully."

# Check if Google IdP Config already exists
echo "🔍 Checking existing Google IdP configuration..."
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://identitytoolkit.googleapis.com/admin/v2/projects/${PROJECT_ID}/defaultSupportedIdpConfigs/google.com" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}")

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "🔄 Google IdP configuration exists. Updating with PATCH..."
    curl -s -X PATCH \
      "https://identitytoolkit.googleapis.com/admin/v2/projects/${PROJECT_ID}/defaultSupportedIdpConfigs/google.com?updateMask=clientId,clientSecret,enabled" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -H "X-Goog-User-Project: ${PROJECT_ID}" \
      -d "{
        \"enabled\": true,
        \"clientId\": \"$CLIENT_ID\",
        \"clientSecret\": \"$CLIENT_SECRET\"
      }"
else
    echo "🆕 Google IdP configuration does not exist. Creating with POST..."
    curl -s -X POST \
      "https://identitytoolkit.googleapis.com/admin/v2/projects/${PROJECT_ID}/defaultSupportedIdpConfigs?idpId=google.com" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -H "X-Goog-User-Project: ${PROJECT_ID}" \
      -d "{
        \"enabled\": true,
        \"clientId\": \"$CLIENT_ID\",
        \"clientSecret\": \"$CLIENT_SECRET\"
      }"
fi

echo ""
echo "✅ Google Sign-in provider successfully configured in Identity Platform!"

