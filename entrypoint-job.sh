#!/bin/bash
set -e

if [ ! -f "/app/config/config.yaml" ] || [ ! -f "/app/config/frequency_words.txt" ]; then
    echo "❌ config files missing"
    exit 1
fi

echo "🔄 crawling..."
python -m trendradar

echo "📤 uploading HTML to GCS..."
python /app/upload_html.py

echo "✅ done"
