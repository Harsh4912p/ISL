#!/bin/bash
set -e

echo "============================================================"
echo "🚀 Building ISL Sign Language Backend for Render Deployment"
echo "============================================================"

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# Check directory structure
if [ -d "backend" ]; then
    echo "📦 Installing requirements from backend/requirements.txt..."
    python -m pip install -r backend/requirements.txt
    cd backend
else
    echo "📦 Installing requirements from requirements.txt..."
    python -m pip install -r requirements.txt
fi

# Ensure necessary directories exist
mkdir -p uploads/videos models datasets

# Train / verify lightweight model during build time so it never blocks live traffic
echo "🧠 Training/verifying lightweight ISL detection model..."
python train_sign_detection_model.py

# Initialize database tables and signs
echo "🗄️ Initializing database tables and sign dataset..."
python init_db.py || true

echo "============================================================"
echo "✅ Build complete! System is ready to serve live traffic."
echo "============================================================"
