#!/bin/bash
# setup_gh_actions_sa.sh: Create a service account for GitHub Actions deployments

PROJECT_ID=$(gcloud config get-value project)
SA_NAME="github-actions-deployer"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "🛠️ Creating Service Account: $SA_EMAIL"
gcloud iam service-accounts create $SA_NAME \
    --display-name="GitHub Actions Deployer" \
    --quiet

echo "🔑 Adding IAM policy bindings..."

# Cloud Run Admin (to deploy services)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.admin" --quiet

# Service Account User (to act as the compute SA)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding $COMPUTE_SA \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/iam.serviceAccountUser" --quiet

# Cloud Build Editor (to build images)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudbuild.builds.editor" --quiet

# Storage Admin (to push images to GCR)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin" --quiet

# Cloud Scheduler Admin (for nasdaq cron jobs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudscheduler.admin" --quiet

# Secret Manager Accessor (to access secrets if needed at build time)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" --quiet

echo "🗝️ Creating JSON key..."
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=$SA_EMAIL --quiet

echo "✅ Service Account setup complete!"
echo "🚀 Next steps:"
echo "1. Copy the contents of github-actions-key.json"
echo "2. Add it to your GitHub Repository Secrets as GCP_SA_KEY"
echo "3. Add your Project ID as GCP_PROJECT_ID"
echo "4. DELETE github-actions-key.json locally after copying the key!"
