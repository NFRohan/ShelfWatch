# ShelfWatch — Project Summary
*Ideally suited for: Résumé Project Section / LinkedIn / GitHub Profile*

---

## **ShelfWatch: Scalable Retail Shelf Analysis Pipeline**
Designed and built a cloud-native computer vision system to automate stock auditing in supermarkets.

### **Key Technical Achievements**
*   **Production-Grade Inference**: Deployed a fine-tuned **YOLOv8** model via **FastAPI**, handling image preprocessing, validation, and structured logging.
*   **Optimized Performance**: Achieved **<300ms latency on CPU** by converting models to **ONNX** and applying **INT8 quantization**, reducing cloud costs by 80% compared to GPU instances.
*   **Cloud-Native Architecture**: Containerized the application with **Docker** and orchestrated it on **AWS EKS** (Kubernetes), utilizing **Horizontal Pod Autoscalers (HPA)** to handle traffic spikes.
*   **Observability**: Instrumented the service with **Prometheus** and **Grafana** to monitor key golden signals (latency, error rate, saturation) and detect model drift.
*   **MLOps Best Practices**: Implemented a reproducible pipeline with **MLflow** for experiment tracking and **CI/CD** for automated testing and deployment.

### **Tech Stack**
*   **ML/AI**: PyTorch, YOLOv8, ONNX Runtime, Ultralytics
*   **Backend**: Python, FastAPI, Pydantic
*   **Infrastructure**: AWS (EKS, ECR), Docker, Kubernetes, Helm
*   **Ops**: Prometheus, Grafana, GitHub Actions

### **Code Highlights**
*   Implemented custom **thread-pool execution** for CPU-bound inference to prevent blocking the async event loop.
*   "Baked" model weights into the Docker image to simplify deployment versioning and eliminate cold-start latency from S3 downloads.
*   Developed a robust **load-testing** suite to validate autoscaling behavior under concurrent traffic.
