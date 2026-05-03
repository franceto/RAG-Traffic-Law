import pickle
import re
import unicodedata
from src.config.settings import settings

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def tokenize(text):
    text = normalize(text)
    return [t for t in text.split() if len(t) >= 2]

def load_bm25():
    with settings.bm25_index_file.open("rb") as f:
        return pickle.load(f)

def detect_vehicle(query):
    q = normalize(query)

    if any(x in q for x in ["o to", "oto", "xe hoi", "xe con", "xe tai", "xe khach"]):
        return "car"

    if any(x in q for x in ["xe may", "mo to", "moto", "xe gan may", "sh", "wave", "vision"]):
        return "motorbike"

    if "xe dap" in q:
        return "bicycle"

    if "nguoi di bo" in q:
        return "pedestrian"

    return ""

def query_has_highway(query):
    q = normalize(query)
    return "cao toc" in q or "duong cao toc" in q

def query_has_intersection(query):
    q = normalize(query)
    return "giao nhau" in q or "noi duong bo giao nhau" in q

def query_has_penalty(query):
    q = normalize(query)
    return any(x in q for x in ["phat", "xu phat", "bao nhieu", "muc phat"])

def row_text(row):
    return normalize(" ".join([
        row.get("citation", ""),
        row.get("fine_text", ""),
        row.get("content", "")
    ]))

def metadata_rerank_score(query, row):
    q = normalize(query)
    txt = row_text(row)
    score = 0.0

    q_vehicle = detect_vehicle(query)
    r_vehicle = row.get("vehicle_group", "")

    if q_vehicle:
        if r_vehicle == q_vehicle:
            score += 10.0
        elif r_vehicle:
            score -= 10.0

    if query_has_penalty(query):
        if row.get("fine_text"):
            score += 5.0
        else:
            score -= 20.0

    if not query_has_highway(query) and "cao toc" in txt:
        score -= 12.0

    if query_has_highway(query) and "cao toc" in txt:
        score += 8.0

    if query_has_intersection(query):
        if "noi duong bo giao nhau" in txt or "noi duong giao nhau" in txt:
            score += 8.0
        if "duong cao toc" in txt:
            score -= 8.0

    if "chuyen lan" in q:
        if "chuyen lan duong khong dung noi cho phep" in txt:
            score += 6.0
        if "cao toc" in txt and not query_has_highway(query):
            score -= 10.0

    if "su dung coi" in q or "bam coi" in q:
        if "su dung coi trong thoi gian tu 22 gio" in txt:
            score += 8.0

    return score

def search_bm25(query, top_k=5):
    payload = load_bm25()
    rows = payload["rows"]
    bm25 = payload["bm25"]

    scores = bm25.get_scores(tokenize(query))
    items = []

    for row, base_score in zip(rows, scores):
        if base_score <= 0:
            continue

        item = dict(row)
        item["bm25_score"] = float(base_score)
        item["rerank_score"] = metadata_rerank_score(query, row)
        item["score"] = item["bm25_score"] + item["rerank_score"]
        item["retriever"] = "bm25"
        items.append(item)

    items = sorted(items, key=lambda x: x["score"], reverse=True)
    return items[:top_k]
