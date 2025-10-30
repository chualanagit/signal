# Google Cloud Run Deployment Guide

## 🚀 Deploy to Google Cloud Run

Cloud Run is a fully managed serverless platform that automatically scales your containers.

### Prerequisites

1. **Install Google Cloud SDK:**
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Login to Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Create a project** (or use existing):
   ```bash
   gcloud projects create intent-finder --name="Intent Finder"
   gcloud config set project intent-finder
   ```

4. **Enable required APIs:**
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

---

## 📦 Quick Deploy (Recommended)

### Option 1: Deploy from Source (Easy)

```bash
cd /Users/alanchu/signal/signal-finder-py

# Deploy directly from source
gcloud run deploy intent-finder \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars OPENAI_API_KEY=sk-proj-your-key-here,GOOGLE_CSE_KEY=your-key-here,GOOGLE_CSE_CX_LINKEDIN=your-id,GOOGLE_CSE_CX_REDDIT=your-id,GOOGLE_CSE_CX_GENERAL=your-id,DISABLE_EMBEDDINGS=false
```

**Note:** Replace environment variables with your actual values!

---

### Option 2: Build Docker Image First (More Control)

#### Step 1: Build and Push Container

```bash
cd /Users/alanchu/signal/signal-finder-py

# Set variables
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SERVICE_NAME=intent-finder

# Build container image
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}

# Or use Artifact Registry (recommended)
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=${REGION} \
  --description="Docker repository"

gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest
```

#### Step 2: Deploy to Cloud Run

```bash
# Deploy with environment variables
gcloud run deploy ${SERVICE_NAME} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars OPENAI_API_KEY=sk-proj-your-key-here,GOOGLE_CSE_KEY=your-key-here,GOOGLE_CSE_CX_LINKEDIN=your-id,GOOGLE_CSE_CX_REDDIT=your-id,GOOGLE_CSE_CX_GENERAL=your-id,DISABLE_EMBEDDINGS=false
```

---

## 🔐 Setting Environment Variables Securely

### Option A: Using Secret Manager (Recommended)

```bash
# Create secrets
echo -n "sk-proj-your-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-google-key" | gcloud secrets create google-cse-key --data-file=-
echo -n "your-linkedin-id" | gcloud secrets create google-cse-cx-linkedin --data-file=-
echo -n "your-reddit-id" | gcloud secrets create google-cse-cx-reddit --data-file=-
echo -n "your-general-id" | gcloud secrets create google-cse-cx-general --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$(gcloud iam service-accounts list --filter='displayName:Cloud Run' --format='value(email)')" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with secrets
gcloud run deploy intent-finder \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest \
  --region ${REGION} \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest,GOOGLE_CSE_KEY=google-cse-key:latest
```

### Option B: Using Environment Variables (Simpler)

```bash
# Create env file
cat > .env.production << EOF
OPENAI_API_KEY=sk-proj-your-key-here
GOOGLE_CSE_KEY=your-google-key-here
GOOGLE_CSE_CX_LINKEDIN=your-linkedin-id
GOOGLE_CSE_CX_REDDIT=your-reddit-id
GOOGLE_CSE_CX_GENERAL=your-general-id
DISABLE_EMBEDDINGS=false
EOF

# Deploy with env file
gcloud run deploy intent-finder \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest \
  --region ${REGION} \
  --env-vars-file .env.production
```

---

## 🚀 Complete Deployment Script

Save this as `deploy-cloud-run.sh`:

```bash
#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SERVICE_NAME=intent-finder

echo "🚀 Deploying to Google Cloud Run..."

# Build and push image
echo "📦 Building Docker image..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/docker-repo/${SERVICE_NAME}:latest

# Deploy to Cloud Run
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
  --set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY},GOOGLE_CSE_KEY=${GOOGLE_CSE_KEY},GOOGLE_CSE_CX_LINKEDIN=${GOOGLE_CSE_CX_LINKEDIN},GOOGLE_CSE_CX_REDDIT=${GOOGLE_CSE_CX_REDDIT},GOOGLE_CSE_CX_GENERAL=${GOOGLE_CSE_CX_GENERAL},DISABLE_EMBEDDINGS=false

echo "✅ Deployment complete!"
echo "🌐 Your app is live at:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
```

Make it executable:
```bash
chmod +x deploy-cloud-run.sh
```

---

## 📝 Cloud Run Configuration

### Recommended Settings:

- **Memory:** 512Mi (minimum) to 1Gi (recommended)
- **CPU:** 1 (sufficient for most loads)
- **Timeout:** 300 seconds (5 minutes) for LLM calls
- **Max Instances:** 10 (adjust based on traffic)
- **Min Instances:** 0 (scale to zero when not in use)

### Update Settings:

```bash
gcloud run services update intent-finder \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2 \
  --max-instances 20 \
  --timeout 300
```

---

## 🔍 Monitoring & Logs

### View Logs:
```bash
gcloud run services logs read intent-finder --region us-central1
```

### Stream Logs:
```bash
gcloud run services logs tail intent-finder --region us-central1
```

### Metrics Dashboard:
```bash
# Open in browser
open "https://console.cloud.google.com/run/detail/us-central1/intent-finder/metrics"
```

---

## 🌐 Custom Domain

### Add Custom Domain:

1. **Map domain in Cloud Run:**
   ```bash
   gcloud run domain-mappings create \
     --service intent-finder \
     --domain yourdomain.com \
     --region us-central1
   ```

2. **Update DNS:**
   - Add CNAME record pointing to the provided Cloud Run URL
   - Or use A record if provided

---

## 💰 Pricing

**Cloud Run Pricing:**
- **Free tier:** 2 million requests/month, 360,000 GB-seconds
- **After free tier:** $0.40 per million requests + compute time
- **Very cost-effective** for low-to-medium traffic

**Estimated cost for 100k requests/month:**
- Compute: ~$0.10-0.50 (depending on memory/CPU)
- Total: ~$0.10-0.50/month

---

## 🔧 Troubleshooting

### Port Issues:
- Cloud Run sets `PORT` env var automatically
- Dockerfile uses `${PORT:-8080}` as fallback
- Make sure your app listens on `0.0.0.0`, not `127.0.0.1`

### Build Failures:
```bash
# Build locally to test
docker build -t test-image .
docker run -p 8080:8080 test-image
```

### Environment Variables Not Working:
```bash
# Check current env vars
gcloud run services describe intent-finder --region us-central1 --format='value(spec.template.spec.containers[0].env)'
```

### Cold Start Issues:
```bash
# Set minimum instances to always keep one warm
gcloud run services update intent-finder \
  --region us-central1 \
  --min-instances 1
```

---

## ✅ Deployment Checklist

- [ ] Google Cloud SDK installed
- [ ] Project created and APIs enabled
- [ ] Dockerfile uses `${PORT}` env var
- [ ] Environment variables set
- [ ] Image builds successfully
- [ ] Service deploys successfully
- [ ] Health check endpoint works (`/health`)
- [ ] Test all endpoints

---

## 🎯 Quick Start Commands

```bash
# 1. Login
gcloud auth login

# 2. Set project
gcloud config set project YOUR_PROJECT_ID

# 3. Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# 4. Create Artifact Registry (if not exists)
gcloud artifacts repositories create docker-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository"

# 5. Deploy from repository root (IMPORTANT: use signal-finder-py subdirectory)
cd /Users/alanchu/signal
gcloud run deploy intent-finder \
  --source signal-finder-py \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key,GOOGLE_CSE_KEY=your-key

# 6. Get URL
gcloud run services describe intent-finder --region us-central1 --format 'value(status.url)'
```

**Your app will be live! 🎉**

