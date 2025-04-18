#!/bin/bash

echo "🔧 Setting up your AI PR Reviewer environment..."

# Optional: create virtualenv
# python3 -m venv venv
# source venv/bin/activate

echo "📦 Installing required Python packages..."


# Upgrade pip inside the venv
python3.11 -m pip install --upgrade pip

# Install required packages
python3.11 -m pip install \
  openai==1.13.3 \
  httpx==0.27.0 \
  langchain==0.1.17 \
  langchain-openai \
  python-dotenv \
  rich \
  flask \
  flask_cors

echo "✅ Installation complete!"
echo "🧠 You can now run: python interactive_langchain_reviewer.py"
