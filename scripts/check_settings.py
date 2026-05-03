import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.settings import settings

print("PROJECT_ROOT:", settings.project_root)
print("RAW_DIR:", settings.raw_dir)
print("PROCESSED_DIR:", settings.processed_dir)
print("CHUNKS_DIR:", settings.chunks_dir)
print("INDEXES_DIR:", settings.indexes_dir)
print("CHUNK_FILE:", settings.chunk_file)