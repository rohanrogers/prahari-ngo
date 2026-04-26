#!/bin/bash
# ══════════════════════════════════════════════════════════
#  PRAHARI-NGO — One-Time GCP Setup
#  Run this ONCE to create project, enable APIs, and set IAM
# ══════════════════════════════════════════════════════════
set -e

export PROJECT_ID="${PROJECT_ID:-prahari-ngo-rj}"
export REGION="${REGION:-asia-south1}"
export BILLING_ACCOUNT="${BILLING_ACCOUNT}"

echo "═══════════════════════════════════════════════════"
echo "  PRAHARI-NGO — GCP Project Setup"
echo "  Project: $PROJECT_ID | Region: $REGION"
echo "═══════════════════════════════════════════════════"

# ── Step 1: Create Project ──
echo ""
echo "▶ Step 1: Creating project..."
gcloud projects create $PROJECT_ID --name="Prahari NGO" 2>/dev/null || echo "Project already exists"

# ── Step 2: Link Billing ──
if [ -n "$BILLING_ACCOUNT" ]; then
  echo "▶ Step 2: Linking billing account..."
  gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
else
  echo "⚠️  Step 2: Skipping billing — set BILLING_ACCOUNT env var"
fi

# ── Step 3: Set Default Project ──
gcloud config set project $PROJECT_ID

# ── Step 4: Enable Required APIs ──
echo ""
echo "▶ Step 4: Enabling APIs..."
APIS=(
  "run.googleapis.com"
  "firestore.googleapis.com"
  "pubsub.googleapis.com"
  "cloudbuild.googleapis.com"
  "cloudscheduler.googleapis.com"
  "storage.googleapis.com"
  "aiplatform.googleapis.com"
  "generativelanguage.googleapis.com"
  "maps-embed-backend.googleapis.com"
  "firebase.googleapis.com"
  "firebasehosting.googleapis.com"
)

for api in "${APIS[@]}"; do
  echo "  Enabling $api..."
  gcloud services enable $api --project=$PROJECT_ID 2>/dev/null || echo "  Already enabled: $api"
done
echo "✅ All APIs enabled"

# ── Step 5: Create Firestore Database ──
echo ""
echo "▶ Step 5: Creating Firestore database (native mode)..."
gcloud firestore databases create \
  --project=$PROJECT_ID \
  --location=$REGION \
  --type=firestore-native 2>/dev/null || echo "Firestore already exists"

# ── Step 6: Create Service Account ──
echo ""
echo "▶ Step 6: Creating service account..."
SA_NAME="prahari-agent"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
  --description="Prahari agent service account for Cloud Run" \
  --display-name="Prahari Agent" \
  --project=$PROJECT_ID 2>/dev/null || echo "Service account already exists"

# Grant necessary roles
ROLES=(
  "roles/datastore.user"
  "roles/pubsub.publisher"
  "roles/pubsub.subscriber"
  "roles/aiplatform.user"
  "roles/storage.objectAdmin"
  "roles/run.invoker"
  "roles/cloudscheduler.admin"
)

for role in "${ROLES[@]}"; do
  echo "  Granting $role..."
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$role" \
    --quiet 2>/dev/null
done
echo "✅ Service account configured: $SA_EMAIL"

# ── Step 7: Create Pub/Sub Topics ──
echo ""
echo "▶ Step 7: Creating Pub/Sub topics..."
bash infra/pubsub_topics.sh

# ── Step 8: Create Storage Bucket ──
echo ""
echo "▶ Step 8: Creating Cloud Storage bucket..."
gsutil mb -l $REGION gs://${PROJECT_ID}-uploads 2>/dev/null || echo "Bucket already exists"

# ── Step 9: Firebase Setup ──
echo ""
echo "▶ Step 9: Setting up Firebase..."
firebase projects:addfirebase $PROJECT_ID 2>/dev/null || echo "Firebase already linked"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ GCP Setup Complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Project:         $PROJECT_ID"
echo "Region:          $REGION"
echo "Service Account: $SA_EMAIL"
echo "Firestore:       Native mode in $REGION"
echo "Storage:         gs://${PROJECT_ID}-uploads"
echo ""
echo "Next steps:"
echo "  1. Run: cd dashboard && npm run build && firebase deploy --only hosting"
echo "  2. Run: ./scripts/deploy_all.sh"
echo "  3. Set OPENWEATHER_API_KEY in Secret Manager:"
echo "     gcloud secrets create openweather-api-key --data-file=<(echo -n 'YOUR_KEY')"
