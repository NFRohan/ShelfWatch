# Port-forward ArgoCD Server (Admin UI)
Write-Host "Usage: Access ArgoCD at https://localhost:8080"
Write-Host "Credentials: admin / (argocd-initial-admin-secret)"
kubectl -n argocd port-forward svc/argocd-server 8080:443
