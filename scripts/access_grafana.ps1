# Port-forward Grafana Dashboard
Write-Host "Usage: Access Grafana at http://localhost:3000"
Write-Host "Credentials: admin / admin (default)"
kubectl port-forward svc/shelfwatch-grafana 3000:80
