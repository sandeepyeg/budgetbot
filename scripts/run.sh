#!/usr/bin/env bash
#!/bin/bash
set -e

# Always ensure we’re at project root
cd "$(dirname "$0")/.."

# Add project root to PYTHONPATH
export PYTHONPATH=$(pwd)
set -euo pipefail
source .venv/bin/activate
python scripts/seed_categories.py
python -m app.bot.main
