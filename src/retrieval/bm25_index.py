import pickle
from rank_bm25 import BM25Okapi
from src.config.settings import settings
from src.ingestion.parser import norm_text
import json
import re
import unicodedata

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def tokenize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [t for t in text.split() if len(t) >= 2]

def build_bm25_index():
    settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with settings.chunk_file.open("r", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]

    corpus = [
        tokenize(" ".join([
            x.get("citation", ""),
            x.get("fine_text", ""),
            x.get("content", "")
        ]))
        for x in rows
    ]

    bm25 = BM25Okapi(corpus)

    payload = {
        "rows": rows,
        "bm25": bm25
    }

    with settings.bm25_index_file.open("wb") as f:
        pickle.dump(payload, f)

    print("SAVED:", settings.bm25_index_file)
    print("CHUNKS:", len(rows))

if __name__ == "__main__":
    build_bm25_index()
