#!/bin/bash
# ──────────────────────────────────────────────
# ShelfWatch — AWS Teardown Script
# ──────────────────────────────────────────────
# Deletes the EKS cluster and ECR repo to stop billing.
#
# Usage:
#   chmod +x infra/aws/teardown.sh
#   ./infra/aws/teardown.sh
# ──────────────────────────────────────────────

set -euo pipefail

REGION="us-east-1"
CLUSTER_NAME="shelfwatch"
ECR_REPO_NAME="shelfwatch-inference"

echo "🗑️  ShelfWatch — AWS Teardown"
echo "================================"
echo ""
echo "⚠️  This will DELETE:"
echo "   - EKS cluster: $CLUSTER_NAME"
echo "   - ECR repository: $ECR_REPO_NAME"
echo "   - All associated resources (nodes, load balancers, etc.)"
echo ""
read -p "Are you sure? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

# ── Delete K8s resources first (releases Load Balancer) ──
echo ""
echo "🔄 Deleting K8s services (to release Load Balancer)..."
kubectl delete svc shelfwatch-inference 2>/dev/null || true
sleep 10

# ── Delete EKS Cluster ──
echo ""
echo "☸️  Deleting EKS cluster: $CLUSTER_NAME..."
eksctl delete cluster --name "$CLUSTER_NAME" --region "$REGION" --wait
echo "   ✅ Cluster deleted"

# ── Delete ECR Repository ──
echo ""
echo "📦 Deleting ECR repository: $ECR_REPO_NAME..."
aws ecr delete-repository \
    --repository-name "$ECR_REPO_NAME" \
    --region "$REGION" \
    --force \
    2>/dev/null || echo "   (Repository not found — already deleted)"
echo "   ✅ ECR repository deleted"

echo ""
echo "================================"
echo "✅ TEARDOWN COMPLETE"
echo "================================"
echo "All AWS resources have been deleted. Billing has stopped."
