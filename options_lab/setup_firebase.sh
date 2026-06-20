#!/bin/bash
set -e
PROJECT_ID="optimal-aurora-495912-n0"

echo "Getting token..."
TOKEN=$(gcloud auth print-access-token --project=$PROJECT_ID 2>/dev/null)
echo "Token length: ${#TOKEN}"

echo "Creating web app..."
curl -s -X POST \
  "https://firebase.googleapis.com/v1beta1/projects/${PROJECT_ID}/webApps" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  -d '{"displayName":"OptionsLab"}'

echo ""
echo "Listing web apps..."
curl -s \
  "https://firebase.googleapis.com/v1beta1/projects/${PROJECT_ID}/webApps" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-Goog-User-Project: ${PROJECT_ID}"
