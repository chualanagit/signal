# IMPORTANT: Don't use --source flag!
# Use cloudbuild.yaml instead (run from repository root)

# The issue: --source flag expects Dockerfile at root, but ours is in signal-finder-py/

# SOLUTION 1: Use cloudbuild.yaml (recommended)
cd /Users/alanchu/signal
gcloud builds submit --config cloudbuild.yaml

# Then deploy:
gcloud run deploy intent-finder \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/docker-repo/intent-finder:latest \
  --region us-central1 \
  --allow-unauthenticated

# SOLUTION 2: Use the deployment script (easiest)
cd /Users/alanchu/signal
./deploy-cloud-run.sh

# SOLUTION 3: Build from subdirectory manually
cd /Users/alanchu/signal/signal-finder-py
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT/docker-repo/intent-finder:latest
cd ..
gcloud run deploy intent-finder \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/docker-repo/intent-finder:latest \
  --region us-central1 \
  --allow-unauthenticated

