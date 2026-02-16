"""
Re-export YOLO model from .pt to FP32 ONNX, then quantize to INT8.

Usage:
    pip install ultralytics onnx onnxruntime
    python scripts/export_and_quantize.py
"""

from ultralytics import YOLO

# Step 1: Export FP32 ONNX (no half!)
print("📦 Exporting best.pt → FP32 ONNX...")
model = YOLO("weights/best.pt")
model.export(format="onnx", imgsz=640, simplify=True, half=False)
print("✅ Exported: weights/best.onnx (FP32)\n")

# Step 2: Quantize to INT8
import os
import time
from onnxruntime.quantization import quantize_dynamic, QuantType

input_path = "weights/best.onnx"
output_path = "weights/best_int8.onnx"

print(f"🔧 Quantizing FP32 → INT8...")
print(f"   Input:  {input_path} ({os.path.getsize(input_path) / 1e6:.1f} MB)")

start = time.perf_counter()
quantize_dynamic(
    model_input=input_path,
    model_output=output_path,
    weight_type=QuantType.QUInt8,
)
elapsed = time.perf_counter() - start

print(f"✅ Output: {output_path} ({os.path.getsize(output_path) / 1e6:.1f} MB)")
print(f"   Took {elapsed:.1f}s")
print(f"   Size reduction: {(1 - os.path.getsize(output_path) / os.path.getsize(input_path)) * 100:.0f}%")
print(f"\n💡 Set WEIGHTS_PATH=weights/best_int8.onnx in docker-compose.yml")
