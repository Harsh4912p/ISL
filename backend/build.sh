#!/bin/bash
set -e

echo "============================================================"
echo "🚀 Building ISL Sign Language Backend (Subdirectory build)"
echo "============================================================"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

mkdir -p uploads/videos models datasets

echo "🧠 Training/verifying lightweight ISL detection model..."
python train_sign_detection_model.py

echo "🗄️ Initializing database tables and sign dataset..."
python init_db.py || true

echo "============================================================"
echo "✅ Build complete!"
echo "============================================================"
