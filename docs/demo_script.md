# ShelfWatch — Demo Screencast Script

**Goal:** Record a 2–3 minute video showcasing the project for recruiters/interviewers.

**Preparation:**
1.  Open **VS Code** with `ShelfWatch` repo.
2.  Open **Terminal**.
3.  Open **Browser** to the AWS LoadBalancer URL (e.g., `http://.../health`).
4.  Open **Architecture Diagram** (`docs/architecture.md`) in preview mode.

---

## Scene 1: Introduction (30s)
*   **Visual:** Show the Architecture Diagram in VS Code.
*   **Script:**
    > "Hi, I'm [Your Name], and this is ShelfWatch — an automated shelf analysis system I built to detect products in dense retail environments."
    > "The system uses a YOLOv8 model fine-tuned on the SKU-110K dataset. It's deployed on AWS EKS with a fully automated CI/CD pipeline."
    > "Key features include:
    > 1.  **Optimized Inference**: ONNX Runtime with INT8 quantization for 3x speedup on CPU.
    > 2.  **Scalable Infrastructure**: Kubernetes HPA to handle traffic spikes.
    > 3.  **Observability**: Prometheus metrics for latency and drift detection."

## Scene 2: The Code (45s)
*   **Visual:** Switch to `inference/app.py` in VS Code.
*   **Action:** Scroll through the `predict` function.
*   **Script:**
    > "Here's the inference service built with FastAPI. It handles image uploads and runs preprocessing."
    > "I implemented a custom thread pool executor to prevent the CPU-bound inference from blocking the async event loop."
    > "The model itself is loaded via a singleton `ModelManager` (show `inference/model.py`) which abstracts the ONNX runtime session."

## Scene 3: Local Demo (45s)
*   **Visual:** Switch to Terminal.
*   **Action:** Run the demo script against `localhost`.
    ```powershell
    # Make sure local server is running in another tab: uvicorn inference.app:app ...
    python scripts/demo_predict.py scripts/shelf.jpg
    ```
*   **Script:**
    > "Let's see it in action locally. I'll send a high-resolution shelf image to the API."
    > (Wait for output)
    > "You can see it detected 357 products in just over 400ms. The response includes the bounding boxes and confidence scores."

## Scene 4: AWS Production Deployment (60s)
*   **Visual:** Switch to Browser (LoadBalancer URL / health endpoint) or Terminal.
*   **Action:** Run the demo script against the **AWS production URL**.
    ```powershell
    $env:API_URL="http://<YOUR_AWS_LB_URL>"
    python scripts/demo_predict.py scripts/shelf.jpg
    ```
*   **Script:**
    > "Now, let's look at the production deployment on AWS EKS."
    > "I set up an infrastructure-as-code pipeline using `eksctl` and Kubernetes manifests."
    > "Running the same test against the live cluster... (run script)... success."
    > "The request hit the Load Balancer, was routed to a pod on an `m7i-flex.large` node, and returned the result."
    > "This setup is production-ready, with liveness probes, rolling updates, and cost-effective auto-scaling."

## Conclusion (15s)
*   **Visual:** Back to Architecture Diagram or GitHub Repo README.
*   **Script:**
    > "ShelfWatch demonstrates an end-to-end MLOps workflow — from training and optimization to cloud-native deployment. Thanks for watching!"
