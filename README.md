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

[**Live Demo UI**](http://a86b4f4c852b64526ae8c22a8b715100-2106448101.us-east-1.elb.amazonaws.com) • [**Grafana Dashboard**](http://aa7f24b6fcb1840baa60271925a86de9-1362079785.us-east-1.elb.amazonaws.com) • [**Architecture Docs**](docs/architecture.md)

</div>

---

## 🚀 Overview

**ShelfWatch** is a production-grade MLOps project designed to solve the problem of manual stock auditing in supermarkets. It deploys a fine-tuned **YOLOv8** object detection model as a scalable microservice on AWS EKS.

![ShelfWatch Demo UI](./images/UI.png)

Unlike typical notebook-ML projects, ShelfWatch features a complete **production lifecycle**:
*   **Infrastructure as Code**: Automated provisioning via `eksctl` and `kubectl`.
*   **Performance Optimization**: 74% model size reduction and <500ms latency via INT8 quantization.
*   **Full Observability**: Live Prometheus metrics visualized in a professional Grafana dashboard.
*   **Auto-Scaling**: Horizontal Pod Autoscaler (HPA) that scales pods based on real-time traffic.

## 🏗️ Architecture

The system uses a **microservices architecture** deployed on **AWS EKS**, leveraging a managed Load Balancer (ELB) to handle incoming traffic and a sidecar-style observability stack.

```mermaid
graph TD
    User[Store Manager] -->|Upload Image| LB1[API Load Balancer]
    LB1 --> API[FastAPI Inference Service]
    API -->|Predict| ONNX[ONNX Runtime (CPU INT8)]
    
    API -->|Expose /metrics| Prom[Prometheus]
    Prom -->|Query| Grafana[Grafana Dashboard]
    Grafana -->|Public Exposure| LB2[Grafana Load Balancer]
    
    subgraph "AWS EKS Cluster"
        API
        ONNX
        Prom
        Grafana
    end
    
    User -->|View Analytics| LB2
```

## ✨ Key Features

- **⚡ High-Performance Inference**: Sub-500ms latency on CPU by converting YOLOv8 to **ONNX INT8**.
- **📈 Cloud-Native Observability**: Custom dashboard tracking tail latency (p99), CPU/RAM, and model drift.
- **🎨 Interactive UI**: Single-page web app with real-time Canvas visualization of detections.
- **☁️ Production-Ready IaC**: Complete `deploy.ps1` and `teardown.ps1` scripts for automated lifecycle management.
- **🛡️ Scalable Infrastructure**: Kubernetes-native scaling using HPA and readiness/liveness probes.

## 📊 Observability

ShelfWatch doesn't just predict; it monitors. The built-in Grafana dashboard provides real-time insights:

![ShelfWatch Analytics](./images/analytics.png)

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Model** | YOLOv8 (Ultralytics) |
| **Optimization** | ONNX Runtime (INT8 Dynamic Quantization) |
| **API Framework** | FastAPI (Python) |
| **Frontend** | Vanilla JS / HTML5 / Canvas |
| **Infrastructure** | AWS EKS, Load Balancer, ECR |
| **Monitoring** | Prometheus, Grafana |

## ⚡ Quick Start

### 1. Local Development (Docker)

Run the entire stack locally with a single command:

```bash
docker compose up --build
```
Access the **Demo UI** at `http://localhost:8000` and **Grafana** at `http://localhost:3000`.

### 2. AWS Production Deployment

Deploy to AWS EKS (m7i-flex clusters):

```powershell
.\infra\aws\deploy.ps1
```

### 3. Run Demo Script

```powershell
$env:API_URL="http://<YOUR-LB-URL>"
python scripts/demo_predict.py scripts/shelf.jpg
```

## 📂 Project Structure

```
ShelfWatch/
├── docs/               # Architecture diagrams (C4 Model)
├── images/             # Documentation screenshots
├── inference/          # FastAPI App & Model Logic
├── infra/              # Kubernetes & AWS IaC
├── scripts/            # Quantization & Model Export
├── tests/              # API Unit Tests
└── ui/                 # Frontend Static Assets
```

## 📜 License

MIT License.

