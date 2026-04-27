#!/bin/bash
# Deploy all Prahari-NGO services to Google Cloud
set -e

export PROJECT_ID="${PROJECT_ID:-prahari-ngo-rj}"
export REGION="${REGION:-asia-south1}"
export SERVICE_ACCOUNT="prahari-agent@${PROJECT_ID}.iam.gserviceaccount.com"

echo "═══════════════════════════════════════════════════"
echo "  PRAHARI-NGO — Deploying All Services"
echo "  Project: $PROJECT_ID | Region: $REGION"
echo "═══════════════════════════════════════════════════"

# Build & deploy Ingestor
echo ""
echo "▶ Deploying Ingestor Agent..."
cd agents/ingestor
gcloud run deploy prahari-ingestor \
  --source . \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},REGION=${REGION}"
cd ../..
echo "✅ Ingestor deployed"

# Build & deploy Watcher
echo ""
echo "▶ Deploying Watcher Agent..."
cd agents/watcher
gcloud run deploy prahari-watcher \
  --source . \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120 \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},REGION=${REGION}" \
  --set-secrets "OPENWEATHER_API_KEY=openweather-api-key:latest"
cd ../..
echo "✅ Watcher deployed"

# Build & deploy Coordinator
echo ""
echo "▶ Deploying Coordinator Agent..."
cd agents/coordinator
gcloud run deploy prahari-coordinator \
  --source . \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT \
  --no-allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "PROJECT_ID=${PROJECT_ID},REGION=${REGION}"
cd ../..
echo "✅ Coordinator deployed"

# Create Scheduler job for Watcher (every 5 minutes)
echo ""
echo "▶ Setting up Watcher scheduler..."
WATCHER_URL=$(gcloud run services describe prahari-watcher --region $REGION --format='value(status.url)')
gcloud scheduler jobs create http prahari-watcher-cycle \
  --schedule "*/5 * * * *" \
  --http-method POST \
  --uri "${WATCHER_URL}/watch/cycle" \
  --oidc-service-account-email $SERVICE_ACCOUNT \
  --location $REGION 2>/dev/null || echo "Scheduler already exists"
echo "✅ Watcher scheduler configured"

# Create Pub/Sub subscriptions
echo ""
echo "▶ Creating Pub/Sub subscriptions..."
COORDINATOR_URL=$(gcloud run services describe prahari-coordinator --region $REGION --format='value(status.url)')

gcloud pubsub subscriptions create coordinator-threats \
  --topic threats-detected \
  --push-endpoint "${COORDINATOR_URL}/on-threat" \
  --push-auth-service-account $SERVICE_ACCOUNT 2>/dev/null || echo "threats subscription exists"

gcloud pubsub subscriptions create coordinator-crises \
  --topic crisis-confirmed \
  --push-endpoint "${COORDINATOR_URL}/on-crisis-confirmed" \
  --push-auth-service-account $SERVICE_ACCOUNT 2>/dev/null || echo "crises subscription exists"
echo "✅ Pub/Sub subscriptions configured"

# Deploy Dashboard
echo ""
echo "▶ Deploying Dashboard..."
cd dashboard
npm run build
vercel --prod
cd ..
echo "✅ Dashboard deployed"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ All services deployed successfully!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Ingestor:    $(gcloud run services describe prahari-ingestor --region $REGION --format='value(status.url)' 2>/dev/null)"
echo "Watcher:     $(gcloud run services describe prahari-watcher --region $REGION --format='value(status.url)' 2>/dev/null)"
echo "Coordinator: $(gcloud run services describe prahari-coordinator --region $REGION --format='value(status.url)' 2>/dev/null)"
echo "Dashboard:   Check Vercel Project URL"
