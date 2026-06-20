#!/bin/bash
# deploy_options_lab.sh: Build, push, and deploy OptionsLab v2 to GCP Cloud Run

PROJECT_ID="optimal-aurora-495912-n0"
SERVICE_NAME="options-lab"
REGION="asia-southeast1"

# Change directory to script location
cd "$(dirname "$0")"

# Service Account configuration
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SA_EMAIL="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

echo "👤 Using default compute service account: $SA_EMAIL"
echo "🚀 Deploying $SERVICE_NAME to Cloud Run in $REGION..."

# 1. Grant IAM permissions to service account
echo "🔑 Granting IAM permissions..."
for ROLE in \
  "roles/secretmanager.secretAccessor" \
  "roles/aiplatform.user"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$ROLE" --quiet 2>/dev/null
done

# Copy historical cache and screener to api/data/ for container inclusion
mkdir -p api/data
cp ../data/historical_cache.parquet api/data/ 2>/dev/null || cp ../../data/historical_cache.parquet api/data/ 2>/dev/null || true
cp ../data/nasdaq_screener.csv api/data/ 2>/dev/null || cp ../../data/nasdaq_screener.csv api/data/ 2>/dev/null || true

# 2. Build and Push Image using Cloud Build
echo "🏗️ Building container image via GCP Cloud Build..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME . --timeout=20m --machine-type=e2-highcpu-8

# 3. Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 600 \
  --min-instances 0 \
  --max-instances 3 \
  --cpu-throttling \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCP_PROJECT_ID=$PROJECT_ID,VERTEX_MODEL=gemini-2.5-flash,FIREBASE_PROJECT_ID=$PROJECT_ID" \
  --service-account $SA_EMAIL

# 4. Get Service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🔍 Health check: $SERVICE_URL/health"
echo ""
echo "📋 IMPORTANT: Share your Google Sheets with this service account:"
echo "   $SA_EMAIL"
echo "   (Viewer access is sufficient for portfolio sync)"
