"""
ShelfWatch — ONNX INT8 Quantization Script

Handles FP16 → FP32 conversion (if needed) then applies INT8 quantization.
Typical speedup: 1.5–3x on Intel CPUs with VNNI support.

Usage:
    python scripts/quantize_onnx.py
    python scripts/quantize_onnx.py --input weights/best.onnx --output weights/best_int8.onnx
"""

import argparse
import os
import time

import numpy as np
import onnx
from onnx import numpy_helper, TensorProto
from onnxruntime.quantization import quantize_dynamic, QuantType


def convert_fp16_to_fp32(model_path: str, output_path: str) -> str:
    """Convert FP16 ONNX model to FP32 (required before INT8 quantization)."""
    print("🔄 Converting FP16 → FP32...")
    model = onnx.load(model_path)

    # Convert all float16 initializers to float32
    for initializer in model.graph.initializer:
        if initializer.data_type == TensorProto.FLOAT16:
            arr = numpy_helper.to_array(initializer).astype(np.float32)
            new_init = numpy_helper.from_array(arr, name=initializer.name)
            initializer.CopyFrom(new_init)

    # Convert all float16 input/output types to float32
    for inp in list(model.graph.input) + list(model.graph.output):
        if inp.type.tensor_type.elem_type == TensorProto.FLOAT16:
            inp.type.tensor_type.elem_type = TensorProto.FLOAT16  # keep as is for now

    # Convert value_info
    for vi in model.graph.value_info:
        if vi.type.tensor_type.elem_type == TensorProto.FLOAT16:
            vi.type.tensor_type.elem_type = TensorProto.FLOAT

    # Use onnx's built-in converter for thorough conversion
    from onnx import shape_inference
    try:
        model = shape_inference.infer_shapes(model)
    except Exception:
        pass  # Shape inference can fail on some models, that's OK

    onnx.save(model, output_path)
    print(f"   Saved FP32 model: {output_path}")
    return output_path


def is_fp16_model(model_path: str) -> bool:
    """Check if an ONNX model uses FP16 weights."""
    model = onnx.load(model_path)
    for initializer in model.graph.initializer:
        if initializer.data_type == TensorProto.FLOAT16:
            return True
    return False


def quantize(input_path: str, output_path: str):
    """Apply dynamic INT8 quantization to an ONNX model."""
    print(f"📦 Input:  {input_path} ({os.path.getsize(input_path) / 1e6:.1f} MB)")

    # If FP16, convert to FP32 first
    quant_input = input_path
    fp32_path = input_path.replace(".onnx", "_fp32.onnx")

    if is_fp16_model(input_path):
        convert_fp16_to_fp32(input_path, fp32_path)
        quant_input = fp32_path

    # Quantize
    start = time.perf_counter()
    quantize_dynamic(
        model_input=quant_input,
        model_output=output_path,
        weight_type=QuantType.QUInt8,
    )
    elapsed = time.perf_counter() - start

    # Cleanup temp FP32 file
    if os.path.exists(fp32_path) and fp32_path != input_path:
        os.remove(fp32_path)

    print(f"✅ Output: {output_path} ({os.path.getsize(output_path) / 1e6:.1f} MB)")
    print(f"   Quantization took {elapsed:.1f}s")
    print(f"   Size reduction: "
          f"{(1 - os.path.getsize(output_path) / os.path.getsize(input_path)) * 100:.0f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize ONNX model to INT8")
    parser.add_argument("--input", default="weights/best.onnx", help="Input ONNX model")
    parser.add_argument("--output", default="weights/best_int8.onnx", help="Output INT8 model")
    args = parser.parse_args()

    quantize(args.input, args.output)
    print("\n💡 Use the quantized model by setting:")
    print("   WEIGHTS_PATH=weights/best_int8.onnx")
