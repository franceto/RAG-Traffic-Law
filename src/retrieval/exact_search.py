import json
import re
import unicodedata
from src.config.settings import settings

STOP = {
    "xe", "may", "oto", "o", "to", "phat", "bao", "nhieu", "co", "bi",
    "khong", "la", "thi", "sao", "the", "nao", "muc", "tien", "hoi",
    "nguoi", "dieu", "khien", "can", "hoi", "ve"
}

QUESTION_PHRASES = [
    "phat bao nhieu",
    "bi phat bao nhieu",
    "muc phat",
    "co bi phat khong",
    "bi xu phat sao",
    "hinh phat la gi",
    "bao nhieu tien"
]

def strip_accents(text):
    text = str(text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")

def normalize(text):
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def detect_vehicle(text):
    q = normalize(text)

    if any(x in q for x in ["o to", "oto", "xe hoi", "xe con", "xe tai", "xe khach"]):
        return "car"

    if any(x in q for x in ["xe may", "mo to", "moto", "xe gan may", "sh", "wave", "vision"]):
        return "motorbike"

    if "xe dap" in q:
        return "bicycle"

    if "nguoi di bo" in q:
        return "pedestrian"

    return "unknown"

def vehicle_ok(query_vehicle, row):
    if query_vehicle == "unknown":
        return True

    row_vehicle = row.get("vehicle_group", "")

    if not row_vehicle:
        return False

    return row_vehicle == query_vehicle

def core_query(text):
    q = normalize(text)
    for p in QUESTION_PHRASES:
        q = q.replace(p, " ")
    return re.sub(r"\s+", " ", q).strip()

def tokens(text):
    return [t for t in normalize(text).split() if len(t) >= 2 and t not in STOP]

def load_chunks():
    with settings.chunk_file.open("r", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def load_mapping():
    p = settings.indexes_dir / "mapping_dictionary.json"
    if not p.exists():
        return {"entries": []}
    return json.loads(p.read_text(encoding="utf-8"))

def row_by_citation(rows):
    return {r.get("citation", ""): r for r in rows}

def make_item(row, score, reason):
    item = dict(row)
    item["score"] = float(score)
    item["retriever"] = "exact"
    item["exact_reason"] = reason
    item["source_query"] = ""
    return item

def exact_search(query, top_k=5):
    rows = load_chunks()
    mapping = load_mapping()
    by_cite = row_by_citation(rows)

    query_vehicle = detect_vehicle(query)
    q_norm = normalize(query)
    q_core = core_query(query)
    q_tokens = set(tokens(q_core))

    if len(q_core) < 8 or len(q_tokens) < 2:
        return []

    hits = []

    for e in mapping.get("entries", []):
        citation = e.get("citation", "")
        row = by_cite.get(citation)

        if not row:
            continue

        if not vehicle_ok(query_vehicle, row):
            continue

        phrase = e.get("legal_phrase", "")
        phrase_norm = normalize(phrase)
        phrase_tokens = set(tokens(phrase_norm))

        if not phrase_norm or not phrase_tokens:
            continue

        if phrase_norm in q_norm or phrase_norm in q_core:
            hits.append(make_item(row, 100000, "legal_phrase_in_query"))
            continue

        if q_core in phrase_norm and len(q_core) >= 12:
            hits.append(make_item(row, 95000, "query_in_legal_phrase"))
            continue

        overlap = len(q_tokens & phrase_tokens)
        recall = overlap / max(1, len(phrase_tokens))
        precision = overlap / max(1, len(q_tokens))

        if recall >= 0.85 and precision >= 0.45 and overlap >= 4:
            score = 80000 + overlap * 100
            hits.append(make_item(row, score, "high_token_overlap_mapping"))

    if hits:
        return sorted(hits, key=lambda x: x["score"], reverse=True)[:top_k]

    for row in rows:
        if not vehicle_ok(query_vehicle, row):
            continue

        content_norm = normalize(row.get("content", ""))

        if q_core in content_norm and len(q_core) >= 15:
            hits.append(make_item(row, 70000, "query_in_chunk_content"))
            continue

        c_tokens = set(tokens(content_norm))
        overlap = len(q_tokens & c_tokens)
        precision = overlap / max(1, len(q_tokens))

        if precision >= 0.9 and overlap >= 6:
            hits.append(make_item(row, 60000 + overlap * 50, "high_token_overlap_content"))

    return sorted(hits, key=lambda x: x["score"], reverse=True)[:top_k]
