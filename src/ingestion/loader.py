from pathlib import Path
from bs4 import BeautifulSoup
from src.config.settings import settings

def read_html(path):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "lxml")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text("\n")

def read_txt(path):
    return path.read_text(encoding="utf-8", errors="ignore")

def load_raw_file(path):
    suffix = path.suffix.lower()

    if suffix in [".html", ".htm"]:
        return read_html(path)

    if suffix == ".txt":
        return read_txt(path)

    return ""

def get_raw_files():
    exts = ["*.html", "*.htm", "*.txt"]
    files = []

    for ext in exts:
        files.extend(settings.raw_dir.glob(ext))

    return sorted(files)

def extract_all():
    settings.processed_dir.mkdir(parents=True, exist_ok=True)

    files = get_raw_files()
    print("RAW_FILES:", len(files))

    for path in files:
        text = load_raw_file(path)
        out = settings.processed_dir / f"{path.stem}.txt"
        out.write_text(text, encoding="utf-8")

        print("INPUT:", path.name)
        print("OUTPUT:", out.name)
        print("CHARS:", len(text))
        print("-" * 60)