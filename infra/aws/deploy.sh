#!/bin/bash
# ──────────────────────────────────────────────
# ShelfWatch — AWS Deployment Script
# ──────────────────────────────────────────────
# Deploys the inference service to EKS in one command.
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - eksctl installed
#   - kubectl installed
#   - Docker running
#
# Usage:
#   chmod +x infra/aws/deploy.sh
#   ./infra/aws/deploy.sh
# ──────────────────────────────────────────────

set -euo pipefail

# ── Config ──
REGION="us-east-1"
CLUSTER_NAME="shelfwatch"
ECR_REPO_NAME="shelfwatch-inference"
IMAGE_TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🏪 ShelfWatch — AWS Deployment"
echo "================================"
echo "Region:  $REGION"
echo "Cluster: $CLUSTER_NAME"
echo ""

# ── Step 1: Get AWS Account ID ──
echo "📋 Step 1/6: Getting AWS account info..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}"
echo "   Account: $ACCOUNT_ID"
echo "   ECR URI: $ECR_URI"

# ── Step 2: Create ECR Repository ──
echo ""
echo "📦 Step 2/6: Creating ECR repository..."
aws ecr create-repository \
    --repository-name "$ECR_REPO_NAME" \
    --region "$REGION" \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "   (Repository already exists — skipping)"

# ── Step 3: Build & Push Docker Image ──
echo ""
echo "🐳 Step 3/6: Building and pushing Docker image..."

# Login to ECR
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build image with weights baked in
cd "$PROJECT_ROOT"
docker build \
    -f Dockerfile.aws \
    -t "${ECR_URI}:${IMAGE_TAG}" \
    .

# Push to ECR
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "   ✅ Image pushed: ${ECR_URI}:${IMAGE_TAG}"

# ── Step 4: Create EKS Cluster ──
echo ""
echo "☸️  Step 4/6: Creating EKS cluster (this takes ~15-20 minutes)..."
if eksctl get cluster --name "$CLUSTER_NAME" --region "$REGION" 2>/dev/null; then
    echo "   Cluster already exists — skipping creation"
else
    eksctl create cluster -f "$SCRIPT_DIR/cluster.yaml"
fi

# Ensure kubectl context is set
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION"
echo "   ✅ kubectl configured for cluster: $CLUSTER_NAME"

# ── Step 5: Apply K8s Manifests ──
echo ""
echo "🚀 Step 5/6: Deploying to Kubernetes..."

# Update the image in deployment manifest
export ECR_IMAGE="${ECR_URI}:${IMAGE_TAG}"

# Apply manifests
kubectl apply -f "$PROJECT_ROOT/infra/k8s/configmap.yaml"

# Substitute the ECR image URI into the deployment
sed "s|shelfwatch-inference:latest|${ECR_IMAGE}|g" \
    "$PROJECT_ROOT/infra/k8s/deployment.yaml" | kubectl apply -f -

echo "   ✅ Manifests applied"

# ── Step 6: Wait for Rollout & Get URL ──
echo ""
echo "⏳ Step 6/6: Waiting for deployment to be ready..."
kubectl rollout status deployment/shelfwatch-inference --timeout=300s

echo ""
echo "🌐 Getting Load Balancer URL..."
echo "   (This may take 1-2 minutes for AWS to provision the ALB)"

for i in {1..30}; do
    LB_URL=$(kubectl get svc shelfwatch-inference \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)
    if [ -n "$LB_URL" ]; then
        break
    fi
    echo "   Waiting for Load Balancer... ($i/30)"
    sleep 10
done

echo ""
echo "================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================"
echo ""
echo "🌐 API URL:     http://${LB_URL}"
echo "🏥 Health:      http://${LB_URL}/health"
echo "📊 Metrics:     http://${LB_URL}/metrics"
echo "🔍 Predict:     curl -X POST http://${LB_URL}/predict -F 'image=@shelf.jpg'"
echo ""
echo "📋 Useful commands:"
echo "   kubectl get pods -l app=shelfwatch"
echo "   kubectl logs -l app=shelfwatch --tail=50"
echo "   kubectl get hpa"
echo ""
echo "💰 COST WARNING: This cluster costs ~\$0.20/hr (~\$147/month)"
echo "   Run './infra/aws/teardown.sh' when done to stop billing!"
