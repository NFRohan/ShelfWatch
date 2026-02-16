# AWS Teardown Script (PowerShell)
# Usage: .\infra\aws\teardown.ps1

$REGION = "us-east-1"
$CLUSTER_NAME = "shelfwatch"
$ECR_REPO_NAME = "shelfwatch-inference"

Write-Host "`nShelfWatch AWS Teardown" -ForegroundColor Red
Write-Host "================================"
Write-Host "`nWARNING: This will DELETE:" -ForegroundColor Yellow
Write-Host "   - EKS cluster: $CLUSTER_NAME"
Write-Host "   - ECR repository: $ECR_REPO_NAME"
Write-Host "   - All associated resources (nodes, load balancers, etc)`n"

$confirm = Read-Host "Are you sure? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled."
    exit
}

# Delete K8s services first (releases Load Balancer)
Write-Host "`nDeleting K8s services..." -ForegroundColor Yellow
try {
    kubectl delete svc shelfwatch-inference 2>$null
    kubectl delete svc shelfwatch-grafana 2>$null
    kubectl delete svc shelfwatch-prometheus 2>$null
    Start-Sleep -Seconds 10
}
catch {}

# Delete EKS Cluster
Write-Host "`nDeleting EKS cluster: $CLUSTER_NAME..." -ForegroundColor Yellow
eksctl delete cluster --name $CLUSTER_NAME --region $REGION --wait
Write-Host "   Cluster deleted"

# Delete ECR Repository
Write-Host "`nDeleting ECR repository..." -ForegroundColor Yellow
try {
    aws ecr delete-repository --repository-name $ECR_REPO_NAME --region $REGION --force 2>$null | Out-Null
    Write-Host "   ECR repository deleted"
}
catch {
    Write-Host "   (Already deleted)"
}

Write-Host "`n================================" -ForegroundColor Green
Write-Host "TEARDOWN COMPLETE" -ForegroundColor Green
Write-Host "================================"
Write-Host "All AWS resources deleted. Billing stopped."
