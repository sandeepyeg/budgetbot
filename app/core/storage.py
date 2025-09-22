import os
from pathlib import Path
from datetime import datetime
from PIL import Image

BASE_DIR = Path("data/receipts")

def ensure_storage_dir(year: int, month: int) -> Path:
    path = BASE_DIR / str(year) / f"{month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path

def generate_receipt_path(user_id: int, expense_id: str, file_ext: str = ".jpg") -> Path:
    now = datetime.now()
    folder = ensure_storage_dir(now.year, now.month)
    filename = f"{user_id}_{expense_id}{file_ext}"
    return folder / filename

def optimize_and_save(image_path: Path, output_path: Path, max_width: int = 1280, quality: int = 80):
    """
    Resize/compress image while keeping good readability.
    """
    img = Image.open(image_path)
    # Resize if wider than max_width (keep aspect ratio)
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(float(img.height) * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    # Save optimized JPEG
    img.save(output_path, "JPEG", optimize=True, quality=quality)
    return output_path
