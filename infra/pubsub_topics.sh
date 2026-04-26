#!/bin/bash
# Create all Pub/Sub topics for Prahari-NGO
set -e

export PROJECT_ID="${PROJECT_ID:-prahari-ngo-rj}"

echo "Creating Pub/Sub topics for project: $PROJECT_ID"

gcloud pubsub topics create threats-detected --project=$PROJECT_ID 2>/dev/null || echo "threats-detected already exists"
gcloud pubsub topics create crisis-confirmed --project=$PROJECT_ID 2>/dev/null || echo "crisis-confirmed already exists"
gcloud pubsub topics create ingestion-events --project=$PROJECT_ID 2>/dev/null || echo "ingestion-events already exists"

echo "All Pub/Sub topics created."
