# 🏪 ShelfWatch

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)
![ONNX](https://img.shields.io/badge/ONNX-Runtime-blueviolet?logo=onnx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/AWS-EKS-FF9900?logo=kubernetes&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**An automated retail shelf analysis pipeline.**
*Detects products. Counts stock. Scales automatically.*

[**View Live Demo**](http://a86b4f4c852b64526ae8c22a8b715100-2106448101.us-east-1.elb.amazonaws.com) • [**Architecture Docs**](docs/architecture.md)

</div>

---

## 🚀 Overview

**ShelfWatch** is a production-grade MLOps project designed to solve the problem of manual stock auditing in supermarkets. It deploys a fine-tuned **YOLOv8** object detection model as a scalable microservice.

Unlike typical notebook-only ML projects, ShelfWatch features a complete **DevOps/MLOps** lifecycle:
*   **Infrastructure as Code** (eksctl / CloudFormation)
*   **CI/CD Pipeline** (GitHub Actions)
*   **Observability** (Prometheus + Grafana)
*   **Cost Optimization** (ONNX + INT8 Quantization on CPU)

## 🏗️ Architecture

The system uses a **microservices architecture** deployed on **AWS EKS**.

```mermaid
graph LR
    User[Store Manager] -->|Upload Image| LB[Load Balancer]
    LB --> API[FastAPI Service]
    API -->|Inference| ONNX[ONNX Runtime (CPU)]
    API -->|Metrics| Prom[Prometheus]
    Prom -->|Viz| Grafana[Grafana Dashboard]
    
    subgraph "AWS EKS Cluster"
        API
        ONNX
        Prom
        Grafana
    end
```

> **See full design details in [docs/architecture.md](docs/architecture.md)** (C4 Model)

## ✨ Key Features

- **⚡ High-Performance Inference**: <300ms latency on CPU using ONNX Runtime with INT8 quantization.
- **☁️ Cloud-Native**: Containerized with Docker and orchestrated on Kubernetes (EKS).
- **📈 Auto-Scaling**: Horizontal Pod Autoscaler (HPA) reacts to CPU load to handle traffic spikes.
- **👀 Observability**: Real-time metrics for request latency, error rates, and inference throughput.
- **🛡️ Robust API**: FastAPI with Pydantic validation, structured logging, and health checks.

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Model** | YOLOv8 (Ultralytics) |
| **Optimization** | ONNX Runtime (INT8) |
| **API Framework** | FastAPI (Python 3.10) |
| **Data** | SKU-110K Dataset (via Roboflow) |
| **Containerization** | Docker (Multi-stage build) |
| **Orchestration** | AWS EKS (Kubernetes 1.31) |
| **Infrastructure** | eksctl, Bash/PowerShell |
| **Monitoring** | Prometheus, Grafana |

## ⚡ Quick Start

### 1. Local Development

```bash
# Clone
git clone https://github.com/<your-username>/ShelfWatch.git
cd ShelfWatch

# Install dependencies
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# Run Inference Server
uvicorn inference.app:app --host 0.0.0.0 --port 8000
```

### 2. AWS Production Deployment

Deploy the entire stack to AWS in one command:

```powershell
.\infra\aws\deploy.ps1
```

This script:
1.  Creates an ECR repository.
2.  Builds the Docker image with "baked-in" optimized weights.
3.  Provisions an EKS cluster (`m7i-flex.large` nodes).
4.  Deploys the Kubernetes manifests (Service, Deployment, HPA).

### 3. Run Demo

Verify the deployment with our demo script:

```powershell
# Target your AWS Load Balancer
$env:API_URL="http://<YOUR-LB-URL>"
python scripts/demo_predict.py scripts/shelf.jpg
```

## 📂 Project Structure

```
ShelfWatch/
├── dataset/            # Dataset configs & download scripts
├── docs/               # Architecture diagrams & documentation
├── inference/          # FastAPI application code
├── infra/              # IaC (AWS) & Kubernetes manifests
├── scripts/            # Utility scripts (demo, quantize, export)
├── tests/              # Pytest suite
└── training/           # YOLOv8 training logic
```

## 📜 License

MIT License.
