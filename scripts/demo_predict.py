"""
ShelfWatch — Demo prediction script

Quick test to verify the inference API is working.

Usage:
    python scripts/demo_predict.py <image_path>
    python scripts/demo_predict.py            # uses a placeholder
"""

import sys
import time
import requests


import os

# Default to localhost, but allow override (e.g., AWS LB URL)
API_URL = os.getenv("API_URL", "http://localhost:8000")


def check_health():
    """Verify the API is up."""
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        data = r.json()
        print(f"🏥 Health: {data['status']} | Model: {data.get('model')} | Runtime: {data.get('runtime')}")
        return data["status"] == "healthy"
    except Exception as e:
        print(f"❌ API not reachable: {e}")
        return False


def predict(image_path: str, confidence: float = 0.25):
    """Send an image to /predict and print results."""
    print(f"\n📤 Sending: {image_path}")
    print(f"   Confidence threshold: {confidence}")

    with open(image_path, "rb") as f:
        start = time.perf_counter()
        r = requests.post(
            f"{API_URL}/predict",
            files={"image": (image_path, f, "image/jpeg")},
            params={"confidence": confidence},
            timeout=30,
        )
        total_ms = (time.perf_counter() - start) * 1000

    if r.status_code != 200:
        print(f"❌ Error {r.status_code}: {r.text}")
        return

    data = r.json()

    print("\n📊 Results:")
    print(f"   Products detected: {data['count']}")
    print(f"   Inference time:    {data['inference_ms']:.1f}ms (server)")
    print(f"   Round-trip time:   {total_ms:.1f}ms (total)")
    print(f"   Image size:        {data['image_size']['width']}x{data['image_size']['height']}")
    print(f"   Model:             {data.get('model', 'N/A')}")
    print(f"   Runtime:           {data.get('runtime', 'N/A')}")

    # Show top 5 detections
    if data["detections"]:
        print(f"\n   Top detections (showing {min(5, len(data['detections']))} of {len(data['detections'])}):")
        for det in data["detections"][:5]:
            bbox = det["bbox"]
            print(f"     • {det['class']} ({det['confidence']:.2%}) "
                  f"[{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")


def main():
    if not check_health():
        print("\n⚠️  Start the API first:")
        print("   uvicorn inference.app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("\nUsage: python scripts/demo_predict.py <path_to_shelf_image.jpg>")
        sys.exit(0)

    predict(image_path)


if __name__ == "__main__":
    main()
