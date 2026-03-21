#!/bin/bash
# deploy_app.sh: Build, push, deploy to Cloud Run + create Cloud Scheduler

# Load .env
if [ -f .env ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        clean_line=$(echo "$line" | tr -d '\r')
        [[ $clean_line =~ ^#.* ]] && continue
        [[ -z $clean_line ]] && continue
        export "$clean_line"
    done < .env
fi

PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
SERVICE_NAME="nasdaq-multi-agent"
REGION="asia-southeast1"

# Service Account Logic
if [ -n "$VERTEX" ]; then
    SA_EMAIL=$VERTEX
    echo "👤 Using service account from .env: $SA_EMAIL"
else
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SA_EMAIL="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
    echo "👤 Using default compute service account: $SA_EMAIL"
fi

echo "🚀 Deploying $SERVICE_NAME to Cloud Run in $REGION..."

# 1. Grant Permissions
echo "🔑 Granting IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor" --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/aiplatform.user" --quiet

# 2. Build and Push Image
echo "🏗️ Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 600 \
  --no-cpu-throttling \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCP_PROJECT_ID=$PROJECT_ID,SLACK_CHANNEL_ID=${SLACK_CHANNEL_ID},EMAIL_SENDER=${EMAIL_SENDER},EMAIL_RECIPIENT=${EMAIL_RECIPIENT},VERTEX_MODEL=${VERTEX_MODEL}" \
  --service-account $SA_EMAIL

# 4. Get Service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

# 5. Create/Update Cloud Scheduler Job (7 PM SGT = 11:00 UTC)
SCHEDULER_JOB="nasdaq-analysis-daily"
echo "⏰ Setting up Cloud Scheduler job: $SCHEDULER_JOB"

# Delete existing job if present
gcloud scheduler jobs delete $SCHEDULER_JOB --location=$REGION --quiet 2>/dev/null

gcloud scheduler jobs create http $SCHEDULER_JOB \
  --location=$REGION \
  --schedule="0 19 * * 1-5" \
  --uri="$SERVICE_URL/cron/analyze" \
  --http-method=POST \
  --headers="X-Cron-Secret=${CRON_SECRET}" \
  --time-zone="Asia/Singapore" \
  --attempt-deadline=300s

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🔍 Health check: $SERVICE_URL/health"
echo "⏰ Scheduler: $SCHEDULER_JOB (Mon-Fri 7PM SGT)"
gcloud scheduler jobs describe $SCHEDULER_JOB --location=$REGION --format="table(name,schedule,timeZone,state)"
