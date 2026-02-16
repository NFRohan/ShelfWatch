# AWS Deployment Script (PowerShell)
# Usage: .\infra\aws\deploy.ps1

$ErrorActionPreference = "Stop"

$REGION = "us-east-1"
$CLUSTER_NAME = "shelfwatch"
$ECR_REPO_NAME = "shelfwatch-inference"
$IMAGE_TAG = "latest"
$PROJECT_ROOT = (Resolve-Path "$PSScriptRoot\..\..").Path

Write-Host "`nShelfWatch AWS Deployment" -ForegroundColor Cyan
Write-Host "============================"
Write-Host "Region:  $REGION"
Write-Host "Cluster: $CLUSTER_NAME`n"

# 1. Get AWS Account ID
Write-Host "Step 1/6: Getting AWS account info..." -ForegroundColor Yellow
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ECR_URI = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME"
Write-Host "   Account: $ACCOUNT_ID"
Write-Host "   ECR URI: $ECR_URI"

# 2. Create ECR Repository
Write-Host "`nStep 2/6: Creating ECR repository..." -ForegroundColor Yellow
try {
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION --image-scanning-configuration scanOnPush=true 2>$null | Out-Null
    Write-Host "   Repository created"
}
catch {
    Write-Host "   (Repository already exists, skipping)"
}

# 3. Build & Push Docker Image
Write-Host "`nStep 3/6: Building and pushing Docker image..." -ForegroundColor Yellow

# Login to ECR
$loginPassword = aws ecr get-login-password --region $REGION
$loginPassword | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Build with weights baked in
Set-Location $PROJECT_ROOT
docker build -f Dockerfile.aws -t "${ECR_URI}:${IMAGE_TAG}" .

# Push
docker push "${ECR_URI}:${IMAGE_TAG}"
Write-Host "   Image pushed: ${ECR_URI}:${IMAGE_TAG}"

# 4. Create EKS Cluster
Write-Host "`nStep 4/6: Creating EKS cluster (this takes 15-20 mins)..." -ForegroundColor Yellow

# Check cluster status
$status = "NONE"
try {
    $status = aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.status" --output text 2>$null
}
catch {}

if ($status -eq "ACTIVE") {
    Write-Host "   Cluster is ACTIVE, checking node groups..."
    
    # Check if a node group exists
    $nodegroups = aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --query "nodegroups" --output text 2>$null
    if (-not $nodegroups) {
        Write-Host "   No node groups found. Creating node group (inference-nodes)..."
        eksctl create nodegroup --config-file "$PROJECT_ROOT\infra\aws\cluster.yaml"
    }
    else {
        Write-Host "   Node groups exist: $nodegroups"
    }

}
elseif ($status -eq "CREATING") {
    Write-Host "   Cluster is CREATING. Waiting for it to become ACTIVE..."
    aws eks wait cluster-active --name $CLUSTER_NAME --region $REGION
    Write-Host "   Cluster is now ACTIVE"
    
    # Check node groups again after wait
    $nodegroups = aws eks list-nodegroups --cluster-name $CLUSTER_NAME --region $REGION --query "nodegroups" --output text 2>$null
    if (-not $nodegroups) {
        Write-Host "   Creating node group (inference-nodes)..."
        eksctl create nodegroup --config-file "$PROJECT_ROOT\infra\aws\cluster.yaml"
    }

}
else {
    Write-Host "   Creating new cluster..."
    eksctl create cluster -f "$PROJECT_ROOT\infra\aws\cluster.yaml"
}

aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION
Write-Host "   kubectl configured for cluster: $CLUSTER_NAME"

# 5. Apply K8s Manifests
Write-Host "`nStep 5/6: Deploying to Kubernetes..." -ForegroundColor Yellow

kubectl apply -f "$PROJECT_ROOT\infra\k8s\configmap.yaml"

# Substitute ECR image into deployment and apply
$deploymentContent = Get-Content "$PROJECT_ROOT\infra\k8s\deployment.yaml" -Raw
$deploymentContent = $deploymentContent -replace "shelfwatch-inference:latest", "${ECR_URI}:${IMAGE_TAG}"
$deploymentContent | kubectl apply -f -

Write-Host "   Manifests applied"

# 6. Wait for Rollout
Write-Host "`nStep 6/6: Waiting for deployment..." -ForegroundColor Yellow
kubectl rollout status deployment/shelfwatch-inference --timeout=300s

Write-Host "`nGetting Load Balancer URL..." -ForegroundColor Yellow
$LB_URL = ""
for ($i = 1; $i -le 30; $i++) {
    $LB_URL = kubectl get svc shelfwatch-inference -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null
    if ($LB_URL) { break }
    Write-Host "   Waiting for Load Balancer... ($i/30)"
    Start-Sleep -Seconds 10
}

Write-Host "`n================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================"
Write-Host ""
Write-Host "API URL:     http://$LB_URL"
Write-Host "Health:      http://$LB_URL/health"
Write-Host "Metrics:     http://$LB_URL/metrics"
Write-Host "Predict:     curl -X POST http://$LB_URL/predict -F 'image=@shelf.jpg'"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "   kubectl get pods -l app=shelfwatch"
Write-Host "   kubectl logs -l app=shelfwatch --tail=50"
Write-Host "   kubectl get hpa"
Write-Host ""
Write-Host "COST WARNING: ~`$0.20/hr (~`$147/month)" -ForegroundColor Red
Write-Host "   Run '.\infra\aws\teardown.ps1' when done!" -ForegroundColor Red
