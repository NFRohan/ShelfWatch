# ──────────────────────────────────────────────
# ShelfWatch — AWS Image Push Script (PowerShell)
# ──────────────────────────────────────────────
# Usage: .\infra\aws\push.ps1
# Use this if you need to update the image without re-creating the cluster.
# ──────────────────────────────────────────────

$ErrorActionPreference = "Stop"

$REGION = "us-east-1"
$ECR_REPO_NAME = "shelfwatch-inference"
$IMAGE_TAG = "latest"
$PROJECT_ROOT = (Resolve-Path "$PSScriptRoot\..\..").Path

Write-Host "🐳 Building and pushing Docker image..." -ForegroundColor Yellow

$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_URI = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME"

# Login
$loginPassword = aws ecr get-login-password --region $REGION
$loginPassword | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Build
Set-Location $PROJECT_ROOT
docker build -f Dockerfile.aws -t "${ECR_URI}:${IMAGE_TAG}" .

# Push
docker push "${ECR_URI}:${IMAGE_TAG}"
Write-Host "✅ Image pushed: ${ECR_URI}:${IMAGE_TAG}"

# Force restart pods if cluster exists
try {
    Write-Host "`n🔄 Restarting pods to pick up new image..." -ForegroundColor Yellow
    kubectl rollout restart deployment/shelfwatch-inference 2>$null
}
catch {}
