# config.py
from pathlib import Path
PROGRAM_DIR = None  # will be set by wrapper at runtime

def get_program_dir() -> Path:
    # Fallback: if wrapper didn't set it, use this file's folder
    return Path(PROGRAM_DIR) if PROGRAM_DIR else Path(__file__).resolve().parent