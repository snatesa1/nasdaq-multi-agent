#!/bin/bash
# destroy_app.sh: Cleanup all created resources (service + scheduler + secrets)

SERVICE_NAME="nasdaq-multi-agent"
SCHEDULER_JOB="nasdaq-analysis-daily"
REGION="asia-southeast1"

echo "⚠️  WARNING: This will delete the Cloud Run service, scheduler job, and all secrets."
read -p "Are you sure? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "Deletion cancelled."
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project)

# 1. Delete Cloud Scheduler Job
echo "🗑️ Deleting Cloud Scheduler job: $SCHEDULER_JOB..."
gcloud scheduler jobs delete $SCHEDULER_JOB --location=$REGION --quiet 2>/dev/null

# 2. Delete Cloud Run Service
echo "🗑️ Deleting Cloud Run service: $SERVICE_NAME..."
gcloud run services delete $SERVICE_NAME --region $REGION --quiet 2>/dev/null && \
    echo "  ✅ Service deleted" || echo "  ⏭️ Service not found (already deleted)"

# 3. Delete Secrets from Secret Manager
echo "🔑 Deleting secrets from Secret Manager..."
SECRETS=(
    "SLACK_BOT_TOKEN"
    "SLACK_SIGNING_SECRET"
    "SLACK_CHANNEL_ID"
    "CRON_SECRET"
    "ALPACA_API_KEY"
    "ALPACA_SECRET_KEY"
    "FMP_API_KEY"
    "FRED_API_KEY"
    "EMAIL_APP_PASSWORD"
)

for secret in "${SECRETS[@]}"; do
    gcloud secrets delete $secret --project=$PROJECT_ID --quiet 2>/dev/null && \
        echo "  🗑️ Deleted: $secret" || \
        echo "  ⏭️ Skipped: $secret (not found)"
done

echo "✅ All resources destroyed successfully."
