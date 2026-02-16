"""
ShelfWatch — Lightweight ONNX Model Manager

Pure ONNX Runtime inference — no PyTorch, no ultralytics.
Designed for CPU-only deployment (m7i-flex / c7i).

Optimizations:
  - Graph-level ONNX optimizations (constant folding, node fusion)
  - Memory pattern optimization
  - Tuned thread count for m7i-flex (2 vCPU)
  - Pre-allocated numpy buffers for preprocessing
"""

import numpy as np
import onnxruntime as ort
from PIL import Image


class ModelManager:
    """Lightweight ONNX-only inference manager."""

    def __init__(self):
        self._session: ort.InferenceSession | None = None
        self._runtime = "none"
        self._input_name: str = ""
        self._imgsz: int = 640
        self._class_names: list[str] = ["objects"]  # SKU-110K single class
        # Pre-allocated canvas for preprocessing (reuse across requests)
        self._canvas: np.ndarray | None = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    @property
    def runtime(self) -> str:
        return self._runtime

    def load(self, weights_path: str):
        """Load ONNX model with optimized CPU session options."""
        import os

        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Model weights not found at '{weights_path}'. "
                "Download best.onnx and place in weights/ directory."
            )

        sess_options = ort.SessionOptions()

        # ── Graph optimizations ──
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True

        # ── Thread tuning for m7i-flex.large (2 vCPU) ──
        # intra = parallelism within a single op (matmul, conv)
        # inter = parallelism across independent ops
        cpu_count = os.cpu_count() or 2
        sess_options.intra_op_num_threads = cpu_count
        sess_options.inter_op_num_threads = max(1, cpu_count // 2)

        # ── Execution mode ──
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        self._session = ort.InferenceSession(
            weights_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        # Cache input metadata
        input_meta = self._session.get_inputs()[0]
        self._input_name = input_meta.name
        self._imgsz = input_meta.shape[-1] if input_meta.shape[-1] else 640

        # Pre-allocate canvas
        self._canvas = np.full((self._imgsz, self._imgsz, 3), 114, dtype=np.uint8)

        self._runtime = "onnx-cpu"

        print(f"✅ ONNX model loaded: {weights_path}")
        print(f"   Input: {self._input_name} {input_meta.shape}")
        print(f"   Threads: intra={sess_options.intra_op_num_threads}, "
              f"inter={sess_options.inter_op_num_threads}")
        print(f"   Providers: {self._session.get_providers()}")

    def warmup(self, imgsz: int = 640):
        """Run a dummy inference to warm up the model (JIT, memory allocation)."""
        if not self.is_loaded:
            return
        dummy = Image.new("RGB", (imgsz, imgsz), color=(114, 114, 114))
        self.predict(dummy, imgsz=imgsz, conf=0.99)
        print("✅ Model warmed up")

    def predict(
        self,
        image: Image.Image,
        imgsz: int = 640,
        conf: float = 0.25,
    ) -> list[dict]:
        """
        Run inference and return parsed detections.

        Preprocessing: letterbox resize → normalize → NCHW
        Postprocessing: confidence filter → NMS → scale boxes back
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        orig_w, orig_h = image.size

        # ── Preprocess ──
        img_array, ratio, pad_w, pad_h = self._preprocess(image, imgsz)

        # ── Inference ──
        outputs = self._session.run(None, {self._input_name: img_array})

        # ── Postprocess ──
        detections = self._postprocess(
            outputs[0], conf, orig_w, orig_h, ratio, pad_w, pad_h
        )

        return detections

    def _preprocess(
        self, image: Image.Image, imgsz: int
    ) -> tuple[np.ndarray, float, float, float]:
        """Letterbox resize, normalize, convert to NCHW float32."""
        orig_w, orig_h = image.size

        # Calculate letterbox resize
        ratio = min(imgsz / orig_w, imgsz / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        pad_w = (imgsz - new_w) / 2
        pad_h = (imgsz - new_h) / 2

        # Resize image
        resized = image.resize((new_w, new_h), Image.BILINEAR)

        # Reuse pre-allocated canvas (avoids allocation per request)
        canvas = self._canvas.copy() if self._canvas is not None else \
            np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)

        top = int(pad_h)
        left = int(pad_w)
        canvas[top : top + new_h, left : left + new_w] = np.array(resized)

        # Normalize + transpose in one step (HWC → CHW, uint8 → float32)
        img_float = canvas.astype(np.float32, copy=False)
        img_float *= (1.0 / 255.0)
        img_batch = np.ascontiguousarray(
            img_float.transpose(2, 0, 1)[np.newaxis, ...]
        )

        return img_batch, ratio, pad_w, pad_h

    def _postprocess(
        self,
        output: np.ndarray,
        conf_thresh: float,
        orig_w: int,
        orig_h: int,
        ratio: float,
        pad_w: float,
        pad_h: float,
    ) -> list[dict]:
        """
        Parse YOLO ONNX output into detections.

        YOLO11 output shape: [1, 5, num_boxes] for single class
        where 5 = [x_center, y_center, width, height, class_conf]
        """
        # Transpose if needed: [1, 5, N] → [1, N, 5]
        if output.shape[1] < output.shape[2]:
            output = output.transpose(0, 2, 1)

        predictions = output[0]  # Remove batch dim → [N, 5]

        # ── Fast confidence filter (vectorized) ──
        scores = predictions[:, 4]
        mask = scores >= conf_thresh
        if not np.any(mask):
            return []

        filtered = predictions[mask]
        filtered_scores = scores[mask]

        # ── Convert xywh → xyxy (vectorized) ──
        half_w = filtered[:, 2] * 0.5
        half_h = filtered[:, 3] * 0.5
        boxes = np.column_stack([
            filtered[:, 0] - half_w,  # x1
            filtered[:, 1] - half_h,  # y1
            filtered[:, 0] + half_w,  # x2
            filtered[:, 1] + half_h,  # y2
        ])

        # ── NMS ──
        keep = self._nms(boxes, filtered_scores, iou_threshold=0.45)
        boxes = boxes[keep]
        final_scores = filtered_scores[keep]

        # ── Scale back to original image coordinates (vectorized) ──
        boxes[:, [0, 2]] = np.clip((boxes[:, [0, 2]] - pad_w) / ratio, 0, orig_w)
        boxes[:, [1, 3]] = np.clip((boxes[:, [1, 3]] - pad_h) / ratio, 0, orig_h)

        # ── Build result list ──
        class_name = self._class_names[0]
        detections = [
            {
                "class": class_name,
                "confidence": round(float(final_scores[i]), 4),
                "bbox": [round(float(c), 2) for c in boxes[i]],
            }
            for i in range(len(boxes))
        ]

        return detections

    @staticmethod
    def _nms(
        boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45
    ) -> list[int]:
        """Non-Maximum Suppression (pure numpy, vectorized)."""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))

            if order.size == 1:
                break

            rest = order[1:]
            xx1 = np.maximum(x1[i], x1[rest])
            yy1 = np.maximum(y1[i], y1[rest])
            xx2 = np.minimum(x2[i], x2[rest])
            yy2 = np.minimum(y2[i], y2[rest])

            intersection = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
            iou = intersection / (areas[i] + areas[rest] - intersection)

            order = rest[iou <= iou_threshold]

        return keep
