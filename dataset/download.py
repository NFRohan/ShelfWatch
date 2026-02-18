"""
Download SKU-110K dataset from Roboflow in YOLO11 format (compatible with YOLOv8).

Usage:
    export ROBOFLOW_API_KEY="your_key_here"
    python dataset/download.py
"""

import os
from roboflow import Roboflow

API_KEY = os.environ.get("ROBOFLOW_API_KEY")
if not API_KEY:
    raise EnvironmentError(
        "Set ROBOFLOW_API_KEY environment variable. "
        "Get your key at https://app.roboflow.com/settings/api"
    )

rf = Roboflow(api_key=API_KEY)
project = rf.workspace("jacobs-workspace").project("sku-110k")
version = project.version(1)  # adjust version number as needed
dataset = version.download("yolov8", location="dataset")

print(f"✅ Dataset downloaded to: {dataset.location}")
