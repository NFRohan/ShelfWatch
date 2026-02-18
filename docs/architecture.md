# ShelfWatch — Serverless Shelf Analysis Architecture

## 1. System Design (C4 Model)

### Context View
The high-level interaction between the user (Store Manager) and the ShelfWatch system.

```mermaid
C4Context
    title System Context Diagram for ShelfWatch

    Person(storeManager, "Store Manager", "Audits shelf stock levels using a mobile device")
    System(shelfWatch, "ShelfWatch", "Analyzes shelf images to detect products and count stock")
    System_Ext(roboflow, "Roboflow", "Datasets & Labeling Platform")
    System_Ext(aws, "AWS Cloud", "Hosting Environment (EKS, ECR)")

    Rel(storeManager, shelfWatch, "Uploads shelf images", "HTTPS/REST")
    Rel(shelfWatch, storeManager, "Returns stock counts & bounding boxes", "JSON")
    Rel(shelfWatch, aws, "Runs on", "EKS")
    Rel(shelfWatch, roboflow, "Downloads dataset updates", "API")
```

### Container View
The major software containers and their interactions.

```mermaid
C4Container
    title Container Diagram for ShelfWatch

    Person(user, "User", "API Client / Curl")

    System_Boundary(c1, "ShelfWatch Cluster") {
        Container(api, "Inference Service", "Python, FastAPI", "Handles HTTP requests, validation, and metrics")
        Container(model, "Model Manager", "ONNX Runtime", "High-performance CPU inference engine")
        Container(metrics, "Prometheus", "Go", "Scrapes metrics (latency, throughput)")
        Container(viz, "Grafana", "Go", "Dashboards for observability")
    }

    System_Ext(ecr, "AWS ECR", "Container Registry")
    System_Ext(s3, "S3 Bucket", "Model Registry (future)")

    Rel(user, api, "POST /predict", "HTTPS")
    Rel(api, model, "In-process call", "Python")
    Rel(metrics, api, "Scrapes /metrics", "HTTP")
    Rel(viz, metrics, "Queries PromQL", "HTTP")
    Rel(api, ecr, "Pulls image", "Docker")
```

### Component View (Inference Service)
Detailed breakdown of the `inference` module.

```mermaid
classDiagram
    class FastAPI_App {
        +POST /predict
        +GET /health
        +GZipMiddleware
        +PrometheusMiddleware
    }

    class ModelManager {
        -onnx_session: lnferenceSession
        -canvas: Valid NP Array
        +load(weights_path)
        +predict(image, conf_thresh)
        -_preprocess(image)
        -_postprocess(output)
        -_nms(boxes, scores)
    }

    class ThreadPool {
        +submit(fn, *args)
    }

    FastAPI_App --> ModelManager : Calls predict()
    FastAPI_App --> ThreadPool : Offloads CPU work
    ModelManager --> ONNX_Runtime : Executes Graph
```

## 2. Key Design Decisions

### Why ONNX Runtime on CPU?
- **Cost Efficiency**: GPU instances (g4dn.xlarge) cost ~$0.52/hr, while CPU instances (m7i-flex.large) cost ~$0.10/hr.
- **Latency**: For batch=1 inference, the overhead of data transfer to GPU often negates the compute speedup. ONNX Runtime with INT8 quantization achieves <300ms latency on CPU, meeting our SLO.

### Why Baking Weights into Docker Image?
- **Pro**: Simplicity. No need for complex volume mounts (EFS/EBS) or S3 sidecars during startup.
- **Pro**: Versioning. The Docker image tag `v1.0.0` strictly corresponds to model version `v1.0.0`.
- **Con**: Large image size (~150MB extra). Mitigated by layer caching in EKS.

### Observability Strategy
- **Golden Signals**: Latency, Traffic, Errors, Saturation.
- **Implementation**: Prometheus scrapes the `/metrics` endpoint every 15s.
- **Alerting**: Setting alerts on `error_rate > 1%` and `p99_latency > 500ms`.

## 3. Scale Plan
How we would scale from 1 req/s to 1,000 req/s:

1.  **Horizontal Pod Autoscaler (HPA)**: Scale pods based on CPU utilization (target 60%).
2.  **Async Queue**: Move from synchronous HTTP to an async worker pattern (SQS + Celery/k8s-jobs) to buffer bursts.
3.  **CDN / Edge**: Use CloudFront to cache static assets and potentially edge-compute for preprocessing.
4.  **Database**: Introduce DynamoDB to store detection results for historical analysis.

## 4. DevOps & GitOps Architecture

The system uses a **GitOps** approach for continuous delivery, minimizing manual operations and ensuring infrastructure-as-code consistency.

```mermaid
flowchart LR
    subgraph CI [Continuous Integration]
        Dev[Developer] -->|Push| Git[GitHub]
        Git -->|Trigger| GHA[GitHub Actions]
        GHA -->|Build & Push| ECR[ECR Registry]
    end

    subgraph CD [Continuous Deployment]
        Argo[ArgoCD in K8s]
        Argo -->|Watch| Git
        Argo -->|Sync| K8s[EKS Cluster]
        K8s -->|Pull Image| ECR
    end
```

### Components
1.  **Helm Chart**: All K8s resources (Deployment, Service, HPA, ConfigMap) are packaged in `charts/shelfwatch`.
2.  **ArgoCD**: Monitors the `main` branch. When `values.yaml` is updated (e.g., new image tag), ArgoCD automatically synchronizes the cluster.
3.  **Self-Healing**: ArgoCD detects manual changes to the cluster (drifts) and reverts them to match the Git state.
