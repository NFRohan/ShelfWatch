"""
ShelfWatch — FastAPI Inference Service

Serves YOLO11 model via ONNX Runtime for dense product detection.
No PyTorch dependency — lightweight CPU-only deployment.
Includes Prometheus metrics for observability.

Optimizations:
  - orjson for fast JSON serialization
  - GZip middleware for compressed responses
  - Thread pool for non-blocking inference
  - Model warmup on startup

Usage:
    uvicorn inference.app:app --host 0.0.0.0 --port 8000

Environment:
    WEIGHTS_PATH    Path to model weights (default: weights/best.onnx)
    CONF_THRESH     Confidence threshold (default: 0.25)
    IMG_SIZE        Inference image size (default: 640)
    MODEL_NAME      Model name for metrics labels (default: yolo11l)
"""

import asyncio
import io
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial

import orjson
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from PIL import Image
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.requests import Request
from starlette.responses import Response, FileResponse
from starlette.staticfiles import StaticFiles

from inference.model import ModelManager

logger = logging.getLogger("shelfwatch")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
WEIGHTS_PATH = os.environ.get("WEIGHTS_PATH", "weights/best.onnx")
CONFIDENCE_THRESHOLD = float(os.environ.get("CONF_THRESH", "0.25"))
IMG_SIZE = int(os.environ.get("IMG_SIZE", "640"))
MAX_IMAGE_SIZE_MB = 10
MODEL_NAME = os.environ.get("MODEL_NAME", "yolo11l")

# Thread pool for CPU inference (prevents blocking the async event loop)
_executor = ThreadPoolExecutor(max_workers=2)

# ──────────────────────────────────────────────
# Prometheus Metrics
# ──────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "shelfwatch_requests_total",
    "Total inference requests",
    ["status"],
)
INFERENCE_LATENCY = Histogram(
    "shelfwatch_inference_seconds",
    "Model inference latency in seconds",
    buckets=[0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.8, 1.0, 2.0, 5.0],
)
DETECTION_COUNT = Histogram(
    "shelfwatch_detections_per_image",
    "Number of detections per image",
    buckets=[0, 10, 25, 50, 100, 150, 200, 300, 500],
)
IN_FLIGHT = Gauge(
    "shelfwatch_in_flight_requests",
    "Number of currently processing requests",
)
MODEL_INFO = Gauge(
    "shelfwatch_model_info",
    "Model metadata",
    ["model_name", "weights_path", "runtime"],
)

# ──────────────────────────────────────────────
# App lifecycle
# ──────────────────────────────────────────────
model_manager = ModelManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model and warmup on startup."""
    logger.info("Loading model from %s", WEIGHTS_PATH)
    model_manager.load(WEIGHTS_PATH)
    model_manager.warmup(imgsz=IMG_SIZE)
    MODEL_INFO.labels(
        model_name=MODEL_NAME,
        weights_path=WEIGHTS_PATH,
        runtime=model_manager.runtime,
    ).set(1)
    logger.info("🚀 ShelfWatch inference ready (runtime=%s)", model_manager.runtime)
    yield
    _executor.shutdown(wait=False)
    logger.info("Shutdown complete")


app = FastAPI(
    title="ShelfWatch Inference API",
    description="Dense product detection on retail shelf images using YOLO11 + ONNX",
    version="0.3.0",
    lifespan=lifespan,
)

# GZip responses > 500 bytes (detection arrays can be large)
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve UI
if os.path.exists("ui"):
    app.mount("/static", StaticFiles(directory="ui"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("ui/index.html")


# ──────────────────────────────────────────────
# JSON helper (orjson is ~10x faster than stdlib json)
# ──────────────────────────────────────────────
class ORJSONResponse(Response):
    media_type = "application/json"

    def render(self, content) -> bytes:
        return orjson.dumps(content)


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@app.get("/health", response_class=ORJSONResponse)
def health():
    """Health check for k8s liveness/readiness probes."""
    return {
        "status": "healthy",
        "model_loaded": model_manager.is_loaded,
        "runtime": model_manager.runtime,
        "model": MODEL_NAME,
    }


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/predict", response_class=ORJSONResponse)
async def predict(
    request: Request,
    image: UploadFile = File(...),
    confidence: float = Query(default=None, ge=0.01, le=1.0),
):
    """
    Run dense product detection on an uploaded shelf image.

    Returns bounding boxes, confidence scores, class names,
    detection count, and inference latency.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    IN_FLIGHT.inc()

    try:
        conf = confidence or CONFIDENCE_THRESHOLD

        # ── Validate ──
        if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
            REQUEST_COUNT.labels(status="error_format").inc()
            raise HTTPException(400, "Unsupported format. Use JPEG, PNG, or WebP.")

        contents = await image.read()
        if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            REQUEST_COUNT.labels(status="error_size").inc()
            raise HTTPException(400, f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit.")

        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
        except Exception:
            REQUEST_COUNT.labels(status="error_decode").inc()
            raise HTTPException(400, "Could not decode image.")

        # ── Inference (in thread pool to not block event loop) ──
        loop = asyncio.get_running_loop()
        start = time.perf_counter()
        detections = await loop.run_in_executor(
            _executor,
            partial(model_manager.predict, img, imgsz=IMG_SIZE, conf=conf),
        )
        latency = time.perf_counter() - start

        logger.info(
            "req=%s detections=%d latency=%.1fms size=%dx%d",
            request_id, len(detections), latency * 1000, img.width, img.height,
        )

        # ── Record metrics ──
        INFERENCE_LATENCY.observe(latency)
        DETECTION_COUNT.observe(len(detections))
        REQUEST_COUNT.labels(status="success").inc()

        return {
            "detections": detections,
            "count": len(detections),
            "inference_ms": round(latency * 1000, 2),
            "image_size": {"width": img.width, "height": img.height},
            "model": MODEL_NAME,
            "runtime": model_manager.runtime,
        }

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(status="error_internal").inc()
        raise HTTPException(500, f"Inference failed: {str(e)}")
    finally:
        IN_FLIGHT.dec()
