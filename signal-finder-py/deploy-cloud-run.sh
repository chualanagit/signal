#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-intent-finder}

echo "🚀 Deploying Intent Finder to Google Cloud Run..."
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check if required env vars are set
if [ -z "$OPENAI_API_KEY" ] || [ -z "$GOOGLE_CSE_KEY" ]; then
    echo "⚠️  Warning: Environment variables not set in shell"
    echo "   Set them with: export OPENAI_API_KEY=your-key"
    echo "   Or they will be read from .env.production file"
fi

# Check if .env.production exists
if [ -f .env.production ]; then
    echo "📄 Using .env.production file..."
    ENV_FLAG="--env-vars-file .env.production"
else
    echo "🔑 Using environment variables from shell..."
    ENV_FLAG="--set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY},GOOGLE_CSE_KEY=${GOOGLE_CSE_KEY},GOOGLE_CSE_CX_LINKEDIN=${GOOGLE_CSE_CX_LINKEDIN},GOOGLE_CSE_CX_REDDIT=${GOOGLE_CSE_CX_REDDIT},GOOGLE_CSE_CX_GENERAL=${GOOGLE_CSE_CX_GENERAL},DISABLE_EMBEDDINGS=false"
fi

# Build and push image
echo ""
echo "📦 Building Docker image..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest

# Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  ${ENV_FLAG}

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your app is live at:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
echo ""
echo "📊 View logs: gcloud run services logs tail ${SERVICE_NAME} --region ${REGION}"
echo "📈 View metrics: https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics"

