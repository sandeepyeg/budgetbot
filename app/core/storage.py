import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("data/receipts")

def ensure_storage_dir():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

def generate_receipt_path(user_id: int, expense_id: str, file_ext: str) -> Path:
    ensure_storage_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{expense_id}_{timestamp}{file_ext}"
    return BASE_DIR / filename
