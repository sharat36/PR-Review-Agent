#!/bin/bash

echo "🔧 Setting up your AI PR Reviewer environment..."

# Optional: create virtualenv
# python3 -m venv venv
# source venv/bin/activate

echo "📦 Installing required Python packages..."

pip install --upgrade pip

pip install \
  openai==1.13.3 \
  httpx==0.27.0 \
  langchain==0.1.17 \
  langchain-openai \
  python-dotenv \
  rich

echo "✅ Installation complete!"
echo "🧠 You can now run: python interactive_langchain_reviewer.py"
