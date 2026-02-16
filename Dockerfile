# ──────────────────────────────────────────────
# ShelfWatch — CPU ONNX Inference Container
# Lightweight: no PyTorch, no CUDA, no ultralytics
# Final image: ~200MB vs ~3GB+ with PyTorch
# ──────────────────────────────────────────────

FROM python:3.10-slim

WORKDIR /app

# Install Python deps (no build stage needed — no compiled packages)
COPY requirements-inference.txt .
RUN pip install --no-cache-dir -r requirements-inference.txt

# Copy application code
COPY inference/ ./inference/

# Weights are mounted at deploy time
# COPY weights/ ./weights/

# Run as non-root user (security best practice for k8s)
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "inference.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
